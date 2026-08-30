from db import get_db_connection

def _ensure_inventory_schema(cursor):
    """Ensure inventory table and Products reorder_level / current_stock exist."""
    # Ensure Products has current_stock and reorder_level
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'current_stock'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE Products ADD COLUMN current_stock INT DEFAULT 0")
            cursor.execute("UPDATE Products SET current_stock = quantity WHERE quantity IS NOT NULL")
    except Exception:
        pass
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'reorder_level'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE Products ADD COLUMN reorder_level INT DEFAULT 10")
            cursor.execute("UPDATE Products SET reorder_level = 10 WHERE reorder_level IS NULL")
    except Exception:
        pass
    # Create inventory ledger table (central real-time snapshot) if not exists
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                inventory_id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT NOT NULL UNIQUE,
                current_stock INT DEFAULT 0,
                reorder_level INT DEFAULT 10,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES Products(product_id) ON DELETE CASCADE
            )
        """)
    except Exception:
        pass
    # Sync inventory from Products (keep ledger in sync)
    try:
        cursor.execute("""
            INSERT INTO inventory (product_id, current_stock, reorder_level)
            SELECT p.product_id, COALESCE(p.current_stock, p.quantity, 0), COALESCE(p.reorder_level, 10)
            FROM Products p
            ON DUPLICATE KEY UPDATE
                current_stock = VALUES(current_stock),
                reorder_level = VALUES(reorder_level)
        """)
    except Exception:
        pass
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'current_stock'")
        has_cs = cursor.fetchone() is not None
        cursor.execute("SHOW COLUMNS FROM inventory LIKE 'current_stock'")
        has_inv = cursor.fetchone() is not None
        if has_cs and has_inv:
            cursor.execute("""
                UPDATE inventory i
                JOIN Products p ON i.product_id = p.product_id
                SET i.current_stock = COALESCE(p.current_stock, p.quantity, 0)
                WHERE i.current_stock != COALESCE(p.current_stock, p.quantity, 0)
            """)
    except Exception:
        pass

def _stock_column(cursor):
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'current_stock'")
        if cursor.fetchone():
            return "COALESCE(p.current_stock, p.quantity, 0)"
    except Exception:
        pass
    return "COALESCE(p.quantity, 0)"

def get_inventory_summary():
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        _ensure_inventory_schema(cur)
        conn.commit()
        stock_expr = _stock_column(cur)
        # Determine reorder expr
        try:
            cur.execute("SHOW COLUMNS FROM Products LIKE 'reorder_level'")
            has_reorder = cur.fetchone() is not None
        except Exception:
            has_reorder=False
        reorder_expr = "COALESCE(p.reorder_level, 10)" if has_reorder else "10"
        # Total unique
        cur.execute("SELECT COUNT(*) AS total FROM Products")
        total_unique = cur.fetchone()['total'] or 0
        # Low/out counts and asset value need per-row evaluation
        cur.execute(f"""
            SELECT 
                {stock_expr} AS cur_stock,
                {reorder_expr} AS reorder_lvl,
                p.price AS price
            FROM Products p
        """)
        rows=cur.fetchall()
        low=out=in_stock=0
        asset=0.0
        for r in rows:
            stock = int(r['cur_stock'] or 0)
            reorder = int(r['reorder_lvl'] or 10)
            price = float(r['price'] or 0)
            asset += stock * price
            if stock == 0:
                out+=1
            elif 0 < stock <= reorder:
                low+=1
            if stock > 0:
                in_stock+=1
        return {
            "total_unique": total_unique,
            "total_asset_value": asset,
            "low_stock_count": low,
            "out_of_stock_count": out,
            "in_stock_count": in_stock
        }
    except Exception as e:
        print(f"[get_inventory_summary] {e}")
        return {"total_unique":0,"total_asset_value":0,"low_stock_count":0,"out_of_stock_count":0,"in_stock_count":0}
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def get_inventory_items(search_query="", category_filter="All", stock_status="All"):
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        _ensure_inventory_schema(cur)
        stock_expr = _stock_column(cur)
        try:
            cur.execute("SHOW COLUMNS FROM Products LIKE 'reorder_level'")
            has_reorder = cur.fetchone() is not None
        except Exception:
            has_reorder=False
        reorder_expr = "COALESCE(p.reorder_level, 10)" if has_reorder else "10"
        sql = f"""
            SELECT 
                p.product_id,
                p.product_name,
                p.category,
                p.details,
                p.unit,
                p.size,
                p.price,
                {stock_expr} AS current_stock,
                {reorder_expr} AS reorder_level,
                ({stock_expr} * p.price) AS total_value,
                s.supplier_name
            FROM Products p
            LEFT JOIN Supplier s ON p.supplier_id = s.id
            WHERE 1=1
        """
        params=[]
        if search_query:
            pat=f"%{search_query}%"
            sql += """ AND (
                p.product_name LIKE %s OR p.category LIKE %s OR p.details LIKE %s 
                OR p.unit LIKE %s OR s.supplier_name LIKE %s OR p.product_id LIKE %s
            )"""
            params.extend([pat]*6)
        if category_filter and category_filter != "All":
            sql += " AND p.category = %s"
            params.append(category_filter)
        sql += " ORDER BY p.product_id DESC"
        cur.execute(sql, tuple(params))
        rows=cur.fetchall()
        # Apply stock_status filter in Python (safer, avoids complex HAVING)
        if stock_status != "All":
            filtered=[]
            for r in rows:
                stock=int(r['current_stock'] or 0)
                reorder=int(r['reorder_level'] or 10)
                if stock_status=="In Stock" and stock > reorder:
                    filtered.append(r)
                elif stock_status=="Low Stock" and 0 < stock <= reorder:
                    filtered.append(r)
                elif stock_status=="Out of Stock" and stock==0:
                    filtered.append(r)
            rows=filtered
        # Normalize types
        for r in rows:
            try: r['current_stock']=int(r['current_stock'] or 0)
            except: r['current_stock']=0
            try: r['reorder_level']=int(r['reorder_level'] or 10)
            except: r['reorder_level']=10
            try: r['price']=float(r['price'] or 0)
            except: r['price']=0.0
            try: r['total_value']=float(r['total_value'] or 0)
            except: r['total_value']=0.0
            # derive status
            if r['current_stock']==0:
                r['stock_status']="Out of Stock"
            elif r['current_stock'] <= r['reorder_level']:
                r['stock_status']="Low Stock"
            else:
                r['stock_status']="In Stock"
        return rows
    except Exception as e:
        print(f"[get_inventory_items] {e}")
        return []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def get_inventory_categories():
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute("SELECT DISTINCT category FROM Products WHERE category IS NOT NULL AND category != '' ORDER BY category ASC")
        return [row[0] for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass
