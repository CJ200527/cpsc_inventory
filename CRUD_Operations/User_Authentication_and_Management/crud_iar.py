from db import get_db_connection

from datetime import datetime

def create_iar_record(po_id, iar_number, iar_date, is_partial, inspected_by, supply_officer, received_items, remarks=""):
    """
    Creates IAR header + items, increments stock, and updates PO status.
    received_items: list of dicts [{'product_id':1,'received_quantity':5,'unit_price':100.00}, ...]
    Returns (True, iar_id) or (False, error_msg)
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Ensure purchase_orders status can hold Completed/Partial (expand ENUM if needed)
        try:
            cursor.execute("ALTER TABLE purchase_orders MODIFY COLUMN status ENUM('Issued','Delivered','Cancelled','Completed','Partial','Partially Delivered') DEFAULT 'Issued';")
        except Exception:
            pass

        # 1. Insert header into iar_deliveries
        cursor.execute("""
            INSERT INTO iar_deliveries (iar_number, po_id, iar_date, is_partial, inspected_by, supply_officer, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (iar_number, po_id, iar_date, 1 if is_partial else 0, inspected_by, supply_officer, remarks))
        iar_id = cursor.lastrowid

        # 2. Insert line items + stock increment
        for it in received_items:
            product_id = int(it['product_id'])
            recv_qty = int(it['received_quantity'])
            unit_price = float(it['unit_price'])
            total_price = recv_qty * unit_price

            cursor.execute("""
                INSERT INTO iar_items (iar_id, product_id, received_quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (iar_id, product_id, recv_qty, unit_price, total_price))

            # 3. Stock increment
            cursor.execute("UPDATE products SET current_stock = current_stock + %s WHERE product_id = %s", (recv_qty, product_id))
            # Also keep starting_stock in sync if it's 0? Keep current_stock only as per spec
            # Update quantity legacy column for backwards compat
            try:
                cursor.execute("UPDATE products SET quantity = current_stock WHERE product_id = %s", (product_id,))
            except Exception:
                pass

        # 4. Check if total received matches PO ordered quantities
        cursor.execute("SELECT COALESCE(SUM(quantity),0) AS ordered FROM po_items WHERE po_id=%s", (po_id,))
        ordered_row = cursor.fetchone()
        ordered_total = int(ordered_row['ordered'] or 0) if ordered_row else 0

        cursor.execute("""
            SELECT COALESCE(SUM(ii.received_quantity),0) AS received
            FROM iar_items ii
            JOIN iar_deliveries id ON ii.iar_id = id.iar_id
            WHERE id.po_id=%s
        """, (po_id,))
        recv_row = cursor.fetchone()
        received_total = int(recv_row['received'] or 0) if recv_row else 0

        # Set status: Completed if fully received, else Partial
        new_status = 'Completed' if (ordered_total > 0 and received_total >= ordered_total) else 'Partial'
        # Map to existing ENUM values if needed: Completed -> Delivered, Partial -> Partially Delivered
        # But we expanded ENUM above to allow Completed/Partial directly
        try:
            cursor.execute("UPDATE purchase_orders SET status=%s WHERE po_id=%s", (new_status, po_id))
        except Exception:
            # Fallback to Delivered/Issued if ENUM not expanded
            fallback = 'Delivered' if new_status == 'Completed' else 'Issued'
            cursor.execute("UPDATE purchase_orders SET status=%s WHERE po_id=%s", (fallback, po_id))

        conn.commit()
        return True, iar_id

    except Exception as err:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[create_iar_record] DB error: {err}")
        return False, str(err)
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


def get_iar_by_po(po_id):
    """Helper to fetch IARs for a PO"""
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM iar_deliveries WHERE po_id=%s ORDER BY iar_id DESC", (po_id,))
        return cur.fetchall()
    except Exception as e:
        print(f"[get_iar_by_po] {e}")
        return []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass
