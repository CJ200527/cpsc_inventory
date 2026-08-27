import os
import sys
import re

from flask import Flask, render_template, request, redirect, url_for, session, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_MANAGEMENT_DIR = os.path.join(BASE_DIR, "CRUD_Operations", "User_Authentication_and_Management")
if USER_MANAGEMENT_DIR not in sys.path:
    sys.path.insert(0, USER_MANAGEMENT_DIR)

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

# Initialize Flask Application
app = Flask(__name__)

# Secret key required by Flask to handle user sessions and flash notification messages
app.secret_key = "cpsc_inventory_secret_key"


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
            return render_template("Loginpage.html")
        try:
            user = login_user(username, password)
        except Exception as err:
            print(f"[login] DB error: {err}")
            flash("Database connection failed. Is MySQL/XAMPP running?", "error")
            return render_template("Loginpage.html")

        if user:
            # Save user identity into browser session
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = f"{user['Firstname']} {user['Lastname']}"
            session["role"] = user["Role"]

            flash(f"Welcome back, {user['Firstname']}!", "success")
            
            # Redirect based on user role
            if user["Role"] == "Admin":
                return redirect(url_for("admin_dashboard"))
            elif user["Role"] == "Staff":
                return redirect(url_for("staff_dashboard"))
            else:
                # Unknown role - clear session and redirect to login
                flash("User role not recognized. Please contact Admin.", "error")
                session.clear()
                return redirect(url_for("login"))
        else:
            flash("Invalid credentials OR account is pending Admin approval.", "error")

    # If method is GET, simply display the HTML page
    return render_template("Loginpage.html")

# --- ROUTE: Forgot Password Reset ---
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        new_password = request.form.get("new_password", "").strip()
        if not all([username, contact_number, new_password]):
            flash("All fields are required to reset password.", "error")
            return render_template("forgot_password.html")
        if not re.fullmatch(r"09\d{9}", contact_number):
            flash("Contact number must be 11 digits starting with 09.", "error")
            return render_template("forgot_password.html")
        try:
            success = reset_password_verified(username, contact_number, new_password)
        except Exception as err:
            print(f"[forgot_password] DB error: {err}")
            flash("Database error. Is MySQL running?", "error")
            return render_template("forgot_password.html")
        if success:
            flash("Password updated successfully! You can now sign in with your new password.", "success")
            return redirect(url_for("login"))
        else:
            flash("Verification failed! Username and Contact Number do not match our records.", "error")
    return render_template("forgot_password.html")


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

    # Philippine mobile: must be 09 + 9 digits = 11 digits total
    if not re.fullmatch(r"09\d{9}", contact_number):
        flash("Invalid contact number! Must be 11 digits starting with '09' (e.g., 09123456789).", "error")
        return redirect(url_for("login"))

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
        flash("Account created! Please wait for Admin approval before signing in.", "success")
        return redirect(url_for("login"))
    else:
        flash("Registration failed. Username may already be taken.", "error")
        return redirect(url_for("login"))


# --- ROUTE 4: Logout Action ---
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# --- ROUTE 5: Admin Dashboard (Protected - Requires Login) ---
@app.route("/admin_dashboard")
def admin_dashboard():
    """Admin dashboard page - only accessible to logged-in admins."""
    if "user_id" not in session:
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for("login"))
    if session.get("role") != "Admin":
        flash("You do not have permission to access the admin dashboard.", "error")
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html", username=session.get("username"), role=session.get("role"), full_name=session.get("full_name"))

# --- ROUTE 6: Staff Dashboard (Protected - Requires Login as Staff) ---
@app.route("/staff_dashboard")
def staff_dashboard():
    """Staff dashboard page - only accessible to logged-in staff users."""
    if "user_id" not in session:
        flash("Please log in to access the staff dashboard.", "error")
        return redirect(url_for("login"))
    if session.get("role") != "Staff":
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("login"))
    return render_template("staff_dashboard.html", username=session.get("username"), role=session.get("role"), full_name=session.get("full_name"))

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
    return render_template("user_management.html", user=session, users=users, search=search, date_filter=date_filter, custom_date=custom_date)

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
        try:
            success = update_user_info(user_id=target_id, first_name=first_name, middle_initial=middle_initial, last_name=last_name, username=username, role=role, contact_number=contact_number)
            if success:
                flash(f"User USR-{'%03d' % target_id} updated successfully!", "success")
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
    return render_template("supplier_management.html", user=session, suppliers=suppliers, search=search, date_filter=date_filter, custom_date=custom_date)

