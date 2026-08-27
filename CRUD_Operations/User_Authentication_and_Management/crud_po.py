import sys
import os
try:
    from db import get_db_connection
except ImportError:
    from CRUD_Operations.User_Authentication_and_Management.db import get_db_connection

from datetime import datetime

def generate_po_number():
    """Generates a unique sequential PO number formatted like PO-2026-001."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_year = datetime.now().year
        cursor.execute("SELECT COUNT(*) FROM purchase_orders;")
        count = cursor.fetchone()[0] + 1
        return f"PO-{current_year}-{count:03d}"
    except Exception as err:
        print(f"[generate_po_number] DB error: {err}")
        return f"PO-{datetime.now().year}-001"
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# --- 1. CREATE: Convert Approved PR into PO (with editable Actual PO prices) ---
def create_po_from_pr(pr_id, created_by_user_id, adjusted_items=None):
    """
    Converts an Approved PR (has_po = 0) into a Purchase Order.
    `adjusted_items` is optional list of dicts: [{'product_id':1,'supplier_id':1,'item_name':'Paper','quantity':5,'unit_price':280.00, ...}, ...]
    If provided, uses adjusted unit_price/quantity (actual vendor prices) while preserving PR estimates in pr_items.
    Otherwise falls back to original PR items.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # A. Fetch PR Header
        cursor.execute("SELECT * FROM purchase_requests WHERE pr_id = %s AND status = 'Approved' AND has_po = 0;", (pr_id,))
        pr_header = cursor.fetchone()
        if not pr_header:
            return False, "Approved PR not found or PO already generated for this PR."

        # B. Determine items to use: adjusted_items if provided else original pr_items
        if adjusted_items and len(adjusted_items) > 0:
            # Normalize adjusted items: ensure required keys, fallback to original PR data for missing fields
            # Fetch original items for supplement if needed
            cursor.execute("SELECT * FROM pr_items WHERE pr_id = %s;", (pr_id,))
            orig_items = {row['product_id']: row for row in cursor.fetchall()}
            normalized = []
            for adj in adjusted_items:
                pid = int(adj.get('product_id'))
                orig = orig_items.get(pid, {})
                normalized.append({
                    'product_id': pid,
                    'supplier_id': int(adj.get('supplier_id') or orig.get('supplier_id') or 1),
                    'item_name': adj.get('item_name') or orig.get('item_name') or '',
                    'category': adj.get('category') or orig.get('category') or '',
                    'unit': adj.get('unit') or orig.get('unit') or 'pcs',
                    'details': adj.get('details') or orig.get('details') or '',
                    'size': adj.get('size') or orig.get('size') or '',
                    'quantity': int(adj.get('quantity') or 1),
                    'unit_price': float(adj.get('unit_price') if 'unit_price' in adj else adj.get('price') or orig.get('price') or 0),
                })
            pr_items_list = normalized
            # Compute actual PO total from adjusted prices
            po_total = sum(it['unit_price'] * it['quantity'] for it in pr_items_list)
            # Main supplier from first adjusted item
            main_supplier_id = pr_items_list[0]['supplier_id']
        else:
            cursor.execute("SELECT * FROM pr_items WHERE pr_id = %s;", (pr_id,))
            pr_items_list = cursor.fetchall()
            if not pr_items_list:
                return False, "No items found in the selected Purchase Request."
            main_supplier_id = pr_items_list[0]['supplier_id']
            po_total = float(pr_header['total_price'])

        po_number = generate_po_number()

        # C. Insert into purchase_orders - correct columns: pr_id, supplier_id, user_id, po_number, total_price, status
        sql_po = """
        INSERT INTO purchase_orders (pr_id, supplier_id, user_id, po_number, total_price, status)
        VALUES (%s, %s, %s, %s, %s, 'Issued');
        """
        # Use actual PO total if adjusted, otherwise PR estimate
        total_to_insert = po_total if (adjusted_items and len(adjusted_items)>0) else pr_header['total_price']
        cursor.execute(sql_po, (pr_id, main_supplier_id, created_by_user_id, po_number, total_to_insert))
        po_id = cursor.lastrowid

        # D. Insert into po_items with actual prices
        sql_po_item = """
        INSERT INTO po_items (po_id, pr_id, user_id, supplier_id, product_id, item_name, category, unit, details, size, price, quantity, total_price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        for item in pr_items_list:
            if adjusted_items and len(adjusted_items)>0:
                # item is normalized dict with unit_price
                u_price = float(item['unit_price'])
                qty = int(item['quantity'])
                tot = u_price * qty
                cursor.execute(sql_po_item, (
                    po_id,
                    pr_id,
                    pr_header['user_id'],
                    item['supplier_id'],
                    item['product_id'],
                    item['item_name'],
                    item.get('category', ''),
                    item.get('unit', 'pcs'),
                    item.get('details', ''),
                    item.get('size', ''),
                    u_price,
                    qty,
                    tot
                ))
            else:
                # original pr_items row
                cursor.execute(sql_po_item, (
                    po_id,
                    item['pr_id'],
                    item['user_id'],
                    item['supplier_id'],
                    item['product_id'],
                    item['item_name'],
                    item.get('category', ''),
                    item.get('unit', 'pcs'),
                    item.get('details', ''),
                    item.get('size', ''),
                    float(item['price']),
                    int(item['quantity']),
                    float(item['total_price'])
                ))

        # E. Mark PR as having a PO
        cursor.execute("UPDATE purchase_requests SET has_po = 1 WHERE pr_id = %s;", (pr_id,))

        conn.commit()
        return True, po_number

    except Exception as err:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[create_po_from_pr] DB error: {err}")
        return False, str(err)
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# --- 2. READ: Fetch Eligible Approved PRs for PO Generation ---
def get_approved_prs_without_po():
    """Fetches all Approved PRs that haven't been converted to a PO yet."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
        SELECT pr.pr_id, pr.pr_number, pr.date_requested, pr.total_price, u.Firstname, u.Lastname
        FROM purchase_requests pr
        JOIN Users u ON pr.user_id = u.id
        WHERE pr.status = 'Approved' AND pr.has_po = 0
        ORDER BY pr.pr_id DESC;
        """
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as err:
        print(f"[get_approved_prs_without_po] DB error: {err}")
        return []
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# --- 3. READ: Fetch Purchase Orders with Search & Filters ---
def get_all_purchase_orders(search_query="", status_filter="All", user_id=None):
    """
    Fetches PO records joined with Users, Supplier, and PR tables.
    Aliases date_ordered->date_issued and total_price->total_amount for App.py JSON compatibility.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
        SELECT po.po_id, po.po_number, po.date_ordered AS date_issued, po.date_ordered, po.status, po.total_price AS total_amount, po.total_price, 0 AS has_delivery,
               pr.pr_number, u.Firstname, u.Lastname, u.username, s.supplier_name
        FROM purchase_orders po
        JOIN Users u ON po.user_id = u.id
        JOIN purchase_requests pr ON po.pr_id = pr.pr_id
        LEFT JOIN Supplier s ON po.supplier_id = s.id
        WHERE 1=1
        """
        params = []

        if user_id:
            sql += " AND po.user_id = %s"
            params.append(user_id)

        if status_filter != "All":
            sql += " AND po.status = %s"
            params.append(status_filter)

        if search_query:
            pattern = f"%{search_query}%"
            sql += """ AND (
                po.po_number LIKE %s OR 
                pr.pr_number LIKE %s OR 
                s.supplier_name LIKE %s OR
                u.Firstname LIKE %s OR 
                u.Lastname LIKE %s
            )"""
            params.extend([pattern] * 5)

        sql += " ORDER BY po.po_id DESC;"

        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

    except Exception as err:
        print(f"[get_all_purchase_orders] DB error: {err}")
        return []
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# --- 4. READ: Fetch Single PO Details with Items ---
def get_po_details(po_id):
    """Fetches PO header and items - aliases columns for App.py JSON compatibility."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Header - alias date_ordered->date_issued, total_price->total_amount, contact_number->phone_number
        sql_header = """
        SELECT po.po_id, po.po_number, po.pr_id, po.supplier_id, po.user_id,
               po.date_ordered AS date_issued, po.date_ordered, po.status, po.total_price AS total_amount, po.total_price,
               pr.pr_number, u.Firstname, u.Lastname, u.username,
               s.supplier_name, s.contact_person, s.contact_number AS phone_number, s.contact_number, s.email
        FROM purchase_orders po
        JOIN Users u ON po.user_id = u.id
        JOIN purchase_requests pr ON po.pr_id = pr.pr_id
        LEFT JOIN Supplier s ON po.supplier_id = s.id
        WHERE po.po_id = %s;
        """
        cursor.execute(sql_header, (po_id,))
        header = cursor.fetchone()

        if not header:
            return None, []

        # Items - alias price->unit_price, quantity->ordered_quantity, add received_quantity=0 for compatibility
        sql_items = """
        SELECT poi.po_item_id, poi.po_id, poi.pr_id, poi.product_id, poi.item_name, poi.category, poi.unit, poi.details, poi.size,
               poi.price AS unit_price, poi.price, poi.quantity AS ordered_quantity, poi.quantity, 0 AS received_quantity, poi.total_price,
               p.product_name, p.unit AS p_unit, p.category AS p_category
        FROM po_items poi
        LEFT JOIN Products p ON poi.product_id = p.product_id
        WHERE poi.po_id = %s;
        """
        cursor.execute(sql_items, (po_id,))
        items = cursor.fetchall()

        return header, items

    except Exception as err:
        print(f"[get_po_details] DB error: {err}")
        return None, []
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# --- 5. UPDATE: Update PO Status ---
def update_po_status(po_id, new_status):
    """Updates status of a PO. Allowed: Issued, Delivered, Cancelled."""
    # Normalize legacy statuses to actual ENUM
    mapping = {"Pending": "Issued", "Partially Delivered": "Delivered", "Completed": "Delivered"}
    if new_status in mapping:
        new_status = mapping[new_status]
    if new_status not in ["Issued", "Delivered", "Cancelled"]:
        return False
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE purchase_orders SET status = %s WHERE po_id = %s;", (new_status, po_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as err:
        print(f"[update_po_status] DB error: {err}")
        return False
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass
