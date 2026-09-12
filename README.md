# Web-Based CPSC Production & Inventory Management System (Prototype 2)

## Project Overview
**Prototype 2 — Secure Web Migration from Legacy MS Access**

The **Web-Based CPSC Production & Inventory Management System (Prototype 2)** is a capstone rebuild for the Camiguin Polytechnic State College (CPSC) Production Office, fully migrated from a legacy **MS Access** desktop file to a modern, secure, and auditable **Python/Flask + MySQL** web architecture.

**Why migrate?** Prototype 1 (MS Access) was single-user and manually tracked. **Prototype 2** adds multi-user security, a direct PR-to-Delivery procurement flow (no purchase-order step), exact-quantity live inventory with double-approval guards, and a just-in-time Master Catalog with product variants.

> **Study Tip for Panel:** Follow the live flow: `Staff creates PR (typed or catalog items, duplicates blocked) → Admin approves PR (status only, catalog untouched) → Staff/Admin creates Delivery directly from Approved PR (Pending, no stock, actual invoice prices editable) → Admin approves & injects (Received, exact received qty + weighted-average costing) → Live Inventory → Withdrawal (RIS) out → Return handling`.

---

## Tech Stack

| Layer | Technology | Role in System |
| :--- | :--- | :--- |
| **Backend** | **Python 3.x**, **Flask Framework** | Micro-framework, Jinja2 templating, `session` auth, `safe_render_template` for Admin/Staff subfolders |
| **Database** | **MySQL (XAMPP / phpMyAdmin)**, `mysql-connector-python` | `production_inventory_db`, parameterized SQL (injection-safe), `FOR UPDATE` locks for idempotency |
| **Frontend** | **HTML5**, **CSS3** (system sans-serif, gradients, flex/grid), **Bootstrap 5** (`data-bs-backdrop="static"` modals) | Responsive 260px sidebar, control bars, data tables, 3-section Flexbox modals |
| **Scripting** | **Vanilla JavaScript (ES6, modular `static/js/`)** | Rich filterable dropdowns, Master-Detail row builders, live totals, fetch submits, toasts, `cascade-unveil` |
| **Tooling** | XAMPP, VS Code, Git | Local Apache/MySQL, DB admin, version control |

---

## Core Modules & Architecture

### 1. Role-Based Access Control (Admin vs Staff)
- **Admin:** Dashboard metrics, user approval (`Approved_By`), full Product Add/Delete (no edit UI — catalog edits flow through Pending PRs), Approve/Reject PRs, approve Deliveries/Withdrawals/Returns, full inventory oversight.
- **Staff:** Create PRs, edit Pending PRs, create/complete Deliveries, view inventory, request withdrawals/returns, add products. **Delete strictly Admin-only**; modifying an Approved record is blocked everywhere (Approved PRs/deliveries are immutable history).
- **Session Management:** `session['user_id','username','full_name','role']` set on `login_user()` (BINARY case-sensitive + `Approved_By` check), validated on every protected route. Registration requires Admin approval; password reset verifies username + contact number (`09\d{9}`).

### 2. Procurement Flow (PR → Delivery, direct — no PO step)
- **Purchase Request (PR) — Master-Detail form:** Header (`pr_number` auto `PR-YYYY-MM-DD-XXX` daily, `fund_source` empty and typed per request with floating-label effect-21 field, `date_requested`, auto Grand Total) + dynamic typed line items (`item_name`, strict `category` ∈ Consumables/Tools/Equipment, `unit`, `size`, `details`, `price`, `quantity`). Submitted via fetch to `/pr/add`.
- **Just-in-Time Catalog + Composite Variants:** Typed rows resolve by 5-field composite key (`item_name, category, unit, size, details`; price ignored) — exact match links the product, any spec difference creates a **new variant**. `GET /products/api/list` feeds the picker with an `is_established` flag (TRUE = in a delivery or an Approved PR).
- **Smart Locking:** Established specs open `readonly` (category pinned); draft/new specs stay editable; price is **always editable** (market fluctuations).
- **Pending PR Editing:** `POST /pr/update/<id>` rewrites the line snapshot and normalizes matched draft products; non-Pending PRs are rejected server-side.
- **Duplicate Protection (dual-layer):** `find_duplicate_pr_item()` blocks repeat products on `/pr/add`, `/pr/update`, and inside `create/update_purchase_request()` (composite-key `set` scan, safe flash error, zero writes); frontend `prRowKey()` guard aborts catalog picks and blocks submit, surfacing the droplet-animated Duplicate-Item modal (green-hover Understood button) instead of `alert()`.
- **Delivery-Driven Actual Costs (no PO step):** Estimates live on `pr_items` only — `update_pr_status()` is status-only and never touches `products.price`. True unit cost is captured per delivery line (editable invoice price, PR estimate as fallback) and blended into the catalog by weighted average at approval, so bidding/partial-delivery variations are valued accurately.

### 3. Delivery & IAR (Strict 2-Step, PR-direct)
- **Step 1 (Admin or Staff):** `create_delivery()` links `pr_id` directly (no `purchase_orders`/`po_items` tables exist), captures free-text `po_reference_number` + `supplier_name`, inserts `deliveries`/`delivery_items` with `status='Pending'`, `is_partial` auto-computed. Guards: `received <= ordered`, no over-delivery across partials, blank/0 quantities allowed per row (≥1 row must be >0), delivery date never in the future. Only Approved PRs with zero deliveries are offered (`d.pr_id IS NULL`); completions go through the Complete action on the existing row.
- **Step 2 (Admin only):** `approve_delivery()` → `SELECT ... FOR UPDATE` lock + guards (`status != 'Pending'`, `approved_by` set, `stock_movements` exists → double-click blocked), then credits **exact received qty** to `products.current_stock`, blends the line's **actual** unit cost into `products.price` via weighted average, syncs `quantity`, writes the `items` physical ledger + `stock_movements (+qty)`, sets `status='Received'`.
- **Delivery UI parity (Admin + Staff):** Receive/Complete modals share the fx21 design language — pinned 3-column Section 1 (floating labels, focus-only border draw), label-free animated item rows, yellow remaining-summary banner pinned in Complete. Tables show short numbers (`DEL-001`, full value on hover via `short_pr`) and human dates (`ph_datetime`); PR Fund Source opens empty.

### 4. Inventory Workspace & Stock Management (Real-time)
- **Workspace Layout (Admin + Staff):** KPI cards removed to prevent dashboard fatigue — a single toolbelt card (search + guaranteed Consumables/Tools/Equipment + status filters + Refresh) above an expanded 7-column ledger (Code, Name, Category, Specs, Unit, Stock, Status). Financial/threshold columns stripped to keep the page focused on stock logistics.
- **Live Ledger:** `products.current_stock` is the source of truth, plus the `items` ledger per delivery. `crud_inventory.py` provides `get_inventory_summary()` (unique count, asset value `sum(current_stock*price)`, low/out counts via `reorder_level`) and `get_inventory_items()` with category/stock filters.
- **Movement Tracking:** Every stock change logs to `stock_movements` (`Delivery`/`Withdrawal`/`Return`, `quantity_change`, `balance_after`, `user_id`) for audit.
- **Strict Data Integrity Rules:** live inventory deductions on withdrawal approval (exact qty, re-validated), return handling with stock restoration rules per condition (`Serviceable`/`Unserviceable` audit paths), and delivery-driven actual costs (weighted-average valuation; PR estimates and edits can never overwrite catalog prices).

### 5. Outbound Operations (Withdrawals / Returns)
- **Withdrawal (RIS):** Created `Pending` after validating `requested <= current_stock` (no deduction yet). Admin `approve_withdrawal()` re-validates, deducts exact qty, logs `-qty`, sets approver + issue date. Guard: only `Pending` can be approved/rejected.
- **Return Slip:** Created `Pending` from a linked Approved `withdraw` (`withdraw_id`) for traceability — picker lists only withdrawals containing Tools/Equipment, and item lines are restricted to that withdrawal's Tools/Equipment items (broken-tools-for-repair flow). **Agreed policy (pending implementation):** Serviceable restocks (`+qty`) on approve; Unserviceable stays history-only with a zero-change audit entry. Admin `approve_return()` **deducts** `Serviceable` qty (stock OUT, like a withdrawal, logged `-qty`); `Unserviceable` logs a zero-change waste-audit entry. Uses singular backticked ``return``/`return_items` tables.

### 6. Master Catalog Rules
- Supplier-free catalog (no `supplier_id`; supplier is free text on deliveries). No Edit UI — corrections flow through Pending-PR edits with draft sync. **Delete is blocked with a flash warning** whenever the product appears in `pr_items`, `delivery_items`, `items`, `withdraw_items`, or `return_items`.

