"""crud_pr.py — Purchase Request Workflow (PR-to-Delivery, finalized schema)
create_purchase_request(): inserts header + pr_items in transaction, generates PR-YYYY-MM-DD-XXX (daily).
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
    """Generates the next daily PR number like PR-2026-09-08-001.

    Sequence resets each day (count of PRs already carrying today's prefix
    + 1). Uniqueness is still enforced by the DB + route validation.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        prefix = datetime.now().strftime("PR-%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM purchase_requests WHERE pr_number LIKE %s;", (prefix + "-%",))
        count = cursor.fetchone()[0] + 1
        return f"{prefix}-{count:03d}"
    except Exception as err:
        print(f"[generate_pr_number] DB error: {err}")
        return f"{datetime.now().strftime('PR-%Y-%m-%d')}-001"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- Product history guard: established catalog rows are immutable ---
def is_product_established(cursor, product_id):
    """TRUE when the product is in ANY delivery_items row or in pr_items of
    an Approved/Completed PR (locked history). Fail-safe returns TRUE so an
    uncertain check protects history instead of overwriting it."""
    try:
        cursor.execute("SELECT 1 FROM delivery_items WHERE product_id = %s LIMIT 1",
                       (product_id,))
        if cursor.fetchone():
            return True
        cursor.execute(
            """SELECT 1 FROM pr_items pri
               JOIN purchase_requests pr ON pri.pr_id = pr.pr_id
               WHERE pri.product_id = %s
                 AND pr.status IN ('Approved', 'Completed') LIMIT 1""",
            (product_id,))
        return cursor.fetchone() is not None
    except Exception as err:
        print(f"[is_product_established] DB error: {err}")
        return True


def _sync_product_specs(cursor, product_id, item):
    """Normalizes a matched DRAFT product row to the submitted specs (price
    EXCLUDED — catalog prices change only via delivery approval
    (weighted-average), never via PR save/approval).
    Established rows are left untouched to protect history.
    Returns True when the catalog was updated."""
    if is_product_established(cursor, product_id):
        return False
    cursor.execute(
        """UPDATE products
           SET product_name = %s, category = %s, unit = %s,
               details = %s, size = %s
           WHERE product_id = %s""",
        (item['item_name'],
         (item.get('category') or '').strip() or 'General',
         (item.get('unit') or '').strip() or 'pcs',
         item.get('details') or '',
         (item.get('size') or '').strip() or 'N/A',
         product_id))
    return True


# --- 1. CREATE: Submit Purchase Request with Line Items ---
def _resolve_product_id(cursor, item):
    """Composite-identity product resolution (variants; no DDL — SELECT/INSERT only).

    Matches on the 5-field composite key (item_name, category, unit, size,
    details) — price is IGNORED. Exact match → existing product id; any
    difference → INSERT a NEW product variant and return its id. A valid
    legacy product_id is honored as an explicit link.
    Returns (product_id, is_new). `cursor` may be plain or dictionary.
    """
    pid = item.get('product_id')
    if pid:
        try:
            cursor.execute("SELECT product_id FROM products WHERE product_id = %s", (int(pid),))
            if cursor.fetchone():
                return int(pid), False
        except Exception:
            pass
    # Normalized composite key (same normalization used at INSERT time).
    name = (item.get('item_name') or '').strip() or 'Unnamed Item'
    category = (item.get('category') or '').strip() or 'General'
    unit = (item.get('unit') or '').strip() or 'pcs'
    size = (item.get('size') or '').strip() or 'N/A'
    details = item.get('details') or ''
    cursor.execute(
        """SELECT product_id FROM products
           WHERE product_name = %s
             AND COALESCE(category, '') = %s
             AND COALESCE(unit, '') = %s
             AND COALESCE(size, '') = %s
             AND COALESCE(details, '') = %s
           LIMIT 1""",
        (name, category, unit, size, details))
    row = cursor.fetchone()
    if row:
        try:
            return (int(row['product_id']) if isinstance(row, dict)
                    else int(row[0])), False
        except Exception:
            pass
    # No exact variant — create a NEW product variant (zero stock, INACTIVE:
    # PR-proposed products stay hidden from Inventory until a delivery wakes
    # them with is_active = 1 on approval).
    cursor.execute(
        """INSERT INTO products
           (product_name, category, details, unit, size, price, quantity, current_stock, is_active)
           VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 0)""",
        (name, category, details, unit, size, float(item.get('price', 0))))
    return cursor.lastrowid, True


