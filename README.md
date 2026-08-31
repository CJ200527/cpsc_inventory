# CPSC Production Office Inventory Management System

**Flask + MySQL + Bootstrap 5 — Normalized Warehouse Lifecycle**

A complete procurement-to-issuance inventory system for **Camiguin Polytechnic State College (CPSC) — Balbagon, Mambajao, Camiguin**. Handles Purchase Requests, Purchase Orders, Delivery/IAR verification, live inventory ledger, withdrawals (RIS), and returns with full stock movement auditing.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3, Flask |
| **Database** | MySQL / MariaDB (phpMyAdmin / XAMPP) |
| **Connector** | `mysql-connector-python` |
| **Frontend** | HTML5 / CSS3, Bootstrap 5, Bootstrap Icons, Poppins font |
| **UI** | Top-center floating toast notifications (auto-dismiss 4s), `Poppins` typography, `#53c5f1` theme |

---

## Database Initialization

### 1. Configure `db.py` for Local MySQL Credentials

File: `db.py` (`get_db_connection()`)

```python
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # ← XAMPP default
        password="",          # ← set if you have a password
        database="production_inventory_db"  # lowercase per spec
    )
```

- The helper auto-creates `production_inventory_db` if `errno 1049` (DB not found).
- All CRUD modules reuse this single connection helper; no direct `mysql.connector.connect` elsewhere.

> **XAMPP Users:** Start Apache + MySQL, create user `root` with empty password, or update `user`/`password` above to match your `phpMyAdmin` credentials.

### 2. Create / Update the Normalized Schema

The consolidated schema lives in `Tables/Database_Tables.py` and is protected by a main guard to prevent accidental execution on `App.py` import:

```python
# Tables/Database_Tables.py
def create_all_tables():
    # CREATE DATABASE IF NOT EXISTS production_inventory_db
    # CREATE TABLE users, supplier, products, purchase_requests, pr_items,
    #              purchase_orders, po_items, deliveries, delivery_items,
    #              items, withdraw, withdraw_items, `return`, return_items, stock_movements

if __name__ == "__main__":
    create_all_tables()  # only runs on `python Tables/Database_Tables.py`
```

Run from project root:

```bash
# Windows (XAMPP MySQL running)
python Tables/Database_Tables.py
# or
python -m Tables.Database_Tables
```

Output: `Database & tables updated successfully!` — creates all **15 normalized tables** (`users`, `supplier`, `products`, `purchase_requests`, `pr_items`, `purchase_orders`, `po_items`, `deliveries`, `delivery_items`, `items`, `withdraw`, `withdraw_items`, `return`, `return_items`, `stock_movements`) with `ENGINE=InnoDB`, `FOREIGN KEY`s, and `ENUM` statuses. Safe to re-run (`IF NOT EXISTS`).

**Do NOT run legacy scripts** (`Tables/inventory`, `Tables/withdrawals` etc. are deleted) — only `Tables/Database_Tables.py`.

---

## System Workflow & Pipeline Architecture

### Procurement: PR → PO → Delivery (IAR Verification)

```
Staff/Admin → purchase_requests (Pending) → Admin approves → Approved
                ↓ has_po=1
              purchase_orders (Pending PO Approval → Approved → Issued)
                ↓
Staff/Admin selects Approved/Issued PO → deliveries (Pending) + delivery_items (only received_quantity editable)
                ↓ Admin Approves
              deliveries.status=Received, items ledger populated, PO → Partial/Delivered
```

- **PR:** `pr_management` (`/pr`) — staff creates multi-line `pr_items`, admin approves/rejects.
- **PO:** `po_management` (`/po`) — generate PO from Approved PR with editable vendor `unit_price`, admin approves `Pending PO Approval → Approved`.
- **Delivery:** `delivery_dashboard` (`/delivery`, `/admin/inventory` split) — `is_partial` auto-computed (`received != ordered`), `received > ordered` blocked, `Pending` → `Received` ingests stock.

### Stock Ingestion

Approving a Delivery (`crud_delivery.approve_delivery` in transaction `commit()/rollback()`):

1. `UPDATE deliveries SET status='Received', approved_by=%s`
2. `INSERT INTO items (delivery_id, po_id, pr_id, user_id, supplier_id, product_id, item_name, item_quantity, item_price)` per `delivery_items`
3. `UPDATE products SET current_stock = current_stock + received_quantity` (sync `quantity`)
4. `INSERT INTO stock_movements (product_id, reference_type='Delivery', reference_id, quantity_change +qty, balance_after, user_id)`

### Stock Requisition & Return

**Requisitions via `withdraw` + `withdraw_items` (RIS):**

- Form validates `requested_quantity ≤ products.current_stock` live + server (`SELECT ... current_stock`); `Pending` does **not** deduct.
- **Decoupled:** pulls strictly from `products` warehouse pool via `product_id` — **not** tied to PR/PO/Delivery batch IDs.
- Admin `POST /withdraw/approve` → `withdraw.status='Issued'`, `products.current_stock -= qty`, `stock_movements` `Withdrawal` `-qty`.

**Returns via `return` + `return_items` (Return Slip):**

- References optional `withdraw_id` (issued RIS); validates `returned ≤ issued` (`SELECT SUM(quantity) FROM withdraw_items`).
- `condition_status` selector: `Serviceable / Unused` vs `Unserviceable / Defective`; `Pending` no stock change.
- Admin `POST /returns/approve`:
  - `Serviceable`: `products.current_stock += returned_quantity` + `stock_movements Return +qty`
  - `Unserviceable`: no usable stock credit, logged as `Return-Unserviceable` for waste audit.

All writes use **parameterized `%s`** and `try: commit() except: rollback()`.

---

## Folder Structure Map

```
CPSC INVENTORY FRESH/
├── App.py                          # Flask routes: /login, /pr, /po, /delivery, /inventory (/admin/inventory), /withdraw (/admin/withdraw), /returns (/admin/returns), /products, /suppliers, /users
├── db.py                           # get_db_connection() → production_inventory_db
├── Tables/
│   └── Database_Tables.py          # Consolidated normalized schema (15 tables) with if __name__ == "__main__" guard
├── CRUD_Operations/
│   └── User_Authentication_and_Management/
│       ├── crud_users.py           # BINARY username/password, Approved_By checks
│       ├── crud_suppliers.py       # %s + commit/rollback
│       ├── crud_products.py        # products.current_stock live
│       ├── crud_pr.py              # purchase_requests / pr_items
│       ├── crud_po.py              # purchase_orders / po_items + delivered qty via approved deliveries
│       ├── crud_delivery.py        # deliveries/delivery_items → items + stock_movements
│       ├── crud_inventory.py       # products.current_stock aggregation (no legacy `inventory` table)
│       ├── crud_withdrawal.py      # withdraw/withdraw_items → stock_movements
│       ├── crud_returns.py         # `return`/return_items → conditional restock
│       └── crud_iar.py             # legacy wrapper → crud_delivery
├── Templates/
│   ├── base.html                   # Global toast container (top-center, non-disruptive)
│   ├── LogIn and Registration/
│   │   ├── Loginpage.html          # Log In + Sign Up with floating toasts, BINARY auth
│   │   └── forgot_password.html    # Blurred cpsc_bg.jpg background + toast
│   ├── Admin Dashboards/
│   │   ├── admin_dashboard.html                # Live cards: total_unique, in_stock, out_of_stock, asset_value
│   │   ├── admin_pr_management.html
│   │   ├── admin_po_management.html            # PR/PO creators + Received By, ₱ {:,.2f}
│   │   ├── admin_delivery_dashboard.html       # Pending queue + Approve confirm modal
│   │   ├── admin_inventory_dashboard.html      # Live ledger, no actions
│   │   ├── admin_withdraw_dashboard.html       # RIS queue + Approve/Reject
│   │   ├── admin_return_dashboard.html         # Return queue + Serviceable/Unserviceable
│   │   ├── product_management.html
│   │   ├── supplier_management.html
│   │   └── user_management.html
│   └── Staff Dashboards/
│       ├── staff_dashboard.html
│       ├── staff_pr_management.html
│       ├── staff_po_management.html
│       ├── staff_delivery_dashboard.html
│       ├── staff_inventory_dashboard.html
│       ├── staff_withdraw_dashboard.html
│       └── staff_return_dashboard.html
└── static/
    └── cpsc_logo.png / cpsc_bg.jpg # School seal & blurred login background
```

---

## Default Test Accounts

Seed via `users` table (`Approved_By=1`):

| Role  | Username  | Password | Note |
|-------|-----------|----------|------|
| **Admin** | `admin`     | `123`      | Full access: approve PR/PO, Delivery, Withdraw, Return |
| **Staff** | `raymond`   | `123`      | Can create PR/PO/Delivery/Withdraw/Return, views all records |

> On first run, register via `Log In → Sign Up`, then log in as `admin` → `Users` → Approve the new Staff account (`Approved_By=0 → 1`).

---

## Running the System

```bash
# 1. Install deps
pip install flask mysql-connector-python

# 2. Init DB (XAMPP MySQL running)
python Tables/Database_Tables.py

# 3. Start Flask
python App.py
# → http://127.0.0.1:5000  (redirects to /login)
```

All CRUD uses `cursor.execute(sql, (%s, ...))` and `flash()` top-center toasts (`toast-card toast-success/error/info` with `😊/⚠️/ℹ️`, auto-dismiss 4s) — no layout shift.