### 7. Modular UI/UX Architecture (`static/css/` + `static/js/`, all lowercase for Linux-safe deploys)
- **CSS:** per-page stylesheets + shared `modals.css` (effect-21 animated fields — frozen `Label: [box]` caption rows, transparent chips, focus-only `#53c5f1` border draw, zero glow shadows; rich `.custom-dropdown-list`, `dropletBounce` entrance on every `.modal-box`, scoped `.pr-modal`/`.delivery-modal` gradient buttons), `main_theme.css` shell, `input_box_enlargement.css` (textarea expansion).
- **JS:** `ui_helpers.js` (clock/toasts/cascade/skeleton), `pr_logic.js` (Master-Detail builder, rich dropdown, smart lock, fetch submits), `delivery_logic.js` (receive/complete/view flows, auto numbers, date guards), `action-icons.js` (single inline-SVG action-icon sprite — hand-drawn, `currentColor`, no emoji/masks), plus per-module files (`product_logic.js`, `user_logic.js`, `auth.js`, admin/staff withdraw + return logic). Zero inline `<style>`/`<script>` tags project-wide; server data reaches scripts via JSON APIs and `data-*` bridges.
- **Modals:** strict 3-section Flexbox layout (sticky header, scrollable body, sticky footer), card-box sections with titles, auto-generated readonly numbers (daily `PR-`/`DEL-`/`IAR-`/`WD-`/`RET-YYYY-MM-DD-XXX` sequences via `/pr/get_next_number`, `/delivery/get_next_number`, `/delivery/get_next_iar`, `/withdraw/get_next_number`, `/returns/get_next_number`), no `X` buttons (explicit Cancel workflow only), droplet-animated Duplicate-Item warning modal, shared `.btn-modal-save` hover system (green `#2e7d32` hover scoped to its Understood button).

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
    - App auto-creates `production_inventory_db` on first run via `db.py:get_db_connection()` (catches `1049` → `CREATE DATABASE`).
    - Manual alternative: `python Tables/Database_Tables.py`

5.  **Run Flask**
    ```bash
    python App.py
    # → * Running on http://127.0.0.1:5000  (debug=False, use_reloader=False)
    ```
    Browser → `http://127.0.0.1:5000` → `/login` → Register (Staff) → Admin approves at `/admin/users`.

6.  **Stop**
    - `CTRL+C` in terminal, then Stop MySQL/Apache in XAMPP.

### B. Clean-Slate Reset (Fresh Demo Data)

**When to use:** Before a full end-to-end run or final defense, to start from zero transactions while keeping logins.

**What to clear (keep `users`):** `purchase_requests`, `pr_items`, `deliveries`, `delivery_items`, `products` (repopulates just-in-time), `items`, `withdraw`, `withdraw_items`, ``return``, `return_items`, `stock_movements` — then reset their `AUTO_INCREMENT` counters.

**Steps in phpMyAdmin:**
1.  XAMPP → Start MySQL → `http://localhost/phpmyadmin` → Click `production_inventory_db` on left.
2.  Top menu → **SQL** → run (FK checks off so child/parent order doesn't matter):
    ```sql
    SET FOREIGN_KEY_CHECKS=0;
    DELETE FROM `pr_items`; DELETE FROM `purchase_requests`;
    DELETE FROM `delivery_items`; DELETE FROM `deliveries`; DELETE FROM `items`;
    DELETE FROM `withdraw_items`; DELETE FROM `withdraw`;
    DELETE FROM `return_items`; DELETE FROM `return`;
    DELETE FROM `stock_movements`; DELETE FROM `products`;
    ALTER TABLE `purchase_requests` AUTO_INCREMENT=1;
    ALTER TABLE `deliveries` AUTO_INCREMENT=1;
    ALTER TABLE `products` AUTO_INCREMENT=1;
    SET FOREIGN_KEY_CHECKS=1;
    ```
    (Repeat the `ALTER TABLE ... AUTO_INCREMENT=1;` line per cleared table as needed. Safe: `DELETE`, no `DROP`.)
3.  **Verify clean state** (same SQL tab):
    ```sql
    SELECT (SELECT COUNT(*) FROM purchase_requests) AS pr,
           (SELECT COUNT(*) FROM deliveries) AS del,
           (SELECT COUNT(*) FROM `withdraw`) AS wit,
           (SELECT COUNT(*) FROM `return`) AS ret,
           (SELECT COUNT(*) FROM stock_movements) AS mov,
           (SELECT COUNT(*) FROM users) AS users;
    -- Expected: all 0 except users (your logins are kept)
    ```
4.  **Test clean flow:** `Create PR (typed items, try a duplicate → blocked) → Approve (status only) → Create Delivery from Approved PR (Pending, stock 0, override one invoice price) → Approve (Received, exact received qty credited + weighted-average cost)` — correct.

---

**Capstone Team — BSIT 3A, CPSC | Prototype 2 (2026) | Tip: Demo the variant flow (same name, changed size → new product), the PR duplicate block (droplet modal), an invoice-price override flowing into weighted-average valuation, and the double-click approval guard live.**
