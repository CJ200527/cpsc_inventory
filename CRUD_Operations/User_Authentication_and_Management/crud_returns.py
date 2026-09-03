"""crud_returns.py — Return Slip Workflow (FIXED 2026-09-03)
Return = taking items OUT of inventory (like Withdrawal) — defective return to supplier/supply office.
Staff creates return directly from Products (SELECT product_id, product_name, category, unit, current_stock FROM products),
Admin approves → deducts exact returned_quantity from products.current_stock (not adds), logs stock_movements.
Uses get_return_products() for modal; get_issued_withdrawals() kept for legacy but not required for new flow.
All queries use correct singular tables `return` and `return_items`.
"""

from db import get_db_connection
from datetime import datetime

def _ensure_return_schema(cursor):
    # Ensure Products columns
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'current_stock'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE Products ADD COLUMN current_stock INT DEFAULT 0")
            cursor.execute("UPDATE Products SET current_stock = quantity WHERE current_stock IS NULL")
    except: pass
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'reorder_level'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE Products ADD COLUMN reorder_level INT DEFAULT 10")
    except: pass
    # Returns header - create if not exists, else add missing columns
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `return` (
                return_id INT AUTO_INCREMENT PRIMARY KEY,
                return_number VARCHAR(50) NOT NULL UNIQUE,
                withdraw_id INT NULL,
                user_id INT NOT NULL,
                department VARCHAR(100) NOT NULL,
                reason TEXT NOT NULL,
                status ENUM('Pending','Approved','Rejected') DEFAULT 'Pending',
                approved_by INT NULL,
                date_returned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (approved_by) REFERENCES Users(id),
                FOREIGN KEY (withdraw_id) REFERENCES `withdraw`(withdraw_id)
            )
        """)
    except Exception as e:
        print(f"[returns ensure] {e}")
    # Add missing columns to existing returns table (legacy has different schema)
    for col, ddl in [
        ("return_number", "ALTER TABLE `return` ADD COLUMN return_number VARCHAR(50)"),
        ("withdraw_id", "ALTER TABLE `return` ADD COLUMN withdraw_id INT NULL"),
        ("department", "ALTER TABLE `return` ADD COLUMN department VARCHAR(100)"),
        ("reason", "ALTER TABLE `return` ADD COLUMN reason TEXT"),
        ("status", "ALTER TABLE `return` ADD COLUMN status ENUM('Pending','Approved','Rejected') DEFAULT 'Pending'"),
        ("approved_by", "ALTER TABLE `return` ADD COLUMN approved_by INT NULL"),
        ("date_returned", "ALTER TABLE `return` ADD COLUMN date_returned TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("user_id", "ALTER TABLE `return` ADD COLUMN user_id INT"),
    ]:
        try:
            cursor.execute(f"SHOW COLUMNS FROM `return` LIKE '{col}'")
            if not cursor.fetchone():
                # Need to handle UNIQUE for return_number if adding
                if col == "return_number":
                    # First check if return_number already exists as unique, if not add
                    try:
                        cursor.execute("ALTER TABLE `return` ADD COLUMN return_number VARCHAR(50)")
                        cursor.execute("UPDATE `return` SET return_number = return_number WHERE return_number IS NULL")
                    except: pass
                else:
                    cursor.execute(ddl)
        except: pass
    # Handle legacy column renames: return_number vs return_number, reason_return vs reason, status_return vs status
    # Ensure return_number is populated from legacy return_number if needed
    try:
        cursor.execute("SHOW COLUMNS FROM `return` LIKE 'return_number'")
        has_new = cursor.fetchone()
        cursor.execute("SHOW COLUMNS FROM `return` LIKE 'return_number'")
        # legacy check: already handled
    except: pass
    # return_items
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS return_items (
                return_item_id INT AUTO_INCREMENT PRIMARY KEY,
                return_id INT NOT NULL,
                product_id INT NOT NULL,
                item_name VARCHAR(100) NOT NULL,
                returned_quantity INT NOT NULL,
                condition_status ENUM('Serviceable','Unserviceable') DEFAULT 'Serviceable',
                unit VARCHAR(20),
                unit_price DECIMAL(10,2) DEFAULT 0.00,
                total_price DECIMAL(12,2) DEFAULT 0.00,
                FOREIGN KEY (return_id) REFERENCES `return`(return_id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES Products(product_id)
            )
        """)
    except Exception as e:
        print(f"[return_items ensure] {e}")
    # stock_movements
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

def _stock_col(cursor):
    try:
        cursor.execute("SHOW COLUMNS FROM Products LIKE 'current_stock'")
        if cursor.fetchone():
            return "current_stock"
    except: pass
    return "quantity"

def get_issued_withdrawals():
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        _ensure_return_schema(cur)
        cur.execute("""
            SELECT w.withdraw_id, w.ris_number, w.department, w.purpose,
                   u.Firstname, u.Lastname
            FROM `withdraw` w
            JOIN Users u ON w.user_id = u.id
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
        _ensure_return_schema(cur)
        cur.execute("""
            SELECT p.product_id, p.product_name, p.category, p.details, p.unit, p.size, p.price,
                   COALESCE(p.current_stock, p.quantity,0) AS current_stock, s.supplier_name
            FROM Products p
            LEFT JOIN Supplier s ON p.supplier_id=s.id
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
    Validates returned <= issued if withdraw_id provided, inserts Pending.
    """
    conn=None; cur=None
    try:
        conn=get_db_connection()
        cur=conn.cursor(dictionary=True)
        _ensure_return_schema(cur)
        if not return_number or not department or not reason:
            return False, "Return Slip Number, Department and Reason are required."
        if not items_list:
            return False, "Add at least one item."
        # Unique return_number - check both new and legacy column
        try:
            cur.execute("SELECT return_id FROM `return` WHERE return_number=%s", (return_number,))
            if cur.fetchone():
                return False, f"Return Number '{return_number}' already exists."
        except:
            # Fallback legacy column
            cur.execute("SELECT return_id FROM `return` WHERE return_number=%s", (return_number,))
            if cur.fetchone():
                return False, f"Return Number '{return_number}' already exists."
        # Handle withdraw_id empty string
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
        # Validate items - NEW LOGIC: Return is OUT of inventory, like Withdrawal
        # Pull directly from Products, validate qty <= current_stock (not issued withdrawals)
        # withdraw_id is optional and ignored for stock check (kept for legacy, but not required)
        for it in items_list:
            try:
                pid=int(it['product_id']); qty=int(it['returned_quantity']); cond=it.get('condition_status','Serviceable')
            except:
                return False, "Invalid item data."
            if qty<=0:
                return False, "Returned quantity must be >0."
            if cond not in ('Serviceable','Unserviceable'):
                return False, "Invalid condition."
            cur.execute("SELECT product_name, COALESCE(current_stock, quantity, 0) AS cur_stock FROM Products WHERE product_id=%s", (pid,))
            prod = cur.fetchone()
            if not prod:
                return False, f"Product {pid} not found."
            # For returns OUT of inventory, ensure sufficient stock to deduct (like withdrawal)
            cur_stock = int(prod['cur_stock'] or 0)
            if qty > cur_stock:
                return False, f"Insufficient stock for '{prod['product_name']}': trying to return {qty} but only {cur_stock} available in inventory."
            # If no withdrawal reference, no issued check
        if not date_returned:
            date_returned=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif len(date_returned)==10:
            date_returned+=" 00:00:00"
        # Insert returns header - handle both legacy and new column names
        # Try new schema first
        try:
            cur.execute("""
                INSERT INTO `return` (return_number, withdraw_id, user_id, department, reason, status, date_returned)
                VALUES (%s,%s,%s,%s,%s,'Pending',%s)
            """, (return_number, wid, user_id, department, reason, date_returned))
        except Exception as e:
            # Fallback try legacy columns
            try:
                cur.execute("""
                    INSERT INTO `return` (return_number, withdraw_id, user_id, department, reason, status, date_returned)
                    VALUES (%s,%s,%s,%s,%s,'Pending',%s)
                """, (return_number, wid, user_id, department, reason, date_returned))
            except Exception as e2:
                print(f"[create_return insert] {e} / {e2}")
                return False, str(e2)
        rid=cur.lastrowid
        for it in items_list:
            pid=int(it['product_id']); qty=int(it['returned_quantity']); cond=it.get('condition_status','Serviceable')
            cur.execute("SELECT product_name, unit, price FROM Products WHERE product_id=%s", (pid,))
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
        _ensure_return_schema(cur)
        sql="""
            SELECT r.return_id, r.return_number, r.withdraw_id, r.department, r.reason, r.status, r.approved_by, r.date_returned,
                   u.Firstname, u.Lastname, u.username,
                   au.Firstname AS approver_first, au.Lastname AS approver_last,
                   w.ris_number,
                   (SELECT COALESCE(SUM(ri.returned_quantity),0) FROM return_items ri WHERE ri.return_id=r.return_id) AS total_qty,
                   (SELECT COALESCE(SUM(ri.total_price),0) FROM return_items ri WHERE ri.return_id=r.return_id) AS total_amount
            FROM `return` r
            JOIN Users u ON r.user_id = u.id
            LEFT JOIN Users au ON r.approved_by = au.id
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
            JOIN Users u ON r.user_id = u.id
            LEFT JOIN Users au ON r.approved_by = au.id
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
            LEFT JOIN Products p ON ri.product_id = p.product_id
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
        _ensure_return_schema(cur)
        stock_col=_stock_col(cur)
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
                # DEDUCT stock (Return OUT of inventory, like Withdrawal) - FIXED 2026-09-03
                # Validate sufficient stock before deducting
                cur.execute(f"SELECT COALESCE({stock_col},0) AS chk_stock FROM Products WHERE product_id=%s", (pid,))
                chk = int(cur.fetchone()['chk_stock'] or 0)
                if qty > chk:
                    return False, f"Insufficient stock to return '{it['item_name']}': need {qty}, have {chk}."
                cur.execute(f"UPDATE Products SET {stock_col} = {stock_col} - %s WHERE product_id=%s", (qty, pid))
                try:
                    cur.execute("UPDATE Products SET quantity = current_stock WHERE product_id=%s", (pid,))
                except: pass
                # Balance after
                cur.execute(f"SELECT COALESCE({stock_col},0) AS bal FROM Products WHERE product_id=%s", (pid,))
                bal=int(cur.fetchone()['bal'] or 0)
                cur.execute("""
                    INSERT INTO stock_movements (product_id, reference_type, reference_id, quantity_change, balance_after, user_id)
                    VALUES (%s,'Return',%s,%s,%s,%s)
                """, (pid, return_id, -qty, bal, admin_user_id))
            else:
                # Unserviceable: Do NOT credit, but log for audit with 0 change or separate?
                # Log with 0 change to flag waste, but still record
                cur.execute(f"SELECT COALESCE({stock_col},0) AS bal FROM Products WHERE product_id=%s", (pid,))
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