# --- ACTION ROUTE: Add New Supplier ---
@app.route("/admin/suppliers/add", methods=["POST"])
def admin_add_supplier_action():
    if session.get("role") != "Admin":
        flash("Admin access required.", "error")
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
    if not all([supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country]):
        flash("All fields are required. Please fill every textbox.", "error")
        return redirect(url_for("admin_suppliers", search=request.args.get("search","")))
    if not re.fullmatch(r"09\d{9}", contact_number):
        flash("Invalid contact number! Must be 11 digits starting with 09.", "error")
        return redirect(url_for("admin_suppliers", search=request.args.get("search","")))
    if "@" not in email or "." not in email:
        flash("Invalid email address.", "error")
        return redirect(url_for("admin_suppliers", search=request.args.get("search","")))
    try:
        ok = add_supplier(supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country)
        flash(f"Supplier '{supplier_name}' added!" if ok else "Failed to add supplier.", "success" if ok else "error")
    except Exception as err:
        flash(f"Add failed: {err}", "error")
    return redirect(url_for("admin_suppliers", search=request.args.get("search","")))

# --- ACTION ROUTE: Update Supplier ---
@app.route("/admin/suppliers/update/<int:target_id>", methods=["POST"])
def admin_update_supplier_action(target_id):
    if session.get("role") != "Admin":
        flash("Admin access required.", "error")
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
    if not all([supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country]):
        flash("All fields are required. Please fill every textbox.", "error")
        return redirect(url_for("admin_suppliers", search=request.args.get("search","")))
    if not re.fullmatch(r"09\d{9}", contact_number):
        flash("Invalid contact number! Must be 11 digits starting with 09.", "error")
        return redirect(url_for("admin_suppliers", search=request.args.get("search","")))
    try:
        ok = update_supplier(target_id, supplier_name, contact_person, contact_number, email, street, barangay, municipality, city, country)
        flash(f"Supplier SUP-{target_id:03d} updated!" if ok else "Update failed.", "success" if ok else "error")
    except Exception as err:
        flash(f"Update failed: {err}", "error")
    return redirect(url_for("admin_suppliers", search=request.args.get("search","")))

# --- ACTION ROUTE: Delete Supplier ---
@app.route("/admin/suppliers/delete/<int:target_id>", methods=["POST"])
def admin_delete_supplier_action(target_id):
    if session.get("role") != "Admin":
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
    return render_template("product_management.html", user=session, products=products, suppliers_list=suppliers_list, search=search, date_filter=date_filter, custom_date=custom_date)

@app.route("/admin/products/add", methods=["POST"])
def admin_add_product():
    if session.get("role") != "Admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    supplier_id = request.form.get("supplier_id", "").strip()
    product_name = request.form.get("product_name", "").strip()
    category = request.form.get("category", "").strip()
    details = request.form.get("details", "").strip()
    unit = request.form.get("unit", "").strip()
    size = request.form.get("size", "").strip()
    price = request.form.get("price", "").strip()
    if not all([supplier_id, product_name, category, unit, size, details, price]):
        flash("All fields are required (including price and specification).", "error")
        return redirect(url_for("admin_products", search=request.args.get("search","")))
    try:
        supplier_id = int(supplier_id)
        price = float(price)
        if price < 0: raise ValueError
    except:
        flash("Price must be a valid number (0 or more) and supplier must be selected.", "error")
        return redirect(url_for("admin_products", search=request.args.get("search","")))
    try:
        ok = add_product(supplier_id, product_name, category, details, unit, size, price)
        flash(f"Product '{product_name}' added!" if ok else "Failed to add product.", "success" if ok else "error")
    except Exception as err:
        flash(f"Add failed: {err}", "error")
    return redirect(url_for("admin_products", search=request.args.get("search","")))

@app.route("/admin/products/update/<int:target_id>", methods=["POST"])
def admin_update_product(target_id):
    if session.get("role") != "Admin":
        flash("Admin access required.", "error")
        return redirect(url_for("login"))
    supplier_id = request.form.get("supplier_id", "").strip()
    product_name = request.form.get("product_name", "").strip()
    category = request.form.get("category", "").strip()
    details = request.form.get("details", "").strip()
    unit = request.form.get("unit", "").strip()
    size = request.form.get("size", "").strip()
    price = request.form.get("price", "").strip()
    if not all([supplier_id, product_name, category, unit, size, details, price]):
        flash("All fields are required.", "error")
        return redirect(url_for("admin_products", search=request.args.get("search","")))
    try:
        supplier_id = int(supplier_id); price = float(price)
        if price < 0: raise ValueError
    except:
        flash("Invalid price or supplier.", "error")
        return redirect(url_for("admin_products", search=request.args.get("search","")))
    try:
        ok = update_product(target_id, supplier_id, product_name, category, details, unit, size, price)
        flash(f"Product PRD-{target_id:03d} updated!" if ok else "Update failed.", "success" if ok else "error")
    except Exception as err:
        flash(f"Update failed: {err}", "error")
    return redirect(url_for("admin_products", search=request.args.get("search","")))

@app.route("/admin/products/delete/<int:target_id>", methods=["POST"])
def admin_delete_product(target_id):
    if session.get("role") != "Admin":
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
    # Staff users view only their own submitted requests; Admins view all institutional requests
    user_id_scope = None if user_role == "Admin" else session.get("user_id")

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

    # Choose template based on active role to guarantee sidebar navigation consistency
    template_file = "admin_pr_management.html" if user_role == "Admin" else "staff_pr_management.html"

    return render_template(
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

    # Build item payloads - skip empty/unselected rows safely
    items_payload = []
    for i, pid_raw in enumerate(product_ids):
        try:
            pid_str = pid_raw.strip() if pid_raw else ""
            sid_str = _safe(supplier_ids, i)
            iname = _safe(item_names, i)
            price_str = _safe(prices, i)
            qty_str = _safe(quantities, i)
            # Skip rows where dropdown not selected or required fields empty
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
    # Safe serialization: datetime -> string, Decimal -> float
    try:
        raw_date = header.get("date_requested")
        if raw_date:
            # Handle both datetime object and string
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
    user_id_scope = None if user_role == "Admin" else session.get("user_id")

    try:
        orders_list = get_all_purchase_orders(
            search_query=search,
            status_filter=status_filter,
            user_id=user_id_scope
        )
        approved_prs = get_approved_prs_without_po() if user_role == "Admin" else []
    except Exception as err:
        print(f"[po_management] DB error: {err}")
        flash("Database error loading Purchase Orders.", "error")
        orders_list = []
        approved_prs = []

    template_file = "admin_po_management.html" if user_role == "Admin" else "staff_po_management.html"

    return render_template(
        template_file,
        user=session,
        orders=orders_list,
        approved_prs=approved_prs,
        search=search,
        status_filter=status_filter
    )

# --- ACTION ROUTE: Generate PO from Approved PR (Admin Only) - with editable Actual PO prices ---
@app.route("/admin/po/generate", methods=["POST"])
def generate_po_action():
    if session.get("role") != "Admin":
        flash("Admin permission required.", "error")
        return redirect(url_for("po_management"))

    pr_id = request.form.get("pr_id")
    if not pr_id:
        flash("Please select an approved Purchase Request.", "error")
        return redirect(url_for("po_management"))

    # Read adjusted items (if form included editable price table)
    product_ids = request.form.getlist("product_id[]")
    supplier_ids = request.form.getlist("supplier_id[]")
    item_names = request.form.getlist("item_name[]")
    categories = request.form.getlist("category[]")
    units = request.form.getlist("unit[]")
    sizes = request.form.getlist("size[]")
    details_list = request.form.getlist("details[]")
    quantities = request.form.getlist("quantity[]")
    # Support both unit_price[] and price[] naming
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
                # Skip rows where required fields empty
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

# --- ACTION ROUTE: Get PO Details API (JSON for Modal) ---
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


if __name__ == "__main__":
    # Keep the app stable on Windows without the Flask reloader crash
    app.run(debug=False, use_reloader=False, port=5000)