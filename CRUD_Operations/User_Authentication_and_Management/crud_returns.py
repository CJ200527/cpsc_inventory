"""crud_returns.py — Return Slip Workflow (finalized schema)
Return = taking items OUT of inventory (like Withdrawal).
Staff creates return directly from products,
Admin approves → deducts exact returned_quantity from products.current_stock, logs stock_movements.
`return` linked back to `withdraw` via withdraw_id (optional reference to an Approved RIS).
No DDL in this module — schema is finalized, DO NOT create/modify tables.
All queries use finalized singular tables `return` and `return_items`.
"""

from db import get_db_connection
from datetime import datetime

STOCK_COL = "current_stock"

def get_issued_withdrawals():
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        cur.execute("""
            SELECT w.withdraw_id, w.ris_number, w.department, w.purpose,
                   u.Firstname, u.Lastname
            FROM `withdraw` w
            JOIN users u ON w.user_id = u.id
            WHERE w.status='Approved'
            ORDER BY w.withdraw_id DESC
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"[get_issued_withdrawals] {e}")
        return []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def get_return_products():
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        cur.execute("""
            SELECT p.product_id, p.product_name, p.category, p.details, p.unit, p.size, p.price,
                   COALESCE(p.current_stock, p.quantity,0) AS current_stock
            FROM products p
            ORDER BY p.product_name ASC
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"[get_return_products] {e}")
        return []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def create_return(user_id, return_number, withdraw_id, department, reason, date_returned, items_list):
    """
    items_list: [{'product_id':1,'returned_quantity':2,'condition_status':'Serviceable'}, ...]
    withdraw_id: optional reference to an Approved `withdraw` row (kept for traceability).
    Validates returned <= current_stock, inserts Pending.
    """
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        if not return_number or not department or not reason:
            return False, "Return Slip Number, Department and Reason are required."
        if not items_list:
            return False, "Add at least one item."
        cur.execute("SELECT return_id FROM `return` WHERE return_number=%s", (return_number,))
        if cur.fetchone():
            return False, f"Return Number '{return_number}' already exists."
        # Handle withdraw_id empty string — must reference Approved withdraw if given
        wid = None
        if withdraw_id:
            try:
                wid=int(withdraw_id)
                cur.execute("SELECT withdraw_id FROM `withdraw` WHERE withdraw_id=%s AND status='Approved'", (wid,))
                if not cur.fetchone():
                    return False, "Referenced RIS must be Approved."
            except:
                return False, "Invalid RIS reference."
        else:
            wid=None
        # Validate items - Return is OUT of inventory, like Withdrawal
        for it in items_list:
            try:
                pid=int(it['product_id']); qty=int(it['returned_quantity']); cond=it.get('condition_status','Serviceable')
            except:
                return False, "Invalid item data."
            if qty<=0:
                return False, "Returned quantity must be >0."
            if cond not in ('Serviceable','Unserviceable'):
                return False, "Invalid condition."
            cur.execute("SELECT product_name, COALESCE(current_stock, quantity, 0) AS cur_stock FROM products WHERE product_id=%s", (pid,))
            prod = cur.fetchone()
            if not prod:
                return False, f"Product {pid} not found."
            cur_stock = int(prod['cur_stock'] or 0)
            if qty > cur_stock:
                return False, f"Insufficient stock for '{prod['product_name']}': trying to return {qty} but only {cur_stock} available in inventory."
        if not date_returned:
            date_returned=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif len(date_returned)==10:
            date_returned+=" 00:00:00"
        cur.execute("""
            INSERT INTO `return` (return_number, withdraw_id, user_id, department, reason, status, date_returned)
            VALUES (%s,%s,%s,%s,%s,'Pending',%s)
        """, (return_number, wid, user_id, department, reason, date_returned))
        rid=cur.lastrowid
        for it in items_list:
            pid=int(it['product_id']); qty=int(it['returned_quantity']); cond=it.get('condition_status','Serviceable')
            cur.execute("SELECT product_name, unit, price FROM products WHERE product_id=%s", (pid,))
            prod=cur.fetchone()
            iname=prod['product_name']; unit=prod['unit'] or 'pcs'; price=float(prod['price'] or 0)
            total=qty*price
            cur.execute("""
                INSERT INTO return_items (return_id, product_id, item_name, returned_quantity, condition_status, unit, unit_price, total_price)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (rid, pid, iname, qty, cond, unit, price, total))
        conn.commit()
        return True, rid
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[create_return] {e}")
        return False, str(e)
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def get_all_returns(search_query="", status_filter="All", user_id=None):
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        sql="""
            SELECT r.return_id, r.return_number, r.withdraw_id, r.department, r.reason, r.status, r.approved_by, r.date_returned,
                   u.Firstname, u.Lastname, u.username,
                   au.Firstname AS approver_first, au.Lastname AS approver_last,
                   w.ris_number,
                   (SELECT COALESCE(SUM(ri.returned_quantity),0) FROM return_items ri WHERE ri.return_id=r.return_id) AS total_qty,
                   (SELECT COALESCE(SUM(ri.total_price),0) FROM return_items ri WHERE ri.return_id=r.return_id) AS total_amount
            FROM `return` r
            JOIN users u ON r.user_id = u.id
            LEFT JOIN users au ON r.approved_by = au.id
            LEFT JOIN `withdraw` w ON r.withdraw_id = w.withdraw_id
            WHERE 1=1
        """
        params=[]
        if user_id:
            sql+=" AND r.user_id=%s"
            params.append(user_id)
        if status_filter!="All":
            sql+=" AND r.status=%s"
            params.append(status_filter)
        if search_query:
            pat=f"%{search_query}%"
            sql+=""" AND (
                r.return_number LIKE %s OR w.ris_number LIKE %s OR r.department LIKE %s OR r.reason LIKE %s
                OR u.Firstname LIKE %s OR u.Lastname LIKE %s
            )"""
            params.extend([pat]*6)
        sql+=" ORDER BY r.return_id DESC"
        cur.execute(sql, tuple(params))
        return cur.fetchall()
    except Exception as e:
        print(f"[get_all_returns] {e}")
        return []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def get_return_details(return_id):
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        cur.execute("""
            SELECT r.*, u.Firstname, u.Lastname, u.username,
                   au.Firstname AS approver_first, au.Lastname AS approver_last,
                   w.ris_number, w.department AS w_department
            FROM `return` r
            JOIN users u ON r.user_id = u.id
            LEFT JOIN users au ON r.approved_by = au.id
            LEFT JOIN `withdraw` w ON r.withdraw_id = w.withdraw_id
            WHERE r.return_id=%s
        """, (return_id,))
        header=cur.fetchone()
        if not header:
            return None, []
        cur.execute("""
            SELECT ri.*, p.product_name, p.category, p.details, p.unit AS p_unit, p.price AS p_price,
                   COALESCE(p.current_stock, p.quantity,0) AS cur_stock
            FROM return_items ri
            LEFT JOIN products p ON ri.product_id = p.product_id
            WHERE ri.return_id=%s
        """, (return_id,))
        items=cur.fetchall()
        return header, items
    except Exception as e:
        print(f"[get_return_details] {e}")
        return None, []
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def approve_return(return_id, admin_user_id):
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM `return` WHERE return_id=%s", (return_id,))
        header=cur.fetchone()
        if not header:
            return False, "Return not found."
        if header['status'] != 'Pending':
            return False, f"Only Pending can be approved. Current: {header['status']}"
        cur.execute("SELECT * FROM return_items WHERE return_id=%s", (return_id,))
        items=cur.fetchall()
        if not items:
            return False, "No items."
        for it in items:
            pid=int(it['product_id']); qty=int(it['returned_quantity']); cond=it['condition_status']
            if cond == 'Serviceable':
                # DEDUCT stock (Return OUT of inventory, like Withdrawal)
                cur.execute(f"SELECT COALESCE({STOCK_COL},0) AS chk_stock FROM products WHERE product_id=%s", (pid,))
                chk = int(cur.fetchone()['chk_stock'] or 0)
                if qty > chk:
                    return False, f"Insufficient stock to return '{it['item_name']}': need {qty}, have {chk}."
                cur.execute(f"UPDATE products SET {STOCK_COL} = {STOCK_COL} - %s WHERE product_id=%s", (qty, pid))
                try:
                    cur.execute("UPDATE products SET quantity = current_stock WHERE product_id=%s", (pid,))
                except: pass
                # Balance after
                cur.execute(f"SELECT COALESCE({STOCK_COL},0) AS bal FROM products WHERE product_id=%s", (pid,))
                bal=int(cur.fetchone()['bal'] or 0)
                cur.execute("""
                    INSERT INTO stock_movements (product_id, reference_type, reference_id, quantity_change, balance_after, user_id)
                    VALUES (%s,'Return',%s,%s,%s,%s)
                """, (pid, return_id, -qty, bal, admin_user_id))
            else:
                # Unserviceable: log for audit with 0 change
                cur.execute(f"SELECT COALESCE({STOCK_COL},0) AS bal FROM products WHERE product_id=%s", (pid,))
                bal=int(cur.fetchone()['bal'] or 0)
                cur.execute("""
                    INSERT INTO stock_movements (product_id, reference_type, reference_id, quantity_change, balance_after, user_id)
                    VALUES (%s,'Return-Unserviceable',%s,0,%s,%s)
                """, (pid, return_id, bal, admin_user_id))
        cur.execute("UPDATE `return` SET status='Approved', approved_by=%s WHERE return_id=%s", (admin_user_id, return_id))
        conn.commit()
        return True, f"Return {header['return_number']} approved. Serviceable items deducted from stock (like Withdrawal)."
    except Exception as e:
        if conn:
            try: conn.rollback()
            except: pass
        print(f"[approve_return] {e}")
        return False, str(e)
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

def reject_return(return_id, admin_user_id):
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute("SELECT status FROM `return` WHERE return_id=%s", (return_id,))
        row=cur.fetchone()
        if not row:
            return False, "Not found."
        status=row[0] if isinstance(row, tuple) else row['status']
        if status != 'Pending':
            return False, f"Only Pending can be rejected. Current: {status}"
        cur.execute("UPDATE `return` SET status='Rejected', approved_by=%s WHERE return_id=%s", (admin_user_id, return_id))
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
