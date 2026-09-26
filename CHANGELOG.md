# Changelog

All notable changes to the **Web-Based CPSC Production & Inventory Management System** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — Import Buttons (Stub) (2026-09-26 nightcap)

> Import buttons land on PR + Inventory toolbelts (both roles) wired to flash-and-redirect stubs — modal + openpyxl backend next session.

#### Added
- **Import stub buttons** — `Import` text (`btn-add-primary`, free Create-PR-exact green hover) on both PR toolbelts; 32px `btn-action btn-import` icon (new `i-upload` tray glyph) after Print on both Inventory toolbelts (Filter, Print, Import) with green hover; `GET /pr/import` + `GET /inventory/import` flash "lands next session" and redirect role-aware. URLs are forward-compatible (same routes gain modal + POST next).

---

## [Unreleased] — Settings Thresholds Wired + Settings UI Fixes (2026-09-26)

> Settings page was display-only (values saved but never read — every consumer hardcoded `10`). Thresholds now drive Inventory status, KPIs, bell, and picker snapshots at read-time; Settings UI fixed per user spec.

#### Added
- **`get_reorder_thresholds()` + `effective_reorder_for()`** (`crud_settings.py`) — category-specific overrides Global Default, unknown categories fall back to global, safe `10/10/5/5` defaults; read-time only, never writes `products`.
- **Consumers wired** — `crud_inventory` summary/items (status + surfaced `reorder_level` now effective), `crud_notifications` low-stock bell (per-category Python count), `crud_products` picker snapshot; dashboards + snapshot inherit via helpers (zero `App.py` edits).
- **Hide-until-dirty save bar + Global cascade** — `static/js/settings_logic.js` (no inline scripts); bar hidden until a box differs from `defaultValue`, Cancel discards in place, Save stays native POST (flash-safe). Typing in Global Default mirrors live into the 3 category boxes (category values win at read time, so the mirror makes Global visibly authoritative); editing one category afterwards diverges only it.
- **Settings layout (final)** — left white card only (`max-width:520px`, full-width on mobile): Global Default on top, Category Thresholds label, vertical stack Consumables → Tools → Equipment; right page side left open for a future block (Withdrawn/Returned pattern; reserved anchor div kept in HTML, hidden by CSS). Number boxes capped `min(240px,100%)`; save bar right-aligned PR-footer style; Cancel anchor underline killed.
- **Save green hover** — Save button gains `btn-confirm-go` + scoped `.settings-save-bar .btn-confirm-go:hover` Create-PR-exact gradient (`#81c784→#4caf50`, white, `scale(1.05)`).

#### Fixed
- **Settings values had no effect** — root cause: hardcoded `COALESCE(reorder_level,10)` in inventory/notifications/picker; verified `Global 50` moves all, `Tools 20` moves Tools only.

#### Pending (in order)
1. **Import backend** (modal + openpyxl templates + `source` backfill + badges; spec archived in session) → 2. Merged compare + print user test (carried) → 3. Settings right-side block (reserved) → 4. Product edit flash → 5. Nav-toggle (user sourcing).

---

## [Unreleased] — Logout Flash Fix (2026-09-30)

> Intermittent white frame on logout handoffs, traced to a timing race (not a role bug).

#### Fixed
- **White flash on logout** — two changes: `::view-transition` backdrop painted app chrome (`#eaf3f8`) instead of browser white, so any handoff micro-gap never flashes white; logout link excluded from morph gating (`.nav-btn:not(.logout-btn)`) — an exit gets a plain instant swap, not a tab morph. Verified both roles (dashboards 200, correct logout toasts).

#### Pending (in order)
1. **Merged compare + print user test** → 2. **Settings polish** (incl. Import move) → 3. **Product edit flash** → 4. **Nav-toggle replacement** (user sourcing).

---

## [Unreleased] — Uniform Motion, Merged Compare + Print, Staff Restructure Tail (2026-09-29)

> One motion language everywhere (morph + stagger + pre-hide on all 16 sheets); virtual merged PR-vs-IAR compare with print sheet; staff dashboard restructured with team KPIs; icon-rail experiment fully reversed. Merged compare + print built but NOT yet user-tested.

#### Added
- **Uniform motion system** — View-Transition morph (frozen sidebar, gliding main; sidebar-link + filter/search/refresh arrivals via one-shot flags, reloads/forms skip); runtime stagger (`0.1 + i×0.22`, will-change hygiene, reduced-motion respected); 16-sheet pre-hide (opacity-0 base, single JS-armed play, no flash-then-replay); single `body .cascade-unveil` settle source (`0.9s`); toast hold stays `850ms`; skeleton stays `1200ms` login-only (`?welcome=1`, sidebar outside animated wrapper).
- **Merged PR-vs-IAR compare (virtual, no DDL)** — `get_merged_comparison()` (item-grouped requested vs received, per-fund tags, grand totals, skipped-with-flash); checkbox + `Compare Selected (N)` counter via shared `reports_compare.js` on both comparative pages; `GET /reports/comparative/print` standalone A4 sheet (college header, requested/received columns, CSS donut, footer legend, screen toolbar hidden).
- **Comparative ledger hardened** — dual-approved rows only (other statuses + crafted `?status_filter=` safely ignored); dates-only filter panel (Start/End + search); count badge = result rows.
- **Staff dashboard restructure** — Withdrawn/Returned graphs (global counts), header chart-filter cluster beside bell, snapshot + activity 3:2 duo, 5 team-wide KPI cards (Available, Low, Pending PR/Withdrawals/Returns; no "My"; cross-checked equal to admin); dead alerts/personal-counter code removed.
- **PO Date required** — `required` on all 4 Receive/Complete inputs (both roles) + `validatePODate()` empty-guard + both backend `all([...])` gates (missing/future blocked live, zero writes).

#### Fixed
- **Overlay-trap regression on rows arrivals** — retained fills held stacking contexts open and buried bell/filter panels behind cards; timed release pass pins rows/header/blocks to natural state.
- **PR edit-save toast missing** — `fetch` consumed the flash queue on redirect; native submit on create + edit (disabled ⏳ double-guard kept).
- **Staff header identity blank** — template read bare `{{ full_name }}` the route never passes; aligned to `{{ user.* }}` like admin (no backend change).
- **Staff header buttons undersized** — sheet lacked the canonical 32px `.btn-action` base; ported verbatim.
- **Return picker listed exhausted withdrawals** — `EXISTS` requires issued−already>0 per Tools/Equipment line.
- **Div-balance hunts** — duplicate closes found via stack parse (staff 107/107, reports 48/48, print 17/17, admin 129/129 + 131/131, PR 106/106 + 108/108).

#### Removed
- **Icon-rail/nav-toggle experiment** — fully reversed before rollout (hamburger buttons, rail CSS, nav JS block, `i-menu` glyph); zero references repo-wide; sidebar back to static full-width.

#### Pending (in order — merged-compare test first)
1. **Merged compare + print user test** (item grouping, fund tags, donut, legend — untested) → 2. **Settings polish** (archived, incl. Import-to-Settings move) → 3. **Product edit flash** (still old `updated!` wording) → 4. **Nav-toggle replacement** (user sourcing, old attempt deleted).

---

## [Unreleased] — Comparative Report, Staff Dashboard Restructure, PO Date Required (2026-09-28)

> Per-PR fulfillment ledger on separate admin + staff pages; staff dashboard restructured (graphs, header filter, duo tables, team KPIs); PO Date now required on IAR flows. Report built but NOT yet user-tested — visual test scheduled next session.

#### Added
- **Comparative Report (per-PR fulfillment)** — new `crud_reports.py` (`get_comparative_rows`: requested vs delivered vs outstanding + %; shared workspace, no `user_id`); `GET /admin/reports/comparative` (admin-only) + `GET /reports/comparative` (Admin/Staff); `/reports` hub now redirects by role (zero nav edits); `admin/staff_reports_comparative.html` + `admin/staff_reports.css` cloned from PR shells (toolbelt + anchored dual-status/date filters + count badge + fulfillment bar + dual badges; read-only, no actions).
- **Staff dashboard restructure** — alerts section replaced by Withdrawn/Returned graphs (global counts, same helpers/colors as admin); header chart-filter cluster beside bell; snapshot + activity side-by-side (3:2, stacked mobile); KPIs → 5 team-wide cards (Available, Low, Pending PR/Withdrawals/Returns; no "My"; counts cross-checked equal to admin); dead alerts/personal-counter code removed.
- **PO Date required** — `required` on all 4 Receive/Complete inputs (both roles) + `validatePODate()` empty-guard + both backend `all([...])` gates; native submits confirmed (no fetch issue); missing/future blocked live with zero writes.

#### Fixed
- **Staff header buttons now match admin** — `staff_dashboard.css` never had the canonical 32px `.btn-action` base; ported verbatim (white bell-style override layers identically).
- **Staff header div imbalance** — reorder had smuggled a duplicate close; caught via stack parse, 107/107.

#### Pending (in order — report test first)
1. **Comparative Report user test** (layout, columns, fulfillment bar, filters — untested) → 2. Report print sheet (deferred) → 3. **Settings polish** (archived, incl. Import move) → 4. Product edit flash family.

---

## [Unreleased] — Dashboard KPIs, Toasts, Borderless Nav, Withdraw/Return Edits (2026-09-27)

> Admin 5-queue KPI revamp + Inventory 4-card KPIs on both roles; toast system cleaned and made interactive; nav borderless everywhere; Pending-only withdraw/return edits; PR native submits; returnable-only withdraw picker.

#### Added
- **Admin KPI revamp** — 5 pending-queue cards in one line (Low Stock Alert, Pending PR/IAR/Withdraw/Returns), centered 44px badge layout, all linked to filtered queues; Total Asset Value removed (now lives on Inventory).
- **`kpi-icons.js` sprite family** — same system as action/nav sprites (`currentColor`, arcs-free): k-alert/pr/iar/withdraw/return/asset/products; nav-stock glyph reused for inventory stock states.
- **Inventory KPIs (admin + staff)** — Total Asset (blue), Total Products (purple), Low Stock (bright orange), Out of Stock (red); all 4 link (full ledger / Low / Out filters); zero backend change (`summary` was already passed).
- **Search magnifier** — 🔍 emoji → `i-view` sprite + shared `.search-ico` rule on all 13 dashboards.
- **Interactive toasts** — save wording (`PR/IAR/Withdrawal/Return … saved. Waiting for approval…`, PR/User edits included); client `showToast()` twin + GET-only ~850ms interceptor for filter/search/refresh (approvals/POSTs never delayed).
- **Withdraw/Return Pending-only edits (v1)** — header + qty/condition, same line set, native POST, revalidation (live stock, issued-minus-returned with self-exclusion, already-returned floor); edit buttons both roles, purple hover parity free; Unserviceable auto-approve preserved.
- **Returnable-only withdraw picker** — `EXISTS` requires issued−already>0 per Tools/Equipment line (both roles, no JS change).
- **PR create/edit native submits** — shared `pr_logic.js`, both roles.

#### Fixed
- **PR edit-save toast missing** — `fetch` followed the redirect internally and consumed the flash queue; native submit restores it (same latent bug on create, plus swallowed error flashes).
- **Toast emoji purge** — 6 auth flash strings de-emojied; login pages now load the sprite so their toasts render icons.
- **Inventory Low orange deepened** (`#bf360c` on `#ffe3d3`) after wash-out verdict; dead `k-out` symbol removed.

#### Pending (in order)
1. **PO Date required** on IAR Receive/Complete (planned: `required` inputs + backend gate) → 2. **Comparative Report spec** (archived, user decides shape + placement) → 3. **Settings polish** (archived, incl. Import-to-Settings move) → 4. Staff dashboard KPIs.

---

## [Unreleased] — Filters Done, Bell + Headers Finalized (2026-09-26)

> Anchored filter panels everywhere incl. dashboard chart revamp; trap defused; bell deep-links, count badges, own-voice rows; Welcome removed.

#### Added
- **Dashboard chart filter revamp** — funnel + panel (Start/End, full Period select, Year), count badge, active label; retired custom dropdown, gear, and 3 droplet modals; deleted `admin_dashboard_logic.js`.
- **Date ranges** — `date_from`/`date_to` on PR/IAR/Product/Users (validated, never future, from ≤ to, preset-compatible).
- **New filters** — PR PO-status, Product Category (guaranteed 3), IAR Completion, Users approval + role.
- **Bell** — deep-links land filtered, badge = result count (dot when empty), 7 rows in own voice, all 16 headers; Welcome removed (username + role pill + avatar stay).

#### Fixed
- **Cascade-unveil overlay trap** — shared guard; Overlay Law in `AGENTS.md`.
- Panel Apply hover unified; focus glow deleted (fx21 only).

#### Pending
1. **Comparative Report spec** → 2. **Settings polish**.

---

## [Unreleased] — Filter Refinement: Buttons, Glow, Category, IAR, Users (2026-09-25)

> Shared green Apply hover wins everywhere, focus glow deleted, guaranteed Product categories, new IAR Completion + Users approval/role filters.

#### Fixed
- **Panel Apply hover unified** — `.filter-panel .btn-confirm-go:hover` (0,3,0) beats all page blue overrides; Product was right by accident, now all 13 match.
- **Focus glow deleted** — blue `box-shadow` ring removed; fx21 border-draw is the sole focus feedback (spans verified on Product).
- **Product Category guaranteed** — Consumables/Tools/Equipment fallbacks + route validation accepts the canonical three.

#### Added
- **IAR Completion filter** — Partial/Complete second dropdown (both dashboards, counted).
- **Users filters** — Approval Status (Approved/Pending on `Approved_By`) + User Role (Admin/Staff), validated, counted.

#### Pending (step-by-step)
1. **Verify remaining 12 panels** → 2. **Paper-test prints** → 3. **Comparative Report spec** → 4. **Settings polish**.

---

## [Unreleased] — Filter Panels Everywhere + Trap Defusal (2026-09-24)

> Anchored filter cards (Start/End + status/category, fx21 focus, count badge, Cancel/Apply/Clear) on all 13 list pages; PO-status filter on PR; date ranges on IAR/Product/Users; the cascade-unveil overlay trap found and killed globally.

#### Added
- **Filter panel system** — relative wrap + absolute 300px card + `.open` toggle + native mini-form (groupmate-proven recipe, our theme/buttons); `filter-panel.js` (bind, outside-click, Escape, Cancel); count badge server-rendered; `i-filter` funnel sprite.
- **Per-page filters** — PR (dates + dual statuses), IAR (dates + status), Withdraw/Return (status), Inventory (category + stock), Product/Users (dates).
- **Date ranges** — `date_from`/`date_to` on PR/IAR/Product/Users backends (validated, never future, from ≤ to, wins over presets).

#### Fixed
- **Cascade-unveil overlay trap (root-caused)** — page-load animation fill left permanent `transform` + `clip-path` on card subtrees, re-anchoring fixed descendants and trapping z-index (five rounds of symptoms, one cause); shared `body .cascade-unveil` guard in `modals.css` releases it everywhere. Recorded as Overlay Law in `AGENTS.md`.
- **Retired** — overlay popover, accordion strip, filter dialog + their scripts (superseded by the panel).

#### Pending (in order)
1. **Paper-test prints** → 2. **Comparative Report spec** → 3. **Settings polish**.

---

## [Unreleased] — Grouped Nav + SVG Icon Sprite (2026-09-23)

> All 16 sidebars grouped by purpose with ruled section labels; emoji replaced by a hand-drawn SVG sprite with per-section theme hues; `/reports` stub live.

#### Added
- **Nav grouping** — Dashboard / Procurement / Operations / Stocks / Others (Reports · Users · Settings on admin, Reports alone on staff); `nav-group-label` shared rule in `modals.css` (black, non-bold, 10px, uppercase + full-width rule line); sidebar scroll retained.
- **Nav icon sprite** — `static/js/nav-icons.js` (11 outline symbols, 24-grid, `currentColor`, arcs-free, same injector architecture as action-icons); `.nav-icon` 18px sizing in `action-icons.css`; all 16 sidebars swapped incl. Log Out exit arrow.
- **Per-section hues** — navy Admin, sky Procurement, amber Operations, purple Stocks, slate Others, red Logout; sky-shift on hover/active (logout → white); shared rules, both roles.
- **`/reports` stub** — flashes "coming soon", redirects per role; nav entry on all sidebars, replaced for real at report spec.

#### Pending (in order)
1. **Comparative Report spec** → 2. **Settings polish**.

---

## [Unreleased] — Return Slip, Uniform Headers, AGENTS.md (2026-09-22)

> Return Slip print joins the family; every dashboard shares one sky-blue header card + spelled-out titles; `AGENTS.md` locks all rules and defaults; shared-workspace doctrine verified and recorded.

#### Added
- **Return print** — `GET /returns/print/<id>` (Admin + Staff, any status); `return_print.html` (IAR skeleton, own Return identity, 7 columns + Condition, 20 ruled rows, `TOTAL RETURNED`, record-driven serviceable note, no doc-code strip); cell icon + View-modal Print on both dashboards; slate hover in both return stylesheets; render-verified with synthetic data (exact 22 rows).
- **`AGENTS.md`** — session-proof operating guide (environment, critical rules, architecture, UI defaults, verification protocol).
- **Shared-workspace doctrine** — all staff share one workspace per module (all records, no "mine" filtering); admin same within admin views; personal scoping lives only in dashboard KPI counters. Verified: every list route passes `user_id=None`.

#### Changed
- **Uniform header cards (all 14 stylesheets)** — sky-blue `#aae0f7` rounded card (`14px 28px 0`, radius 12px, `#94d2ee` edge), sticky + mask shim, 20px de-italic titles, de-italic user names; frozen as the default for future dashboards.
- **Spelled-out titles (both roles)** — Purchase Request · Inspection and Acceptance Report (IAR) · Inventory Ledger · Requisition and Issue Slip (RIS) / Withdraw · Return Slip.

#### Pending (in order)
1. **Paper-test all new sheets** → 2. **Nav grouping** (approved: Procurement / Operations / Stock / Admin) → 3. **Nav icon sprite** → 4. **Comparative Report spec** → 5. **Settings polish**.

---

## [Unreleased] — Inventory + Withdraw Printing, Valuation Settled (2026-09-18/19)

> Filter-aware Inventory List sheet + photo-mirror 20-row Withdrawal Slip, both render-verified; unit-price truthfulness settled on moving weighted average (no architecture change); user paper-testing still pending.

#### Added
- **Inventory print** — `GET /inventory/print` (Admin + Staff) passing live `search`/`category`/`stock_status` into `get_inventory_items()`; `inventory_print.html` with centered school header + `Inventory List of Items` + as-of line + filter note; `#/Item Name/Specs/Unit/Category/Current Stock/Status` grid; printer icon after 2nd filter in both toolbelts (server-rendered href, same-tab + Close); slate hover in both inventory stylesheets.
- **Withdraw print** — `GET /withdraw/print/<id>` (Admin + Staff, any status incl. Pending); `withdraw_print.html` mirrors the office slip: seal-text header, Department/Date/blank PO Date/PO No./`Withdrawal No. W`, 6-column grid + `TOTAL RECEIVED`, 20 ruled rows (items + pads), static `[X]` inspected, blank Complete/Partial, `Received By: <record>` + blanks, blank officer block, `CPSC-SUP-F015 / Rev. 01` strip; cell icon + View-modal Print on both dashboards; slate hover in both withdraw stylesheets.
- **Valuation policy (settled)** — moving weighted average confirmed in code (blended at IAR approval, snapshotted at withdrawal; per-batch actuals preserved in `items` ledger); no FIFO work; snapshot timing = request-time.

#### Pending (tomorrow, in order)
1. **User test both new sheets on paper** (withdraw 20-row slip vs photo; inventory filtered subset) — NOT yet eyeballed.
2. **Return slip** → **IAR signature alignment** → **action-button crowding** (deferred: display-scale) → **Settings polish** → **`AGENTS.md`**.

---

## [Unreleased] — Full IAR Cutover + Two-Stage Approval + Decision Modals (2026-09-17/18)

> `deliveries`/`delivery_items` replaced by `iar`/`iar_items` (yearly numbers, staff-typed P.O. Date, no Delivery Number); PRs gain a second procurement approval so history stays truthful; PO-Rejected locked out of merge-print; branded Confirm/Cancel decision modals everywhere with a Create-PR-exact green Confirm hover default; header icons made visible.

