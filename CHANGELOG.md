# Changelog

All notable changes to the **Web-Based CPSC Production & Inventory Management System** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — Inventory Workspace & Delivery Pricing Integrity (2026-09-07)

#### Added
- **Inventory Workspace layouts (Admin + Staff)** — `admin_inventory_dashboard.html` / `staff_inventory_dashboard.html` rebuilt as pure data-management workspaces: KPI cards removed, single horizontal `.toolbelt-container` (search + category/status filters + Refresh), expanded ledger table with header + record count. No page header added (global layout already provides one).
- **Guaranteed category options** — Category filter always offers All Categories/Consumables/Tools/Equipment (static fallbacks render only when the DB-driven `{% for cat in categories %}` loop lacks them; never duplicated).
- **Delivery actual unit-price editing** — `delivery-unit-price` input (`type=number step=0.01`, pre-filled from the PR estimate) in both Create and Complete modals; live row-total + grand-total recalculation (`recalcDeliveryTbody()`); per-row validation; backend `_resolve_actual_price()` stores the true invoice cost in `delivery_items.price` (blank falls back to the PR estimate; negatives rejected).
- **Weighted-average inventory costing** — `approve_delivery()` blends each line's actual delivery cost into `products.price` (`(old_stock×old_price + qty×actual)/(old_stock+qty)`; zero-stock adopts the latest verified cost), so asset valuation tracks real invoices.
- **Dual-layer PR duplicate protection** — `find_duplicate_pr_item()` (composite-key `set` scan) guards `/pr/add`, `/pr/update`, `create_purchase_request()`, and `update_purchase_request()` (insertion fully blocked, safe flash error, no crash); frontend `prRowKey()` guard aborts catalog picks, warns once on typed matches, and blocks submit on row-pair duplicates.
- **Duplicate-Item droplet modal** — `duplicateItemModal` (Delete-modal language: overlay + 520px box + amber panel, single Understood button) replaces all native `alert()`s on duplicate paths, with row-aware messaging (`Rows X and Y: …`).
- **Shared modal-button hover system** — `modals.css` gains unified `.btn-modal-save` lift/shadow/darken hover (`all 0.2s ease`); `#duplicateItemConfirm` scoped to success-green hover (`#2e7d32`) for save semantics.

#### Changed
- **Inventory tables stripped to stock logistics** — Removed Unit Price, Reorder Threshold, and Total Stock Value columns (both `<th>` and `<td>`); 7 columns remain (Code, Name, Category, Specs, Unit, Stock, Status); empty-state `colspan` 10→7, table `min-width` 1250px→900px. Backend bindings (`price`, `reorder_level`, `total_value`) still passed, untouched.
- **PR approval no longer rewrites catalog prices** — `update_pr_status()` is status-only; estimates stay on `pr_items`, true cost enters exclusively via delivery approval (reverses the earlier approval-sync behavior noted below).

#### Removed
- **Inventory KPI cards + styles** — `.cards-grid`/`.metric-*` blocks deleted from both inventory pages and stylesheets; `.control-card` replaced by `.toolbelt-container` (cascade selector in `ui_helpers.js` extended).
- **Native `alert()` on PR duplicate paths** — all three call sites now open the droplet modal (other alerts — required-field, network, locked-record — intentionally retained).

---

## [Unreleased] — Major Refactoring & UI Polishing Phase (September 2026)

