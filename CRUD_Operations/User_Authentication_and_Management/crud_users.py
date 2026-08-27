from CRUD_Operations.User_Authentication_and_Management.db import get_db_connection

# --- 1. CREATE: Register New User ---
def register_user(first_name, middle_initial, last_name, username, password, role="Staff", contact_number=""):
    """Inserts a new user record (Approved_By = 0 by default)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    INSERT INTO Users (Firstname, MI, Lastname, fullname, username, password, Role, Contact_Number, Approved_By)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0);
    """
    try:
        fullname = f"{first_name} {last_name}"
        cursor.execute(query, (first_name, middle_initial, last_name, fullname, username, password, role, contact_number))
        conn.commit()
        return True
    except Exception as err:
        print(f"Error registering user: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

# --- 2. READ: Authenticate Login ---
def login_user(username, password):
    """Verifies credentials and checks if approved by Admin."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM Users WHERE username = %s AND password = %s;"
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

    # 1. Check if username and contact number exist together
    query_check = "SELECT user_id FROM users WHERE username = %s AND contact_number = %s;"
    cursor.execute(query_check, (username, contact_number))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return False  # Verification failed

    # 2. Hash new password and update
    new_hash = hash_password(new_password)
    query_update = "UPDATE users SET password_hash = %s WHERE user_id = %s;"
    cursor.execute(query_update, (new_hash, user["user_id"]))
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
    Updates a user's details in MySQL without touching password_hash.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    UPDATE Users
    SET Firstname = %s, MI = %s, Lastname = %s, username = %s, Role = %s, Contact_Number = %s
    WHERE id = %s;
    """
    try:
        cursor.execute(query, (first_name, middle_initial, last_name, username, role, contact_number, user_id))
        conn.commit()
        return True
    except Exception as err:
        print(f"Error updating user: {err}")
        return False
    finally:
        cursor.close()
        conn.close()