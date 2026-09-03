# Web-Based CPSC Production & Inventory Management System (Prototype 2)

## Project Overview
**Prototype 2 — Secure Web Migration from Legacy MS Access**

The **Web-Based CPSC Production & Inventory Management System (Prototype 2)** is a capstone rebuild for the Camiguin Polytechnic State College (CPSC) Production Office, fully migrated from a legacy **MS Access** desktop file to a modern, secure, and auditable **Python/Flask + MySQL** web architecture.

**Why migrate?** Prototype 1 (MS Access) was single-user, manually tracked, and had two critical logic gaps:

1.  **PR/PO Price Variance:** Purchase Request (PR) estimates and Purchase Order (PO) vendor actuals were locked together, preventing real-world price differences.
2.  **Ghost Inventory Stock:** Manual row deletions left `Products.current_stock` desynced (e.g., deleting all deliveries but stock stayed 235, so next 50-item delivery showed 285).

**Prototype 2 fixes both** with strict validation, dynamic price overrides, and a clean-slate recovery path, while adding multi-user security and intelligent Camiguin-local features.

> **Study Tip for Panel:** Follow the live flow: `Staff PR (estimate) → Admin Approve PR → PO (vendor actual, can differ) → Delivery (Pending, no stock) → Admin Approve & Inject (Received, stock 0→50) → Inventory Ledger → Withdrawal (RIS) out → Return handling`.

---

## Tech Stack

| Layer | Technology | Role in System |
| :--- | :--- | :--- |
| **Backend** | **Python 3.x**, **Flask Framework** | Micro-framework, Jinja2 templating, `session` auth, `safe_render_template` for Admin/Staff subfolders |
| **Database** | **MySQL (XAMPP / phpMyAdmin)**, `mysql-connector-python` | `Production_Inventory_db`, parameterized SQL (injection-safe), `FOR UPDATE` locks for idempotency |
| **Frontend** | **HTML5** (`<datalist>` combobox), **Bootstrap 5** (`data-bs-backdrop="static"` modals), **CSS3** (Poppins, gradients, flex/grid) | Responsive 260px sidebar, 42px buttons, control bars, data tables |
| **Scripting** | **JavaScript (ES6)** | Camiguin autocomplete, cascading `Municipality → Barangay`, form validation (`09\d{9}` PH mobile), toasts, `cascade-unveil` (header 0s → cards 0.25s → tables 0.5s) |
| **Tooling** | XAMPP, VS Code, Git | Local Apache/MySQL, DB admin, version control |

---

## Core Modules & Architecture

### 1. Role-Based Access Control (Admin vs Staff)
- **Admin (Full CRUD):** Dashboard metrics, User approval (`Approved_By`), Supplier/Product full CRUD (Add/Edit/Delete), Approve/Reject PR/PO/Delivery/Withdraw/Return, full Inventory oversight.
- **Staff (Add/Edit Only):** Submit PR, Track PO, Receive Delivery (fill IAR), view Inventory, Request Withdrawal/Return, Supplier/Product Add/Edit — **Delete strictly Admin-only** (`if session.get("role") != "Admin": flash("Delete access denied...")` + redirect to `staff_*`).
- **Session Management:** `session['user_id','username','full_name','role']` set on `login_user()` (BINARY case-sensitive), validated on every protected route (`if "user_id" not in session: redirect /login`).

### 2. Procurement Flow (PR → PO with Dynamic Price Overrides → Deliveries/IAR)
- **Purchase Request (PR):** Staff multi-line `purchase_requests` + `pr_items` (price = estimate), `PR-YYYY-XXX`, `Pending` → Admin `Approved/Rejected`, `has_po` prevents duplicate PO.
- **Purchase Order (PO) — Critical Fix:** `create_po_from_pr(pr_id, user_id, adjusted_items)` — If `adjusted_items` (modal editable **Actual PO Price**) provided, uses `unit_price * quantity` as vendor actual and recomputes `po_total`; else falls back to PR items. Modal shows `PR Est. Price (read-only)` vs `Actual PO Price (editable)` + `PRD-XXX` preview. Fixes Prototype 1 gap where `pr_items.price == po_items.price` was forced.
- **Delivery & IAR (Strict 2-Step):**
    - **Step 1 (Any role):** `create_delivery()` inserts `deliveries`/`delivery_items` with `status='Pending'`, `is_partial` auto-computed (`received != ordered` → partial), **NO stock change**, validates `received <= ordered` and `prev + new <= ordered` (prevents over-delivery across partials).
    - **Step 2 (Admin only):** `approve_delivery()` → `SELECT ... FOR UPDATE` lock, guards: `if status != 'Pending'` or `approved_by IS NOT NULL` or `stock_movements` exists → block double-click (`flash "Approve blocked: already 'Received' — double-click"`), then `UPDATE Products SET current_stock = current_stock + received_quantity` (**exact accepted qty**, not ordered), `quantity = current_stock` sync, logs `stock_movements (+qty)`, updates `purchase_orders` → `Partial/Delivered`, sets `deliveries.status='Received'`.

### 3. Inventory Ledger & Stock Management (Real-time)
- **Live Ledger:** `Products.current_stock` (not static `quantity`) is the source of truth, plus `items` physical ledger per delivery. `crud_inventory.py` provides `get_inventory_summary()` (total_unique, asset_value `sum(current_stock*price)`, low/out counts via `reorder_level`) and `get_inventory_items()` with category/stock filters (`In Stock > reorder`, `Low Stock 0<stock<=reorder`, `Out of Stock ==0`).
- **Movement Tracking:** Every stock change logs to `stock_movements` (`reference_type='Delivery'/'Withdrawal'/'Return'`, `quantity_change`, `balance_after`, `user_id`) for audit. `FOR UPDATE` and idempotency guards prevent ghost stock.
- **Ghost Fix:** Strict `Pending → Received` validation + `RESET_CLEAN_SLATE.sql` (see below) to zero `current_stock` after manual deletions.

### 4. Outbound Operations (Withdrawals / RIS)
- **Withdrawal (RIS):** Staff creates `withdraw` + `withdraw_items` with `status='Pending'` after validating `requested <= current_stock` (live check). **No deduction yet**. Admin `approve_withdrawal()` re-validates, then `UPDATE Products SET current_stock = current_stock - qty` (exact requested), syncs `quantity`, logs `stock_movements (-qty)`, sets `status='Approved'`, `issued_by`. Guard: `if status != 'Pending'` → block double-approve. Rejects set `Rejected`.
- **Return (Defective to Supplier):** Similar to Withdrawal but for returns: Staff creates `return` + `return_items` from `Products` directly (not linked to withdrawals), validates `qty <= current_stock`, `Pending`. Admin `approve_return()` → if `Serviceable` **deducts** (`current_stock - qty`) and logs `-qty` (like Withdrawal, taking OUT of inventory); `Unserviceable` logs `0` change for waste audit. Uses correct singular tables ``return``/``return_items`` (backticked, `RETURN` is reserved).

---

## Local Setup & Reset Guide

### Prerequisites
- **XAMPP** (Apache + MySQL), **Python 3.10+**, `pip`, Git (optional)

### A. Start Flask Server (`python App.py`)

1.  **Open Project**
    ```bash
    cd "C:\Users\user\OneDrive\Desktop\BSIT 3A 1ST SEM\IM 103 - ADVANCE DATABASE SYSTEM 2\CPSC INVENTORY FRESH"
    ```

2.  **Start MySQL (XAMPP)**
    - XAMPP Control Panel → Start **Apache** + **MySQL** (`root` no password, port 3306). Verify at `http://localhost/phpmyadmin`.

3.  **Create Python Env & Install Deps**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    pip install flask mysql-connector-python
    ```

4.  **Configure Database**
    - App auto-creates `Production_Inventory_db` on first run via `db.py:get_db_connection()` (catches `1049` → `CREATE DATABASE`).
    - Manual alternative: `python Tables/Database_Tables.py`

5.  **Run Flask**
    ```bash
    python App.py
    # → * Running on http://127.0.0.1:5000  (debug=False, use_reloader=False)
    ```
    Browser → `http://127.0.0.1:5000` → `/login` → Register (Staff) → Admin approves at `/admin/users`.

6.  **Stop**
    - `CTRL+C` in terminal, then Stop MySQL/Apache in XAMPP.

### B. Clean-Slate Reset (If Database Desync / Ghost Stock Occurs)

**When to use:** You manually `DELETE FROM purchase_requests` etc. but `Products.current_stock` stayed `235` → next delivery `50` showed `285`. Or before final defense for clean `PR-001` demo.

**File:** `RESET_CLEAN_SLATE.sql` (at project root) — **Retains** `Users`, `Supplier`, `Products` rows; **Deletes** all transaction tables and **zeroes stock**.

**Steps in phpMyAdmin:**
1.  XAMPP → Start MySQL → `http://localhost/phpmyAdmin` → Click `Production_Inventory_db` (or `production_inventory_db`) on left.
2.  Top menu → **SQL** → Click **Choose File** or paste → Open `RESET_CLEAN_SLATE.sql` in VS Code (`Ctrl+A`, `Ctrl+C`), paste into SQL box.
3.  Click **Go**. You should see green check, `X rows affected` for each `DELETE`.
4.  **Verify clean state** (run in same SQL tab):
    ```sql
    SELECT product_id, product_name, current_stock, quantity FROM products LIMIT 5;
    -- Expected: all current_stock=0, quantity=0
    SELECT (SELECT COUNT(*) FROM purchase_requests) AS pr,
           (SELECT COUNT(*) FROM purchase_orders) AS po,
           (SELECT COUNT(*) FROM deliveries) AS del,
           (SELECT COUNT(*) FROM `withdraw`) AS wit,
           (SELECT COUNT(*) FROM `return`) AS ret,
           (SELECT COUNT(*) FROM stock_movements) AS mov;
    -- Expected: all 0
    ```
5.  **Test clean flow:** `PR → Approve → PO (override price) → Approve → Delivery 50 (Pending, stock 0) → Approve (Received, stock 0→50, not 235)` — correct.

**What the script does (safe, no `DROP`):**
```sql
SET FOREIGN_KEY_CHECKS=0;
DELETE FROM `pr_items`; DELETE FROM `purchase_orders`; DELETE FROM `po_items`; DELETE FROM `purchase_requests`;
DELETE FROM `delivery_items`; DELETE FROM `deliveries`; DELETE FROM `items`;
DELETE FROM `withdraw_items`; DELETE FROM `withdraw`;
DELETE FROM `return_items`; DELETE FROM `return`;
DELETE FROM `stock_movements`;
ALTER TABLE `purchase_requests` AUTO_INCREMENT=1; -- (all transaction tables)
UPDATE `products` SET `current_stock`=0, `quantity`=0, `starting_stock`=0;
SET FOREIGN_KEY_CHECKS=1;
```
*Legacy `iar_*` and `stock_withdrawals` deletes are commented out — uncomment only if those tables exist, to avoid `Table doesn't exist` error.*

---
**Capstone Team — BSIT 3A, CPSC | Prototype 2 (2026) | Tip: Demo the fixed variance (PR 100 → PO 120) and ghost-stock reset live.**
