# Changelog

All notable changes to the **Web-Based CPSC Production & Inventory Management System** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — System-Wide fx21 Rollout + Return/Withdraw Details (2026-09-12)

> The Delivery caption-row trial (`Label: [box]`, frozen labels, animation-only focus) won and was rolled out to **every form surface**: Receive, Complete, PR create/edit, Withdraw, Return, Add Product, Edit User, Login/Signup/Forgot, and dashboard filter modals. Glow shadows deleted project-wide; labels parked (never rise/drop).

#### Added
- **Caption-row headers everywhere** — `fx21-inline` (`Label:` + flex box) + `fx21-box` draw stage; globalized from the Receive trial. Section titles de-AI'd (`Section 1:` / `Section 2:`) and shortened (`Delivery Items`, `PR Items`, `Withdraw Items`, `Return Items`).
- **Dropdown carets + in-box guides** — monochrome `▾` on custom pickers, `Dropdown`/`e.g. Bonita`/`e.g. PO-2026-001` placeholder guides, required `*` moved from labels into placeholders.
- **Combined `Needs Attention` stock filter** (`stock <= reorder`, low + out) in `crud_inventory.py`, exposed as `Low & Out of Stock` in both inventory toolbelts.
- **Dashboard card click-throughs** — Low Stock (low + out) → filtered inventory; Pending PRs/Withdrawals → filtered queues, staff + admin (backend; needs Flask restart to load).
- **Withdraw/Return Details overhauls** — 3-column headers, short titles (`WD-001 Details`), `ph_datetime` dates, Grand Total docked in footers, footer action buttons, universal Close hover, money stripped from Withdraw items view.
- **Return Tools/Equipment scoping** — `issued_withdrawals` limited to withdrawals containing Tools/Equipment; Return item picker offers only the chosen withdrawal's Tools/Equipment lines (empty until picked); Withdraw item picker restored to all in-stock (any category).

#### Changed
- **PR Fund Source** opens empty with an `e.g. Fund 05` hint (no autofill); Edit keeps its value.
- **Return table columns** rebuilt (Item Name · Category · Specification · Unit · Qty in view; reordered create rows with Category + Condition).
- **Login/Signup** use fixed top labels + animation-only boxes (float experiment reverted); Chrome autofill wash neutralized with load-time label sync.

#### Fixed
- **`create_return_action` NameError** — passed undefined `withdraw_id`; now `withdrawal_id or None`, so Return records save.
- **fx21 wrapper overshoot** (inline-block shrink-wrap), **peso-in-number-input revert**, **missing header close tag**, **Add Remaining white-on-hover** (amber hover keeps dark text).

#### Pending (agreed, not yet implemented)
- **Return restock policy (Option B):** Serviceable restocks (`+qty`) on approve; Unserviceable stays history-only. Submit gate switches to issued-minus-returned for linked returns. Spec approved 2026-09-12; implementation + live test is tomorrow's first job.

---

## [Unreleased] — Delivery Module UI/UX Parity (2026-09-11)

> Context: the preceding pass brought **PR + Withdraw + Return** to the shared design language (effect-21 fields, `pr-modal-large` shell, section cards, monochrome row actions, `action-icons.js` sprite). This release brings the **Delivery dashboards** (staff + admin) to the same bar. No backend bindings changed anywhere — `name=`, Jinja, element IDs, form actions, and `url_for` endpoints verified intact after every edit.

#### Added
- **fx21 Section 1 headers in Receive + Complete** — 3-column pinned grids (`Approved PR + auto numbers | PO-Ref + inspectors | supplier + date + remarks` for Receive; `auto/inherited numbers | supplier + inspectors | date + remarks` for Complete) with floating black labels and focus-only `#53c5f1` border draw, replicating the PR Section 1 pattern.
- **Pinned-Section-1 modal structure for deliveries** — title + PR banner + Section 1 live in `.delivery-modal-header` (never scrolls); `.delivery-modal-body` scrolls the Section 2 items table only (same contract as PR's `.pr-modal-header`/`.pr-modal-body`).
- **Label-free fx21 item rows** — unit-price + received/complete-qty inputs wrapped in shrink-hugged `fx21-field` (`display:inline-block`) so the animation traces the box, not the cell; no labels (column headers caption them).
- **Complete-table enrichment** — Category, Unit, and Item/Specs (name + details + size) columns rendered from the existing `/delivery/remaining` payload (no backend change; fields were already shipped, just unrendered); Remaining reordered adjacent to Complete Qty.
- **Short display numbers + readable dates on delivery tables** — `short_pr` filter on Delivery/IAR/PR cells (`DEL-2026-09-11-001` → `DEL-001`, full value on `title` hover); `ph_datetime` on Delivery Date (`September 11, 2026 | 12:00 AM` shape — time reads midnight, deliveries store date-only).

#### Changed
- **PR Fund Source no longer prefilled** — Create modal opens empty with the label inside the box (label floats on click/type, matching Delivery); Edit modal and view fallback keep their `Fund 05` default.
- **Delivery table copy** — `Delivery #/IAR #/PR #/PO Ref #` → full `Delivery Number/IAR Number/PR Number/PO Ref Number` headers; `Unit Price (editable)` → `Unit Price`; search placeholders updated to match.
- **Receive/Complete row styling** — resting borders docked to header gray `#d0dbe5`, transparent fills (section card carries the surface), centered Category/Unit/price/qty columns, docked thead widths so Item/Specs absorbs free space.

#### Fixed
- **fx21 wrapper overshoot** — block-level `.fx21-field` in table cells drew the animation at full column width; `inline-block` shrink-wrap + narrowed inputs fixed it.
- **Peso sign inside number input** — reverted; `type=number` cannot hold `₱` (it wrapped above the box and broke the frame). Currency context stays in Total/footer, as in PR.
- **Unclosed pinned header** — div-balance check caught a missing `.delivery-modal-header` close mid-edit; recounted to 75/75 (staff) and 92/92 (admin).

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
