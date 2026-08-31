# Changelog — CPSC Production Office Inventory Management System

All notable architectural changes are documented here. Follows `production_inventory_db` normalized lifecycle.

---

## [v1.3.0] — UI/UX Refactor: Floating Toast System
**Date:** 2026-08-31

- **Converted all notifications to top-center floating toasts** (`base.html`, `Loginpage.html`, `forgot_password.html`, all `Admin/Staff Dashboards/*`):
  - Removed inline `{% with messages = get_flashed_messages() %}` blocks from `.form-section`, `.dashboard-container`, `table-card`, and modals that previously pushed/warped layout.
  - Introduced global markup outside main wrapper:
    ```html
    <div id="toast-container" class="toast-container">
      {% with messages = get_flashed_messages(with_categories=true) %}
        <div class="toast-card toast-{{ category }}">
          <span class="toast-icon">{% if success %}😊{% elif error %}⚠️{% else %}ℹ️{% endif %}</span>
          <span class="toast-message">{{ message }}</span>
          <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
        </div>
      {% endwith %}
    </div>
    ```
  - Non-disruptive CSS: `position:fixed; top:20px; left:50%; transform:translateX(-50%); z-index:9999; pointer-events:none` + `toast-card` `box-shadow:0 8px 20px rgba(0,0,0,0.18); animation:toastIn 0.4s / toastOut 0.4s 3.5s forwards`.
  - Auto-dismiss JS: `DOMContentLoaded → querySelectorAll('.toast-card') → setTimeout 4000ms → fade+scale → remove()`.
  - **Forgot Password** redesigned to match Login: `body::before` blurred `cpsc_bg.jpg` (`filter:blur(6px); opacity:0.35; transform:scale(1.05)`) + `backdrop-filter:blur(5px)` card, consistent `Poppins` theme.

---

## [v1.2.0] — Centralized Schema Setup
**Date:** 2026-08-30

- **Consolidated table creation into `Tables/Database_Tables.py`** with `if __name__ == "__main__":` main guard to prevent automatic table creation bugs on `App.py` startup:
  ```python
  def create_all_tables():
      # CREATE DATABASE IF NOT EXISTS production_inventory_db
      # CREATE TABLE users, supplier, products, purchase_requests, pr_items,
      #              purchase_orders, po_items, deliveries, delivery_items,
      #              items, withdraw, withdraw_items, `return`, return_items, stock_movements
  if __name__ == "__main__":
      create_all_tables()
  ```
- Deleted legacy scattered scripts (`User_Supplier_Products_Table.py`, `PR_PO_Delivery_Tables.py`, `Return_Withdraw.py`, `migrate_enums.py`) that auto-executed on import.
- Verified `db.py` targets lowercase `production_inventory_db` (`get_db_connection()` auto-creates DB if `errno 1049`) and `App.py`/`db.py` contain **no** `import Tables.Database_Tables` side-effects that recreate `inventory`/`withdrawals`/`withdrawal_items`.
- All CRUD now call `_ensure_*_schema()` lazily via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` rather than import-time DDL.

---

## [v1.1.0] — Normalized Database Architecture
**Date:** 2026-08-29

- **Decoupled withdrawals from batch delivery constraints** to support warehouse-wide pooling:
  - Before: `withdraw` legacy table tied to `po_id`/`pr_id`/`delivery_id` per batch (`quantity` single row, `withdraw_number`).
  - After: Clean `withdraw(withdraw_id, ris_number UNIQUE, user_id, department, purpose, status ENUM Pending/Approved/Rejected/Issued, issued_by, received_by, date_requested, date_issued)` + `withdraw_items(withdraw_item_id, withdraw_id, product_id, item_name, quantity, unit, unit_price, total_price)` — **strictly `product_id` sourced**, validated `requested ≤ products.current_stock` (live `COALESCE(current_stock,quantity)`).
- **Physical ledger `items`** generated only on Delivery `Received`: `INSERT INTO items (delivery_id, po_id, pr_id, user_id, supplier_id, product_id, item_name, item_quantity, item_price)`.
- **Stock audit `stock_movements`** unified: `reference_type ENUM('Delivery','Withdrawal','Return')`, `quantity_change` (+/-), `balance_after` — Delivery `+qty`, Withdrawal `-qty`, Return `+qty` only for `Serviceable`.
- **Return normalization:** `return(return_id, return_number UNIQUE, withdraw_id NULL, user_id, department, reason, status Pending/Approved/Rejected, approved_by)` (backticked) + `return_items(return_item_id, return_id, product_id, returned_quantity, condition_status Serviceable/Unserviceable)` — validates `returned ≤ issued` when `withdraw_id` set; `Unserviceable` does not credit stock (waste audit via `stock_movements` `Return-Unserviceable` 0 change).
- Impact: `crud_withdrawal`, `crud_returns`, `crud_delivery` now strictly query active tables (`withdraw`/`withdraw_items`, `return`/`return_items`, `products.current_stock`, `items`) with parameterized `%s`; legacy `inventory`, `withdrawals`, `withdrawal_items` no longer created.

---

## [v1.0.0] — Initial Flask Setup
**Date:** 2026-08-20

- **Flask + MySQL bootstrap:** `App.py` with `Flask`, `render_template`, `request`, `session`, `flash`, `safe_render_template()` helper; `db.py` `get_db_connection()` to `Production_Inventory_db` (later normalized to lowercase).
- **Basic authentication & CRUD routes:** `/login`, `/register`, `/logout`, `/admin/users`, `/admin/suppliers`, `/admin/products` with `crud_users` (`register_user`, `login_user WHERE username=%s AND password=%s`), `crud_suppliers`, `crud_products` (`quantity` only).
- **Procurement stubs:** `purchase_requests` / `pr_items` and `purchase_orders` / `po_items` with `Pending → Approved` flow, but coupled and without `current_stock`/`reorder_level` or `items` ledger.
- **UI:** Bootstrap 5 + `Poppins`, static `cpsc_logo.png`, inline `alert` flash messages inside cards (later refactored to toasts).

---

## Migration Notes

- **Re-init DB:** `python Tables/Database_Tables.py` is idempotent (`IF NOT EXISTS`); safe to re-run after `v1.1.0`/`v1.2.0` to add `current_stock`, `reorder_level`, and new `withdraw`/`return` tables. Legacy `inventory`/`withdrawals` tables, if present, are ignored (no longer recreated).
- **Test Accounts:** `admin/123`, `raymond/123` — ensure `users.Approved_By=1` for Admin.
