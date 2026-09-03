# Changelog

All notable changes to the **Web-Based CPSC Production & Inventory Management System** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and [Semantic Versioning](https://semver.org/).

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