#### Added
- **IAR schema (live)** — `iar` (`iar_id`, `iar_number UNIQUE NOT NULL`, `po_reference_number`, `po_date DATE`, `supplier_name`, `inspected_by`, `supply_officer`, `is_partial`, `iar_date`, `remarks`, `Pending/Received/Incomplete`) + `iar_items` + `items.iar_id`; legacy tables dropped (empty after wipe); `Database_Tables.py` rewritten + `po_status` backfill; cleanup scripts updated.
- **Two-stage PR approval** — `purchase_requests.po_status` (`Pending/Approved/Rejected`, default `Pending`); `set_po_status()` (director-Approved first, reversible); `/admin/pr/po_approve` + `/po_reject` (Admin only); PO badges on both PR tables + View modal; staff dashboard + IAR dropdown + picker queries require dual approval.
- **Yearly IAR numbers** — `generate_iar_number()` → `IAR-YYYY-001` (MAX-per-year + 1); `generate_delivery_number()` deleted with its route.
- **PO-Rejected merge lock** — checkboxes hidden + server-side crafted-URL skip (named flash); single-PR print kept as evidence.
- **Decision modals** — reusable 4-action PR confirm (two-stage explainer) + Withdraw/Return red reject modals replacing native `confirm()`; IAR approve-confirm verified compliant (Partial/Complete branch, irreversibility warning, triple injection guards).
- **`btn-confirm-go` default** — class-based Create-PR-exact green hover (`#81c784→#4caf50`, white, `scale(1.05)`) on all 6 Confirms; 22px solid-green/red header icons replacing invisible white-on-pale glyphs.
- **Receive IAR UI** — Delivery Number removed, IAR Number required, staff-typed P.O. Date (triple-guarded past-only), P.O. Date column + prefill, all 16 sidebars renamed (Inventory labels kept), `/delivery/*` URLs kept as-is.

#### Pending (tomorrow, in order)
1. **IAR signature alignment** — supply-officer block sits lower; flex-baseline fix, retest single + merged.
2. **Action-button crowding (PR + IAR)** — nowrap action-cells + approver tooltips (more urgent: PO badge + 5 buttons/row).
3. **Settings full polish** → **`AGENTS.md`**.

---

## [Unreleased] — PR Print Fixes Done + Delivery IAR Printing (2026-09-16/17)

> All three PR carry-overs closed (green hover match, same-tab everywhere, `Print` rename) and the Delivery IAR print shipped one-shot: single + merged Received-only stacked sheets mirroring the office paper, same checkbox/merge UX as PR, plus a Jinja dict-method crash fix.

#### Added
- **Delivery IAR print** — `GET /delivery/print/<delivery_id>` (login only, Admin + Staff, any status) + `GET /delivery/print_merged?ids=` (existing + `Received` only, others skipped with flash); new `Templates/delivery_iar_print.html` mirrors the photo: `Inspection & Acceptance Report` title, `Supplier / P.O. No. / P.O. Date: -` + `IAR No.: delivery_number (for now) / IAR Date: delivery_date`, `Requisitioning Dept: Production`, `Fund Source: parent fund_source`, `No. / Qty. / Unit / Supply and delivery of the following: / Unit Cost / Total Cost` grid + `TOTAL =` row (received qty × actual delivery price), `[X] Inspected...` + `Complete / Partial` from `is_partial`, dynamic `inspected_by / supply_officer` signatures (fallback `NATHANIEL B. STA. ELENA / MARIA EILEEN H. BAGTASOS`); stacked blocks with page-break + screen-only merged strip; `@page` A4 portrait.
- **Delivery merge UX (same as PR)** — checkbox first column + header select-all (Received rows only) + `🖨 Print Merged (N)` counter `btn-add-primary is-disabled` on both delivery dashboards; cell `Print IAR` icon (same-tab) + View-modal `🖨 Print` (same-tab via `delivery_logic.js`); `refreshMergeBtn()` classList toggle; `admin_delivery.css`/`staff_delivery.css` anchor states (green hover via `modals.css`, no blue override).
- **Backend (no DDL)** — `get_delivery_details()` now selects `pr.fund_source, pr.date_requested`; `App.py` `_normalize_delivery_for_print()` (date `MM/DD/YYYY`, received-qty totals, `is_partial` int).

#### Fixed
- **PR merge-button hover now matches + Create PR green** — removed per-page blue `a.btn-add-primary:not(.is-disabled):hover` from `admin_pr.css`/`staff_pr.css`; single source `modals.css:389-390` green `linear-gradient(135deg, #81c784, #4caf50)` + `scale(1.05)` wins for both `<button>` and `<a>` (generic blue `0,2,0` loses to `0,2,1 / 0,3,1`).
- **PR tab stacking closed** — `target="_blank"` dropped from merge button + cell icon (both PR dashboards); `pr_print.html` Close is `history.back()` fallback `/pr`.
- **PR `Print (A4)` rename done** — `Print` in toolbar, View-modals, cell titles (0 hits left).
- **Delivery merged/single 500 crash** — `delivery_iar_print.html:64-65` `bundle.items` hit the dict method in Jinja; switched to `bundle['header']` / `bundle['items']`; verified single + 2-block merged render.

#### Pending (tomorrow, in order)
1. **IAR signature alignment** — supply-officer block sits lower (unequal top content in `.foot-grid`); fix flex alignment so both `.sig` baselines match; retest single + merged.
2. **Action-button crowding (PR + Delivery)** — tall rows from wrapping View/Print/Complete/Approve + `by Admin` text; fix with nowrap action-cell + tighter gap + approver into `title` tooltip (bindings untouched).
3. **Print enhancements batch** (user list tomorrow) → **Settings full polish** → **`AGENTS.md`**.

---

## [Unreleased] — PR Printing, Merged Multi-Fund Print & Global Numbering (2026-09-15)

> Single-PR A4 official sheet + merged Approved-only multi-fund print landed; PR suffix made global so the short display can never repeat; trace strip, checkbox merge UI, and print-window flow added. Two UI carry-overs (merge hover, tab stacking) plus label rename scheduled next.

#### Added
- **Single-PR print** — `GET /pr/print/<pr_id>` (login only, Admin + Staff, any status) reusing `get_pr_details()`; `Templates/pr_print.html` mirrors the office paper: college header block, full-grid `#/Source/Item/Qty/Unit/Price/Total` table (Qty/Unit centered, Price/Total left), fixed `ROLAND L. VIOS / Director of Production` signatory, stacked inline `Received by: ____` + indented `Date: ____`, bottom-pinned footer, `@page` portrait + `@media print` hiding screen UI. Native dialog covers paper-size choice (A4/Letter/Legal) + Save-as-PDF.
- **Merged Approved-only print** — `GET /pr/print_merged?ids=` (existing + `Approved` only, others skipped with flash); each row keeps its own parent `fund_source`; checkbox first column + header select-all (Approved rows only) + `🖨 Print Merged (N)` counter button on both PR dashboards; `pr_logic.js` selection/counter logic; screen-only `Merged from: (PR-001), (PR-002)` strip via `short_pr()` (hidden on paper).
- **Print entry points** — printer cell icon (both dashboards) + `Print` button in View-modal footer + new `#i-print` sprite in `action-icons.js` with slate hover.
- **Global PR numbering** — `generate_pr_number()` switched from per-day `COUNT+1` to global `MAX(suffix)+1`; `create_purchase_request()` regenerates + retries (up to 3x) on duplicate-key instead of failing. Stored `PR-YYYY-MM-DD-XXX` shape unchanged; suffix now means Nth PR ever.

#### Fixed
- **Display-collision diagnosis** — `PR-2026-09-14-001` vs `PR-2026-09-15-001` both rendering `PR-001` proven to be daily-reset + date-stripping, not a data duplicate (`fund_source` confirmed uninvolved); backend fixed, display intentionally untouched.
- **Merge-button height parity** — `a.btn-add-primary` normalization in `admin_pr.css` + `staff_pr.css`; missing `:hover` added to `admin_pr.css`.

#### Pending (carry-over, next session in order)
1. **Merge-button hover still dead** — likely inline `pointer-events:none` while disabled + `modals.css` element-qualified `button.btn-add-primary:hover`; add explicit `a.btn-add-primary:hover` + disabled style, retest enabled after hard refresh.
2. **Tab stacking persists** — cell icon + merge button still `target="_blank"`; decide same-tab-everywhere vs new-tab-with-reliable-close, then apply.
3. **Rename `Print (A4)` labels** — drop `(A4)` from print-tab button, View-modal buttons, cell titles, merge text (paper size comes from the dialog).
4. **Settings full polish (after print fixes)** + **`AGENTS.md`**.

---

## [Unreleased] — System Settings, Return Restock Policy & Security Hardening (2026-09-14)

> The Settings module landed (5 tabs, 28 defaults, CRUD + route), the return restock policy was implemented end-to-end (Unserviceable auto-approve, Serviceable requires admin approval + restock), and security hardening was applied (env-var secrets, `.gitignore`, plaintext passwords restored after hashing revert).