def _normalize_pr_dup_key(item):
    """Identity key mirroring _resolve_product_id (explicit product_id wins,
    else the 5-field composite). Lowercased: MySQL's default collation treats
    'Bond Paper' and 'bond paper' as the same row."""
    try:
        pid = item.get('product_id')
        if pid is not None and str(pid).strip() != '':
            return ('id', int(pid))
    except (TypeError, ValueError):
        pass
    parts = [
        (item.get('item_name') or '').strip().lower(),
        ((item.get('category') or '').strip() or 'General').lower(),
        ((item.get('unit') or '').strip() or 'pcs').lower(),
        ((item.get('size') or '').strip() or 'N/A').lower(),
        (item.get('details') or '').strip().lower(),
    ]
    return ('spec',) + tuple(parts)


def find_duplicate_pr_item(items_list):
    """Returns the display name of the first duplicated product in the payload,
    or None when all lines are unique. Pure function — safe to call pre-insert."""
    seen = set()
    for item in items_list or []:
        if not (item.get('item_name') or '').strip():
            continue  # blank rows are dropped/skipped by the callers, not dups
        key = _normalize_pr_dup_key(item)
        if key in seen:
            return (item.get('item_name') or '').strip()
        seen.add(key)
    return None


def create_purchase_request(user_id, items_list, fund_source="Fund 05", date_requested=None):
    """
    Inserts a purchase_requests header and pr_items line items in a single transaction.
    `items_list` expects a list of dicts with:
    [{'product_id': 2 (optional legacy link),
      'item_name': 'Paper', 'category': 'Supplies',
      'unit': 'ream', 'details': '', 'size': 'A4', 'price': 250.00, 'quantity': 5}, ...]
    Composite identity: lines link by exact (item_name, category, unit,
    size, details) — price ignored; any spec difference creates a NEW
    product variant. Matched draft rows are spec-normalized (established
    rows untouched); catalog prices change only via delivery approval
    (weighted-average of actual invoice costs).
    `fund_source` defaults to 'Fund 05'; `date_requested` ('YYYY-MM-DD' or
    'YYYY-MM-DD HH:MM:SS') defaults to the DB CURRENT_TIMESTAMP when omitted.
    NOTE: supplier_id is intentionally ignored (no supplier table; supplier captured
    later as free-text deliveries.supplier_name). Any 'supplier_id' key present for
    backwards compatibility is silently dropped.
    """
    dup = find_duplicate_pr_item(items_list)
    if dup:
        return False, f"This product is already in the request ('{dup}'). Please adjust the quantity of the existing item instead."
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
            product_id, is_new = _resolve_product_id(cursor, item)
            if not is_new:
                # Draft-spec sync: normalize a matched draft row (established ignored).
                _sync_product_specs(cursor, product_id, item)

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
               u.id AS user_id, u.Firstname, u.Lastname, u.username, u.Role
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


def _is_draft_product(cursor, product_id):
    """True when the product is a PR-proposed draft (is_active = 0).

    Falls back to the history-based check on legacy DBs lacking the column.
    Works with plain or dictionary cursors.
    """
    try:
        pid = int(product_id)
    except (TypeError, ValueError):
        return False
    try:
        cursor.execute("SELECT is_active FROM products WHERE product_id = %s", (pid,))
        row = cursor.fetchone()
        if row is None:
            return False
        val = row.get('is_active') if isinstance(row, dict) else row[0]
        return int(val or 0) == 0
    except Exception:
        try:
            return not is_product_established(cursor, pid)
        except Exception:
            return False


def _resolve_existing_product(cursor, item):
    """Like _resolve_product_id but NEVER inserts: honors an explicit link,
    else matches the 5-field composite key. Returns product_id or None.
    Works with plain or dictionary cursors.
    """
    pid = item.get('product_id')
    if pid:
        try:
            cursor.execute("SELECT product_id FROM products WHERE product_id = %s", (int(pid),))
            if cursor.fetchone():
                return int(pid)
        except Exception:
            pass
    name = (item.get('item_name') or '').strip() or 'Unnamed Item'
    category = (item.get('category') or '').strip() or 'General'
    unit = (item.get('unit') or '').strip() or 'pcs'
    size = (item.get('size') or '').strip() or 'N/A'
    details = item.get('details') or ''
    cursor.execute(
        """SELECT product_id FROM products
           WHERE product_name = %s
             AND COALESCE(category, '') = %s
             AND COALESCE(unit, '') = %s
             AND COALESCE(size, '') = %s
             AND COALESCE(details, '') = %s
           LIMIT 1""",
        (name, category, unit, size, details))
    row = cursor.fetchone()
    if row:
        try:
            return (int(row['product_id']) if isinstance(row, dict)
                    else int(row[0]))
        except Exception:
            pass
    return None


