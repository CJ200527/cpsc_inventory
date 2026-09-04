"""crud_delivery.py — Delivery 2-Step Workflow (PR-to-Delivery, finalized schema)
Step 1 create_delivery(): inserts deliveries (Pending) + delivery_items (no stock change), is_partial auto-computed.
Step 2 approve_delivery(): Admin only — sets Received, approved_by, credits products.current_stock.

Finalized schema (DO NOT modify — no DDL in this module):
- deliveries(delivery_id, approved_by, pr_id, user_id, delivery_number, iar_number,
             po_reference_number, supplier_name, inspected_by, supply_officer,
             is_partial, delivery_date, remarks, status ENUM('Pending','Received','Incomplete'))
- delivery_items(delivery_items_id, delivery_id, pr_id, user_id, product_id, item_name,
                 ordered_quantity, received_quantity, category, details, unit, size, price, total_price)
- items(item_id, delivery_id, pr_id, user_id, product_id, item_number, item_name, item_quantity,
        item_category, item_details, item_unit, item_size, item_price, item_total_price)
- products(product_id, ..., current_stock, ...)
- stock_movements(movement_id, product_id, reference_type, reference_id, quantity_change, balance_after, user_id)

Deliveries link DIRECTLY to purchase_requests via pr_id. po_reference_number and
supplier_name are free-text tracking columns on deliveries (no purchase_orders /
po_items / supplier tables). Uses parameterized SQL throughout.
"""

from db import get_db_connection
from datetime import datetime


def generate_delivery_number():
    """Generates the next sequential delivery number like DEL-2026-001 (display hint; DB enforces uniqueness)."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_year = datetime.now().year
        cursor.execute("SELECT COUNT(*) FROM deliveries;")
        count = cursor.fetchone()[0] + 1
        return f"DEL-{current_year}-{count:03d}"
    except Exception as err:
        print(f"[generate_delivery_number] DB error: {err}")
        return f"DEL-{datetime.now().year}-001"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def _compute_is_partial(pr_items_map, received_items):
    """
    Auto-determine partial: if ANY received_quantity != ordered_quantity => partial.
    Returns 1 if partial, 0 if complete (all equal).
    """
    for it in received_items:
        pid = int(it.get('product_id'))
        recv = int(it.get('received_quantity', 0))
        ordered = int(pr_items_map.get(pid, {}).get('quantity', 0))
        if recv != ordered:
            return 1
    return 0


# ============================================================
# 1. Get PRs eligible for Delivery — ONLY Approved, searchable
# ============================================================
def get_deliverable_prs(search_query="", user_id=None):
    """
    Returns Approved PRs with NO delivery record yet (COUNT(deliveries) == 0),
    searchable by pr_number / requestor name. Any PR that already has a row
    in deliveries — Pending, Received, or Incomplete — is excluded; remaining
    quantities are finished via the 'Complete' action on the existing row,
    never via a second fresh delivery.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT pr.pr_id, pr.pr_number, pr.date_requested AS date_issued,
                   pr.status, pr.total_price AS total_amount,
                   u.Firstname, u.Lastname, u.username
            FROM purchase_requests pr
            JOIN users u ON pr.user_id = u.id
            LEFT JOIN deliveries d ON d.pr_id = pr.pr_id
            WHERE pr.status = 'Approved'
              AND d.pr_id IS NULL
        """
        params = []
        if user_id:
            sql += " AND pr.user_id = %s"
            params.append(user_id)
        if search_query:
            pat = f"%{search_query}%"
            sql += """ AND (pr.pr_number LIKE %s OR u.Firstname LIKE %s OR u.Lastname LIKE %s OR u.username LIKE %s)"""
            params.extend([pat, pat, pat, pat])
        sql += " ORDER BY pr.pr_id DESC"
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    except Exception as err:
        print(f"[get_deliverable_prs] DB error: {err}")
        return []
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


# Backwards-compatible aliases (old PO-based names now serve PRs).
def get_deliverable_pos(search_query="", user_id=None):
    """Deprecated alias of get_deliverable_prs (PR-direct workflow, no PO)."""
    return get_deliverable_prs(search_query=search_query, user_id=user_id)


def search_deliverable_pos(search_query, user_id=None):
    """Alias for live search in modal (now searches Approved PRs)."""
    return get_deliverable_prs(search_query=search_query, user_id=user_id)


def search_deliverable_prs(search_query, user_id=None):
    """Alias for live search in modal."""
    return get_deliverable_prs(search_query=search_query, user_id=user_id)


# ============================================================
# 1b. Remaining quantity per PR — ordered minus SUM(all deliveries received)
# ============================================================
def get_pr_remaining(pr_id):
    """
    Computes remaining per product for a PR.
    Returns list of dicts merging pr_items with remaining_quantity.
    Remaining = ordered_quantity - COALESCE(SUM delivery_items.received_quantity for that product)
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Fetch PR items authoritative
        cursor.execute("SELECT * FROM pr_items WHERE pr_id = %s", (pr_id,))
        pr_items = cursor.fetchall()
        if not pr_items:
            return []

        # Sum received per product across ALL deliveries for this PR
        cursor.execute("""
            SELECT product_id, COALESCE(SUM(received_quantity),0) AS total_received
            FROM delivery_items
            WHERE pr_id = %s
            GROUP BY product_id
        """, (pr_id,))
        received_map = {int(r['product_id']): int(r['total_received']) for r in cursor.fetchall()}

        result = []
        for item in pr_items:
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
            })
        return result
    except Exception as err:
        print(f"[get_pr_remaining] DB error: {err}")
        return []
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