#### Added
- **Live Sequence APIs for Auto-Generated Numbers** — `generate_pr_number()`, `generate_delivery_number()`, `generate_iar_number()`, `generate_withdraw_number()` (daily `PREFIX-YYYY-MM-DD-XXX` sequences resetting each day) with JSON routes `/pr/get_next_number`, `/delivery/get_next_number`, `/delivery/get_next_iar`, `/withdraw/get_next_number`, `/returns/get_next_number`; readonly auto-filled number fields in PR/Delivery/Withdraw/Return modals (server still enforces uniqueness).
- **Smart Product Picker API** — `GET /products/api/list` now returns `is_established` per product (TRUE = in any `delivery_items` row or `pr_items` of an Approved/Completed PR; FALSE = Pending-only draft), plus live `stock`/`reorder` snapshots for withdraw/return modals.
- **Pending PR Editing** — `POST /pr/update/<id>` + `update_purchase_request()` rewrites the line snapshot and normalizes matched draft products; non-Pending PRs are rejected (Approved records are immutable history). Edit buttons render only on Pending rows.
- **Price Sync on PR Approval** — `update_pr_status()` writes each approved line price back to its linked `products` row; catalog prices change only on approval, never on save. *(REVERSED 2026-09-07 — approval is now status-only; true cost enters via delivery weighted-average. See entry above.)*
- **Product Delete Safety Check** — `delete_product()` returns `(ok, msg)` and blocks deletion with a flash warning naming the blocking history (`pr_items`, `delivery_items`, `items` ledger, `withdraw_items`, `return_items`).
- **Rich Custom Dropdowns** — Reusable `.custom-dropdown-list` component (bold name, gray specs, price badge, slide-down animation, 180px cap, HTML-escaped) replacing native `<datalist>`: PR item picker with smart locking, filterable Approved-PR picker in deliveries.
- **Card-Box Modal System** — Shared `.form-section-card` (Section 1 light-blue, Section 2 light-brown→blue) with titles, strict 3-section Flexbox layouts (sticky header, scrollable body, sticky footer), `dropletBounce` entrance on every `.modal-box`, scoped gradient action buttons.
- **Strict Form Guards** — Per-row zero/blank quantities allowed (≥1 row >0), no future delivery dates (frontend `max` + server reject), single-`pr_id` submission, fully-delivered PRs hidden from the dropdown.

#### Changed
- **Composite Identity Matching for Product Variants** — PR save/edit links lines by exact 5-field key (`item_name, category, unit, size, details`; price ignored); any spec difference creates a NEW zero-stock variant instead of overwriting history.
- **Direct PR-to-Delivery Workflow** — Deliveries link `pr_id` straight to Approved PRs (only zero-delivery PRs offered; completions via the Complete action); free-text `po_reference_number` + `supplier_name` replace the old order/supplier tables.
- **Category Standardization** — Strict `Consumables`/`Tools`/`Equipment` selects in PR rows and the Add-Product modal.
- **Focus Styling** — Removed `transform: scale()` input enlargement; universal blue-glow `:focus` (`#53c5f1` + ring) across all pages, search bars keep a flat inner input with bar-level glow.
- **Delivery Tables & Details** — Separate `PR #` / `PO Ref #` columns, supplier-as-text, remaining-quantity completion flow.

#### Removed
- **Purchase Order module** — `purchase_orders`/`po_items` tables, `crud_po.py`, `/po*` flows (routes kept as redirects), PO price-variance logic (superseded first by approval price sync, now by delivery actual-cost editing + weighted-average valuation).
- **Supplier module** — `Supplier` table, `crud_suppliers.py`, supplier nav/management pages, `supplier_id` linkage everywhere (supplier is now delivery free text).
- **Product Edit UI** — Edit buttons/modals/JS removed from both product pages (catalog corrections flow through Pending-PR edits); dead `issuedWithdrawals` array, legacy PO/Supplier templates.
- **Modal `X` Close Buttons** — All 26 removed project-wide; explicit Cancel/Close footer workflow enforced.

#### Fixed
- **Fully-Delivered PRs Reappearing** — Dropdown now excludes any PR with a `deliveries` row (`d.pr_id IS NULL`); over-delivery across partials still guarded server-side.
- **Zero-Quantity Rejection** — Blank inputs normalize to `0` client + server; only all-zero submissions are rejected with a clear message.
- **Stale Prefill Bugs** — Completion modal PO-ref/supplier refills overwrite per open; smart-lock `lastMatch` tracking preserves manually typed specs.
- **Static Asset Casing** — All `static/css/` + `static/js/` references lowercase (Linux-safe); verified zero `CSS/`/`Javascript/` refs remain.

---

## [v2.0.0] - Prototype 2 (Current - Current Semester) - 2026-09-03
### Milestone: Secure Web Migration & Logic Correction

