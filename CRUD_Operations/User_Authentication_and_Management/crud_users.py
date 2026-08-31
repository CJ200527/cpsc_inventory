from db import get_db_connection

# --- 1. CREATE: Register New User ---
def register_user(first_name, middle_initial, last_name, username, password, role="Staff", contact_number=""):
    """Inserts a new user record (Approved_By = 0 by default). Case-sensitive username & unique contact check."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Case-Sensitive Username Check
        cursor.execute("SELECT id FROM Users WHERE BINARY username = %s", (username,))
        if cursor.fetchone():
            print(f"Username already exists (case-sensitive): {username}")
            return False
        # Unique Contact Number Validation
        cursor.execute("SELECT id FROM Users WHERE Contact_Number = %s", (contact_number,))
        if cursor.fetchone():
            print(f"Contact number already exists: {contact_number}")
            return False

        query = """
        INSERT INTO Users (Firstname, MI, Lastname, fullname, username, password, Role, Contact_Number, Approved_By)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0);
        """
        fullname = f"{first_name} {last_name}"
        cursor.execute(query, (first_name, middle_initial, last_name, fullname, username, password, role, contact_number))
        conn.commit()
        return True
    except Exception as err:
        print(f"Error registering user: {err}")
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        cursor.close()
        conn.close()

# --- 2. READ: Authenticate Login ---
def login_user(username, password):
    """Verifies credentials case-sensitive and checks if approved by Admin."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM Users WHERE BINARY username = %s AND BINARY password = %s;"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not user or user['Approved_By'] == 0:
        return None
        
    return user

# --- UPDATE: Reset Password using Username + Contact Verification ---
def reset_password_verified(username, contact_number, new_password):
    """
    Verifies that username and contact number match, then updates password.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Check if username and contact number exist together (case-sensitive username)
    query_check = "SELECT id FROM Users WHERE BINARY username = %s AND Contact_Number = %s;"
    cursor.execute(query_check, (username, contact_number))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return False  # Verification failed

    # 2. Update password (plain as per existing schema)
    query_update = "UPDATE Users SET password = %s WHERE id = %s;"
    cursor.execute(query_update, (new_password, user["id"]))
    conn.commit()

    cursor.close()
    conn.close()
    return True

# --- 3. READ: Advanced Search & Date Filter for User Management ---
def get_all_users_filtered(search_query="", date_filter="All", custom_date=""):
    """
    Fetches users matching a multi-field search and date range filters.
    Excludes password from results for security.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Base query selecting all non-sensitive user fields
    sql = """
        SELECT id AS user_id, Firstname AS first_name, MI AS middle_initial,
            Lastname AS last_name, username, Role AS role,
            Contact_Number AS contact_number, Approved_By AS is_approved,
            created_at
        FROM Users
    WHERE 1=1
    """
    params = []

    # A. Search Filter (Matches ID, names, username, role, or contact number)
    if search_query:
        search_pattern = f"%{search_query}%"
        sql += """ AND (
            id LIKE %s OR
            Firstname LIKE %s OR
            MI LIKE %s OR
            Lastname LIKE %s OR
            username LIKE %s OR 
            Role LIKE %s OR
            Contact_Number LIKE %s
        )"""
        params.extend([search_pattern] * 7)

    # B. Date Filters
    if date_filter == "Today":
        sql += " AND DATE(created_at) = CURDATE()"
    elif date_filter == "Last Month":
        sql += " AND created_at >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
    elif date_filter == "Last Year":
        sql += " AND created_at >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)"
    elif date_filter == "Custom" and custom_date:
        sql += " AND DATE(created_at) = %s"
        params.append(custom_date)

    sql += " ORDER BY id DESC;"

    cursor.execute(sql, tuple(params))
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return users

# --- 4. UPDATE: Approve User Account ---
def approve_user(user_id):
    """Sets Approved_By to 1 (Approved)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET Approved_By = 1 WHERE id = %s;", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

# --- 5. UPDATE/DELETE: Reject or Revoke User Account ---
def reject_user(user_id):
    """Sets Approved_By to 0 (Pending/Rejected)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET Approved_By = 0 WHERE id = %s;", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

def delete_user(user_id):
    """Permanently deletes a user account."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Users WHERE id = %s;", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
# --- UPDATE: Edit User Information ---
def update_user_info(user_id, first_name, middle_initial, last_name, username, role, contact_number):
    """
    Updates a user's details in MySQL without touching password.
    Backend Uniqueness Guard: username (BINARY case-sensitive) and contact_number must be unique across other accounts.
    Returns (True, None) on success or (False, error_message) on duplicate.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # --- Duplicate Guard: Username (case-sensitive) ---
        cursor.execute("SELECT id FROM Users WHERE BINARY username = %s AND id != %s", (username, user_id))
        if cursor.fetchone():
            return False, f"Username '{username}' is already taken by another account."

        # --- Duplicate Guard: Contact Number ---
        cursor.execute("SELECT id FROM Users WHERE Contact_Number = %s AND id != %s", (contact_number, user_id))
        if cursor.fetchone():
            return False, f"Contact number '{contact_number}' is already registered to another account."

        query = """
        UPDATE Users
        SET Firstname = %s, MI = %s, Lastname = %s, username = %s, Role = %s, Contact_Number = %s
        WHERE id = %s;
        """
        cursor.execute(query, (first_name, middle_initial, last_name, username, role, contact_number, user_id))
        conn.commit()
        if cursor.rowcount == 0:
            # No rows updated — user not found
            return False, "User not found or no changes made."
        return True, None
    except Exception as err:
        print(f"Error updating user: {err}")
        try:
            conn.rollback()
        except:
            pass
        return False, str(err)
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass
