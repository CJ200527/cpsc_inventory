"""crud_withdrawal.py — RIS Withdrawal Workflow (finalized schema)
Staff creates withdrawal, Admin approves/rejects, deducts stock via products.current_stock.
Uses ONLY the finalized tables `withdraw` and `withdraw_items`
(withdraw_id PK, ris_number, user_id, department, purpose, status, issued_by, received_by, date_requested, date_issued)
and (withdraw_item_id PK, withdraw_id FK, product_id, item_name, quantity, unit, unit_price, total_price).
No DDL in this module — schema is finalized, DO NOT create/modify tables.
"""

from db import get_db_connection
from datetime import datetime

STOCK_COL = "current_stock"

def get_available_products():
    """Products with stock > 0 for the withdraw modal."""
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        cur.execute("""
            SELECT p.product_id, p.product_name, p.category, p.details, p.unit, p.size, p.price,
                   COALESCE(p.current_stock, p.quantity, 0) AS current_stock,
                   COALESCE(p.reorder_level, 10) AS reorder_level
            FROM products p
            WHERE COALESCE(p.current_stock, p.quantity, 0) > 0
            ORDER BY p.product_name ASC
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"[get_available_products] {e}")
        return []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def create_withdrawal(user_id, ris_number, department, purpose, received_by, date_requested, items_list):
    """
    items_list: [{'product_id':1,'quantity':5}, ...]
    Validates requested <= current_stock, inserts Pending into `withdraw` + `withdraw_items`, no deduction.
    Returns (True, withdrawal_id) or (False, msg)
    """
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        if not ris_number or not department or not purpose:
            return False, "RIS Number, Department and Purpose are required."
        if not items_list:
            return False, "Add at least one item."
        # Unique RIS
        cur.execute("SELECT withdraw_id FROM `withdraw` WHERE ris_number=%s", (ris_number,))
        if cur.fetchone():
            return False, f"RIS Number '{ris_number}' already exists."
        # Validate stock for each item
        for it in items_list:
            try:
                pid=int(it['product_id']); qty=int(it['quantity'])
            except:
                return False, "Invalid item data."
            if qty <=0:
                return False, "Quantity must be >0."
            cur.execute(f"SELECT product_name, {STOCK_COL} AS cur_stock, price, unit FROM products WHERE product_id=%s", (pid,))
            prod=cur.fetchone()
            if not prod:
                return False, f"Product ID {pid} not found."
            cur_stock=int(prod['cur_stock'] or 0)
            if qty > cur_stock:
                return False, f"Insufficient stock for '{prod['product_name']}': requested {qty} > available {cur_stock}."
        # Normalize date
        if not date_requested:
            date_requested = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif len(date_requested)==10:
            date_requested += " 00:00:00"
        # Insert header into `withdraw`
        cur.execute("""
            INSERT INTO `withdraw` (ris_number, user_id, department, purpose, status, received_by, date_requested)
            VALUES (%s,%s,%s,%s,'Pending',%s,%s)
        """, (ris_number, user_id, department, purpose, received_by or "", date_requested))
        wid=cur.lastrowid
        # Insert items into `withdraw_items`
        for it in items_list:
            pid=int(it['product_id']); qty=int(it['quantity'])
            cur.execute("SELECT product_name, unit, price FROM products WHERE product_id=%s", (pid,))
            prod=cur.fetchone()
            iname=prod['product_name']
            unit=prod['unit'] or 'pcs'
            price=float(prod['price'] or 0)
            total=qty*price
            cur.execute("""
                INSERT INTO `withdraw_items` (withdraw_id, product_id, item_name, quantity, unit, unit_price, total_price)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (wid, pid, iname, qty, unit, price, total))
        conn.commit()
        return True, wid
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[create_withdrawal] {e}")
        return False, str(e)
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def get_all_withdrawals(search_query="", status_filter="All", user_id=None):
    """Fetch from `withdraw` + `withdraw_items`."""
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        sql="""
            SELECT w.withdraw_id, w.ris_number, w.department, w.purpose, w.status, w.issued_by, w.received_by, w.date_requested, w.date_issued,
                   u.Firstname, u.Lastname, u.username,
                   iu.Firstname AS issuer_first, iu.Lastname AS issuer_last,
                   (SELECT COALESCE(SUM(wi.quantity),0) FROM `withdraw_items` wi WHERE wi.withdraw_id=w.withdraw_id) AS total_qty,
                   (SELECT COALESCE(SUM(wi.total_price),0) FROM `withdraw_items` wi WHERE wi.withdraw_id=w.withdraw_id) AS total_amount
            FROM `withdraw` w
            JOIN users u ON w.user_id = u.id
            LEFT JOIN users iu ON w.issued_by = iu.id
            WHERE 1=1
        """
        params=[]
        if user_id:
            sql+=" AND w.user_id=%s"
            params.append(user_id)
        if status_filter!="All":
            sql+=" AND w.status=%s"
            params.append(status_filter)
        if search_query:
            pat=f"%{search_query}%"
            sql+=""" AND (
                w.ris_number LIKE %s OR w.department LIKE %s OR w.purpose LIKE %s
                OR u.Firstname LIKE %s OR u.Lastname LIKE %s
            )"""
            params.extend([pat]*5)
        sql+=" ORDER BY w.withdraw_id DESC"
        cur.execute(sql, tuple(params))
        return cur.fetchall()
    except Exception as e:
        print(f"[get_all_withdrawals] {e}")
        return []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def get_withdrawal_details(withdraw_id):
    """Fetch header + items from `withdraw` / `withdraw_items`."""
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        cur.execute("""
            SELECT w.*, u.Firstname, u.Lastname, u.username,
                   iu.Firstname AS issuer_first, iu.Lastname AS issuer_last
            FROM `withdraw` w
            JOIN users u ON w.user_id = u.id
            LEFT JOIN users iu ON w.issued_by = iu.id
            WHERE w.withdraw_id=%s
        """, (withdraw_id,))
        header=cur.fetchone()
        if not header:
            return None, []
        cur.execute("""
            SELECT wi.*, p.product_name, p.category, p.details, p.unit AS p_unit, p.price AS p_price,
                   COALESCE(p.current_stock, p.quantity,0) AS cur_stock,
                   COALESCE(p.reorder_level,10) AS reorder_lvl
            FROM `withdraw_items` wi
            LEFT JOIN products p ON wi.product_id = p.product_id
            WHERE wi.withdraw_id=%s
        """, (withdraw_id,))
        items=cur.fetchall()
        return header, items
    except Exception as e:
        print(f"[get_withdrawal_details] {e}")
        return None, []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def approve_withdrawal(withdraw_id, admin_user_id):
    """Approve Pending → deduct exact quantity from current_stock, log movement. Guard: only Pending."""
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM `withdraw` WHERE withdraw_id=%s", (withdraw_id,))
        header=cur.fetchone()
        if not header:
            return False, "Withdrawal not found."
        if header['status'] != 'Pending':
            return False, f"Only Pending can be approved. Current: {header['status']}"
        cur.execute("SELECT * FROM `withdraw_items` WHERE withdraw_id=%s", (withdraw_id,))
        items=cur.fetchall()
        if not items:
            return False, "No items."
        # Re-validate stock before deduction (exact qty guard)
        for it in items:
            pid=int(it['product_id']); qty=int(it['quantity'])
            cur.execute(f"SELECT COALESCE({STOCK_COL},0) AS cur_stock, COALESCE(reorder_level,10) AS reorder_lvl, product_name FROM products WHERE product_id=%s", (pid,))
            prod=cur.fetchone()
            cur_stock=int(prod['cur_stock'] or 0)
            if qty > cur_stock:
                return False, f"Insufficient stock for '{prod['product_name']}': need {qty}, have {cur_stock}."
        # Deduct exact quantity
        for it in items:
            pid=int(it['product_id']); qty=int(it['quantity'])
            cur.execute(f"UPDATE products SET {STOCK_COL} = {STOCK_COL} - %s WHERE product_id=%s", (qty, pid))
            try:
                cur.execute("UPDATE products SET quantity = current_stock WHERE product_id=%s", (pid,))
            except: pass
            cur.execute(f"SELECT COALESCE({STOCK_COL},0) AS bal FROM products WHERE product_id=%s", (pid,))
            bal=int(cur.fetchone()['bal'] or 0)
            cur.execute("""
                INSERT INTO stock_movements (product_id, reference_type, reference_id, quantity_change, balance_after, user_id)
                VALUES (%s,'Withdrawal',%s,%s,%s,%s)
            """, (pid, withdraw_id, -qty, bal, admin_user_id))
        cur.execute("UPDATE `withdraw` SET status='Approved', issued_by=%s, date_issued=NOW() WHERE withdraw_id=%s", (admin_user_id, withdraw_id))
        conn.commit()
        return True, f"Withdrawal {header['ris_number']} approved. Stock deducted and logged."
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[approve_withdrawal] {e}")
        return False, str(e)
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def reject_withdrawal(withdraw_id, admin_user_id):
    """Reject Pending withdrawal."""
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute("SELECT status FROM `withdraw` WHERE withdraw_id=%s", (withdraw_id,))
        row=cur.fetchone()
        if not row:
            return False, "Not found."
        status=row[0] if isinstance(row, tuple) else row['status']
        if status != 'Pending':
            return False, f"Only Pending can be rejected. Current: {status}"
        cur.execute("UPDATE `withdraw` SET status='Rejected', issued_by=%s, date_issued=NOW() WHERE withdraw_id=%s", (admin_user_id, withdraw_id))
        conn.commit()
        return True, "Rejected."
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        return False, str(e)
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass
