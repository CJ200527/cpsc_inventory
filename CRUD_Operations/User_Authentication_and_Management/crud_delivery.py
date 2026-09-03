"""crud_delivery.py — Delivery 2-Step Workflow (Study Guide)
Step 1 create_delivery(): inserts deliveries (Pending) + delivery_items (no stock change), is_partial auto-computed.
Step 2 approve_delivery(): Admin only — sets Received, approved_by, credits products.current_stock, updates PO Partial/Delivered.
Uses parameterized SQL; helper get_deliverable_pos() lists Approved POs ready for IAR.
"""

from db import get_db_connection
from datetime import datetime

# ============================================================
# Helpers
# ============================================================

def _ensure_delivery_schema(cursor):
    """Ensure deliveries / delivery_items / products schema supports spec."""
    try:
        cursor.execute("""
            ALTER TABLE deliveries MODIFY COLUMN status ENUM('Pending','Received','Incomplete') DEFAULT 'Pending'
        """)
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS approved_by INT NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS iar_number VARCHAR(50) NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS inspected_by VARCHAR(100) NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS supply_officer VARCHAR(100) NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS is_partial TINYINT(1) DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS remarks TEXT NULL")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS delivery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE Products ADD COLUMN IF NOT EXISTS current_stock INT DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("UPDATE Products SET current_stock = quantity WHERE current_stock IS NULL OR current_stock = 0")
    except Exception:
        pass
    try:
        cursor.execute("""
            ALTER TABLE purchase_orders MODIFY COLUMN status 
            ENUM('Pending PO Approval','Approved','Issued','Delivered','Cancelled','Completed','Partial','Partially Delivered') DEFAULT 'Pending PO Approval'
        """)
    except Exception:
        pass


def _get_product_stock_column(cursor):
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'current_stock'")
        if cursor.fetchone():
            return "current_stock"
    except Exception:
        pass
    return "quantity"


def _compute_is_partial(po_items_map, received_items):
    """
    Auto-determine partial: if ANY received_quantity != ordered_quantity => partial.
    Returns 1 if partial, 0 if complete (all equal).
    """
    for it in received_items:
        pid = int(it.get('product_id'))
        recv = int(it.get('received_quantity', 0))
        ordered = int(po_items_map.get(pid, {}).get('quantity', 0))
        if recv != ordered:
            return 1
    return 0


# ============================================================
# 1. Get POs eligible for Delivery — ONLY Approved/Issued, searchable
#    Excludes POs that already have ANY delivery (partial/completed) — use Complete action instead.
#    Also excludes when delivery is completed (Delivered) — removed from selection.
# ============================================================
def get_deliverable_pos(search_query="", user_id=None):
    """
    Returns ONLY Approved / Issued POs that have NO deliveries yet.
    Searchable by po_number / pr_number / supplier_name.
    Partial / Delivered / Completed POs are excluded — use 'Complete Remaining' action on table row.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT po.po_id, po.po_number, po.pr_id, po.supplier_id, po.status,
                   po.date_ordered AS date_issued, po.total_price AS total_amount,
                   pr.pr_number, s.supplier_name, u.Firstname, u.Lastname
            FROM purchase_orders po
            JOIN purchase_requests pr ON po.pr_id = pr.pr_id
            JOIN Users u ON po.user_id = u.id
            LEFT JOIN Supplier s ON po.supplier_id = s.id
            WHERE po.status IN ('Approved','Issued')
              AND NOT EXISTS (SELECT 1 FROM deliveries d WHERE d.po_id = po.po_id)
        """
        params = []
        if user_id:
            sql += " AND po.user_id = %s"
            params.append(user_id)
        if search_query:
            pat = f"%{search_query}%"
            sql += """ AND (po.po_number LIKE %s OR pr.pr_number LIKE %s OR s.supplier_name LIKE %s)"""
            params.extend([pat, pat, pat])
        sql += " ORDER BY po.po_id DESC"
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    except Exception as err:
        print(f"[get_deliverable_pos] DB error: {err}")
        return []
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


def search_deliverable_pos(search_query, user_id=None):
    """Alias for live search in modal."""
    return get_deliverable_pos(search_query=search_query, user_id=user_id)


# ============================================================
# 1b. Remaining quantity per PO — ordered minus SUM(all deliveries received)
# ============================================================
def get_po_remaining(po_id):
    """
    Computes remaining per product for a PO.
    Returns list of dicts merging po_items with remaining_quantity.
    Remaining = ordered_quantity - COALESCE(SUM delivery_items.received_quantity for that product)
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Fetch PO items authoritative
        cursor.execute("SELECT * FROM po_items WHERE po_id = %s", (po_id,))
        po_items = cursor.fetchall()
        if not po_items:
            return []

        # Sum received per product across ALL deliveries for this PO
        cursor.execute("""
            SELECT product_id, COALESCE(SUM(received_quantity),0) AS total_received
            FROM delivery_items
            WHERE po_id = %s
            GROUP BY product_id
        """, (po_id,))
        received_map = {int(r['product_id']): int(r['total_received']) for r in cursor.fetchall()}

        result = []
        for item in po_items:
            pid = int(item['product_id'])
            ordered = int(item['quantity'])
            total_recv = received_map.get(pid, 0)
            remaining = max(0, ordered - total_recv)
            result.append({
                'product_id': pid,
                'item_name': item['item_name'],
                'category': item.get('category'),
                'unit': item.get('unit'),
                'details': item.get('details'),
                'size': item.get('size'),
                'price': float(item['price']),
                'ordered_quantity': ordered,
                'total_received': total_recv,
                'remaining_quantity': remaining,
                'supplier_id': item['supplier_id'],
            })
        return result
    except Exception as err:
        print(f"[get_po_remaining] DB error: {err}")
        return []
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# ============================================================
# 2. CREATE: Step 1 — Receiving & IAR Submission
#    AUTO partial, empty received default, guard received > ordered
# ============================================================
def create_delivery(po_id, user_id, delivery_number, iar_number, inspected_by, supply_officer, delivery_date, remarks, received_items, is_partial=None):
    """
    Creates deliveries + delivery_items with status Pending (NO stock change).
    - is_partial AUTO-computed: 1 if any received != ordered, else 0 (checkbox removed).
    - received_items: [{product_id, received_quantity}] — received must be <= ordered.
    - Returns (True, delivery_id) or (False, error_msg)
    """
    # is_partial param kept for backwards compat but ignored — auto computed
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        _ensure_delivery_schema(cursor)

        cursor.execute("SELECT * FROM purchase_orders WHERE po_id = %s", (po_id,))
        po = cursor.fetchone()
        if not po:
            return False, "Purchase Order not found."
        if po['status'] not in ('Approved', 'Issued'):
            return False, f"PO status '{po['status']}' not eligible. Only Approved / Issued can create new delivery. Use 'Complete Remaining' for Partial."

        pr_id = po['pr_id']
        supplier_id = po['supplier_id']

        if not delivery_number or not iar_number or not inspected_by or not supply_officer:
            return False, "Delivery Number, IAR Number, Inspected By and Supply Officer are required."
        if not received_items or len(received_items) == 0:
            return False, "At least one item with received quantity is required."

        # Uniqueness
        cursor.execute("SELECT delivery_id FROM deliveries WHERE delivery_number = %s", (delivery_number,))
        if cursor.fetchone():
            return False, f"Delivery Number '{delivery_number}' already exists."
        if iar_number:
            cursor.execute("SELECT delivery_id FROM deliveries WHERE iar_number = %s", (iar_number,))
            if cursor.fetchone():
                return False, f"IAR Number '{iar_number}' already exists."

        cursor.execute("SELECT * FROM po_items WHERE po_id = %s", (po_id,))
        po_items = cursor.fetchall()
        if not po_items:
            return False, "No items found for this PO."
        po_items_map = {int(r['product_id']): r for r in po_items}

        # Validate each received <= ordered and auto compute partial
        for it in received_items:
            try:
                pid = int(it.get('product_id'))
                recv_qty = int(it.get('received_quantity', 0))
            except Exception:
                return False, "Invalid received quantity data."
            if recv_qty < 0:
                return False, "Received quantity cannot be negative."
            po_item = po_items_map.get(pid)
            if not po_item:
                return False, f"Product ID {pid} not found in PO."
            ordered_qty = int(po_item['quantity'])
            if recv_qty > ordered_qty:
                return False, f"Received quantity ({recv_qty}) cannot exceed ordered quantity ({ordered_qty}) for '{po_item['item_name']}'."

        # Check for empty received (all zeros) — require at least one >0
        if all(int(it.get('received_quantity', 0)) == 0 for it in received_items):
            return False, "Please enter at least one received quantity greater than 0."

        # Auto is_partial: any received != ordered => partial
        is_partial_flag = _compute_is_partial(po_items_map, received_items)

        # Also consider already-delivered sum for remaining validation (prevent over-delivery across multiple deliveries)
        # Sum already received for this PO
        cursor.execute("SELECT product_id, COALESCE(SUM(received_quantity),0) AS tot FROM delivery_items WHERE po_id=%s GROUP BY product_id", (po_id,))
        already = {int(r['product_id']): int(r['tot']) for r in cursor.fetchall()}
        for it in received_items:
            pid = int(it['product_id'])
            recv = int(it['received_quantity'])
            ordered = int(po_items_map[pid]['quantity'])
            prev = already.get(pid, 0)
            if prev + recv > ordered:
                return False, f"Total received would exceed ordered for '{po_items_map[pid]['item_name']}': already {prev} + new {recv} > ordered {ordered}. Remaining is {ordered - prev}."

        if not delivery_date:
            delivery_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            try:
                if len(delivery_date) == 10:
                    delivery_date = delivery_date + " 00:00:00"
            except Exception:
                delivery_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sql_header = """
            INSERT INTO deliveries
            (po_id, pr_id, user_id, supplier_id, delivery_number, iar_number, inspected_by, supply_officer, remarks, is_partial, delivery_date, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pending')
        """
        cursor.execute(sql_header, (po_id, pr_id, user_id, supplier_id, delivery_number, iar_number, inspected_by, supply_officer, remarks or "", is_partial_flag, delivery_date))
        delivery_id = cursor.lastrowid

        sql_item = """
            INSERT INTO delivery_items
            (delivery_id, po_id, pr_id, user_id, supplier_id, product_id, item_name, ordered_quantity, received_quantity, price, total_price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        for it in received_items:
            pid = int(it['product_id'])
            recv_qty = int(it['received_quantity'])
            po_item = po_items_map[pid]
            ordered_qty = int(po_item['quantity'])
            price = float(po_item['price'])
            item_name = po_item['item_name']
            total_price = recv_qty * price
            cursor.execute(sql_item, (delivery_id, po_id, pr_id, user_id, supplier_id, pid, item_name, ordered_qty, recv_qty, price, total_price))

        conn.commit()
        return True, delivery_id

    except Exception as err:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[create_delivery] DB error: {err}")
        return False, str(err)
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# ============================================================
# 2b. COMPLETE — create follow-up delivery for remaining qty
# ============================================================
def create_completion_delivery(original_delivery_id, user_id, delivery_number, iar_number, inspected_by, supply_officer, delivery_date, remarks, received_items):
    """
    Creates a NEW delivery for remaining quantity of same PO as original_delivery_id.
    Shows remaining = ordered - sum(all deliveries) so user never sees initial qty when completing.
    Validates received <= remaining.
    Returns (True, new_delivery_id) or (False, msg)
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        _ensure_delivery_schema(cursor)

        cursor.execute("SELECT * FROM deliveries WHERE delivery_id=%s", (original_delivery_id,))
        orig = cursor.fetchone()
        if not orig:
            return False, "Original delivery not found."
        po_id = int(orig['po_id'])
        pr_id = int(orig['pr_id'])
        supplier_id = int(orig['supplier_id'])

        # Must be partial / not fully delivered
        # Check remaining >0
        remaining_list = get_po_remaining(po_id)
        if not remaining_list:
            return False, "PO has no remaining items."
        total_remaining = sum(r['remaining_quantity'] for r in remaining_list)
        if total_remaining <= 0:
            return False, "All items already fully delivered — nothing remaining to complete."

        if not delivery_number or not iar_number or not inspected_by or not supply_officer:
            return False, "Delivery Number, IAR Number, Inspected By and Supply Officer are required."

        cursor.execute("SELECT delivery_id FROM deliveries WHERE delivery_number=%s", (delivery_number,))
        if cursor.fetchone():
            return False, f"Delivery Number '{delivery_number}' already exists."
        cursor.execute("SELECT delivery_id FROM deliveries WHERE iar_number=%s", (iar_number,))
        if cursor.fetchone():
            return False, f"IAR Number '{iar_number}' already exists."

        cursor.execute("SELECT * FROM po_items WHERE po_id=%s", (po_id,))
        po_items = cursor.fetchall()
        po_map = {int(r['product_id']): r for r in po_items}
        remain_map = {int(r['product_id']): int(r['remaining_quantity']) for r in remaining_list}

        # Validate each received <= remaining
        for it in received_items:
            try:
                pid = int(it.get('product_id'))
                recv = int(it.get('received_quantity', 0))
            except:
                return False, "Invalid received quantity."
            if recv < 0:
                return False, "Received cannot be negative."
            if pid not in remain_map:
                return False, f"Product {pid} not in PO."
            if recv > remain_map[pid]:
                return False, f"Received ({recv}) exceeds remaining ({remain_map[pid]}) for '{po_map[pid]['item_name']}'."

        if all(int(it.get('received_quantity', 0)) == 0 for it in received_items):
            return False, "Enter at least one received quantity >0."

        # Auto is_partial: if sum of new received < total remaining => still partial
        total_new_recv = sum(int(it.get('received_quantity', 0)) for it in received_items)
        is_partial_flag = 0 if total_new_recv >= total_remaining else 1
        # Also if any individual recv < remain => partial (above covers)
        # To be safe, if after this delivery remaining would still >0 => partial

        if not delivery_date:
            delivery_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            if len(delivery_date) == 10:
                delivery_date += " 00:00:00"

        sql_header = """
            INSERT INTO deliveries
            (po_id, pr_id, user_id, supplier_id, delivery_number, iar_number, inspected_by, supply_officer, remarks, is_partial, delivery_date, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pending')
        """
        cursor.execute(sql_header, (po_id, pr_id, user_id, supplier_id, delivery_number, iar_number, inspected_by, supply_officer, remarks or "", is_partial_flag, delivery_date))
        new_id = cursor.lastrowid

        sql_item = """
            INSERT INTO delivery_items
            (delivery_id, po_id, pr_id, user_id, supplier_id, product_id, item_name, ordered_quantity, received_quantity, price, total_price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        for it in received_items:
            pid = int(it['product_id'])
            recv = int(it['received_quantity'])
            # Store ordered_quantity as remaining (so table reflects remaining basis) but keep original ordered for history? Spec says show remaining not initial.
            # For correctness, store ordered_quantity = remain_map[pid] (remaining) — this makes display align with "remaining" logic.
            # However to preserve audit, we also could store original ordered. Requirement explicitly: when completing, should NOT see initial ordered quantity instead remaining. So we store remaining as ordered_quantity in new row.
            # We'll store ordered_quantity = remaining before this completion (so comparison is recv vs remaining).
            ordered_for_display = remain_map[pid]
            price = float(po_map[pid]['price'])
            item_name = po_map[pid]['item_name']
            total = recv * price
            cursor.execute(sql_item, (new_id, po_id, pr_id, user_id, supplier_id, pid, item_name, ordered_for_display, recv, price, total))

        conn.commit()
        return True, new_id
    except Exception as err:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[create_completion_delivery] DB error: {err}")
        return False, str(err)
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# ============================================================
# 3. READ — all deliveries
# ============================================================
def get_all_deliveries(search_query="", status_filter="All", date_filter="All", custom_date="", user_id=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT d.delivery_id, d.delivery_number, d.iar_number, d.inspected_by, d.supply_officer,
                   d.is_partial, d.delivery_date, d.status, d.approved_by, d.remarks,
                   po.po_id, po.po_number, po.status AS po_status,
                   pr.pr_id, pr.pr_number,
                   s.supplier_name, s.id AS supplier_id,
                   u.Firstname, u.Lastname, u.username,
                   approver.Firstname AS approver_first, approver.Lastname AS approver_last
            FROM deliveries d
            JOIN purchase_orders po ON d.po_id = po.po_id
            JOIN purchase_requests pr ON d.pr_id = pr.pr_id
            LEFT JOIN Supplier s ON d.supplier_id = s.id
            JOIN Users u ON d.user_id = u.id
            LEFT JOIN Users approver ON d.approved_by = approver.id
            WHERE 1=1
        """
        params = []
        if user_id:
            sql += " AND d.user_id = %s"
            params.append(user_id)
        if status_filter != "All":
            sql += " AND d.status = %s"
            params.append(status_filter)
        if search_query:
            pat = f"%{search_query}%"
            sql += """ AND (
                d.delivery_number LIKE %s OR d.iar_number LIKE %s OR
                po.po_number LIKE %s OR pr.pr_number LIKE %s OR
                s.supplier_name LIKE %s OR u.Firstname LIKE %s OR u.Lastname LIKE %s
            )"""
            params.extend([pat]*7)
        if date_filter == "Today":
            sql += " AND DATE(d.delivery_date) = CURDATE()"
        elif date_filter == "Last Month":
            sql += " AND d.delivery_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
        elif date_filter == "Last Year":
            sql += " AND d.delivery_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)"
        elif date_filter == "Custom" and custom_date:
            sql += " AND DATE(d.delivery_date) = %s"
            params.append(custom_date)
        sql += " ORDER BY d.delivery_id DESC"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        for r in rows:
            try: r['is_partial'] = int(r['is_partial'] or 0)
            except: r['is_partial'] = 0

        # --- Enrich with PO remaining + latest flag for Complete button logic ---
        # Compute remaining per PO (ordered - sum received across ALL deliveries for that PO)
        # and mark is_latest_for_po (only newest delivery per PO keeps Complete button)
        if rows:
            try:
                # Gather distinct po_ids
                po_ids = list({int(r['po_id']) for r in rows if r.get('po_id')})
                if po_ids:
                    fmt = ",".join(["%s"]*len(po_ids))
                    # Ordered totals per PO
                    cursor.execute(f"SELECT po_id, COALESCE(SUM(quantity),0) AS ordered FROM po_items WHERE po_id IN ({fmt}) GROUP BY po_id", tuple(po_ids))
                    ordered_map = {int(r['po_id']): int(r['ordered']) for r in cursor.fetchall()}
                    # Received totals per PO (all deliveries, any status)
                    cursor.execute(f"SELECT po_id, COALESCE(SUM(received_quantity),0) AS received FROM delivery_items WHERE po_id IN ({fmt}) GROUP BY po_id", tuple(po_ids))
                    received_map = {int(r['po_id']): int(r['received']) for r in cursor.fetchall()}
                    remaining_map = {}
                    for pid in po_ids:
                        ordered = ordered_map.get(pid, 0)
                        received = received_map.get(pid, 0)
                        remaining_map[pid] = max(0, ordered - received)

                    # is_latest_for_po: first occurrence in DESC order is latest
                    seen = set()
                    for r in rows:
                        pid = int(r['po_id'])
                        r['po_remaining'] = remaining_map.get(pid, 0)
                        r['po_is_complete'] = 1 if r['po_remaining'] == 0 else 0
                        if pid not in seen:
                            r['is_latest_for_po'] = 1
                            seen.add(pid)
                        else:
                            r['is_latest_for_po'] = 0
                        # Show Complete only if still has remaining AND is latest AND is_partial (original partial) OR latest pending with remaining
                        # Computed as: remaining >0 and latest
                        r['show_complete'] = 1 if (r['po_remaining'] > 0 and r['is_latest_for_po'] == 1) else 0
                else:
                    for r in rows:
                        r['po_remaining'] = 0
                        r['po_is_complete'] = 0
                        r['is_latest_for_po'] = 0
                        r['show_complete'] = 0
            except Exception as e:
                print(f"[get_all_deliveries enrich] {e}")
                for r in rows:
                    r.setdefault('po_remaining', 0)
                    r.setdefault('po_is_complete', 0)
                    r.setdefault('is_latest_for_po', 0)
                    r.setdefault('show_complete', 0)
        return rows
    except Exception as err:
        print(f"[get_all_deliveries] DB error: {err}")
        return []
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


def get_delivery_details(delivery_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql_header = """
            SELECT d.*, po.po_number, pr.pr_number, s.supplier_name, s.contact_person, s.contact_number, s.email,
                   u.Firstname, u.Lastname, u.username,
                   approver.Firstname AS approver_first, approver.Lastname AS approver_last
            FROM deliveries d
            JOIN purchase_orders po ON d.po_id = po.po_id
            JOIN purchase_requests pr ON d.pr_id = pr.pr_id
            LEFT JOIN Supplier s ON d.supplier_id = s.id
            JOIN Users u ON d.user_id = u.id
            LEFT JOIN Users approver ON d.approved_by = approver.id
            WHERE d.delivery_id = %s
        """
        cursor.execute(sql_header, (delivery_id,))
        header = cursor.fetchone()
        if not header:
            return None, []
        sql_items = """
            SELECT di.*, p.product_name, p.unit AS p_unit, p.category AS p_category, p.details AS p_details, p.size AS p_size
            FROM delivery_items di
            LEFT JOIN Products p ON di.product_id = p.product_id
            WHERE di.delivery_id = %s
        """
        cursor.execute(sql_items, (delivery_id,))
        items = cursor.fetchall()
        return header, items
    except Exception as err:
        print(f"[get_delivery_details] DB error: {err}")
        return None, []
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# ============================================================
# 5. Approve — ingest stock (FIXED: exact qty + double-injection guard)
#    Guard: Only Pending can be approved; block if already Received/Injected or stock_movement exists.
#    Adds EXACT received_quantity per item to Products.current_stock (not ordered qty).
# ============================================================
def approve_delivery(delivery_id, admin_user_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        _ensure_delivery_schema(cursor)
        # Use FOR UPDATE to lock row and prevent race double-click
        try:
            cursor.execute("SELECT * FROM deliveries WHERE delivery_id = %s FOR UPDATE", (delivery_id,))
        except Exception:
            cursor.execute("SELECT * FROM deliveries WHERE delivery_id = %s", (delivery_id,))
        delivery = cursor.fetchone()
        if not delivery:
            return False, "Delivery not found."
        # --- STRICT GUARD: prevent double stock injection ---
        if delivery['status'] != 'Pending':
            return False, f"Only Pending deliveries can be approved. Current: {delivery['status']} — possible double-click blocked."
        if delivery.get('approved_by') is not None:
            return False, "Delivery already approved — stock already injected (approved_by is set)."
        # Check stock_movements for existing injection (idempotency)
        try:
            cursor.execute("SELECT 1 FROM stock_movements WHERE reference_type='Delivery' AND reference_id=%s LIMIT 1", (delivery_id,))
            if cursor.fetchone():
                return False, "Stock already injected for this delivery — double approval blocked (stock_movements exists)."
        except Exception:
            pass  # table may not exist yet, ignore
        cursor.execute("SELECT * FROM delivery_items WHERE delivery_id = %s", (delivery_id,))
        items = cursor.fetchall()
        if not items:
            return False, "No items for this delivery."
        stock_col = _get_product_stock_column(cursor)
        # Ensure stock_movements and items ledger exist
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_movements (
                    movement_id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    reference_type VARCHAR(20) NOT NULL,
                    reference_id INT NOT NULL,
                    quantity_change INT NOT NULL,
                    balance_after INT NOT NULL,
                    user_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES Products(product_id),
                    FOREIGN KEY (user_id) REFERENCES Users(id)
                )
            """)
        except: pass
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    item_id INT AUTO_INCREMENT PRIMARY KEY,
                    delivery_id INT,
                    po_id INT,
                    pr_id INT,
                    user_id INT,
                    supplier_id INT,
                    product_id INT NOT NULL,
                    item_number VARCHAR(50),
                    item_name VARCHAR(100) NOT NULL,
                    item_quantity INT NOT NULL DEFAULT 0,
                    item_category VARCHAR(50),
                    item_details TEXT,
                    item_unit VARCHAR(20),
                    item_size VARCHAR(20),
                    item_price DECIMAL(10,2) DEFAULT 0.00,
                    item_total_price DECIMAL(12,2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (delivery_id) REFERENCES deliveries(delivery_id),
                    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
                    FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
                    FOREIGN KEY (user_id) REFERENCES Users(id),
                    FOREIGN KEY (supplier_id) REFERENCES Supplier(id),
                    FOREIGN KEY (product_id) REFERENCES Products(product_id)
                )
            """)
        except: pass
        cursor.execute("UPDATE deliveries SET status='Received', approved_by=%s WHERE delivery_id=%s", (admin_user_id, delivery_id))
        for it in items:
            pid = int(it['product_id'])
            qty = int(it['received_quantity'] or 0)
            if qty <= 0:
                continue
            cursor.execute(f"UPDATE Products SET {stock_col} = {stock_col} + %s WHERE product_id = %s", (qty, pid))
            try:
                if stock_col == "current_stock":
                    cursor.execute("UPDATE Products SET quantity = current_stock WHERE product_id = %s", (pid,))
                else:
                    cursor.execute("UPDATE Products SET current_stock = quantity WHERE product_id = %s", (pid,))
            except Exception:
                pass
            # Populate physical ledger `items`
            try:
                # Fetch extra details from po_items for this product
                cursor.execute("SELECT category, details, unit, size FROM po_items WHERE po_id=%s AND product_id=%s LIMIT 1", (delivery['po_id'], pid))
                po_extra = cursor.fetchone()
                cat = po_extra['category'] if po_extra and po_extra.get('category') else None
                det = po_extra['details'] if po_extra and po_extra.get('details') else None
                unit = po_extra['unit'] if po_extra and po_extra.get('unit') else (it.get('unit') or 'pcs')
                size = po_extra['size'] if po_extra and po_extra.get('size') else None
                cursor.execute("""
                    INSERT INTO items (delivery_id, po_id, pr_id, user_id, supplier_id, product_id, item_name, item_quantity, item_category, item_details, item_unit, item_size, item_price, item_total_price)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (delivery_id, delivery['po_id'], delivery['pr_id'], delivery['user_id'], delivery['supplier_id'], pid, it['item_name'], qty, cat, det, unit, size, float(it['price'] or 0), float(qty * float(it['price'] or 0))))
            except Exception as e:
                print(f"[items ledger] {e}")
            # Audit log stock_movements Delivery positive
            try:
                cursor.execute(f"SELECT COALESCE({stock_col},0) AS bal FROM Products WHERE product_id=%s", (pid,))
                bal = int(cursor.fetchone()['bal'] or 0)
                cursor.execute("""
                    INSERT INTO stock_movements (product_id, reference_type, reference_id, quantity_change, balance_after, user_id)
                    VALUES (%s,'Delivery',%s,%s,%s,%s)
                """, (pid, delivery_id, qty, bal, admin_user_id))
            except Exception as e:
                print(f"[stock_movements Delivery] {e}")
        po_id = int(delivery['po_id'])
        is_partial = int(delivery.get('is_partial') or 0)
        new_po_status = "Partial" if is_partial == 1 else "Delivered"
        try:
            cursor.execute("UPDATE purchase_orders SET status=%s WHERE po_id=%s", (new_po_status, po_id))
        except Exception:
            try:
                cursor.execute("UPDATE purchase_orders SET status=%s WHERE po_id=%s", (new_po_status, po_id))
            except Exception as e2:
                print(f"[approve_delivery] PO status failed: {e2}")
        conn.commit()
        return True, f"Delivery {delivery['delivery_number']} approved. Stock ingested; PO set to '{new_po_status}'."
    except Exception as err:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[approve_delivery] DB error: {err}")
        return False, str(err)
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass
