try:
    from db import get_db_connection
except ImportError:
    from CRUD_Operations.User_Authentication_and_Management.db import get_db_connection


def get_all_products_filtered(search_query="", date_filter="All", custom_date=""):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT p.product_id, p.supplier_id, s.supplier_name,
                   p.product_name, p.category, p.details, p.unit, p.size, p.price, p.quantity, p.created_at
            FROM Products p
            LEFT JOIN Supplier s ON p.supplier_id = s.id
            WHERE 1=1
        """
        params = []
        if search_query:
            pat = f"%{search_query}%"
            sql += """ AND (
                p.product_id LIKE %s OR p.product_name LIKE %s OR p.category LIKE %s
                OR p.details LIKE %s OR p.unit LIKE %s OR p.size LIKE %s
                OR s.supplier_name LIKE %s
            )"""
            params.extend([pat] * 7)
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
        # Fallback for lowercase table name if DB was created with different case
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
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, supplier_name FROM Supplier ORDER BY supplier_name ASC")
        return cursor.fetchall()
    except Exception as err:
        print(f"[get_suppliers_list] DB error: {err}")
        return []
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass


def add_product(supplier_id, product_name, category, details="", unit="", size="", price=0.00, quantity=0):
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Products (supplier_id, product_name, category, details, unit, size, price, quantity)
            VALUES (%s,%s,%s,%s,%s,%s,%s,0)
        """, (supplier_id, product_name, category, details, unit, size, price))
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


def update_product(product_id, supplier_id, product_name, category, details="", unit="", size="", price=0.00, quantity=0):
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Products SET supplier_id=%s, product_name=%s, category=%s, details=%s, unit=%s, size=%s, price=%s
            WHERE product_id=%s
        """, (supplier_id, product_name, category, details, unit, size, price, product_id))
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
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Products WHERE product_id=%s", (product_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as err:
        print(f"[delete_product] DB error: {err}")
        return False
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass
