"""crud_pr.py — Purchase Request Workflow (PR-to-Delivery, finalized schema)
create_purchase_request(): inserts header + pr_items in transaction, generates PR-YYYY-XXX.
get_all_purchase_requests() supports search + status/date filters, joined with users.
update_pr_status() for Admin approve/reject.
get_approved_prs_without_delivery(): approved PRs eligible for direct delivery.

Finalized schema (DO NOT modify — no DDL here):
- purchase_requests(pr_id, user_id, pr_number, fund_source, date_requested, status, total_price)
- pr_items(pr_item_id, pr_id, user_id, product_id, item_name, category, unit, details, size, price, quantity, total_price)
- No supplier_id, no has_po, no purchase_orders / po_items.
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
def _resolve_product_id(cursor, item):
    """Just-in-time product resolution (no DDL — SELECT/INSERT only).

    Returns the products.product_id for a PR line: reuses the given
    product_id when it exists, else matches by exact item_name, else
    inserts a new Master Catalog row (lazy creation) and returns its id.
    `cursor` may be a plain or dictionary cursor.
    """
    pid = item.get('product_id')
    if pid:
        try:
            cursor.execute("SELECT product_id FROM products WHERE product_id = %s", (int(pid),))
            if cursor.fetchone():
                return int(pid)
        except Exception:
            pass
    name = (item.get('item_name') or '').strip()
    if name:
        cursor.execute("SELECT product_id FROM products WHERE product_name = %s LIMIT 1", (name,))
        row = cursor.fetchone()
        if row:
            try:
                return int(row['product_id']) if isinstance(row, dict) else int(row[0])
            except Exception:
                pass
    # Lazy creation: brand-new typed item becomes a catalog product (zero stock).
    cursor.execute(
        """INSERT INTO products
           (product_name, category, details, unit, size, price, quantity, current_stock)
           VALUES (%s, %s, %s, %s, %s, %s, 0, 0)""",
        (name or 'Unnamed Item',
         (item.get('category') or '').strip() or 'General',
         item.get('details') or '',
         (item.get('unit') or '').strip() or 'pcs',
         (item.get('size') or '').strip() or 'N/A',
         float(item.get('price', 0)))
    )
    return cursor.lastrowid


def create_purchase_request(user_id, items_list, fund_source="Fund 05", date_requested=None):
    """
    Inserts a purchase_requests header and pr_items line items in a single transaction.
    `items_list` expects a list of dicts with:
    [{'product_id': 2 (optional — lazy-created when missing),
      'item_name': 'Paper', 'category': 'Supplies',
      'unit': 'ream', 'details': '', 'size': 'A4', 'price': 250.00, 'quantity': 5}, ...]
    `fund_source` defaults to 'Fund 05'; `date_requested` ('YYYY-MM-DD' or
    'YYYY-MM-DD HH:MM:SS') defaults to the DB CURRENT_TIMESTAMP when omitted.
    NOTE: supplier_id is intentionally ignored (no supplier table; supplier captured
    later as free-text deliveries.supplier_name). Any 'supplier_id' key present for
    backwards compatibility is silently dropped.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        pr_number = generate_pr_number()
        grand_total = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in items_list)
        fund_source = (fund_source or 'Fund 05').strip() or 'Fund 05'

        # Normalize optional date_requested ('YYYY-MM-DD' -> full timestamp)
        date_val = (date_requested or '').strip() if date_requested else ''
        if date_val and len(date_val) == 10:
            date_val = date_val + ' 00:00:00'

        # A. Insert Header into purchase_requests (no has_po column in finalized schema)
        if date_val:
            sql_pr = """
            INSERT INTO purchase_requests (user_id, pr_number, fund_source, date_requested, total_price, status)
            VALUES (%s, %s, %s, %s, %s, 'Pending');
            """
            cursor.execute(sql_pr, (user_id, pr_number, fund_source, date_val, grand_total))
        else:
            sql_pr = """
            INSERT INTO purchase_requests (user_id, pr_number, fund_source, total_price, status)
            VALUES (%s, %s, %s, %s, 'Pending');
            """
            cursor.execute(sql_pr, (user_id, pr_number, fund_source, grand_total))
        pr_id = cursor.lastrowid

        # B. Insert Items into pr_items (no supplier_id column in finalized schema)
        sql_item = """
        INSERT INTO pr_items
        (pr_id, user_id, product_id, item_name, category, unit, details, size, price, quantity, total_price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """

        for item in items_list:
            item_price = float(item.get('price', 0))
            item_qty = int(item.get('quantity', 1))
            item_total = item_price * item_qty
            product_id = _resolve_product_id(cursor, item)

            cursor.execute(sql_item, (
                pr_id, user_id, product_id,
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
    Fetches PR records joined with users table.
    Filters by user_id if passed (for Staff viewing their own PRs).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
        SELECT pr.pr_id, pr.pr_number, pr.date_requested, pr.status, pr.total_price,
               u.id AS user_id, u.Firstname, u.Lastname, u.username
        FROM purchase_requests pr
        JOIN users u ON pr.user_id = u.id
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


def get_approved_prs_for_delivery(search_query="", user_id=None):
    """Approved PRs eligible for direct delivery (PR-to-Delivery workflow, no PO)."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT pr.pr_id, pr.pr_number, pr.date_requested, pr.status, pr.total_price,
                   u.Firstname, u.Lastname, u.username
            FROM purchase_requests pr
            JOIN users u ON pr.user_id = u.id
            WHERE pr.status = 'Approved'
        """
        params = []
        if user_id:
            sql += " AND pr.user_id = %s"
            params.append(user_id)
        if search_query:
            pat = f"%{search_query}%"
            sql += " AND (pr.pr_number LIKE %s OR u.Firstname LIKE %s OR u.Lastname LIKE %s)"
            params.extend([pat, pat, pat])
        sql += " ORDER BY pr.pr_id DESC"
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    except Exception as err:
        print(f"[get_approved_prs_for_delivery] DB error: {err}")
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
        JOIN users u ON pr.user_id = u.id
        WHERE pr.pr_id = %s;
        """
        cursor.execute(sql_header, (pr_id,))
        header = cursor.fetchone()

        if not header:
            return None, []

        # Fetch Line Items (no supplier join — supplier captured at delivery as text)
        sql_items = """
        SELECT pri.*, p.product_name AS catalog_name, p.unit AS catalog_unit,
               p.category AS catalog_category, p.price AS catalog_price
        FROM pr_items pri
        LEFT JOIN products p ON pri.product_id = p.product_id
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


# --- 5. UPDATE: Edit a Pending PR (header + line items) with master-product sync ---
def update_purchase_request(pr_id, fund_source="Fund 05", date_requested=None, items_list=None):
    """
    Edits a Purchase Request ONLY while its status is Pending. Replaces the
    pr_items snapshot and syncs every line back to its linked products row so
    the Master Catalog reflects renames/attribute changes gracefully.
    Approved/Rejected PRs are immutable historical records.
    Returns (True, pr_number) or (False, error_msg). No DDL — DML only.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT pr_id, pr_number, user_id, status FROM purchase_requests WHERE pr_id = %s",
            (pr_id,))
        pr = cursor.fetchone()
        if not pr:
            return False, "Purchase Request not found."
        if pr['status'] != 'Pending':
            return False, (
                f"Only Pending PRs can be edited. Current status: {pr['status']} — "
                "approved records are immutable."
            )
        items_list = items_list or []
        if not items_list:
            return False, "A Purchase Request must keep at least one line item."
        fund_source = (fund_source or 'Fund 05').strip() or 'Fund 05'
        grand_total = sum(float(i.get('price', 0)) * int(i.get('quantity', 1))
                          for i in items_list)
        date_val = (date_requested or '').strip() if date_requested else ''
        if date_val and len(date_val) == 10:
            date_val += ' 00:00:00'
        if date_val:
            cursor.execute(
                """UPDATE purchase_requests
                   SET fund_source = %s, date_requested = %s, total_price = %s
                   WHERE pr_id = %s""",
                (fund_source, date_val, grand_total, pr_id))
        else:
            cursor.execute(
                """UPDATE purchase_requests
                   SET fund_source = %s, total_price = %s WHERE pr_id = %s""",
                (fund_source, grand_total, pr_id))

        # Replace the line-item snapshot (nothing references pr_items by id).
        cursor.execute("DELETE FROM pr_items WHERE pr_id = %s", (pr_id,))
        for item in items_list:
            price = float(item.get('price', 0))
            qty = int(item.get('quantity', 1))
            if qty < 1:
                continue
            pid = _resolve_product_id(cursor, item)
            # Graceful master-product sync: catalog follows the edited line.
            cursor.execute(
                """UPDATE products
                   SET product_name = %s, category = %s, unit = %s,
                       details = %s, size = %s, price = %s
                   WHERE product_id = %s""",
                (item['item_name'],
                 (item.get('category') or '').strip() or 'General',
                 (item.get('unit') or '').strip() or 'pcs',
                 item.get('details') or '',
                 (item.get('size') or '').strip() or 'N/A',
                 price, pid))
            cursor.execute(
                """INSERT INTO pr_items
                   (pr_id, user_id, product_id, item_name, category, unit,
                    details, size, price, quantity, total_price)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (pr_id, pr['user_id'], pid,
                 item['item_name'], item.get('category', ''),
                 item.get('unit', 'pcs'), item.get('details', ''),
                 item.get('size', ''), price, qty, price * qty))

        conn.commit()
        return True, pr['pr_number']
    except Exception as err:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[update_purchase_request] DB error: {err}")
        return False, str(err)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- 6. UPDATE: Approve or Reject PR ---
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
