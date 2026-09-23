# AGENTS.md — Session-Proof Operating Guide (CPSC Inventory, Prototype 2)

> Read this file first in every fresh session. It encodes every rule, default,
> and hard-won lesson so context is never lost. Plan mode = read-only
> (no edits, no shell writes); build mode = edits allowed with verification.

## 1. Environment
- **Working dir:** `C:\Users\user\OneDrive\Desktop\BSIT 3A 1ST SEM\IM 103 - ADVANCE DATABASE SYSTEM 2\CPSC INVENTORY FRESH`
- **Python:** 3.14 via `python` (never `python3` — that alias is 3.12).
- **Run:** `python App.py` → `http://127.0.0.1:5000` → `/login`.
- **MySQL:** start via **XAMPP Control Panel**. Background/shell server launches
  get reaped (once mid-`CREATE`, leaving an orphan frm — dropped and recovered).
  Credentials: root / no password / `production_inventory_db` (env-overridable).
- **Logins:** admin / Staff / Cj — all password `123`.
- **Passwords are plaintext.** Werkzeug hashing was fully removed on purpose.
  Never re-add it. `__pycache__` staleness once re-hashed passwords — always
  clear caches after Python edits.

## 2. Critical Rules (never violate)
1. **Never alter backend bindings:** `input name=`, Jinja `{{ }}`, element `id=`
   (JS hooks), `form action=`, `url_for()` endpoints. Style/markup around them
   freely; bindings never.
2. **Shared workspace doctrine:** all staff share ONE workspace per module —
   every list route passes `user_id=None` (PR, IAR, withdraw, return,
   inventory). Same for admin within admin views. No "my records" filtering
   anywhere. Personal scoping lives ONLY in dashboard KPI counters
   (`my_prs`, `my_withdrawals`, `my_returns` on staff_dashboard).
3. **Approved records are immutable history.** Pending-only edits everywhere.
4. **Titles use em-dashes (`—`, U+2014), not hyphens.** Edit-tool and shell
   matching fail silently on the wrong dash — dump char codes when in doubt.
5. **CRLF line endings** in templates. PowerShell backticks mangle quoting —
   prefer script files over long `-c` one-liners for SQL.

## 3. Architecture (do not redesign without user approval)
- **Two-stage PR approval:** `status` (director) + `po_status` (procurement).
  Only dual-approved PRs enter IAR creation (`get_deliverable_prs`,
  `get_approved_prs_for_delivery`). Merge-print needs director-approval only;
  PO-Rejected is locked out (checkbox + server skip); single prints stay as
  evidence for any status.
- **PR → IAR direct** (no PO tables). Tables: `iar`/`iar_items`
  (`iar_number` yearly `IAR-YYYY-001` UNIQUE, staff-typed `po_date`,
  `iar_date`, NO delivery number), `items.iar_id`, `purchase_requests.po_status`.
  Old `/delivery/*` URLs intentionally kept; function names (`create_delivery`,
  …) kept with `iar_*` aliases.
- **Valuation = moving weighted average.** Blended at IAR approval
  (`(old_stock×old_price + qty×unit_cost)/(old_stock+qty)`), snapshotted at
  withdrawal/request time. Never overwrite, never FIFO (non-perishables).
  Per-batch actuals preserved in `items` ledger. Panel line: outflow +
  remainder always reconcile (10×50 + 10×90 = 1400; out 5×70 = 350;
  15×70 = 1050; 350 + 1050 = 1400 ✓).
- **PR numbers:** global ever-incrementing suffix (`MAX+1`, 3× retry on
  duplicate-key). Short display `PR-001` strips the date — cross-day twins
  are display collisions, not duplicates. Never "fix" by resetting.
- **Stock truth:** `products.current_stock` is the ledger; approval paths
  carry `FOR UPDATE` + double-injection guards (`status`, `approved_by`,
  `stock_movements`). `reference_type='IAR'` for IAR movements.
- **Return policy:** Unserviceable auto-approves (record only, no stock move);
  Serviceable needs admin approval → restock. Only Tools/Equipment returnable.

## 4. Frozen UI Defaults (apply to every new page/modal/print)
- **Header card (all 14 dashboard sheets):** sky `#aae0f7`, `margin:14px 28px 0`,
  radius 12px, `#94d2ee` edge, `padding:14px 24px`, sticky `top:14px` z-20;
  `main-wrapper` owns scroll + `::before` shim (16px/−2px, body bg `#eaf3f8`,
  z-30); content containers `overflow:visible`; h1 20px de-italic, user-name
  de-italic. Titles (both roles): Purchase Request · Inspection and
  Acceptance Report (IAR) · Inventory Ledger · Requisition and Issue Slip
  (RIS) / Withdraw · Return Slip.
- **Buttons:** actions = 32px monochrome icon buttons, color-on-hover
  (view sky / edit purple / approve green / reject red / print slate).
  Popups = exactly Confirm (`btn-modal-save btn-confirm-go`) + Cancel
  (`btn-modal-cancel`); green Create-PR-exact hover is the default standard.
  Popup header glyphs: 22px solid green/red (never white-on-pale).
- **Modals:** 520px decision shells, droplet entrance, no X buttons (explicit
  Cancel/Close footers), hidden-POST-form + JS opener pattern (never native
  `confirm()`).
- **fx21 fields:** structure `.fx21-field > input.effect-21 + span.focus-border`
  + label; box styling is inline per input; parked labels need 26px row rhythm.
  Focus draws the `#53c5f1` rounded border animation (focus-only, never glow).
- **Overlay law (hard-won):** NO popup/panel may render inside a card subtree
  (`.control-card`, `.toolbelt-container`, `.table-card`). The page-load
  `cascade-unveil` animation fill leaves permanent `transform` + `clip-path`
  on those containers, which re-anchors fixed descendants (coordinates
  misfire) and traps z-index (panels slice behind later content). Body-level
  overlays (decision modals) are always safe. Shared guard in `modals.css`
  (`body .cascade-unveil` fill release) — never remove it. Proven pattern:
  filter panel = relative wrap + absolute card + `.open` toggle + native
  mini-form, with Cancel (discard) + Apply (green) + Clear link.
- **Icons:** three inline-SVG sprites (`action-icons.js`, `nav-icons.js`,
  `kpi-icons.js`; all `currentColor`, arcs-free). Reuse across families
  (`i-view` magnifier for search boxes, `n-inventory` for stock states) —
  never draw a duplicate. KPI badges: 44px, 8px radius, 1px bordered box,
  section tint; centered icon + label-over-count + sub.
- **Nav:** resting buttons borderless/transparent; hover + active = header
  sky `#aae0f7`, borderless. Logout keeps red text + red-fill hover.
- **Toasts:** server flashes + client `showToast()` twin (same card markup,
  category → `i-check`/`i-x`/`i-bell` + circled tint); flash text is
  emoji-free. One `#toast-container`-scoped block in `modals.css` beats all
  per-page duplicates. Interactive layer: GET-only interceptor, ~850ms
  delayed submit/nav for filter/search/refresh (POSTs never intercepted).
- **Form submits + flashes (hard-won):** NEVER `fetch`-POST a flash +
  redirect form — fetch follows the redirect internally and consumes the
  flash queue, so the visible navigation shows no toast (killed PR saves
  twice). Use native submit; keep the disabled ⏳ button for double-guard.
- **Pending-only edits:** PR/User/Withdraw/Return all edit Pending records
  only (server re-checks status in-transaction). V1 = header + qty/condition
  on the same line set (no add/remove); identity fields frozen (numbers,
  links). Return revalidation excludes the edited record from the
  already-returned SUM; withdraw qty can't drop below already-returned.
  Unserviceable auto-approve preserved on edit. RBAC: only User edit is
  admin-only. Picker lists returnable-only (issued − already > 0).
- **Filters:** anchored panel = relative wrap + absolute card + `.open` toggle + native mini-form; Start/End dates where applicable; Cancel + green Apply + Clear link; count badge = result rows (dot when empty); dashboard chart exception (no rows → active-count). Backend ranges validated (never future, from ≤ to).
- **Bell:** `crud_notifications` single source; rows link filtered; own-voice labels; no Welcome (username + role pill + avatar).
- **Print family:** standalone sheet, `@page` portrait, screen toolbar hidden
  on paper, repeating `thead`, same-tab + `history.back()` Close (no
  `target="_blank"` anywhere). PR (meta-free official doc, fixed VIOS
  signatory), merged multi-fund (per-row fund, screen-only trace strip),
  IAR (photo-mirror + signatory baselines), 20-row Withdrawal Slip
  (`CPSC-SUP-F015`), filter-aware Inventory List, Return Slip (IAR skeleton,
  no doc-code strip).

## 5. Verification Protocol (every build)
- `python -m py_compile <touched .py>` · `node --check <touched .js>` ·
  div open/close balance on every touched template · live render via
  `test_client` (login admin/123) for new routes · `Ctrl+Shift+R` after CSS.
- Behavioral rules: never crash a dashboard (safe defaults), flash + redirect
  on invalid input, crafted-URL guards on all merge/print endpoints.
- Never commit/push unless explicitly asked. Never delete records to "fix"
  display issues. Wipe policy: transactions only, keep `users` + `products`.

## 6. Key References
- Routes: `/pr`, `/pr/print/<id>`, `/pr/print_merged`, `/delivery/*` (IAR),
  `/withdraw`, `/withdraw/print/<id>`, `/returns`, `/returns/print/<id>`,
  `/inventory`, `/inventory/print`, `/admin/*`, `/api/settings`.
- Core CRUD: `crud_pr` (numbering, duplicates, `set_po_status`),
  `crud_delivery` (IAR-native + aliases), `crud_inventory`, `crud_withdrawal`,
  `crud_returns`, `crud_products` (delete guards), `crud_users`, `crud_settings`.
- Palette: sidebar `#f7f0e8` · active `#e1f3fe→#cbebfe` · accent `#53c5f1` ·
  header `#aae0f7` · body `#eaf3f8` · navy `#0d47a1`.
- Clean slate (phpMyAdmin, FK checks off): DELETE `pr_items`,
  `purchase_requests`, `iar_items`, `iar`, `items`, `withdraw_items`,
  `withdraw`, `return_items`, ``return``, `stock_movements` (+ `products` only
  for full reset); reset `AUTO_INCREMENT`; keep `users`.
