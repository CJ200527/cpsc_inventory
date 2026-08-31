import os
import sys
import re
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_MANAGEMENT_DIR = os.path.join(BASE_DIR, "CRUD_Operations", "User_Authentication_and_Management")
if USER_MANAGEMENT_DIR not in sys.path:
    sys.path.insert(0, USER_MANAGEMENT_DIR)

from db import get_db_connection

from crud_users import (
    register_user,
    login_user,
    get_all_users_filtered,
    approve_user,
    reject_user,
    delete_user,
    update_user_info,
    reset_password_verified,
)
from crud_suppliers import (
    get_all_suppliers,
    get_all_suppliers_filtered,
    add_supplier,
    update_supplier,
    delete_supplier,
)
from crud_products import (
    get_all_products,
    get_all_products_filtered,
    get_suppliers_list,
    add_product,
    update_product,
    delete_product,
)
from crud_pr import (
    create_purchase_request,
    get_all_purchase_requests,
    get_pr_details,
    update_pr_status
)

# --- IMPORTS FOR PO MODULE ---
from crud_po import (
    create_po_from_pr,
    get_approved_prs_without_po,
    get_all_purchase_orders,
    get_po_details,
    update_po_status
)

# --- IMPORTS FOR IAR MODULE (legacy) ---
from crud_iar import create_iar_record, get_iar_by_po

# --- IMPORTS FOR DELIVERY/IAR MODULE (spec-compliant 2-step) ---
from crud_delivery import (
    create_delivery,
    create_completion_delivery,
    get_all_deliveries,
    get_delivery_details,
    approve_delivery,
    get_deliverable_pos,
    search_deliverable_pos,
    get_po_remaining
)

# --- IMPORTS FOR INVENTORY MODULE (Live ledger) ---
from crud_inventory import get_inventory_summary, get_inventory_items, get_inventory_categories

# --- IMPORTS FOR WITHDRAWAL MODULE (RIS) ---
from crud_withdrawal import (
    get_available_products as get_withdraw_products,
    create_withdrawal,
    get_all_withdrawals,
    get_withdrawal_details,
    approve_withdrawal,
    reject_withdrawal
)

# --- IMPORTS FOR RETURN MODULE (Return Slip) ---
from crud_returns import (
    get_issued_withdrawals,
    get_return_products,
    create_return,
    get_all_returns,
    get_return_details,
    approve_return,
    reject_return
)

# Initialize Flask Application
app = Flask(__name__)

# Secret key required by Flask to handle user sessions and flash notification messages
app.secret_key = "cpsc_inventory_secret_key"


# Helper function to render template regardless of whether it's in a subfolder or root templates directory
def safe_render_template(subfolder_template, **kwargs):
    try:
        return render_template(subfolder_template, **kwargs)
    except Exception:
        direct_template = subfolder_template.split("/")[-1]
        return render_template(direct_template, **kwargs)


# --- ROUTE 1: Home Redirect ---
@app.route("/")
def index():
    """Always start at the login page."""
    return redirect(url_for("login"))


# --- ROUTE 2: Login Page (Handles display and authentication) ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Username and password are required. Please fill in all fields.", "error")
            return safe_render_template("LogIn and Registration/Loginpage.html")
        try:
            user = login_user(username, password)
        except Exception as err:
            print(f"[login] DB error: {err}")
            flash("Database connection failed. Is MySQL/XAMPP running?", "error")
            return safe_render_template("LogIn and Registration/Loginpage.html")

        if user:
            # Save user identity into browser session
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = f"{user['Firstname']} {user['Lastname']}"
            session["role"] = user["Role"]

            flash(f"Log In Successfully! Welcome {user['username']} 😊", "success")
            
            # Redirect based on user role
            if user["Role"] == "Admin":
                return redirect(url_for("admin_dashboard"))
            elif user["Role"] == "Staff":
                return redirect(url_for("staff_dashboard"))
            else:
                flash("User role not recognized. Please contact Admin.", "error")
                session.clear()
                return redirect(url_for("login"))
        else:
            flash("Invalid credentials OR account is pending Admin approval.", "error")

    return safe_render_template("LogIn and Registration/Loginpage.html")

# --- ROUTE: Forgot Password Reset ---
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        new_password = request.form.get("new_password", "").strip()
        if not all([username, contact_number, new_password]):
            flash("All fields are required to reset password.", "error")
            return safe_render_template("LogIn and Registration/forgot_password.html")
        if not re.fullmatch(r"09\d{9}", contact_number):
            flash("Contact number must be 11 digits starting with 09.", "error")
            return safe_render_template("LogIn and Registration/forgot_password.html")
        try:
            success = reset_password_verified(username, contact_number, new_password)
        except Exception as err:
            print(f"[forgot_password] DB error: {err}")
            flash("Database error. Is MySQL running?", "error")
            return safe_render_template("LogIn and Registration/forgot_password.html")
        if success:
            flash("Password updated successfully! Please log in with your new password 😊", "success")
            return redirect(url_for("login"))
        else:
            flash("Verification failed! Username and Contact Number do not match our records ⚠️", "error")
    return safe_render_template("LogIn and Registration/forgot_password.html")


# --- ROUTE 3: Registration Action ---
@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    first_name = request.form.get("first_name", "").strip()
    middle_initial = request.form.get("middle_initial", "").strip()
    last_name = request.form.get("last_name", "").strip()
    contact_number = request.form.get("contact_number", "").strip()
    role = request.form.get("role", "Staff").strip()

    if not all([username, password, first_name, middle_initial, last_name, contact_number]):
        flash("All fields are required. Please fill in all textboxes before signing up.", "error")
        return redirect(url_for("login"))

    if not re.fullmatch(r"09\d{9}", contact_number):
        flash("Invalid contact number! Must be 11 digits starting with '09' (e.g., 09123456789).", "error")
        return redirect(url_for("login"))

    # Case-Sensitive Username & Unique Contact Number Validation (Database Guard)
    try:
        conn_check = get_db_connection()
        cur_check = conn_check.cursor()
        cur_check.execute("SELECT id FROM Users WHERE BINARY username = %s", (username,))
        if cur_check.fetchone():
            flash("Username already exists (case-sensitive). Please choose another username.", "error")
            cur_check.close()
            conn_check.close()
            return redirect(url_for("login"))
        cur_check.execute("SELECT id FROM Users WHERE Contact_Number = %s", (contact_number,))
        if cur_check.fetchone():
            flash("Contact number already registered. Please use another number.", "error")
            cur_check.close()
            conn_check.close()
            return redirect(url_for("login"))
        cur_check.close()
        conn_check.close()
    except Exception as err:
        print(f"[register] check DB error: {err}")
        # Continue to attempt registration; crud will also guard

    try:
        success = register_user(
            first_name=first_name, middle_initial=middle_initial, last_name=last_name,
            username=username, password=password, role=role, contact_number=contact_number
        )
    except Exception as err:
        print(f"[register] DB error: {err}")
        flash("Database error. Is MySQL/XAMPP running?", "error")
        return redirect(url_for("login"))

    if success:
        flash("Sign Up Successful! Please wait for Admin approval 😊😊😊", "success")
        return redirect(url_for("login"))
    else:
        flash("Registration failed. Username or Contact Number may already be taken.", "error")
        return redirect(url_for("login"))


# --- ROUTE 4: Logout Action ---
@app.route("/logout")
def logout():
    username = session.get("username", "")
    session.clear()
    if username:
        flash(f"Successfully logged out {username} 😢", "info")
    else:
        flash("Successfully logged out 😢", "info")
    return redirect(url_for("login"))

# --- ROUTE 5: Admin Dashboard ---
@app.route("/admin_dashboard")
def admin_dashboard():
    if "user_id" not in session:
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for("login"))
    if session.get("role") != "Admin":
        flash("You do not have permission to access the admin dashboard.", "error")
        return redirect(url_for("login"))
    # Live inventory metrics for dashboard cards
    try:
        summary = get_inventory_summary()
    except Exception as err:
        print(f"[admin_dashboard] summary error: {err}")
        summary = {"total_unique":0,"total_asset_value":0,"low_stock_count":0,"out_of_stock_count":0,"in_stock_count":0}
    return safe_render_template("Admin Dashboards/admin_dashboard.html", username=session.get("username"), role=session.get("role"), full_name=session.get("full_name"), summary=summary)

# --- ROUTE 6: Staff Dashboard ---
@app.route("/staff_dashboard")
def staff_dashboard():
    if "user_id" not in session:
        flash("Please log in to access the staff dashboard.", "error")
        return redirect(url_for("login"))
    if session.get("role") != "Staff":
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("login"))
    return safe_render_template("Staff Dashboards/staff_dashboard.html", username=session.get("username"), role=session.get("role"), full_name=session.get("full_name"))

# --- ROUTE: Admin User Management View & Filters ---
@app.route("/admin/users")
def admin_users():
    if "user_id" not in session or session.get("role") != "Admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date_filter", "All")
    custom_date = request.args.get("custom_date", "")
    try:
        users = get_all_users_filtered(search_query=search, date_filter=date_filter, custom_date=custom_date)
    except Exception as err:
        print(f"[admin_users] DB error: {err}")
        flash("Database error while loading users.", "error")
        users = []
    return safe_render_template("Admin Dashboards/user_management.html", user=session, users=users, search=search, date_filter=date_filter, custom_date=custom_date)

# --- ACTION ROUTES: Approve, Reject, Delete ---
@app.route("/admin/users/approve/<int:target_id>", methods=["POST"])
def admin_approve_user_action(target_id):
    if session.get("role") == "Admin":
        try:
            approve_user(target_id)
            flash(f"User account USR-{'%03d' % target_id} approved!", "success")
        except Exception as err:
            flash(f"Approve failed: {err}", "error")
    return redirect(url_for("admin_users", search=request.args.get("search", ""), date_filter=request.args.get("date_filter", "All")))

@app.route("/admin/users/reject/<int:target_id>", methods=["POST"])
def admin_reject_user_action(target_id):
    if session.get("role") == "Admin":
        try:
            reject_user(target_id)
            flash(f"User account USR-{'%03d' % target_id} set to Pending/Rejected.", "info")
        except Exception as err:
            flash(f"Reject failed: {err}", "error")
    return redirect(url_for("admin_users", search=request.args.get("search", ""), date_filter=request.args.get("date_filter", "All")))

@app.route("/admin/users/delete/<int:target_id>", methods=["POST"])
def admin_delete_user_action(target_id):
    if session.get("role") == "Admin":
        try:
            delete_user(target_id)
            flash(f"User account USR-{'%03d' % target_id} removed permanently.", "error")
        except Exception as err:
            flash(f"Delete failed: {err}", "error")
    return redirect(url_for("admin_users", search=request.args.get("search", ""), date_filter=request.args.get("date_filter", "All")))

# --- ACTION ROUTE: Update User Information ---
@app.route("/admin/users/update/<int:target_id>", methods=["POST"])
def admin_update_user_action(target_id):
    if session.get("role") == "Admin":
        first_name = request.form.get("first_name", "").strip()
        middle_initial = request.form.get("middle_initial", "").strip()
        last_name = request.form.get("last_name", "").strip()
        username = request.form.get("username", "").strip()
        role = request.form.get("role", "Staff").strip()
        contact_number = request.form.get("contact_number", "").strip()
        if not re.fullmatch(r"09\d{9}", contact_number):
            flash("Invalid contact number! Must be 11 digits starting with '09' (e.g., 09123456789).", "error")
            return redirect(url_for("admin_users", search=request.args.get("search", ""), date_filter=request.args.get("date_filter", "All")))

        # Backend Uniqueness Guard: pre-check before calling crud (redundant safety)
        try:
            conn_check = get_db_connection()
            cur_check = conn_check.cursor()
            cur_check.execute("SELECT id FROM Users WHERE BINARY username = %s AND id != %s", (username, target_id))
            if cur_check.fetchone():
                flash(f"Failed to update user: Username '{username}' is already taken by another account.", "error")
                cur_check.close()
                conn_check.close()
                return redirect(url_for("admin_users", search=request.args.get("search", ""), date_filter=request.args.get("date_filter", "All")))
            cur_check.execute("SELECT id FROM Users WHERE Contact_Number = %s AND id != %s", (contact_number, target_id))
            if cur_check.fetchone():
                flash(f"Failed to update user: Contact number '{contact_number}' is already registered to another account.", "error")
                cur_check.close()
                conn_check.close()
                return redirect(url_for("admin_users", search=request.args.get("search", ""), date_filter=request.args.get("date_filter", "All")))
            cur_check.close()
            conn_check.close()
        except Exception as err:
            print(f"[admin_update_user_action] duplicate check error: {err}")

        try:
            result = update_user_info(user_id=target_id, first_name=first_name, middle_initial=middle_initial, last_name=last_name, username=username, role=role, contact_number=contact_number)
            # Support both tuple (success, msg) and legacy boolean
            if isinstance(result, tuple):
                success, msg = result
            else:
                success, msg = bool(result), None

            if success:
                flash(f"User USR-{'%03d' % target_id} updated successfully!", "success")
            else:
                if msg and ("Username" in msg or "Contact number" in msg):
                    flash(f"Failed to update user: {msg}", "error")
                elif msg:
                    flash(f"Failed to update user: {msg}", "error")
                else:
                    flash(f"Failed to update USR-{'%03d' % target_id}. Username might already exist.", "error")
        except Exception as err:
            flash(f"Update failed: {err}", "error")
    return redirect(url_for("admin_users", search=request.args.get("search", ""), date_filter=request.args.get("date_filter", "All")))

# --- ROUTE: Admin Supplier Management View & Search ---
@app.route("/admin/suppliers")
def admin_suppliers():
    if "user_id" not in session or session.get("role") != "Admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date_filter", "All")
    custom_date = request.args.get("custom_date", "")
    try:
        suppliers = get_all_suppliers(search_query=search, date_filter=date_filter, custom_date=custom_date)
    except Exception as err:
        print(f"[admin_suppliers] DB error: {err}")
        flash("Database error while loading suppliers.", "error")
        suppliers = []
    return safe_render_template("Admin Dashboards/supplier_management.html", user=session, suppliers=suppliers, search=search, date_filter=date_filter, custom_date=custom_date)

# --- ROUTE: Staff Supplier Management View (Staff + Admin) ---
@app.route("/staff/suppliers")
def staff_suppliers():
    if "user_id" not in session:
        flash("Please log in to access Supplier Directory.", "error")
        return redirect(url_for("login"))
    if session.get("role") not in ["Admin", "Staff"]:
        flash("Staff access required.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date_filter", "All")
    custom_date = request.args.get("custom_date", "")
    try:
        suppliers = get_all_suppliers(search_query=search, date_filter=date_filter, custom_date=custom_date)
    except Exception as err:
        print(f"[staff_suppliers] DB error: {err}")
        flash("Database error while loading suppliers.", "error")
        suppliers = []
    return safe_render_template("Staff Dashboards/staff_supplier_management.html", user=session, suppliers=suppliers, search=search, date_filter=date_filter, custom_date=custom_date)

