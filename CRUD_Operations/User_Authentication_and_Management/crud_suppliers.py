"""
Supplier CRUD Module — Handles Supplier table (id, supplier_name, contact..., address fields).
Used by Admin (full CRUD) and Staff (Add/Edit only) via App.py RBAC.
All queries use parameterized SQL to prevent injection; dynamic address learning
(SELECT DISTINCT street/barangay/...) is done in App.py and merged with Camiguin dataset in JS.
"""

from db import get_db_connection


def get_all_suppliers_filtered(search_query="", date_filter="All", custom_date=""):
    """Fetch suppliers with search + date filter; used by admin_suppliers/staff_suppliers. Supports distinct address learning."""
    """Fetch suppliers with optional search + date filter (mirrors user_management)."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT id AS supplier_id, supplier_name, contact_person, contact_number,
                   email, street, barangay, municipality, city, country, created_at
            FROM Supplier
            WHERE 1=1
        """
        params = []
        if search_query:
            pat = f"%{search_query}%"
            sql += """ AND (
                id LIKE %s OR supplier_name LIKE %s OR contact_person LIKE %s
                OR contact_number LIKE %s OR email LIKE %s
                OR street LIKE %s OR barangay LIKE %s OR municipality LIKE %s OR city LIKE %s
            )"""
            params.extend([pat] * 9)
        if date_filter == "Today":
            sql += " AND DATE(created_at) = CURDATE()"
        elif date_filter == "Last Month":
            sql += " AND created_at >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
        elif date_filter == "Last Year":
            sql += " AND created_at >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)"
        elif date_filter == "Custom" and custom_date:
            sql += " AND DATE(created_at) = %s"
            params.append(custom_date)
        sql += " ORDER BY id DESC;"
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    except Exception as err:
        print(f"[get_all_suppliers] DB error: {err}")
        return []
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass

# Aliases for compatibility
get_all_suppliers = get_all_suppliers_filtered


def add_supplier(supplier_name, contact_person="", contact_number="", email="", street="", barangay="", municipality="", city="", country="Philippines"):
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Supplier (supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country))
        conn.commit()
        return True
    except Exception as err:
        print(f"[add_supplier] DB error: {err}")
        return False
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass


def update_supplier(supplier_id, supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country):
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Supplier SET supplier_name=%s, contact_person=%s, contact_number=%s, email=%s,
                street=%s, barangay=%s, municipality=%s, city=%s, country=%s
            WHERE id=%s
        """, (supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country, supplier_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as err:
        print(f"[update_supplier] DB error: {err}")
        return False
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass


def delete_supplier(supplier_id):
    conn = None; cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Supplier WHERE id=%s", (supplier_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as err:
        print(f"[delete_supplier] DB error: {err}")
        return False
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        if conn is not None:
            try: conn.close()
            except: pass
