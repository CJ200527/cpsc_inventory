"""crud_inventory.py — Live Inventory Ledger (finalized schema)
Reads products.current_stock (live ledger, not static quantity). Provides get_inventory_summary() and get_inventory_items().
No DDL in this module — schema is finalized (products, no supplier table).
"""

from db import get_db_connection

def _stock_expr():
    return "COALESCE(p.current_stock, p.quantity, 0)"

def get_inventory_summary():
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        stock_expr = _stock_expr()
        cur.execute("SELECT COUNT(*) AS total FROM products")
        total_unique = cur.fetchone()['total'] or 0
        cur.execute(f"""
            SELECT
                {stock_expr} AS cur_stock,
                COALESCE(p.reorder_level, 10) AS reorder_lvl,
                p.price AS price
            FROM products p
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
        stock_expr = _stock_expr()
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
                COALESCE(p.reorder_level, 10) AS reorder_level,
                ({stock_expr} * p.price) AS total_value
            FROM products p
            WHERE 1=1
        """
        params=[]
        if search_query:
            pat=f"%{search_query}%"
            sql += """ AND (
                p.product_name LIKE %s OR p.category LIKE %s OR p.details LIKE %s
                OR p.unit LIKE %s OR p.product_id LIKE %s
            )"""
            params.extend([pat]*5)
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
            r['supplier_name'] = ""
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
        cur.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category ASC")
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
