"""
Legacy IAR wrapper — now delegates to spec-compliant crud_delivery.
Maintained for backwards compatibility with App.py imports.
Do NOT use iar_deliveries/iar_items tables; use deliveries/delivery_items per spec.
"""
from db import get_db_connection
from datetime import datetime

# Import spec-compliant implementation
try:
    from crud_delivery import (
        create_delivery as _create_delivery,
        get_all_deliveries,
        get_delivery_details,
        approve_delivery,
        get_deliverable_pos
    )
except ImportError:
    # Fallback relative import
    from CRUD_Operations.User_Authentication_and_Management.crud_delivery import (
        create_delivery as _create_delivery,
        get_all_deliveries,
        get_delivery_details,
        approve_delivery,
        get_deliverable_pos
    )


def create_iar_record(po_id, iar_number, iar_date, is_partial, inspected_by, supply_officer, received_items, remarks=""):
    """
    Legacy signature kept for compatibility.
    Previously created iar_deliveries + immediate stock. Now delegates to Pending workflow.
    received_items: [{'product_id':1,'received_quantity':5,'unit_price':100.00}, ...]
    NOTE: delivery_number is auto-generated as DEL-<po_id>-<timestamp> if not supplied.
    """
    # Generate a delivery_number from iar_number if not explicit
    delivery_number = f"DEL-{po_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    # Try to derive user_id: use supply_officer lookup or 1 as fallback
    # Legacy call didn't pass user_id; attempt to find admin user or use 1
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM Users LIMIT 1")
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

    # Delegate - map received_items to new format (ignore unit_price, trust PO price)
    mapped = []
    for it in received_items or []:
        try:
            mapped.append({
                'product_id': int(it.get('product_id')),
                'received_quantity': int(it.get('received_quantity', 0))
            })
        except Exception:
            continue

    # Fetch PO to get pr_id/supplier if needed - _create_delivery will pull from PO
    success, result = _create_delivery(
        po_id=int(po_id),
        user_id=fallback_user,
        delivery_number=delivery_number,
        iar_number=iar_number,
        inspected_by=inspected_by or "N/A",
        supply_officer=supply_officer or "N/A",
        delivery_date=delivery_date,
        remarks=remarks or "",
        is_partial=1 if is_partial else 0,
        received_items=mapped
    )
    return success, result


def get_iar_by_po(po_id):
    """Legacy: fetch deliveries for a PO (replaces iar_deliveries query)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM deliveries WHERE po_id=%s ORDER BY delivery_id DESC", (po_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[get_iar_by_po legacy] {e}")
        return []