# --- ACTION ROUTE: Add New Supplier (Admin + Staff) ---
@app.route("/admin/suppliers/add", methods=["POST"])
@app.route("/suppliers/add", methods=["POST"])
def admin_add_supplier_action():
    if session.get("role") not in ["Admin", "Staff"]:
        flash("Admin or Staff access required.", "error")
        return redirect(url_for("login"))
    _redir = "staff_suppliers" if session.get("role") == "Staff" else "admin_suppliers"
    supplier_name = request.form.get("supplier_name", "").strip()
    contact_person = request.form.get("contact_person", "").strip()
    contact_number = request.form.get("contact_number", "").strip()
    email = request.form.get("email", "").strip()
    street = request.form.get("street", "").strip()
    barangay = request.form.get("barangay", "").strip()
    municipality = request.form.get("municipality", "").strip()
    city = request.form.get("city", "").strip()
    country = request.form.get("country", "Philippines").strip() or "Philippines"
    if not all([supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country]):
        flash("All fields are required. Please fill every textbox.", "error")
        return redirect(url_for(_redir, search=request.args.get("search","")))
    if not re.fullmatch(r"09\d{9}", contact_number):
        flash("Invalid contact number! Must be 11 digits starting with 09.", "error")
        return redirect(url_for(_redir, search=request.args.get("search","")))
    if "@" not in email or "." not in email:
        flash("Invalid email address.", "error")
        return redirect(url_for(_redir, search=request.args.get("search","")))
    try:
        ok = add_supplier(supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country)
        flash(f"Supplier '{supplier_name}' added!" if ok else "Failed to add supplier.", "success" if ok else "error")
    except Exception as err:
        flash(f"Add failed: {err}", "error")
    if session.get("role") == "Staff":
        return redirect(url_for("staff_suppliers", search=request.args.get("search","")))
    return redirect(url_for("admin_suppliers", search=request.args.get("search","")))

# --- ACTION ROUTE: Update Supplier (Admin + Staff) ---
@app.route("/admin/suppliers/update/<int:target_id>", methods=["POST"])
@app.route("/suppliers/update/<int:target_id>", methods=["POST"])
def admin_update_supplier_action(target_id):
    if session.get("role") not in ["Admin", "Staff"]:
        flash("Admin or Staff access required.", "error")
        return redirect(url_for("login"))
    supplier_name = request.form.get("supplier_name", "").strip()
    contact_person = request.form.get("contact_person", "").strip()
    contact_number = request.form.get("contact_number", "").strip()
    email = request.form.get("email", "").strip()
    street = request.form.get("street", "").strip()
    barangay = request.form.get("barangay", "").strip()
    municipality = request.form.get("municipality", "").strip()
    city = request.form.get("city", "").strip()
    country = request.form.get("country", "Philippines").strip() or "Philippines"
    _redir = "staff_suppliers" if session.get("role") == "Staff" else "admin_suppliers"
    if not all([supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country]):
        flash("All fields are required. Please fill every textbox.", "error")
        return redirect(url_for(_redir, search=request.args.get("search","")))
    if not re.fullmatch(r"09\d{9}", contact_number):
        flash("Invalid contact number! Must be 11 digits starting with 09.", "error")
        return redirect(url_for(_redir, search=request.args.get("search","")))
    try:
        ok = update_supplier(target_id, supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country)
        flash(f"Supplier SUP-{target_id:03d} updated!" if ok else "Update failed.", "success" if ok else "error")
    except Exception as err:
        flash(f"Update failed: {err}", "error")
    return redirect(url_for(_redir, search=request.args.get("search","")))

# --- ACTION ROUTE: Delete Supplier (Admin Only) ---
@app.route("/admin/suppliers/delete/<int:target_id>", methods=["POST"])
@app.route("/suppliers/delete/<int:target_id>", methods=["POST"])
def admin_delete_supplier_action(target_id):
    if session.get("role") != "Admin":
        if session.get("role") == "Staff":
            flash("Delete access denied: Only Admin can delete suppliers. Staff can only Add/Edit.", "error")
            return redirect(url_for("staff_suppliers"))
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    try:
        ok = delete_supplier(target_id)
        if ok:
            flash(f"Supplier SUP-{target_id:03d} deleted.", "error")
        else:
            flash("Delete failed — supplier may be linked to products.", "error")
    except Exception as err:
        flash(f"Delete failed: {err}", "error")
    return redirect(url_for("admin_suppliers", search=request.args.get("search","")))

# --- PRODUCT MANAGEMENT ---
@app.route("/admin/products")
def admin_products():
    if "user_id" not in session or session.get("role") != "Admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date_filter", "All")
    custom_date = request.args.get("custom_date", "")
    try:
        products = get_all_products(search_query=search, date_filter=date_filter, custom_date=custom_date)
        suppliers_list = get_suppliers_list()
    except Exception as err:
        print(f"[admin_products] DB error: {err}")
        flash("Database error while loading products.", "error")
        products = []; suppliers_list = []
    return safe_render_template("Admin Dashboards/product_management.html", user=session, products=products, suppliers_list=suppliers_list, search=search, date_filter=date_filter, custom_date=custom_date)

# --- ROUTE: Staff Product Catalog View (Staff + Admin) ---
@app.route("/staff/products")
def staff_products():
    if "user_id" not in session:
        flash("Please log in to access Product Catalog.", "error")
        return redirect(url_for("login"))
    if session.get("role") not in ["Admin", "Staff"]:
        flash("Staff access required.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    date_filter = request.args.get("date_filter", "All")
    custom_date = request.args.get("custom_date", "")
    try:
        products = get_all_products(search_query=search, date_filter=date_filter, custom_date=custom_date)
        suppliers_list = get_suppliers_list()
    except Exception as err:
        print(f"[staff_products] DB error: {err}")
        flash("Database error while loading products.", "error")
        products = []; suppliers_list = []
    return safe_render_template("Staff Dashboards/staff_product_management.html", user=session, products=products, suppliers_list=suppliers_list, search=search, date_filter=date_filter, custom_date=custom_date)

@app.route("/admin/products/add", methods=["POST"])
@app.route("/products/add", methods=["POST"])
def admin_add_product():
    if session.get("role") not in ["Admin", "Staff"]:
        flash("Admin or Staff access required.", "error")
        return redirect(url_for("login"))
    _redir = "staff_products" if session.get("role") == "Staff" else "admin_products"
    supplier_id = request.form.get("supplier_id", "").strip()
    product_name = request.form.get("product_name", "").strip()
    category = request.form.get("category", "").strip()
    details = request.form.get("details", "").strip()
    unit = request.form.get("unit", "").strip()
    size = request.form.get("size", "").strip()
    price = request.form.get("price", "").strip()
    if not all([supplier_id, product_name, category, unit, size, details, price]):
        flash("All fields are required (including price and specification).", "error")
        return redirect(url_for(_redir, search=request.args.get("search","")))
    try:
        supplier_id = int(supplier_id)
        price = float(price)
        if price < 0: raise ValueError
    except:
        flash("Price must be a valid number (0 or more) and supplier must be selected.", "error")
        return redirect(url_for(_redir, search=request.args.get("search","")))
    try:
        ok = add_product(supplier_id, product_name, category, details, unit, size, price)
        flash(f"Product '{product_name}' added!" if ok else "Failed to add product.", "success" if ok else "error")
    except Exception as err:
        flash(f"Add failed: {err}", "error")
    return redirect(url_for(_redir, search=request.args.get("search","")))

@app.route("/admin/products/update/<int:target_id>", methods=["POST"])
@app.route("/products/update/<int:target_id>", methods=["POST"])
def admin_update_product(target_id):
    if session.get("role") not in ["Admin", "Staff"]:
        flash("Admin or Staff access required.", "error")
        return redirect(url_for("login"))
    _redir = "staff_products" if session.get("role") == "Staff" else "admin_products"
    supplier_id = request.form.get("supplier_id", "").strip()
    product_name = request.form.get("product_name", "").strip()
    category = request.form.get("category", "").strip()
    details = request.form.get("details", "").strip()
    unit = request.form.get("unit", "").strip()
    size = request.form.get("size", "").strip()
    price = request.form.get("price", "").strip()
    if not all([supplier_id, product_name, category, unit, size, details, price]):
        flash("All fields are required.", "error")
        return redirect(url_for(_redir, search=request.args.get("search","")))
    try:
        supplier_id = int(supplier_id); price = float(price)
        if price < 0: raise ValueError
    except:
        flash("Invalid price or supplier.", "error")
        return redirect(url_for(_redir, search=request.args.get("search","")))
    try:
        ok = update_product(target_id, supplier_id, product_name, category, details, unit, size, price)
        flash(f"Product PRD-{target_id:03d} updated!" if ok else "Update failed.", "success" if ok else "error")
    except Exception as err:
        flash(f"Update failed: {err}", "error")
    return redirect(url_for(_redir, search=request.args.get("search","")))

@app.route("/admin/products/delete/<int:target_id>", methods=["POST"])
@app.route("/products/delete/<int:target_id>", methods=["POST"])
def admin_delete_product(target_id):
    if session.get("role") != "Admin":
        if session.get("role") == "Staff":
            flash("Delete access denied: Only Admin can delete products. Staff can only Add/Edit.", "error")
            return redirect(url_for("staff_products"))
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    try:
        ok = delete_product(target_id)
        flash(f"Product PRD-{target_id:03d} deleted." if ok else "Delete failed — may be referenced by inventory.", "error" if ok else "error")
    except Exception as err:
        flash(f"Delete failed: {err}", "error")
    return redirect(url_for("admin_products", search=request.args.get("search","")))

# --- ROUTE: Purchase Request Management (Role-Separated View) ---
@app.route("/pr")
def pr_management():
    if "user_id" not in session:
        flash("Please log in to access Purchase Requests.", "error")
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status_filter", "All")
    date_filter = request.args.get("date_filter", "All")
    custom_date = request.args.get("custom_date", "")

    user_role = session.get("role")
    # Staff now sees ALL records (not just own) to avoid confusion with Admin
    user_id_scope = None

    try:
        requests_list = get_all_purchase_requests(
            search_query=search,
            status_filter=status_filter,
            date_filter=date_filter,
            custom_date=custom_date,
            user_id=user_id_scope
        )
        products_list = get_all_products()
    except Exception as err:
        print(f"[pr_management] DB error: {err}")
        flash("Database error loading Purchase Requests.", "error")
        requests_list = []
        products_list = []

    template_file = "Admin Dashboards/admin_pr_management.html" if user_role == "Admin" else "Staff Dashboards/staff_pr_management.html"

    return safe_render_template(
        template_file,
        user=session,
        requests=requests_list,
        products=products_list,
        search=search,
        status_filter=status_filter,
        date_filter=date_filter,
        custom_date=custom_date
    )

# --- ACTION ROUTE: Submit New PR (Supports Multiple Line Items) ---
@app.route("/pr/add", methods=["POST"])
def add_pr_action():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    product_ids = request.form.getlist("product_id[]")
    supplier_ids = request.form.getlist("supplier_id[]")
    item_names = request.form.getlist("item_name[]")
    categories = request.form.getlist("category[]")
    units = request.form.getlist("unit[]")
    sizes = request.form.getlist("size[]")
    details_list = request.form.getlist("details[]")
    prices = request.form.getlist("price[]")
    quantities = request.form.getlist("quantity[]")

    if not product_ids:
        flash("Please add at least one item to your purchase request.", "error")
        return redirect(url_for("pr_management"))

    def _safe(lst, idx, default=""):
        return lst[idx].strip() if idx < len(lst) and lst[idx] is not None else default

    items_payload = []
    for i, pid_raw in enumerate(product_ids):
        try:
            pid_str = pid_raw.strip() if pid_raw else ""
            sid_str = _safe(supplier_ids, i)
            iname = _safe(item_names, i)
            price_str = _safe(prices, i)
            qty_str = _safe(quantities, i)
            if not pid_str or not sid_str or not iname or not price_str or not qty_str:
                continue
            items_payload.append({
                "product_id": int(pid_str),
                "supplier_id": int(sid_str),
                "item_name": iname,
                "category": _safe(categories, i),
                "unit": _safe(units, i, "pcs"),
                "size": _safe(sizes, i),
                "details": _safe(details_list, i),
                "price": float(price_str),
                "quantity": int(qty_str)
            })
        except (ValueError, IndexError, AttributeError):
            continue

    if not items_payload:
        flash("Invalid item details submitted.", "error")
        return redirect(url_for("pr_management"))

    success, result = create_purchase_request(user_id, items_payload)
    if success:
        flash(f"Purchase Request {result} submitted successfully!", "success")
    else:
        flash(f"Failed to submit PR: {result}", "error")

    return redirect(url_for("pr_management"))

# --- ACTION ROUTE: View Single PR Details (JSON Response for Modal) ---
@app.route("/pr/details/<int:pr_id>")
def get_pr_details_api(pr_id):
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401
    header, items = get_pr_details(pr_id)
    if not header:
        return {"error": "Purchase request not found"}, 404
    try:
        raw_date = header.get("date_requested")
        if raw_date:
            header["date_requested"] = raw_date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(raw_date, "strftime") else str(raw_date)
        else:
            header["date_requested"] = ""
    except Exception:
        header["date_requested"] = str(header.get("date_requested", ""))
    try:
        header["total_price"] = float(header.get("total_price") or 0)
    except Exception:
        header["total_price"] = 0.0
    for item in items:
        try:
            item["price"] = float(item.get("price") or 0)
        except Exception:
            item["price"] = 0.0
        try:
            item["total_price"] = float(item.get("total_price") or 0)
        except Exception:
            item["total_price"] = 0.0
    return {"header": header, "items": items}

# --- ACTION ROUTE: Approve PR (Admin Only) ---
@app.route("/admin/pr/approve/<int:pr_id>", methods=["POST"])
def approve_pr_action(pr_id):
    if session.get("role") != "Admin":
        flash("Admin permission required.", "error")
        return redirect(url_for("pr_management"))

    if update_pr_status(pr_id, "Approved"):
        flash(f"Purchase Request PR-{'%03d' % pr_id} approved!", "success")
    else:
        flash("Failed to approve Purchase Request.", "error")

    return redirect(url_for("pr_management"))

# --- ACTION ROUTE: Reject PR (Admin Only) ---
@app.route("/admin/pr/reject/<int:pr_id>", methods=["POST"])
def reject_pr_action(pr_id):
    if session.get("role") != "Admin":
        flash("Admin permission required.", "error")
        return redirect(url_for("pr_management"))

    if update_pr_status(pr_id, "Rejected"):
        flash(f"Purchase Request PR-{'%03d' % pr_id} rejected.", "info")
    else:
        flash("Failed to update Purchase Request.", "error")

    return redirect(url_for("pr_management"))

# --- ROUTE: Purchase Order Management (Role-Separated) ---
@app.route("/po")
def po_management():
    if "user_id" not in session:
        flash("Please log in to access Purchase Orders.", "error")
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status_filter", "All")

    user_role = session.get("role")
    # Staff sees ALL POs regardless of creator
    user_id_scope = None

    try:
        orders_list = get_all_purchase_orders(
            search_query=search,
            status_filter=status_filter,
            user_id=user_id_scope
        )
        approved_prs = get_approved_prs_without_po()
    except Exception as err:
        print(f"[po_management] DB error: {err}")
        flash("Database error loading Purchase Orders.", "error")
        orders_list = []
        approved_prs = []

    template_file = "Admin Dashboards/admin_po_management.html" if user_role == "Admin" else "Staff Dashboards/staff_po_management.html"

    return safe_render_template(
        template_file,
        user=session,
        orders=orders_list,
        approved_prs=approved_prs,
        search=search,
        status_filter=status_filter
    )

# --- ACTION ROUTE: Generate PO from Approved PR ---
@app.route("/admin/po/generate", methods=["POST"])
@app.route("/po/generate", methods=["POST"])
def generate_po_action():
    if session.get("role") not in ["Admin", "Staff"]:
        flash("Login required to generate PO.", "error")
        return redirect(url_for("po_management"))

    pr_id = request.form.get("pr_id")
    if not pr_id:
        flash("Please select an approved Purchase Request.", "error")
        return redirect(url_for("po_management"))

    product_ids = request.form.getlist("product_id[]")
    supplier_ids = request.form.getlist("supplier_id[]")
    item_names = request.form.getlist("item_name[]")
    categories = request.form.getlist("category[]")
    units = request.form.getlist("unit[]")
    sizes = request.form.getlist("size[]")
    details_list = request.form.getlist("details[]")
    quantities = request.form.getlist("quantity[]")
    unit_prices = request.form.getlist("unit_price[]") or request.form.getlist("price[]")

    adjusted_items = []
    if product_ids:
        def _safe(lst, idx, default=""):
            return lst[idx].strip() if idx < len(lst) and lst[idx] is not None else default
        for i in range(len(product_ids)):
            try:
                pid_str = product_ids[i].strip() if product_ids[i] else ""
                if not pid_str:
                    continue
                qty_str = _safe(quantities, i)
                price_str = _safe(unit_prices, i)
                if not qty_str or not price_str:
                    continue
                adjusted_items.append({
                    "product_id": int(pid_str),
                    "supplier_id": int(_safe(supplier_ids, i) or 1),
                    "item_name": _safe(item_names, i),
                    "category": _safe(categories, i),
                    "unit": _safe(units, i, "pcs"),
                    "size": _safe(sizes, i),
                    "details": _safe(details_list, i),
                    "quantity": int(qty_str),
                    "unit_price": float(price_str)
                })
            except (ValueError, IndexError, AttributeError):
                continue

    success, result = create_po_from_pr(int(pr_id), session.get("user_id"), adjusted_items if adjusted_items else None)
    if success:
        flash(f"Purchase Order {result} generated successfully with updated vendor pricing!", "success")
    else:
        flash(f"Failed to generate PO: {result}", "error")

    return redirect(url_for("po_management"))

# --- Admin-Only PO Approval ---
@app.route("/po/approve/<int:po_id>", methods=["POST"])
def approve_po_action(po_id):
    if session.get("role") != "Admin":
        flash("Admin permission required.", "error")
        return redirect(url_for("po_management"))
    header, _ = get_po_details(po_id)
    if not header:
        flash("Purchase Order not found.", "error")
        return redirect(url_for("po_management"))
    if header.get("status") != "Pending PO Approval":
        flash("Only POs with status 'Pending PO Approval' can be approved.", "error")
        return redirect(url_for("po_management"))
    if update_po_status(po_id, "Approved"):
        flash(f"Purchase Order {header.get('po_number')} approved!", "success")
    else:
        flash("Failed to approve Purchase Order.", "error")
    return redirect(url_for("po_management"))

# --- ACTION ROUTE: Get PO Details API ---
@app.route("/po/details/<int:po_id>")
def get_po_details_api(po_id):
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401

    header, items = get_po_details(po_id)
    if not header:
        return {"error": "Purchase order not found"}, 404

    header["date_issued"] = header["date_issued"].strftime("%Y-%m-%d %H:%M:%S") if header["date_issued"] else ""
    header["total_amount"] = float(header["total_amount"])

    for item in items:
        item["unit_price"] = float(item["unit_price"])
        item["total_price"] = float(item["total_price"])
        item["ordered_quantity"] = int(item["ordered_quantity"])
        item["received_quantity"] = int(item["received_quantity"])

    return {"header": header, "items": items}

# --- ACTION ROUTE: Update PO Status (Admin Only) ---
@app.route("/admin/po/status/<int:po_id>", methods=["POST"])
def update_po_status_action(po_id):
    if session.get("role") != "Admin":
        flash("Admin permission required.", "error")
        return redirect(url_for("po_management"))

    new_status = request.form.get("status")
    if new_status in ["Issued", "Partially Delivered", "Completed", "Cancelled"]:
        if update_po_status(po_id, new_status):
            flash(f"Purchase Order status updated to '{new_status}'.", "success")
        else:
            flash("Failed to update Purchase Order status.", "error")

    return redirect(url_for("po_management"))



# ============================================================
# DELIVERY & IAR MODULE — 2-STEP WORKFLOW (Spec-Compliant)
# ============================================================

@app.route("/delivery")
def delivery_dashboard():
    """Unified delivery dashboard — renders admin vs staff template based on role."""
    if "user_id" not in session:
        flash("Please log in to access Delivery.", "error")
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status_filter", "All")
    date_filter = request.args.get("date_filter", "All")
    custom_date = request.args.get("custom_date", "")

    user_role = session.get("role")
    # Staff and Admin both see ALL deliveries to keep records in sync
    user_id_scope = None

    try:
        deliveries = get_all_deliveries(
            search_query=search,
            status_filter=status_filter,
            date_filter=date_filter,
            custom_date=custom_date,
            user_id=user_id_scope
        )
        # Deliverable POs: Approved/Issued without prior deliveries — visible to all roles
        deliverable_pos = get_deliverable_pos(
            search_query="",
            user_id=None
        )
        # Also fetch without scope for admin to see all
        if user_role == "Admin":
            # Admin sees all deliverable POs
            pass
    except Exception as err:
        print(f"[delivery_dashboard] DB error: {err}")
        flash("Database error loading Deliveries.", "error")
        deliveries = []
        deliverable_pos = []

    template_file = "Admin Dashboards/admin_delivery_dashboard.html" if user_role == "Admin" else "Staff Dashboards/staff_delivery_dashboard.html"

    return safe_render_template(
        template_file,
        user=session,
        deliveries=deliveries,
        deliverable_pos=deliverable_pos,
        search=search,
        status_filter=status_filter,
        date_filter=date_filter,
        custom_date=custom_date
    )


@app.route("/delivery/create", methods=["POST"])
def create_delivery_action():
    """Step 1: Receiving & IAR — Pending, AUTO partial, guard received > ordered."""
    if "user_id" not in session:
        flash("Please log in to submit a delivery.", "error")
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    po_id = request.form.get("po_id", "").strip()
    delivery_number = request.form.get("delivery_number", "").strip()
    iar_number = request.form.get("iar_number", "").strip()
    inspected_by = request.form.get("inspected_by", "").strip()
    supply_officer = request.form.get("supply_officer", "").strip()
    delivery_date = request.form.get("delivery_date", "").strip()
    remarks = request.form.get("remarks", "").strip()
    # is_partial AUTO-computed inside create_delivery — checkbox removed per new spec

    if not all([po_id, delivery_number, iar_number, inspected_by, supply_officer, delivery_date]):
        flash("Delivery Number, IAR Number, Inspected By, Supply Officer, and Delivery Date are required.", "error")
        return redirect(url_for("delivery_dashboard"))

    try:
        po_id_int = int(po_id)
    except:
        flash("Invalid Purchase Order selected.", "error")
        return redirect(url_for("delivery_dashboard"))

    product_ids = request.form.getlist("product_id[]")
    received_qtys = request.form.getlist("received_quantity[]")

    if not product_ids:
        flash("No items. Please select a PO and enter received quantities.", "error")
        return redirect(url_for("delivery_dashboard"))

    received_items = []
    for i, pid_raw in enumerate(product_ids):
        try:
            pid = int(pid_raw.strip()) if pid_raw else None
            if pid is None:
                continue
            # Empty input -> must be filled by user (no autofill) — treat empty as error
            qty_raw = received_qtys[i].strip() if i < len(received_qtys) and received_qtys[i] is not None else ""
            if qty_raw == "":
                flash(f"Received quantity required for item row {i+1} — please enter a value (0 if none).", "error")
                return redirect(url_for("delivery_dashboard"))
            qty = int(qty_raw)
            if qty < 0:
                raise ValueError
            received_items.append({"product_id": pid, "received_quantity": qty})
        except (ValueError, IndexError, AttributeError):
            flash(f"Invalid received quantity for item row {i+1}. Must be integer 0..ordered.", "error")
            return redirect(url_for("delivery_dashboard"))

    if not received_items:
        flash("No valid received quantities provided.", "error")
        return redirect(url_for("delivery_dashboard"))

    success, result = create_delivery(
        po_id=po_id_int,
        user_id=user_id,
        delivery_number=delivery_number,
        iar_number=iar_number,
        inspected_by=inspected_by,
        supply_officer=supply_officer,
        delivery_date=delivery_date,
        remarks=remarks,
        received_items=received_items
    )

    if success:
        flash(f"Delivery {delivery_number} submitted! Pending approval. Partial auto-detected if any received != ordered.", "success")
    else:
        flash(f"Failed to submit delivery: {result}", "error")

    return redirect(url_for("delivery_dashboard"))


@app.route("/delivery/details/<int:delivery_id>")
def get_delivery_details_api(delivery_id):
    """JSON for delivery details modal (header + items)."""
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401

    header, items = get_delivery_details(delivery_id)
    if not header:
        return {"error": "Delivery not found"}, 404

    # Normalize dates and decimals for JSON
    try:
        raw = header.get("delivery_date")
        header["delivery_date"] = raw.strftime("%Y-%m-%d %H:%M:%S") if hasattr(raw, "strftime") else str(raw or "")
    except Exception:
        header["delivery_date"] = str(header.get("delivery_date", ""))
    try:
        header["is_partial"] = int(header.get("is_partial", 0))
    except Exception:
        header["is_partial"] = 0

    for it in items:
        try: it["price"] = float(it.get("price") or 0)
        except: it["price"] = 0.0
        try: it["total_price"] = float(it.get("total_price") or 0)
        except: it["total_price"] = 0.0
        try: it["ordered_quantity"] = int(it.get("ordered_quantity") or 0)
        except: it["ordered_quantity"] = 0
        try: it["received_quantity"] = int(it.get("received_quantity") or 0)
        except: it["received_quantity"] = 0

    return {"header": header, "items": items}


@app.route("/delivery/approve/<int:delivery_id>", methods=["POST"])
def approve_delivery_action(delivery_id):
    """Step 2: Admin-only verification & stock ingestion."""
    if session.get("role") != "Admin":
        flash("Admin permission required to approve deliveries.", "error")
        return redirect(url_for("delivery_dashboard"))

    admin_id = session.get("user_id")
    success, msg = approve_delivery(delivery_id, admin_id)
    if success:
        flash(msg, "success")
    else:
        flash(f"Approve failed: {msg}", "error")
    return redirect(url_for("delivery_dashboard"))


# --- LIVE SEARCH for Approved POs in Receive modal ---
@app.route("/delivery/search_pos")
def search_pos_api():
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401
    q = request.args.get("q", "").strip()
    user_role = session.get("role")
    scope = None  # all roles see same Approved POs
    rows = search_deliverable_pos(search_query=q, user_id=scope)
    # Minimal payload
    out = []
    for r in rows:
        out.append({
            "po_id": r["po_id"],
            "po_number": r["po_number"],
            "pr_number": r["pr_number"],
            "supplier_name": r.get("supplier_name") or "N/A",
            "status": r["status"],
            "total_amount": float(r.get("total_amount") or 0)
        })
    return {"results": out}


# --- Remaining quantities for a PO (for Complete action) ---
@app.route("/delivery/remaining/<int:po_id>")
def get_remaining_api(po_id):
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401
    data = get_po_remaining(po_id)
    # Also fetch PO header for context
    header, _ = get_po_details(po_id) if po_id else (None, [])
    if header:
        try:
            header["total_amount"] = float(header.get("total_amount") or 0)
        except: pass
        try:
            header["date_issued"] = header["date_issued"].strftime("%Y-%m-%d %H:%M:%S") if header.get("date_issued") else ""
        except: pass
    return {"header": header, "remaining": data}


# --- COMPLETE REMAINING: create follow-up delivery for same PO ---
@app.route("/delivery/complete/<int:delivery_id>", methods=["POST"])
def complete_delivery_action(delivery_id):
    if "user_id" not in session:
        flash("Please log in.", "error")
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    delivery_number = request.form.get("delivery_number", "").strip()
    iar_number = request.form.get("iar_number", "").strip()
    inspected_by = request.form.get("inspected_by", "").strip()
    supply_officer = request.form.get("supply_officer", "").strip()
    delivery_date = request.form.get("delivery_date", "").strip()
    remarks = request.form.get("remarks", "").strip()

    if not all([delivery_number, iar_number, inspected_by, supply_officer, delivery_date]):
        flash("Delivery Number, IAR Number, Inspected By, Supply Officer, Delivery Date required for completion.", "error")
        return redirect(url_for("delivery_dashboard"))

    product_ids = request.form.getlist("product_id[]")
    received_qtys = request.form.getlist("received_quantity[]")

    if not product_ids:
        flash("No items for completion.", "error")
        return redirect(url_for("delivery_dashboard"))

    received_items = []
    for i, pid_raw in enumerate(product_ids):
        try:
            pid = int(pid_raw.strip()) if pid_raw else None
            if pid is None: continue
            qty_raw = received_qtys[i].strip() if i < len(received_qtys) and received_qtys[i] else ""
            if qty_raw == "":
                flash(f"Received quantity required for item row {i+1}.", "error")
                return redirect(url_for("delivery_dashboard"))
            qty = int(qty_raw)
            if qty < 0: raise ValueError
            received_items.append({"product_id": pid, "received_quantity": qty})
        except (ValueError, IndexError, AttributeError):
            flash(f"Invalid received quantity row {i+1}.", "error")
            return redirect(url_for("delivery_dashboard"))

    success, result = create_completion_delivery(
        original_delivery_id=delivery_id,
        user_id=user_id,
        delivery_number=delivery_number,
        iar_number=iar_number,
        inspected_by=inspected_by,
        supply_officer=supply_officer,
        delivery_date=delivery_date,
        remarks=remarks,
        received_items=received_items
    )
    if success:
        flash(f"Completion delivery {delivery_number} created! Pending approval for remaining {sum(r['received_quantity'] for r in received_items)} units.", "success")
    else:
        flash(f"Complete failed: {result}", "error")
    return redirect(url_for("delivery_dashboard"))


# ============================================================
# INVENTORY MODULE — Live Ledger (inventory table via Products)
# Split into two separate routes as per spec
# ============================================================
def _inventory_context(search, category_filter, stock_filter):
    """Shared logic for both Admin and Staff inventory dashboards."""
    try:
        summary = get_inventory_summary()
        items = get_inventory_items(search_query=search, category_filter=category_filter, stock_status=stock_filter)
        categories = get_inventory_categories()
        return summary, items, categories
    except Exception as err:
        print(f"[inventory_dashboard] DB error: {err}")
        return {"total_unique":0,"total_asset_value":0,"low_stock_count":0,"out_of_stock_count":0}, [], []

@app.route("/admin/inventory")
def admin_inventory_dashboard():
    if "user_id" not in session:
        flash("Please log in to access Inventory.", "error")
        return redirect(url_for("login"))
    if session.get("role") != "Admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    category_filter = request.args.get("category", "All")
    stock_filter = request.args.get("stock_status", "All")
    summary, items, categories = _inventory_context(search, category_filter, stock_filter)
    return safe_render_template(
        "Admin Dashboards/admin_inventory_dashboard.html",
        user=session,
        summary=summary,
        items=items,
        categories=categories,
        search=search,
        category_filter=category_filter,
        stock_filter=stock_filter
    )

@app.route("/inventory")
@app.route("/staff/inventory")
def staff_inventory_dashboard():
    if "user_id" not in session:
        flash("Please log in to access Inventory.", "error")
        return redirect(url_for("login"))
    if session.get("role") not in ("Staff", "Admin"):
        flash("Staff access required.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    category_filter = request.args.get("category", "All")
    stock_filter = request.args.get("stock_status", "All")
    summary, items, categories = _inventory_context(search, category_filter, stock_filter)
    # Staff and Admin can both view staff template via /inventory, but admin_inventory has dedicated route
    # If Admin hits /inventory, show staff view for consistency; admin should use /admin/inventory
    return safe_render_template(
        "Staff Dashboards/staff_inventory_dashboard.html",
        user=session,
        summary=summary,
        items=items,
        categories=categories,
        search=search,
        category_filter=category_filter,
        stock_filter=stock_filter
    )

# Backward compatibility: old generic endpoint that staff templates previously used
@app.route("/inventory_legacy")
def inventory_dashboard():
    # Redirect based on role to correct dashboard
    if session.get("role") == "Admin":
        return redirect(url_for("admin_inventory_dashboard"))
    return redirect(url_for("staff_inventory_dashboard"))

# ============================================================
# WITHDRAWAL & REQUISITION MODULE (RIS) — Separate Admin/Staff
# ============================================================
@app.route("/admin/withdraw")
def admin_withdraw_dashboard():
    if "user_id" not in session:
        flash("Please log in to access Withdrawals.", "error")
        return redirect(url_for("login"))
    if session.get("role") != "Admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status_filter", "All")
    try:
        withdrawals = get_all_withdrawals(search_query=search, status_filter=status_filter, user_id=None)
        available = get_withdraw_products()
    except Exception as err:
        print(f"[admin_withdraw_dashboard] {err}")
        flash("Database error loading Withdrawals.", "error")
        withdrawals=[]; available=[]
    return safe_render_template(
        "Admin Dashboards/admin_withdraw_dashboard.html",
        user=session,
        withdrawals=withdrawals,
        available_products=available,
        search=search,
        status_filter=status_filter
    )

@app.route("/withdraw")
@app.route("/staff/withdraw")
def staff_withdraw_dashboard():
    if "user_id" not in session:
        flash("Please log in to access Withdrawals.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status_filter", "All")
    # Staff sees all withdrawals (shared ledger) — no user filter to avoid confusion
    try:
        withdrawals = get_all_withdrawals(search_query=search, status_filter=status_filter, user_id=None)
        available = get_withdraw_products()
    except Exception as err:
        print(f"[staff_withdraw_dashboard] {err}")
        flash("Database error loading Withdrawals.", "error")
        withdrawals=[]; available=[]
    return safe_render_template(
        "Staff Dashboards/staff_withdraw_dashboard.html",
        user=session,
        withdrawals=withdrawals,
        available_products=available,
        search=search,
        status_filter=status_filter
    )

@app.route("/withdraw/create", methods=["POST"])
def create_withdrawal_action():
    if "user_id" not in session:
        flash("Please log in.", "error")
        return redirect(url_for("login"))
    user_id=session.get("user_id")
    ris_number=request.form.get("ris_number","").strip()
    department=request.form.get("department","").strip()
    purpose=request.form.get("purpose","").strip()
    received_by=request.form.get("received_by","").strip()
    date_requested=request.form.get("date_requested","").strip()
    product_ids=request.form.getlist("product_id[]")
    quantities=request.form.getlist("quantity[]")
    if not all([ris_number, department, purpose]):
        flash("RIS Number, Department and Purpose are required.", "error")
        return redirect(request.referrer or url_for("staff_withdraw_dashboard" if session.get("role")=="Staff" else "admin_withdraw_dashboard"))
    if not product_ids:
        flash("Add at least one item.", "error")
        return redirect(request.referrer or url_for("staff_withdraw_dashboard" if session.get("role")=="Staff" else "admin_withdraw_dashboard"))
    items=[]
    for i, pid_raw in enumerate(product_ids):
        try:
            pid=int(pid_raw.strip()) if pid_raw else None
            if pid is None: continue
            qty_raw=quantities[i].strip() if i < len(quantities) and quantities[i] else ""
            if qty_raw=="":
                flash(f"Quantity required for item row {i+1}.", "error")
                return redirect(request.referrer or url_for("staff_withdraw_dashboard" if session.get("role")=="Staff" else "admin_withdraw_dashboard"))
            qty=int(qty_raw)
            if qty<=0: raise ValueError
            items.append({"product_id":pid,"quantity":qty})
        except (ValueError, IndexError, AttributeError):
            flash(f"Invalid quantity row {i+1}.", "error")
            return redirect(request.referrer or url_for("staff_withdraw_dashboard" if session.get("role")=="Staff" else "admin_withdraw_dashboard"))
    success, result = create_withdrawal(user_id, ris_number, department, purpose, received_by, date_requested, items)
    if success:
        flash(f"Withdrawal {ris_number} submitted! Pending approval (stock not yet deducted).", "success")
    else:
        flash(f"Failed: {result}", "error")
    # Redirect back to appropriate dashboard
    if session.get("role")=="Admin":
        return redirect(url_for("admin_withdraw_dashboard"))
    return redirect(url_for("staff_withdraw_dashboard"))

@app.route("/withdraw/details/<int:withdrawal_id>")
def get_withdrawal_details_api(withdrawal_id):
    if "user_id" not in session:
        return {"error":"Unauthorized"}, 401
    header, items = get_withdrawal_details(withdrawal_id)
    if not header:
        return {"error":"Withdrawal not found"}, 404
    try:
        header["date_requested"]=header["date_requested"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(header["date_requested"],"strftime") else str(header["date_requested"] or "")
    except: header["date_requested"]=str(header.get("date_requested",""))
    try:
        header["date_issued"]=header["date_issued"].strftime("%Y-%m-%d %H:%M:%S") if header.get("date_issued") and hasattr(header["date_issued"],"strftime") else str(header.get("date_issued") or "")
    except: header["date_issued"]=str(header.get("date_issued",""))
    for it in items:
        try: it["unit_price"]=float(it.get("unit_price") or 0)
        except: it["unit_price"]=0.0
        try: it["total_price"]=float(it.get("total_price") or 0)
        except: it["total_price"]=0.0
        try: it["quantity"]=int(it.get("quantity") or 0)
        except: it["quantity"]=0
    return {"header":header,"items":items}

@app.route("/withdraw/approve/<int:withdrawal_id>", methods=["POST"])
def approve_withdrawal_action(withdrawal_id):
    if session.get("role") != "Admin":
        flash("Admin required.", "error")
        return redirect(url_for("admin_withdraw_dashboard"))
    admin_id=session.get("user_id")
    ok,msg=approve_withdrawal(withdrawal_id, admin_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_withdraw_dashboard"))

@app.route("/withdraw/reject/<int:withdrawal_id>", methods=["POST"])
def reject_withdrawal_action(withdrawal_id):
    if session.get("role") != "Admin":
        flash("Admin required.", "error")
        return redirect(url_for("admin_withdraw_dashboard"))
    admin_id=session.get("user_id")
    ok,msg=reject_withdrawal(withdrawal_id, admin_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_withdraw_dashboard"))

# ============================================================
# RETURN MODULE — Separate Admin/Staff
# ============================================================
@app.route("/admin/returns")
def admin_return_dashboard():
    if "user_id" not in session:
        flash("Please log in to access Returns.", "error")
        return redirect(url_for("login"))
    if session.get("role") != "Admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status_filter", "All")
    try:
        returns = get_all_returns(search_query=search, status_filter=status_filter, user_id=None)
        issued = get_issued_withdrawals()
        products = get_return_products()
    except Exception as err:
        print(f"[admin_return] {err}")
        flash("Database error loading Returns.", "error")
        returns=[]; issued=[]; products=[]
    return safe_render_template(
        "Admin Dashboards/admin_return_dashboard.html",
        user=session,
        returns=returns,
        issued_withdrawals=issued,
        available_products=products,
        search=search,
        status_filter=status_filter
    )

@app.route("/returns")
@app.route("/staff/returns")
def staff_return_dashboard():
    if "user_id" not in session:
        flash("Please log in to access Returns.", "error")
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status_filter", "All")
    try:
        returns = get_all_returns(search_query=search, status_filter=status_filter, user_id=None)
        issued = get_issued_withdrawals()
        products = get_return_products()
    except Exception as err:
        print(f"[staff_return] {err}")
        flash("Database error loading Returns.", "error")
        returns=[]; issued=[]; products=[]
    return safe_render_template(
        "Staff Dashboards/staff_return_dashboard.html",
        user=session,
        returns=returns,
        issued_withdrawals=issued,
        available_products=products,
        search=search,
        status_filter=status_filter
    )

@app.route("/returns/create", methods=["POST"])
def create_return_action():
    if "user_id" not in session:
        flash("Please log in.", "error")
        return redirect(url_for("login"))
    user_id=session.get("user_id")
    return_number=request.form.get("return_number","").strip()
    withdrawal_id=request.form.get("withdrawal_id","").strip()
    department=request.form.get("department","").strip()
    reason=request.form.get("reason","").strip()
    date_returned=request.form.get("date_returned","").strip()
    product_ids=request.form.getlist("product_id[]")
    quantities=request.form.getlist("returned_quantity[]")
    conditions=request.form.getlist("condition_status[]")
    if not all([return_number, department, reason]):
        flash("Return Number, Department and Reason are required.", "error")
        return redirect(request.referrer or (url_for("staff_return_dashboard") if session.get("role")=="Staff" else url_for("admin_return_dashboard")))
    if not product_ids:
        flash("Add at least one item.", "error")
        return redirect(request.referrer or (url_for("staff_return_dashboard") if session.get("role")=="Staff" else url_for("admin_return_dashboard")))
    items=[]
    for i, pid_raw in enumerate(product_ids):
        try:
            pid=int(pid_raw.strip()) if pid_raw else None
            if pid is None: continue
            qty_raw=quantities[i].strip() if i < len(quantities) and quantities[i] else ""
            if qty_raw=="":
                flash(f"Returned quantity required row {i+1}.", "error")
                return redirect(request.referrer or (url_for("staff_return_dashboard") if session.get("role")=="Staff" else url_for("admin_return_dashboard")))
            qty=int(qty_raw)
            cond=conditions[i].strip() if i < len(conditions) and conditions[i] else "Serviceable"
            if cond not in ("Serviceable","Unserviceable"):
                cond="Serviceable"
            items.append({"product_id":pid,"returned_quantity":qty,"condition_status":cond})
        except (ValueError, IndexError, AttributeError):
            flash(f"Invalid row {i+1}.", "error")
            return redirect(request.referrer or (url_for("staff_return_dashboard") if session.get("role")=="Staff" else url_for("admin_return_dashboard")))
    success, result = create_return(user_id, return_number, withdrawal_id or None, department, reason, date_returned, items)
    if success:
        flash(f"Return {return_number} submitted! Pending approval (serviceable will restock on approve).", "success")
    else:
        flash(f"Failed: {result}", "error")
    if session.get("role")=="Admin":
        return redirect(url_for("admin_return_dashboard"))
    return redirect(url_for("staff_return_dashboard"))

@app.route("/returns/details/<int:return_id>")
def get_return_details_api(return_id):
    if "user_id" not in session:
        return {"error":"Unauthorized"}, 401
    header, items = get_return_details(return_id)
    if not header:
        return {"error":"Return not found"}, 404
    try:
        header["date_returned"]=header["date_returned"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(header["date_returned"],"strftime") else str(header["date_returned"] or "")
    except: header["date_returned"]=str(header.get("date_returned",""))
    for it in items:
        try: it["unit_price"]=float(it.get("unit_price") or 0)
        except: it["unit_price"]=0.0
        try: it["total_price"]=float(it.get("total_price") or 0)
        except: it["total_price"]=0.0
        try: it["returned_quantity"]=int(it.get("returned_quantity") or it.get("quantity") or 0)
        except: it["returned_quantity"]=0
    return {"header":header,"items":items}

@app.route("/returns/approve/<int:return_id>", methods=["POST"])
def approve_return_action(return_id):
    if session.get("role") != "Admin":
        flash("Admin required.", "error")
        return redirect(url_for("admin_return_dashboard"))
    admin_id=session.get("user_id")
    ok,msg=approve_return(return_id, admin_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_return_dashboard"))

@app.route("/returns/reject/<int:return_id>", methods=["POST"])
def reject_return_action(return_id):
    if session.get("role") != "Admin":
        flash("Admin required.", "error")
        return redirect(url_for("admin_return_dashboard"))
    admin_id=session.get("user_id")
    ok,msg=reject_return(return_id, admin_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_return_dashboard"))


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, port=5000) 