def _norm_spec(value, default):
    """Normalized comparison form (same defaults as _resolve_product_id)."""
    return ((value or '').strip() or default).lower()


def _draft_spec_row(cursor, pid):
    """Normalized spec dict of a products row, or None when missing."""
    try:
        cursor.execute("SELECT product_name, category, unit, size, details FROM products WHERE product_id = %s", (pid,))
        r = cursor.fetchone()
        if not r:
            return None
        g = (lambda k: r.get(k)) if isinstance(r, dict) else (lambda k: None)
        if not isinstance(r, dict):
            try:
                name, cat, unit, size, det = r[0], r[1], r[2], r[3], r[4]
            except Exception:
                return None
            return {'name': _norm_spec(name, 'Unnamed Item'), 'category': _norm_spec(cat, 'General'),
                    'unit': _norm_spec(unit, 'pcs'), 'size': _norm_spec(size, 'N/A'),
                    'details': _norm_spec(det, '')}
        return {'name': _norm_spec(g('product_name'), 'Unnamed Item'), 'category': _norm_spec(g('category'), 'General'),
                'unit': _norm_spec(g('unit'), 'pcs'), 'size': _norm_spec(g('size'), 'N/A'),
                'details': _norm_spec(g('details'), '')}
    except Exception:
        return None


def _update_draft_specs(cursor, pid, item):
    """Overwrites a draft's specs with the submitted values (display casing kept)."""
    cursor.execute(
        """UPDATE products
           SET product_name = %s, category = %s, unit = %s,
               details = %s, size = %s
           WHERE product_id = %s""",
        ((item.get('item_name') or '').strip() or 'Unnamed Item',
         (item.get('category') or '').strip() or 'General',
         (item.get('unit') or '').strip() or 'pcs',
         item.get('details') or '',
         (item.get('size') or '').strip() or 'N/A',
         pid))


def _link_edit_item(cursor, item, unclaimed_drafts):
    """Resolves one submitted edit line to a product_id without orphaning drafts.

    unclaimed_drafts: {pid: normalized specs} of this PR's original draft
    links, each consumable once. Resolution order:
    1. explicit product_id link (drafts among them update in place);
    2. exact composite match (unchanged row, any status — link as-is);
    3. same-name unclaimed original draft with the best field overlap
       (score >= 1) → UPDATE in place (a pure spec tweak, no rename);
    4. otherwise delegate to _resolve_product_id (links another existing
       row or inserts an inactive variant); renames land here.
    Returns (product_id, is_new).
    """
    pid = item.get('product_id')
    if pid:
        try:
            cursor.execute("SELECT product_id FROM products WHERE product_id = %s", (int(pid),))
            if cursor.fetchone():
                pid = int(pid)
                if _is_draft_product(cursor, pid):
                    _update_draft_specs(cursor, pid, item)
                unclaimed_drafts.pop(pid, None)
                return pid, False
        except Exception:
            pass
    pid = _resolve_existing_product(cursor, item)
    if pid is not None:
        unclaimed_drafts.pop(pid, None)
        return pid, False
    name = _norm_spec(item.get('item_name'), 'Unnamed Item')
    best, best_score = None, 0
    for dp, specs in unclaimed_drafts.items():
        if specs['name'] != name:
            continue
        score = sum(
            1 for key, default in (('category', 'General'), ('unit', 'pcs'),
                                   ('size', 'N/A'), ('details', ''))
            if _norm_spec(item.get(key), default) == specs[key])
        if score > best_score:
            best, best_score = dp, score
    if best is not None and best_score >= 1:
        del unclaimed_drafts[best]
        _update_draft_specs(cursor, best, item)
        return best, False
    return _resolve_product_id(cursor, item)


