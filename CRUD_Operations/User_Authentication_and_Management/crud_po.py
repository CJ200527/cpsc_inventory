from db import get_db_connection

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
        VALUES (%s, %s, %s, %s, %s, 'Pending PO Approval');
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
    Fetches PO records joined with Users, Supplier, PR tables and latest Delivery receiver.
    Adds pr_creator, po_creator (Requested By), received_by, and delivery progress.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
        SELECT po.po_id, po.po_number, po.date_ordered AS date_issued, po.date_ordered, po.status, po.total_price AS total_amount, po.total_price,
               pr.pr_number, 
               u.Firstname, u.Lastname, u.username,
               pr_u.Firstname AS pr_Firstname, pr_u.Lastname AS pr_Lastname, pr_u.username AS pr_username,
               s.supplier_name,
               ld.delivery_id AS last_delivery_id, ld.delivery_number AS last_delivery_number, ld.status AS last_delivery_status,
               ru.Firstname AS recv_Firstname, ru.Lastname AS recv_Lastname, ru.username AS recv_username,
               CASE WHEN ld.delivery_id IS NOT NULL THEN 1 ELSE 0 END AS has_delivery
        FROM purchase_orders po
        JOIN Users u ON po.user_id = u.id
        JOIN purchase_requests pr ON po.pr_id = pr.pr_id
        JOIN Users pr_u ON pr.user_id = pr_u.id
        LEFT JOIN Supplier s ON po.supplier_id = s.id
        LEFT JOIN (
            SELECT d.po_id, MAX(d.delivery_id) AS max_delivery_id
            FROM deliveries d
            GROUP BY d.po_id
        ) latest ON latest.po_id = po.po_id
        LEFT JOIN deliveries ld ON ld.delivery_id = latest.max_delivery_id
        LEFT JOIN Users ru ON ld.user_id = ru.id
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
                u.Lastname LIKE %s OR
                pr_u.Firstname LIKE %s OR
                pr_u.Lastname LIKE %s OR
                ru.Firstname LIKE %s OR
                ru.Lastname LIKE %s
            )"""
            params.extend([pattern] * 9)

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
    """Fetches PO header and items — received_quantity now reflects SUM of APPROVED deliveries (status='Received')."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Header with PR creator and latest delivery receiver for completeness
        sql_header = """
        SELECT po.po_id, po.po_number, po.pr_id, po.supplier_id, po.user_id,
               po.date_ordered AS date_issued, po.date_ordered, po.status, po.total_price AS total_amount, po.total_price,
               pr.pr_number, pr_u.Firstname AS pr_Firstname, pr_u.Lastname AS pr_Lastname,
               u.Firstname, u.Lastname, u.username,
               s.supplier_name, s.contact_person, s.contact_number AS phone_number, s.contact_number, s.email
        FROM purchase_orders po
        JOIN Users u ON po.user_id = u.id
        JOIN purchase_requests pr ON po.pr_id = pr.pr_id
        JOIN Users pr_u ON pr.user_id = pr_u.id
        LEFT JOIN Supplier s ON po.supplier_id = s.id
        WHERE po.po_id = %s;
        """
        cursor.execute(sql_header, (po_id,))
        header = cursor.fetchone()

        if not header:
            return None, []

        # Items — delivered qty is SUM of approved delivery_items for this PO/product
        sql_items = """
        SELECT poi.po_item_id, poi.po_id, poi.pr_id, poi.product_id, poi.item_name, poi.category, poi.unit, poi.details, poi.size,
               poi.price AS unit_price, poi.price, poi.quantity AS ordered_quantity, poi.quantity,
               COALESCE(agg.received_qty, 0) AS received_quantity,
               poi.total_price,
               p.product_name, p.unit AS p_unit, p.category AS p_category
        FROM po_items poi
        LEFT JOIN Products p ON poi.product_id = p.product_id
        LEFT JOIN (
            SELECT di.product_id, SUM(di.received_quantity) AS received_qty
            FROM delivery_items di
            JOIN deliveries d ON di.delivery_id = d.delivery_id
            WHERE di.po_id = %s AND d.status = 'Received'
            GROUP BY di.product_id
        ) agg ON agg.product_id = poi.product_id
        WHERE poi.po_id = %s;
        """
        cursor.execute(sql_items, (po_id, po_id))
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
    """Updates status of a PO. Allowed: Pending PO Approval, Approved, Issued, Delivered, Cancelled, etc."""
    # Normalize legacy statuses
    mapping = {"Pending": "Pending PO Approval", "Partially Delivered": "Delivered", "Completed": "Delivered"}
    if new_status in mapping:
        new_status = mapping[new_status]
    if new_status not in ["Pending PO Approval", "Approved", "Issued", "Delivered", "Cancelled", "Completed", "Partial", "Partially Delivered", "Pending"]:
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
