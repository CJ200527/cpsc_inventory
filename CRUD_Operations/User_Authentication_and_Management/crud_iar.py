"""
Legacy IAR wrapper — now delegates to PR-direct crud_delivery.
Maintained for backwards compatibility with App.py imports.
Do NOT use iar_deliveries/iar_items or purchase_orders tables; use deliveries/delivery_items per finalized schema.
No DDL in this module.
"""
from db import get_db_connection
from datetime import datetime

# Import PR-direct implementation
try:
    from crud_delivery import (
        create_delivery as _create_delivery,
        get_all_deliveries,
        get_delivery_details,
        approve_delivery,
        get_deliverable_prs,
        get_deliverable_pos,
        get_pr_remaining,
    )
except ImportError:
    # Fallback relative import
    from CRUD_Operations.User_Authentication_and_Management.crud_delivery import (
        create_delivery as _create_delivery,
        get_all_deliveries,
        get_delivery_details,
        approve_delivery,
        get_deliverable_prs,
        get_deliverable_pos,
        get_pr_remaining,
    )


def create_iar_record(pr_id, iar_number, iar_date, is_partial, inspected_by, supply_officer, received_items, remarks="",
                      delivery_number=None, po_reference_number=None, supplier_name=None, user_id=None):
    """
    Legacy signature kept for compatibility (pr_id was formerly po_id).
    Now delegates to PR-direct Pending workflow.
    received_items: [{'product_id':1,'received_quantity':5}, ...]
    """
    delivery_number = delivery_number or f"DEL-{pr_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    # Try to derive user_id if not supplied
    fallback_user = user_id
    if not fallback_user:
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM users LIMIT 1")
            row = cur.fetchone()
            fallback_user = row['id'] if row else 1
        except Exception:
            fallback_user = 1
        finally:
            if cur:
                try: cur.close()
                except: pass
            if conn:
                try: conn.close()
                except: pass

    # Normalize iar_date to delivery_date string
    if hasattr(iar_date, 'strftime'):
        delivery_date = iar_date.strftime("%Y-%m-%d %H:%M:%S")
    else:
        delivery_date = str(iar_date) if iar_date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Delegate - map received_items to new format
    mapped = []
    for it in received_items or []:
        try:
            mapped.append({
                'product_id': int(it.get('product_id')),
                'received_quantity': int(it.get('received_quantity', 0))
            })
        except Exception:
            continue

    success, result = _create_delivery(
        pr_id=int(pr_id),
        user_id=fallback_user,
        delivery_number=delivery_number,
        iar_number=iar_number,
        inspected_by=inspected_by or "N/A",
        supply_officer=supply_officer or "N/A",
        delivery_date=delivery_date,
        remarks=remarks or "",
        received_items=mapped,
        po_reference_number=po_reference_number,
        supplier_name=supplier_name or "N/A",
    )
    return success, result


def get_iar_by_po(pr_id):
    """Legacy: fetch deliveries for a PR (formerly PO)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM deliveries WHERE pr_id=%s ORDER BY delivery_id DESC", (pr_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[get_iar_by_po legacy] {e}")
        return []


def get_iar_by_pr(pr_id):
    """Fetch deliveries for a PR."""
    return get_iar_by_po(pr_id)
