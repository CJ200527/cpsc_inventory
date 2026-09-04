"""crud_products.py — Product Catalog (finalized schema)
Products table has NO supplier linkage (supplier captured as free-text
deliveries.supplier_name). No DDL in this module.
"""

from db import get_db_connection


def get_all_products_filtered(search_query="", date_filter="All", custom_date=""):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT p.product_id,
                   p.product_name, p.category, p.details, p.unit, p.size, p.price,
                   p.quantity, p.current_stock, p.created_at
            FROM products p
            WHERE 1=1
        """
        params = []
        if search_query:
            pat = f"%{search_query}%"
            sql += """ AND (
                p.product_id LIKE %s OR p.product_name LIKE %s OR p.category LIKE %s
                OR p.details LIKE %s OR p.unit LIKE %s OR p.size LIKE %s
            )"""
            params.extend([pat] * 6)
        if date_filter == "Today":
            sql += " AND DATE(p.created_at) = CURDATE()"
        elif date_filter == "Last Month":
            sql += " AND p.created_at >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
        elif date_filter == "Last Year":
            sql += " AND p.created_at >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)"
        elif date_filter == "Custom" and custom_date:
            sql += " AND DATE(p.created_at) = %s"
            params.append(custom_date)
        sql += " ORDER BY p.product_id DESC;"
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    except Exception as err:
        print(f"[get_all_products] DB error: {err}")
        try:
            if cursor: cursor.close()
            if conn: conn.close()
        except: pass
        return []
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass

get_all_products = get_all_products_filtered


def get_suppliers_list():
    """Deprecated: supplier table removed (supplier is free-text on deliveries)."""
    return []


def add_product(supplier_id=None, product_name="", category="General", details="", unit="pcs", size="N/A", price=0.00, quantity=0, **kwargs):
    """supplier_id ignored (no supplier column in finalized products table)."""
    # Backwards compat: allow add_product(product_name, ...) positional shifts
    if isinstance(supplier_id, str) and product_name == "":
        # Called as add_product(product_name, category, ...) without supplier
        product_name, category = supplier_id, product_name or "General"
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (product_name, category, details, unit, size, price, quantity, current_stock)
            VALUES (%s,%s,%s,%s,%s,%s,0,0)
        """, (product_name, category, details, unit, size, price))
        conn.commit()
        return True
    except Exception as err:
        print(f"[add_product] DB error: {err}")
        return False
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass


def update_product(product_id, supplier_id=None, product_name="", category="General", details="", unit="pcs", size="N/A", price=0.00, quantity=0, **kwargs):
    """supplier_id ignored (no supplier column in finalized products table)."""
    if isinstance(supplier_id, str) and product_name == "":
        product_name, category = supplier_id, product_name or "General"
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET product_name=%s, category=%s, details=%s, unit=%s, size=%s, price=%s
            WHERE product_id=%s
        """, (product_name, category, details, unit, size, price, product_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as err:
        print(f"[update_product] DB error: {err}")
        return False
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass


def delete_product(product_id):
    """Deletes a catalog product unless it has transaction history.

    Safety check (no DDL — SELECT guards only): blocks deletion when the
    product is referenced by pr_items, delivery_items, the items inventory
    ledger, withdraw_items, or return_items. Returns (ok, message).
    """
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        history_checks = [
            ("pr_items", "Purchase Request"),
            ("delivery_items", "Delivery"),
            ("items", "Inventory ledger"),
            ("withdraw_items", "Withdrawal"),
            ("return_items", "Return"),
        ]
        for table, label in history_checks:
            cursor.execute(f"SELECT 1 FROM {table} WHERE product_id = %s LIMIT 1",
                           (product_id,))
            if cursor.fetchone():
                return False, (
                    f"Cannot delete PRD-{int(product_id):03d}: it is tied to "
                    f"existing {label} transaction history and must be kept "
                    "for audit trail."
                )
        cursor.execute("DELETE FROM products WHERE product_id=%s", (product_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return True, f"Product PRD-{int(product_id):03d} deleted."
        return False, "Product not found — nothing was deleted."
    except Exception as err:
        print(f"[delete_product] DB error: {err}")
        return False, str(err)
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass
