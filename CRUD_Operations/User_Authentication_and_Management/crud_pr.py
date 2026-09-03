"""crud_pr.py — Purchase Request Workflow (Study Guide)
create_purchase_request(): inserts header + pr_items in transaction, generates PR-YYYY-XXX.
get_all_purchase_requests() supports search + status/date filters, joined with Users.
update_pr_status() for Admin approve/reject.
"""

from db import get_db_connection

from datetime import datetime

def generate_pr_number():
    """Generates a unique sequential PR number formatted like PR-2026-001."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_year = datetime.now().year
        cursor.execute("SELECT COUNT(*) FROM purchase_requests;")
        count = cursor.fetchone()[0] + 1
        return f"PR-{current_year}-{count:03d}"
    except Exception as err:
        print(f"[generate_pr_number] DB error: {err}")
        return f"PR-{datetime.now().year}-001"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- 1. CREATE: Submit Purchase Request with Line Items ---
def create_purchase_request(user_id, items_list):
    """
    Inserts a purchase_requests header and pr_items line items in a single transaction.
    `items_list` expects a list of dicts with:
    [{'supplier_id': 1, 'product_id': 2, 'item_name': 'Paper', 'category': 'Supplies', 
      'unit': 'ream', 'details': '', 'size': 'A4', 'price': 250.00, 'quantity': 5}, ...]
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        pr_number = generate_pr_number()
        grand_total = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in items_list)

        # A. Insert Header into purchase_requests
        sql_pr = """
        INSERT INTO purchase_requests (user_id, pr_number, total_price, status, has_po)
        VALUES (%s, %s, %s, 'Pending', 0);
        """
        cursor.execute(sql_pr, (user_id, pr_number, grand_total))
        pr_id = cursor.lastrowid

        # B. Insert Items into pr_items
        sql_item = """
        INSERT INTO pr_items 
        (pr_id, user_id, supplier_id, product_id, item_name, category, unit, details, size, price, quantity, total_price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """

        for item in items_list:
            item_price = float(item.get('price', 0))
            item_qty = int(item.get('quantity', 1))
            item_total = item_price * item_qty

            cursor.execute(sql_item, (
                pr_id, user_id, item['supplier_id'], item['product_id'],
                item['item_name'], item.get('category', ''), item.get('unit', 'pcs'),
                item.get('details', ''), item.get('size', ''),
                item_price, item_qty, item_total
            ))

        conn.commit()
        return True, pr_number

    except Exception as err:
        if conn: conn.rollback()
        print(f"[create_purchase_request] DB error: {err}")
        return False, str(err)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- 2. READ: Fetch Purchase Requests with Search & Filters ---
def get_all_purchase_requests(search_query="", status_filter="All", date_filter="All", custom_date="", user_id=None):
    """
    Fetches PR records joined with Users table.
    Filters by user_id if passed (for Staff viewing their own PRs).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
        SELECT pr.pr_id, pr.pr_number, pr.date_requested, pr.status, pr.total_price, pr.has_po,
               u.id AS user_id, u.Firstname, u.Lastname, u.username
        FROM purchase_requests pr
        JOIN Users u ON pr.user_id = u.id
        WHERE 1=1
        """
        params = []

        if user_id:
            sql += " AND pr.user_id = %s"
            params.append(user_id)

        if status_filter != "All":
            sql += " AND pr.status = %s"
            params.append(status_filter)

        if search_query:
            pattern = f"%{search_query}%"
            sql += """ AND (
                pr.pr_number LIKE %s OR 
                u.Firstname LIKE %s OR 
                u.Lastname LIKE %s OR 
                u.username LIKE %s
            )"""
            params.extend([pattern] * 4)

        if date_filter == "Today":
            sql += " AND DATE(pr.date_requested) = CURDATE()"
        elif date_filter == "Last Month":
            sql += " AND pr.date_requested >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
        elif date_filter == "Last Year":
            sql += " AND pr.date_requested >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)"
        elif date_filter == "Custom" and custom_date:
            sql += " AND DATE(pr.date_requested) = %s"
            params.append(custom_date)

        sql += " ORDER BY pr.pr_id DESC;"

        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

    except Exception as err:
        print(f"[get_all_purchase_requests] DB error: {err}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- 3. READ: Fetch Details of a Single PR ---
def get_pr_details(pr_id):
    """Fetches single PR header and its associated pr_items line items."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch Header
        sql_header = """
        SELECT pr.*, u.Firstname, u.Lastname, u.username, u.Contact_Number
        FROM purchase_requests pr
        JOIN Users u ON pr.user_id = u.id
        WHERE pr.pr_id = %s;
        """
        cursor.execute(sql_header, (pr_id,))
        header = cursor.fetchone()

        if not header:
            return None, []

        # Fetch Line Items
        sql_items = """
        SELECT pri.*, s.supplier_name
        FROM pr_items pri
        LEFT JOIN Supplier s ON pri.supplier_id = s.id
        WHERE pri.pr_id = %s;
        """
        cursor.execute(sql_items, (pr_id,))
        items = cursor.fetchall()

        return header, items

    except Exception as err:
        print(f"[get_pr_details] DB error: {err}")
        return None, []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- 4. UPDATE: Approve or Reject PR ---
def update_pr_status(pr_id, new_status):
    """Updates status of a PR to 'Approved' or 'Rejected'."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE purchase_requests SET status = %s WHERE pr_id = %s;", (new_status, pr_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as err:
        print(f"[update_pr_status] DB error: {err}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()