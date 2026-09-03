"""crud_withdrawal.py — RIS Withdrawal Workflow (Study Guide)
Staff creates withdrawal (Request Withdraw), Admin approves/rejects, deducts stock via Products.current_stock.
Uses get_available_products() for modal and get_all_withdrawals() for tables.

FIXED 2026-09-03: Now uses ONLY the correct schema tables `withdraw` and `withdraw_items`
as per your strict DB (withdraw_id PK, ris_number, user_id, department, purpose, status, issued_by, received_by, date_requested, date_issued)
and (withdraw_item_id PK, withdraw_id FK, product_id, item_name, quantity, unit, unit_price, total_price).
Legacy tables `withdrawals` / `withdrawal_items` are NOT used to prevent 1452 FK errors.
"""

from db import get_db_connection
from datetime import datetime

def _ensure_withdrawal_schema(cursor):
    """Ensure Products stock columns and `withdraw` / `withdraw_items` exist with EXACT spec columns."""
    # Ensure Products has current_stock and reorder_level
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'current_stock'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE Products ADD COLUMN current_stock INT DEFAULT 0")
            cursor.execute("UPDATE Products SET current_stock = quantity WHERE current_stock IS NULL")
    except Exception:
        pass
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'reorder_level'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE Products ADD COLUMN reorder_level INT DEFAULT 10")
    except Exception:
        pass
    # Ensure parent `withdraw` exists with exact spec columns
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `withdraw` (
                withdraw_id INT AUTO_INCREMENT PRIMARY KEY,
                ris_number VARCHAR(50) NOT NULL UNIQUE,
                user_id INT NOT NULL,
                department VARCHAR(100) NOT NULL,
                purpose TEXT NOT NULL,
                status ENUM('Pending','Approved','Rejected','Issued') DEFAULT 'Pending',
                issued_by INT NULL,
                received_by VARCHAR(100),
                date_requested TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_issued DATETIME NULL,
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (issued_by) REFERENCES Users(id)
            )
        """)
    except Exception as e:
        print(f"[withdraw ensure] parent: {e}")
    # Ensure child `withdraw_items` exists with exact spec columns and FK to `withdraw`
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `withdraw_items` (
                withdraw_item_id INT AUTO_INCREMENT PRIMARY KEY,
                withdraw_id INT NOT NULL,
                product_id INT NOT NULL,
                item_name VARCHAR(100) NOT NULL,
                quantity INT NOT NULL,
                unit VARCHAR(20),
                unit_price DECIMAL(10,2) DEFAULT 0.00,
                total_price DECIMAL(12,2) DEFAULT 0.00,
                FOREIGN KEY (withdraw_id) REFERENCES `withdraw`(withdraw_id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES Products(product_id)
            )
        """)
    except Exception as e:
        print(f"[withdraw ensure] child: {e}")
    # stock_movements log (for audit)
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
    except Exception as e:
        print(f"[withdraw ensure] movements: {e}")

def _stock_col(cursor):
    """Return the active stock column name."""
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'current_stock'")
        if cursor.fetchone():
            return "current_stock"
    except Exception:
        pass
    return "quantity"

def get_available_products():
    """Products with stock > 0 for the withdraw modal."""
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        _ensure_withdrawal_schema(cur)
        cur.execute("""
            SELECT p.product_id, p.product_name, p.category, p.details, p.unit, p.size, p.price, p.supplier_id, s.supplier_name,
                   COALESCE(p.current_stock, p.quantity, 0) AS current_stock,
                   COALESCE(p.reorder_level, 10) AS reorder_level
            FROM Products p
            LEFT JOIN Supplier s ON p.supplier_id = s.id
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
    Validates requested <= current_stock, inserts Pending into `withdraw` + `withdraw_items` ONLY (no legacy tables), no deduction.
    Returns (True, withdrawal_id) or (False, msg)
    """
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        _ensure_withdrawal_schema(cur)
        stock_col=_stock_col(cur)
        if not ris_number or not department or not purpose:
            return False, "RIS Number, Department and Purpose are required."
        if not items_list:
            return False, "Add at least one item."
        # Unique RIS - check ONLY `withdraw` (your strict table)
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
            cur.execute(f"SELECT product_name, {stock_col} AS cur_stock, price, unit FROM Products WHERE product_id=%s", (pid,))
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
        # Insert header into `withdraw` ONLY
        cur.execute("""
            INSERT INTO `withdraw` (ris_number, user_id, department, purpose, status, received_by, date_requested)
            VALUES (%s,%s,%s,%s,'Pending',%s,%s)
        """, (ris_number, user_id, department, purpose, received_by or "", date_requested))
        wid=cur.lastrowid
        # Insert items into `withdraw_items` ONLY
        for it in items_list:
            pid=int(it['product_id']); qty=int(it['quantity'])
            cur.execute("SELECT product_name, unit, price FROM Products WHERE product_id=%s", (pid,))
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
    """Fetch from `withdraw` + `withdraw_items` ONLY."""
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        _ensure_withdrawal_schema(cur)
        sql="""
            SELECT w.withdraw_id, w.ris_number, w.department, w.purpose, w.status, w.issued_by, w.received_by, w.date_requested, w.date_issued,
                   u.Firstname, u.Lastname, u.username,
                   iu.Firstname AS issuer_first, iu.Lastname AS issuer_last,
                   (SELECT COALESCE(SUM(wi.quantity),0) FROM `withdraw_items` wi WHERE wi.withdraw_id=w.withdraw_id) AS total_qty,
                   (SELECT COALESCE(SUM(wi.total_price),0) FROM `withdraw_items` wi WHERE wi.withdraw_id=w.withdraw_id) AS total_amount
            FROM `withdraw` w
            JOIN Users u ON w.user_id = u.id
            LEFT JOIN Users iu ON w.issued_by = iu.id
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
    """Fetch header + items from `withdraw` / `withdraw_items` ONLY."""
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        cur.execute("""
            SELECT w.*, u.Firstname, u.Lastname, u.username,
                   iu.Firstname AS issuer_first, iu.Lastname AS issuer_last
            FROM `withdraw` w
            JOIN Users u ON w.user_id = u.id
            LEFT JOIN Users iu ON w.issued_by = iu.id
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
            LEFT JOIN Products p ON wi.product_id = p.product_id
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
        _ensure_withdrawal_schema(cur)
        stock_col=_stock_col(cur)
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
            cur.execute(f"SELECT COALESCE({stock_col},0) AS cur_stock, COALESCE(reorder_level,10) AS reorder_lvl, product_name FROM Products WHERE product_id=%s", (pid,))
            prod=cur.fetchone()
            cur_stock=int(prod['cur_stock'] or 0)
            if qty > cur_stock:
                return False, f"Insufficient stock for '{prod['product_name']}': need {qty}, have {cur_stock}."
        # Deduct exact quantity
        for it in items:
            pid=int(it['product_id']); qty=int(it['quantity'])
            cur.execute(f"UPDATE Products SET {stock_col} = {stock_col} - %s WHERE product_id=%s", (qty, pid))
            try:
                cur.execute("UPDATE Products SET quantity = current_stock WHERE product_id=%s", (pid,))
            except: pass
            cur.execute(f"SELECT COALESCE({stock_col},0) AS bal FROM Products WHERE product_id=%s", (pid,))
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