def _delete_orphan_draft(cursor, product_id):
    """Deletes product_id iff it is a draft AND unreferenced everywhere
    (any pr_items, delivery/withdraw/return/items ledgers, stock_movements).
    A referenced row — even in another Pending PR — is always kept, since
    pr_items carries a foreign key to products. Returns True if deleted.
    """
    try:
        pid = int(product_id)
    except (TypeError, ValueError):
        return False
    if not _is_draft_product(cursor, pid):
        return False
    checks = [
        "SELECT 1 FROM pr_items WHERE product_id = %s LIMIT 1",
        "SELECT 1 FROM delivery_items WHERE product_id = %s LIMIT 1",
        "SELECT 1 FROM withdraw_items WHERE product_id = %s LIMIT 1",
        "SELECT 1 FROM return_items WHERE product_id = %s LIMIT 1",
        "SELECT 1 FROM items WHERE product_id = %s LIMIT 1",
        "SELECT 1 FROM stock_movements WHERE product_id = %s LIMIT 1",
    ]
    try:
        for sql in checks:
            cursor.execute(sql, (pid,))
            if cursor.fetchone():
                return False
        cursor.execute("DELETE FROM products WHERE product_id = %s", (pid,))
        return cursor.rowcount > 0
    except Exception as err:
        print(f"[_delete_orphan_draft] {err}")
        return False


# --- 5. UPDATE: Edit a Pending PR (header + line items) with smart draft sync ---
def update_purchase_request(pr_id, fund_source="Fund 05", date_requested=None, items_list=None):
    """
    Edits a Purchase Request ONLY while its status is Pending. Replaces the
    pr_items snapshot with smart draft handling: lines linked to draft
    products (is_active = 0) UPDATE the catalog row in place instead of
    spawning duplicates; established products (is_active = 1) are never
    touched — only pr_items changes. Draft products removed by the edit are
    garbage-collected when truly orphaned.
    Approved/Rejected PRs are immutable historical records.
    Returns (True, pr_number) or (False, error_msg). No DDL — DML only.
    """
    dup = find_duplicate_pr_item(items_list)
    if dup:
        return False, f"This product is already in the request ('{dup}'). Please adjust the quantity of the existing item instead."
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

        # Snapshot original links BEFORE replacing: full draft-spec map for
        # same-line matching plus the id set for orphan-draft GC.
        cursor.execute("SELECT product_id FROM pr_items WHERE pr_id = %s", (pr_id,))
        original_pids = []
        for r in cursor.fetchall():
            try:
                original_pids.append(int(r['product_id'] if isinstance(r, dict) else r[0]))
            except (TypeError, ValueError):
                continue
        unclaimed_drafts = {}
        for pid in original_pids:
            if _is_draft_product(cursor, pid):
                specs = _draft_spec_row(cursor, pid)
                if specs is not None:
                    unclaimed_drafts[pid] = specs

        # Replace the line-item snapshot (nothing references pr_items by id).
        cursor.execute("DELETE FROM pr_items WHERE pr_id = %s", (pr_id,))
        new_pids = []
        for item in items_list:
            price = float(item.get('price', 0))
            qty = int(item.get('quantity', 1))
            if qty < 1:
                continue
            # Smart link: unchanged rows re-link, same-line draft tweaks
            # update in place, established rows stay untouched, genuinely new
            # specs create an inactive variant (renames land here, GC below
            # retires the abandoned draft when truly orphaned).
            pid, _ = _link_edit_item(cursor, item, unclaimed_drafts)
            new_pids.append(pid)
            cursor.execute(
                """INSERT INTO pr_items
                   (pr_id, user_id, product_id, item_name, category, unit,
                    details, size, price, quantity, total_price)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (pr_id, pr['user_id'], pid,
                 item['item_name'], item.get('category', ''),
                 item.get('unit', 'pcs'), item.get('details', ''),
                 item.get('size', ''), price, qty, price * qty))

        # Garbage-collect drafts this edit orphaned (referenced ones survive).
        for pid in set(original_pids) - set(new_pids):
            _delete_orphan_draft(cursor, pid)

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


# --- 6. UPDATE: Approve or Reject PR (status only — catalog prices untouched) ---
def update_pr_status(pr_id, new_status):
    """Updates status of a PR to 'Approved' or 'Rejected'.

    Pricing integrity: PR approval NO LONGER rewrites products.price.
    Estimated PR prices stay on pr_items only; the true unit cost enters the
    catalog via delivery approval (weighted-average in approve_delivery),
    keeping the product catalog stable against estimate fluctuations.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE purchase_requests SET status = %s WHERE pr_id = %s;", (new_status, pr_id))
        if cursor.rowcount == 0:
            conn.rollback()
            return False
        conn.commit()
        return True
    except Exception as err:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[update_pr_status] DB error: {err}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
