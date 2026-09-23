"""crud_notifications.py — header bell counts (single shared source).

Returns pending-action rows for the notification bell on every dashboard:
each item carries label + count + filtered-list URL. Only rows with
count > 0 are returned. Admin alone sees the user-approval row; every
other row reflects the shared workspace (identical for both roles).
No DDL — SELECT COUNT(*) only.
"""

from db import get_db_connection


def get_notification_counts(role="Staff"):
    """Returns (items, total). Item: {label, count, url}."""
    items = []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        def one(sql, args=()):
            cursor.execute(sql, args)
            row = cursor.fetchone()
            try:
                return int(row[0] if not isinstance(row, dict) else list(row.values())[0] or 0)
            except Exception:
                return 0

        if role == "Admin":
            n = one("SELECT COUNT(*) FROM users WHERE Approved_By = 0 OR Approved_By IS NULL")
            if n > 0:
                items.append({"label": "User accounts pending approval", "count": n,
                              "url": "/admin/users"})

        n = one("SELECT COUNT(*) FROM purchase_requests WHERE status = 'Pending'")
        if n > 0:
            items.append({"label": "Purchase Requests pending director action", "count": n,
                          "url": "/pr?status_filter=Pending"})
        n = one("SELECT COUNT(*) FROM purchase_requests WHERE status = 'Approved' "
                "AND COALESCE(po_status, 'Pending') = 'Pending'")
        if n > 0:
            items.append({"label": "Purchase Requests pending procurement decision", "count": n,
                          "url": "/pr?status_filter=Approved&po_status_filter=Pending"})
        n = one("SELECT COUNT(*) FROM iar WHERE status = 'Pending'")
        if n > 0:
            items.append({"label": "IARs awaiting receiving", "count": n,
                          "url": "/delivery?status_filter=Pending"})
        n = one("SELECT COUNT(*) FROM `withdraw` WHERE status = 'Pending'")
        if n > 0:
            items.append({"label": "Requisitions pending issuance", "count": n,
                          "url": "/withdraw?status_filter=Pending"})
        n = one("SELECT COUNT(*) FROM `return` WHERE status = 'Pending'")
        if n > 0:
            items.append({"label": "Return slips pending processing", "count": n,
                          "url": "/returns?status_filter=Pending"})
        n = one("SELECT COUNT(*) FROM products WHERE is_active = 1 "
                "AND COALESCE(current_stock, quantity, 0) <= COALESCE(reorder_level, 10)")
        if n > 0:
            inv_url = ("/admin/inventory?stock_status=Needs+Attention"
                       if role == "Admin" else "/inventory?stock_status=Needs+Attention")
            items.append({"label": "Items needing attention (low & out of stock)", "count": n,
                          "url": inv_url})

        total = sum(i["count"] for i in items)
        return items, total
    except Exception as err:
        print(f"[get_notification_counts] DB error: {err}")
        return [], 0
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