#### Added
- **Full Web-Based Migration from MS Access to Python/Flask and MySQL Architecture** — Rebuilt single-user MS Access file into multi-user web system. Stack: `Flask` + `mysql-connector-python` + `Jinja2` + `MySQL (XAMPP)` with modular CRUD (`crud_users`, `crud_suppliers`, `crud_products`, `crud_pr`, `crud_po`, `crud_delivery`/`crud_iar`, `crud_inventory`, `crud_withdrawal`, `crud_returns`) and `safe_render_template()` for Admin/Staff subfolders.
- **Role-Based Access Control (RBAC) Separating Admin and Staff Capabilities** — `Admin`: full CRUD, user approval (`Approved_By`), PR/PO/Delivery/Withdraw/Return approvals, inventory. `Staff`: Add/Edit only for Supplier/Product (Delete blocked → flash `"Delete access denied..."` + redirect to `staff_*`), submit PR, track PO, receive Delivery (IAR), request Withdraw/Return. Session `session['user_id','username','full_name','role']` validated on every protected route.
- **Dynamic Address Autocomplete for Camiguin Municipalities and Barangays** — Pre-loaded PSA `CAMIGUIN_DATA` (5 towns, 57 barangays: Mambajao 15, Mahinog 13, Catarman 15, Guinsiliban 7, Sagay 9) + `COMMON_STREETS` (12). Routes `admin_suppliers`/`staff_suppliers` query `SELECT DISTINCT street/barangay/municipality/city FROM Supplier` for **dynamic learning** (`existing_*` → Jinja `tojson`). Client `mergeUnique()` + `populateDatalist()` + cascading `filterBarangays()` on Municipality `oninput` (e.g., `Mambajao` → Mambajao barangays first). HTML5 `<datalist>` retains freeform typing; addresses sanitized `strip().title()`.

#### Fixed
- **Critical Procurement Logic Gap where Purchase Request (PR) and Purchase Order (PO) Prices Could Not Differ; System Now Supports Dynamic PO Price Overrides** — Prototype 1 forced `pr_items.price == po_items.price`. **Prototype 2:** `create_po_from_pr(pr_id, user_id, adjusted_items)` uses `adjusted_items` `unit_price` (vendor actual, editable in PO modal `PR Est. Price (read-only)` vs `Actual PO Price (editable)`) and recomputes `po_total = sum(unit_price * quantity)`; falls back to PR if `None`. Shows `PRD-001` preview (`products[0].product_id+1`).
- **Inventory Calculation Desyncs and Ghost Stock Issues by Implementing Strict Delivery-to-Inventory Approval Validation and Clean-Slate Database Reset Scripts** — **Desync:** Manual `DELETE FROM purchase_requests` left `Products.current_stock` at `235` (ghost) → next `50` showed `285`. **Fix:** `approve_delivery()` now `SELECT ... FOR UPDATE` lock + guards: `if status != 'Pending'` or `approved_by IS NOT NULL` or `stock_movements` exists → block double-click (`flash "Approve blocked: already 'Received'"`), then `UPDATE Products SET current_stock = current_stock + received_quantity` (**exact accepted qty**, not ordered) + `stock_movements (+qty)` + PO `Partial/Delivered`. **Recovery:** `RESET_CLEAN_SLATE.sql` (at root) does `SET FOREIGN_KEY_CHECKS=0; DELETE FROM pr_items, po_items, purchase_orders, purchase_requests, delivery_items, deliveries, items, withdraw_items, withdraw, return_items, return, stock_movements; ALTER TABLE ... AUTO_INCREMENT=1; UPDATE products SET current_stock=0, quantity=0, starting_stock=0; SET FOREIGN_KEY_CHECKS=1;` — retains `Users, Supplier, Products` rows, zeroes stock, next flow `0→50` clean.

---

## [v1.0.0] - Prototype 1 (Previous Semester) - 2025-2026
### Milestone: Initial MS Access Build

- **Note:** Initial offline MS Access build evaluated and checked at the end of last semester. Single-user desktop file, limited concurrent access, basic Supplier/Product/User tables, manual PR/PO forms without web deployment, RBAC, or dynamic features. Served as proof-of-concept and baseline for migration requirements. No web codebase retained — all logic re-architected for Prototype 2.

---

**Legend:** `Added` = new feature, `Fixed` = bug/logic correction.