#### Added
- **System Settings module** — `crud_settings.py` (key-value `admin_settings` table, `ensure_settings_table()`, `init_default_settings()`, `get_all_settings()`, `get_setting()`, `save_settings()`); `/admin/settings` GET/POST route + `/api/settings` JSON endpoint; `admin_settings.html` template with 5 tabs (Branding, Theme, Business Rules, Stock Alerts, UI Preferences), 28 default settings, fx21 fields, color picker, toggle switch, sticky save bar; Settings button added to all 8 admin dashboard sidebars.
- **Return restock policy (implemented)** — `create_return()` auto-approves Unserviceable-only returns (record only, zero stock change); Serviceable returns save as `Pending` requiring admin approval → `approve_return()` restocks (`current_stock += qty`) on approve; Mixed returns (both conditions) stay Pending; `crud_returns.py` submit gate: Unserviceable skips stock check, Serviceable linked checks issued-minus-returned, Serviceable direct checks current_stock.
- **Returnable items endpoint** — `/returns/returnable-items/<withdraw_id>` joins `withdraw_items` + `return_items`, filters Tools/Equipment, returns items where `issued - already_returned > 0` with `maxQty = remaining`; "+ Add Item" dropdown excludes items already in the table (by product_id).
- **Security hardening** — Flask secret key from env var `FLASK_SECRET_KEY`; DB credentials from env vars in `db.py` (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`); `.gitignore` created (excludes `__pycache__/`, `*.pyc`, `*.pyo`, `.env`, `*.db`).

#### Changed
- **Return view modal redesigned (staff + admin)** — Columns now: Item Name / Specification / Unit / Size / Category / Condition (money removed); title uses short numbers (`RET-001 Details`); headers show "Return Number" and "Ref Withdrawal".
- **Return table columns rebuilt (staff + admin)** — Return Number / Withdraw Number / Department / Condition / Date / Total Qty / Status / Actions with `short_pr`/`shortRetNum`/`shortWdNum`, `ph_datetime`, Condition color-coded (green Serviceable / red Unserviceable).
- **Approve modal text updated** — "Serviceable items will be restocked to inventory".
- **Return dashboard info banners removed** (staff + admin).

#### Fixed
- **Stale `cpython-314.pyc` cache** — Flask runs on Python 3.14 but `__pycache__` clearing targeted 3.12; old hashed `crud_users.cpython-314.pyc` was re-loaded on every restart, re-hashing plaintext passwords. Cleared 3.14 caches, confirmed all users plaintext `123`.
- **Settings page `BuildError`** — `admin_pr_management` endpoint corrected to `pr_management`.
- **Settings page `TemplateNotFound`** — switched from `safe_render_template` to `render_template` directly; removed `@app.before_request` hook that ran DB queries on every request.

#### Removed
- **All werkzeug password hashing** — `generate_password_hash`/`check_password_hash` removed from `crud_users.py`; all `__pycache__` directories cleared; passwords confirmed plaintext.
- **Dashboard info banners from Return pages** (staff + admin).
- **Dead files (2026-09-14 night)** — `CRUD_Operations/crud/` (orphan, only stale `cpython-311.pyc`, never imported), `Templates/base.html` (no route, no `extends`), `static/css/main_theme.css` (only used by `base.html` + settings; removed from settings `<head>`), all `__pycache__`/`*.pyc`.

#### Changed (2026-09-14 night — partial)
- **Settings structural pass** — `admin_settings.html` now uses canonical sidebar (`sidebar` + `main-wrapper`, `nav-menu`, `school-title`/`school-subtitle`, `cpsc_logo.png` + onerror, `💻` + `Submit PR`) and header (`user-profile-box`/`user-name`/`user-role`); Theme tab `select`/color wrapped in `.fx21-field` + `.focus-border` + `.fx21-label`; divs balanced 97/97; `App.py` compiles. Page still visually broken per screenshot — full polish deferred.

#### Pending
- **Reports + Print button (priority, 2026-09-15)** — build missing reports and a print-reports button; finish core system first.
- **Settings full polish (after reports)** — fx21 label overlap, spacing, save-bar, functionality check; decide which of 5 tabs / 28 keys to keep.
- **Create `AGENTS.md` (2026-09-15)** — session-proof operating guide so a fresh session never loses context.

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

#### ~~Pending~~ (implemented 2026-09-14)
- **Return restock policy (Option B):** Serviceable restocks (`+qty`) on approve; Unserviceable stays history-only. See entry above.

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