def get_po_remaining(po_id):
    """Deprecated alias — PR-direct workflow uses pr_id; delegates to get_pr_remaining."""
    return get_pr_remaining(po_id)


# ============================================================
# 2. CREATE: Step 1 — Receiving & IAR Submission (PR-direct)
#    AUTO partial, empty received default, guard received > ordered
# ============================================================
def create_delivery(pr_id, user_id, delivery_number, iar_number, inspected_by, supply_officer,
                    delivery_date, remarks, received_items,
                    po_reference_number=None, supplier_name=None, is_partial=None, **kwargs):
    """
    Creates deliveries + delivery_items with status Pending (NO stock change).
    - Links DIRECTLY to purchase_requests via pr_id (no PO required).
    - po_reference_number / supplier_name are free-text tracking columns.
    - is_partial AUTO-computed: 1 if any received != ordered, else 0.
    - received_items: [{product_id, received_quantity}] — received must be <= ordered.
    - Returns (True, delivery_id) or (False, error_msg)

    Backwards compat: also accepts po_id= kwarg (treated as pr_id) and
    supplier_id kwarg (ignored).
    """
    # Backwards compat: allow po_id kwarg meaning pr_id
    if pr_id is None and kwargs.get('po_id') is not None:
        pr_id = kwargs.get('po_id')
    if kwargs.get('po_reference') and not po_reference_number:
        po_reference_number = kwargs.get('po_reference')
    # is_partial param kept for backwards compat but ignored — auto computed
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            pr_id = int(pr_id)
        except Exception:
            return False, "Invalid Purchase Request selected."

        cursor.execute("SELECT * FROM purchase_requests WHERE pr_id = %s", (pr_id,))
        pr = cursor.fetchone()
        if not pr:
            return False, "Purchase Request not found."
        if pr['status'] != 'Approved':
            return False, f"PR status '{pr['status']}' not eligible. Only Approved PRs can be delivered."

        if not delivery_number or not iar_number or not inspected_by or not supply_officer:
            return False, "Delivery Number, IAR Number, Inspected By and Supply Officer are required."
        if not supplier_name or not str(supplier_name).strip():
            return False, "Supplier Name is required (text input)."
        supplier_name = str(supplier_name).strip()
        po_reference_number = str(po_reference_number or "").strip() or None
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

        cursor.execute("SELECT * FROM pr_items WHERE pr_id = %s", (pr_id,))
        pr_items = cursor.fetchall()
        if not pr_items:
            return False, "No items found for this Purchase Request."
        pr_items_map = {int(r['product_id']): r for r in pr_items}

        # Validate each received <= ordered and auto compute partial
        for it in received_items:
            try:
                pid = int(it.get('product_id'))
                recv_qty = int(it.get('received_quantity', 0))
            except Exception:
                return False, "Invalid received quantity data."
            if recv_qty < 0:
                return False, "Received quantity cannot be negative."
            pr_item = pr_items_map.get(pid)
            if not pr_item:
                return False, f"Product ID {pid} not found in PR."
            ordered_qty = int(pr_item['quantity'])
            if recv_qty > ordered_qty:
                return False, f"Received quantity ({recv_qty}) cannot exceed ordered quantity ({ordered_qty}) for '{pr_item['item_name']}'."

        # Check for empty received (all zeros) — require at least one >0
        if all(int(it.get('received_quantity', 0)) == 0 for it in received_items):
            return False, "Please enter at least one received quantity greater than 0."

        # Auto is_partial: any received != ordered => partial
        is_partial_flag = _compute_is_partial(pr_items_map, received_items)

        # Also consider already-delivered sum for remaining validation (prevent over-delivery across multiple deliveries)
        cursor.execute("SELECT product_id, COALESCE(SUM(received_quantity),0) AS tot FROM delivery_items WHERE pr_id=%s GROUP BY product_id", (pr_id,))
        already = {int(r['product_id']): int(r['tot']) for r in cursor.fetchall()}
        for it in received_items:
            pid = int(it['product_id'])
            recv = int(it['received_quantity'])
            ordered = int(pr_items_map[pid]['quantity'])
            prev = already.get(pid, 0)
            if prev + recv > ordered:
                return False, f"Total received would exceed ordered for '{pr_items_map[pid]['item_name']}': already {prev} + new {recv} > ordered {ordered}. Remaining is {ordered - prev}."

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
            (pr_id, user_id, delivery_number, iar_number, po_reference_number, supplier_name,
             inspected_by, supply_officer, remarks, is_partial, delivery_date, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pending')
        """
        cursor.execute(sql_header, (pr_id, user_id, delivery_number, iar_number,
                                    po_reference_number, supplier_name,
                                    inspected_by, supply_officer, remarks or "",
                                    is_partial_flag, delivery_date))
        delivery_id = cursor.lastrowid

        sql_item = """
            INSERT INTO delivery_items
            (delivery_id, pr_id, user_id, product_id, item_name, ordered_quantity,
             received_quantity, category, details, unit, size, price, total_price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        for it in received_items:
            pid = int(it['product_id'])
            recv_qty = int(it['received_quantity'])
            pr_item = pr_items_map[pid]
            ordered_qty = int(pr_item['quantity'])
            price = float(pr_item['price'])
            item_name = pr_item['item_name']
            total_price = recv_qty * price
            cursor.execute(sql_item, (delivery_id, pr_id, user_id, pid, item_name,
                                      ordered_qty, recv_qty,
                                      pr_item.get('category'), pr_item.get('details'),
                                      pr_item.get('unit'), pr_item.get('size'),
                                      price, total_price))

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
# 2b. COMPLETE — create follow-up delivery for remaining qty (same PR)
# ============================================================
def create_completion_delivery(original_delivery_id, user_id, delivery_number, iar_number,
                               inspected_by, supply_officer, delivery_date, remarks, received_items,
                               po_reference_number=None, supplier_name=None, **kwargs):
    """
    Creates a NEW delivery for remaining quantity of same PR as original_delivery_id.
    Shows remaining = ordered - sum(all deliveries) so user never sees initial qty when completing.
    Validates received <= remaining.
    po_reference_number / supplier_name default to the original delivery's values if omitted.
    Returns (True, new_delivery_id) or (False, msg)
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM deliveries WHERE delivery_id=%s", (original_delivery_id,))
        orig = cursor.fetchone()
        if not orig:
            return False, "Original delivery not found."
        pr_id = int(orig['pr_id'])
        if po_reference_number is None:
            po_reference_number = orig.get('po_reference_number')
        if not supplier_name:
            supplier_name = orig.get('supplier_name') or kwargs.get('supplier') or ""
        supplier_name = str(supplier_name).strip()
        if not supplier_name:
            return False, "Supplier Name is required (text input)."
        if po_reference_number is not None:
            po_reference_number = str(po_reference_number).strip() or None

        # Check remaining >0
        remaining_list = get_pr_remaining(pr_id)
        if not remaining_list:
            return False, "PR has no remaining items."
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

        cursor.execute("SELECT * FROM pr_items WHERE pr_id=%s", (pr_id,))
        pr_items = cursor.fetchall()
        pr_map = {int(r['product_id']): r for r in pr_items}
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
                return False, f"Product {pid} not in PR."
            if recv > remain_map[pid]:
                return False, f"Received ({recv}) exceeds remaining ({remain_map[pid]}) for '{pr_map[pid]['item_name']}'."

        if all(int(it.get('received_quantity', 0)) == 0 for it in received_items):
            return False, "Enter at least one received quantity >0."

        # Auto is_partial: if sum of new received < total remaining => still partial
        total_new_recv = sum(int(it.get('received_quantity', 0)) for it in received_items)
        is_partial_flag = 0 if total_new_recv >= total_remaining else 1

        if not delivery_date:
            delivery_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            if len(delivery_date) == 10:
                delivery_date += " 00:00:00"

        sql_header = """
            INSERT INTO deliveries
            (pr_id, user_id, delivery_number, iar_number, po_reference_number, supplier_name,
             inspected_by, supply_officer, remarks, is_partial, delivery_date, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pending')
        """
        cursor.execute(sql_header, (pr_id, user_id, delivery_number, iar_number,
                                    po_reference_number, supplier_name,
                                    inspected_by, supply_officer, remarks or "",
                                    is_partial_flag, delivery_date))
        new_id = cursor.lastrowid

        sql_item = """
            INSERT INTO delivery_items
            (delivery_id, pr_id, user_id, product_id, item_name, ordered_quantity,
             received_quantity, category, details, unit, size, price, total_price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        for it in received_items:
            pid = int(it['product_id'])
            recv = int(it['received_quantity'])
            # Store ordered_quantity = remaining before this completion (so comparison is recv vs remaining).
            ordered_for_display = remain_map[pid]
            price = float(pr_map[pid]['price'])
            item_name = pr_map[pid]['item_name']
            total = recv * price
            cursor.execute(sql_item, (new_id, pr_id, user_id, pid, item_name,
                                      ordered_for_display, recv,
                                      pr_map[pid].get('category'), pr_map[pid].get('details'),
                                      pr_map[pid].get('unit'), pr_map[pid].get('size'),
                                      price, total))

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
# 3. READ — all deliveries (PR-direct, no PO/Supplier joins)
# ============================================================
def get_all_deliveries(search_query="", status_filter="All", date_filter="All", custom_date="", user_id=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT d.delivery_id, d.pr_id, d.delivery_number, d.iar_number,
                   d.po_reference_number, d.supplier_name,
                   d.inspected_by, d.supply_officer,
                   d.is_partial, d.delivery_date, d.status, d.approved_by, d.remarks,
                   pr.pr_number,
                   u.Firstname, u.Lastname, u.username,
                   approver.Firstname AS approver_first, approver.Lastname AS approver_last
            FROM deliveries d
            JOIN purchase_requests pr ON d.pr_id = pr.pr_id
            JOIN users u ON d.user_id = u.id
            LEFT JOIN users approver ON d.approved_by = approver.id
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
                d.po_reference_number LIKE %s OR d.supplier_name LIKE %s OR
                pr.pr_number LIKE %s OR u.Firstname LIKE %s OR u.Lastname LIKE %s
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

        # --- Enrich with PR remaining + latest flag for Complete button logic ---
        # Compute remaining per PR (ordered - sum received across ALL deliveries for that PR)
        # and mark is_latest_for_pr (only newest delivery per PR keeps Complete button)
        if rows:
            try:
                # Gather distinct pr_ids
                pr_ids = list({int(r['pr_id']) for r in rows if r.get('pr_id')})
                if pr_ids:
                    fmt = ",".join(["%s"]*len(pr_ids))
                    # Ordered totals per PR
                    cursor.execute(f"SELECT pr_id, COALESCE(SUM(quantity),0) AS ordered FROM pr_items WHERE pr_id IN ({fmt}) GROUP BY pr_id", tuple(pr_ids))
                    ordered_map = {int(r['pr_id']): int(r['ordered']) for r in cursor.fetchall()}
                    # Received totals per PR (all deliveries, any status)
                    cursor.execute(f"SELECT pr_id, COALESCE(SUM(received_quantity),0) AS received FROM delivery_items WHERE pr_id IN ({fmt}) GROUP BY pr_id", tuple(pr_ids))
                    received_map = {int(r['pr_id']): int(r['received']) for r in cursor.fetchall()}
                    remaining_map = {}
                    for pid in pr_ids:
                        ordered = ordered_map.get(pid, 0)
                        received = received_map.get(pid, 0)
                        remaining_map[pid] = max(0, ordered - received)

                    # is_latest_for_pr: first occurrence in DESC order is latest
                    seen = set()
                    for r in rows:
                        pid = int(r['pr_id'])
                        r['pr_remaining'] = remaining_map.get(pid, 0)
                        # Backwards-compat keys for templates still referencing PO names
                        r['po_remaining'] = r['pr_remaining']
                        r['po_is_complete'] = 1 if r['pr_remaining'] == 0 else 0
                        r['pr_is_complete'] = r['po_is_complete']
                        if pid not in seen:
                            r['is_latest_for_pr'] = 1
                            r['is_latest_for_po'] = 1
                            seen.add(pid)
                        else:
                            r['is_latest_for_pr'] = 0
                            r['is_latest_for_po'] = 0
                        r['show_complete'] = 1 if (r['pr_remaining'] > 0 and r['is_latest_for_pr'] == 1) else 0
                        # Compat: expose po_number/pr_number and supplier for old templates
                        r.setdefault('po_number', r.get('po_reference_number') or '')
                        r.setdefault('po_id', r.get('pr_id'))
                else:
                    for r in rows:
                        r['pr_remaining'] = 0
                        r['po_remaining'] = 0
                        r['po_is_complete'] = 0
                        r['pr_is_complete'] = 0
                        r['is_latest_for_pr'] = 0
                        r['is_latest_for_po'] = 0
                        r['show_complete'] = 0
            except Exception as e:
                print(f"[get_all_deliveries enrich] {e}")
                for r in rows:
                    r.setdefault('pr_remaining', 0)
                    r.setdefault('po_remaining', 0)
                    r.setdefault('po_is_complete', 0)
                    r.setdefault('pr_is_complete', 0)
                    r.setdefault('is_latest_for_pr', 0)
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
            SELECT d.*, pr.pr_number,
                   u.Firstname, u.Lastname, u.username,
                   approver.Firstname AS approver_first, approver.Lastname AS approver_last
            FROM deliveries d
            JOIN purchase_requests pr ON d.pr_id = pr.pr_id
            JOIN users u ON d.user_id = u.id
            LEFT JOIN users approver ON d.approved_by = approver.id
            WHERE d.delivery_id = %s
        """
        cursor.execute(sql_header, (delivery_id,))
        header = cursor.fetchone()
        if not header:
            return None, []
        sql_items = """
            SELECT di.*, p.product_name, p.unit AS p_unit, p.category AS p_category, p.details AS p_details, p.size AS p_size
            FROM delivery_items di
            LEFT JOIN products p ON di.product_id = p.product_id
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
# 5. Approve — ingest stock (exact qty + double-injection guard, no DDL)
#    Guard: Only Pending can be approved; block if already Received/Injected or stock_movement exists.
#    Adds EXACT received_quantity per item to products.current_stock (not ordered qty).
# ============================================================
def approve_delivery(delivery_id, admin_user_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Lock row to prevent race double-click (no schema changes here)
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
            pass
        cursor.execute("SELECT * FROM delivery_items WHERE delivery_id = %s", (delivery_id,))
        items = cursor.fetchall()
        if not items:
            return False, "No items for this delivery."
        cursor.execute("UPDATE deliveries SET status='Received', approved_by=%s WHERE delivery_id=%s", (admin_user_id, delivery_id))
        for it in items:
            pid = int(it['product_id'])
            qty = int(it['received_quantity'] or 0)
            if qty <= 0:
                continue
            cursor.execute("UPDATE products SET current_stock = current_stock + %s WHERE product_id = %s", (qty, pid))
            try:
                cursor.execute("UPDATE products SET quantity = current_stock WHERE product_id = %s", (pid,))
            except Exception:
                pass
            # Populate physical ledger `items` (finalized columns, no po_id/supplier_id)
            try:
                cursor.execute("SELECT category, details, unit, size FROM pr_items WHERE pr_id=%s AND product_id=%s LIMIT 1", (delivery['pr_id'], pid))
                pr_extra = cursor.fetchone()
                cat = pr_extra['category'] if pr_extra and pr_extra.get('category') else it.get('category')
                det = pr_extra['details'] if pr_extra and pr_extra.get('details') else it.get('details')
                unit = pr_extra['unit'] if pr_extra and pr_extra.get('unit') else (it.get('unit') or 'pcs')
                size = pr_extra['size'] if pr_extra and pr_extra.get('size') else it.get('size')
                cursor.execute("""
                    INSERT INTO items (delivery_id, pr_id, user_id, product_id, item_name, item_quantity, item_category, item_details, item_unit, item_size, item_price, item_total_price)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (delivery_id, delivery['pr_id'], delivery['user_id'], pid, it['item_name'], qty, cat, det, unit, size, float(it['price'] or 0), float(qty * float(it['price'] or 0))))
            except Exception as e:
                print(f"[items ledger] {e}")
            # Audit log stock_movements Delivery positive
            try:
                cursor.execute("SELECT COALESCE(current_stock,0) AS bal FROM products WHERE product_id=%s", (pid,))
                bal = int(cursor.fetchone()['bal'] or 0)
                cursor.execute("""
                    INSERT INTO stock_movements (product_id, reference_type, reference_id, quantity_change, balance_after, user_id)
                    VALUES (%s,'Delivery',%s,%s,%s,%s)
                """, (pid, delivery_id, qty, bal, admin_user_id))
            except Exception as e:
                print(f"[stock_movements Delivery] {e}")
        conn.commit()
        return True, f"Delivery {delivery['delivery_number']} approved. Stock ingested from PR-{delivery['pr_id']}."
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
