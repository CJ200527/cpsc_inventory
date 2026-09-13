# Session Continuation Prompt — CPSC Inventory System
## Date: September 14, 2026

---

## SYSTEM OVERVIEW
- **Tech Stack**: Python/Flask + MySQL (XAMPP), vanilla JS, Jinja2 templates
- **Working Dir**: `C:\Users\user\OneDrive\Desktop\BSIT 3A 1ST SEM\IM 103 - ADVANCE DATABASE SYSTEM 2\CPSC INVENTORY FRESH`
- **Python**: Flask runs on **Python 3.14** (`C:\Python314\python.exe`), `python3` alias is 3.12. Always use `python` (3.14) to match Flask.
- **Debug Mode**: `app.run(debug=True, use_reloader=False, port=5000)`
- **Passwords**: Stored as **plaintext** — werkzeug hashing was fully removed. Never re-add.

---

## CRITICAL RULES
1. **Never alter backend bindings**: `input name=`, Jinja `{{ variables }}`, element `id=` (used by JS), `form action=`, `url_for()` endpoints
2. **After every HTML structural edit**: verify div open/close balance
3. **After every JS edit**: run `node --check <file>`
4. **After every Python edit**: run `py_compile` on the file
5. **Always Ctrl+Shift+R** (hard refresh) when styles change — browser caches CSS aggressively
6. **CSS reference**: `modals.css` has the fx21 design language; `admin_dashboard.css` has sidebar/header styles

---

## WHAT WAS COMPLETED (All Sessions)

### Modules Brought to Full Parity
- **Delivery** (Receive/Complete modals, data tables, View modals, staff+admin)
- **PR Creation + Edit** (staff+admin): 3-column caption rows
- **Withdraw Creation** (staff+admin): 3-column caption rows, data tables, View modals
- **Return Creation** (staff+admin): Pinned Section 1, rich custom dropdown picker
- **Return Tables** (staff+admin): Return Number / Withdraw Number / Department / Condition / Date / Total Qty / Status / Actions — short numbers, ph_datetime
- **Return View Modals** (staff+admin): Item Name / Specification / Unit / Size / Category / Condition (no money)

### Return Policy (Implemented + Tested)
- **Unserviceable returns**: Auto-approve on save (record only, zero stock change)
- **Serviceable returns**: Save as `Pending` → admin approves → restock (`current_stock += qty`)
- **Mixed returns** (both conditions): Stay Pending
- Only Tools/Equipment items can be returned
- Item picker shows only unreturned items from chosen withdrawal
- "+ Add Item" dropdown excludes items already in the table (by product_id)

### Git
- **Last commit**: `c0fa42c` — "Return restock policy: Unserviceable auto-approve, Serviceable requires admin approval, returnable-items endpoint, view modal redesign, short numbers"
- **Pushed to GitHub**

### Security Fixes (Implemented)
- Flask secret key from env var `FLASK_SECRET_KEY`
- DB credentials from env vars in `db.py` (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`)
- `.gitignore` created: `__pycache__/`, `*.pyc`, `.pyo`, `.env`, `*.db`

### Settings Module (Built, Needs UI Redesign)
- **Backend**: `crud_settings.py` — `ensure_settings_table()`, `init_default_settings()`, `get_all_settings()`, `get_setting()`, `save_settings()`
- **DB table**: `admin_settings` (key/value + timestamp)
- **Route**: `/admin/settings` (GET/POST) + `/api/settings` (GET) in `App.py` ~line 2224
- **Template**: `Templates/Admin Dashboards/admin_settings.html`
- **5 Tabs**: Branding, Theme, Business Rules, Stock Alerts, UI Preferences
- **28 default settings** across categories
- **Status**: Route works, page loads, but design is inconsistent with rest of system

### Password Issue (Resolved)
- Root cause: `crud_users.cpython-314.pyc` cached old werkzeug hash code
- All `__pycache__` directories cleared; passwords confirmed plaintext `123`
- **All 3 users**: admin (1001), Staff (1002), Cj (1003) — all password `123`

---

## WHAT NEEDS TO BE DONE NEXT

### Priority 1: Settings Page Redesign (Tomorrow's Main Task)

The settings page works but its design is inconsistent with the rest of the system. Here's exactly what needs to change:

#### Sidebar Structural Fixes
1. **Remove `<div class="page-wrapper">` wrapper** — other pages use direct sibling `<div class="sidebar">` + `<div class="main-wrapper">`
2. **Replace `class="nav-scroll" > class="nav-section"`** with plain `<div>` wrapping header + `<div class="nav-menu">`
3. **Change class names**:
   - `class="sidebar-header-text"` → plain `<div>`
   - `class="school-name"` → `class="school-title"`
   - `class="school-address"` → `class="school-subtitle"`
4. **Fix logo path**: `images/cpsc_logo.png` → `cpsc_logo.png` + add `onerror` fallback
5. **Fix Dashboard icon**: `📊` → `💻`
6. **Fix PR label**: `Purchase Request` → `Submit PR`
7. **Fix profile classes**: `class="header-profile"` → `class="user-profile-box"`, `class="header-username"` → `class="user-name"`, `class="header-role"` → `class="user-role"`

#### CSS Fixes
8. **Remove `main_theme.css`** from `<head>` — it duplicates body styles already in `admin_dashboard.css`
9. **Convert Theme tab** raw `<select>` and `<label>` to use `.fx21-field` / `.effect-21` / `.focus-border` pattern
10. **Replace custom button styles** in `.settings-save-bar` with existing `.btn-modal-save` / `.btn-modal-cancel` from `modals.css`

#### Content Review
11. User will decide which settings tabs/fields to keep or remove
12. Review all 28 settings keys — some may not be needed

### Reference: fx21 Design Language (from `modals.css`)
```html
<div class="fx21-field">
    <input type="text" name="field_name" class="effect-21" value="..." placeholder="...">
    <span class="focus-border"><i></i></span>
    <label class="fx21-label">Caption Label</label>
</div>
```
- Labels fixed above the box (`position: absolute; top: -18px`)
- `border-radius: 6px` on `.focus-border`
- Rounded draw animation on focus (4-stage border)
- No glow (`box-shadow: none`)
- Transparent label chips
- Color: `#53c5f1` (sky blue)

### Reference: Canonical Sidebar HTML (from `admin_dashboard.html`)
```html
<div class="sidebar">
    <div>
        <div class="sidebar-header">
            <img class="sidebar-logo" src="{{ url_for('static', filename='cpsc_logo.png') }}"
                 alt="CPSC Seal" onerror="this.src='https://upload.wikimedia.org/...png'">
            <div>
                <div class="school-title">Camiguin Polytechnic State College</div>
                <div class="school-subtitle">Balbagon, Mambajao, Camiguin</div>
            </div>
        </div>
        <div class="nav-menu">
            <a href="{{ url_for('admin_dashboard') }}" class="nav-btn"><span class="icon">💻</span><span>Dashboard</span></a>
            <a href="{{ url_for('pr_management') }}" class="nav-btn"><span class="icon">📋</span><span>Submit PR</span></a>
            <a href="{{ url_for('delivery_dashboard') }}" class="nav-btn"><span class="icon">🚚</span><span>Receive Delivery</span></a>
            <a href="{{ url_for('admin_inventory_dashboard') }}" class="nav-btn"><span class="icon">📦</span><span>Stock Inventory</span></a>
            <a href="{{ url_for('admin_withdraw_dashboard') }}" class="nav-btn"><span class="icon">📤</span><span>Withdraw</span></a>
            <a href="{{ url_for('admin_return_dashboard') }}" class="nav-btn"><span class="icon">🔄</span><span>Return</span></a>
            <a href="{{ url_for('admin_products') }}" class="nav-btn"><span class="icon">🏷️</span><span>Product</span></a>
            <a href="{{ url_for('admin_users') }}" class="nav-btn"><span class="icon">👥</span><span>Users</span></a>
        </div>
    </div>
    <div>
        <a href="{{ url_for('admin_settings') }}" class="nav-btn active"><span class="icon">⚙</span><span>Settings</span></a>
        <a href="/logout" class="nav-btn logout-btn"><span class="icon">🚩</span><span>Log Out</span></a>
        <div class="sidebar-footer">@ CPSC Production Office 2026</div>
    </div>
</div>
```

### Reference: Canonical Top Header
```html
<div class="top-header">
    <div class="header-title-box">
        <h1>Settings</h1>
        <div class="date-time-box" id="live-clock">Loading Date & Time...</div>
    </div>
    <div class="user-profile-box">
        <div class="user-name">{{ full_name }}</div>
        <div class="user-role">{{ role }}</div>
    </div>
</div>
```

---

## KEY DATABASE TABLES
- `products`: includes `category, details, size, unit, price, current_stock, quantity, reorder_level`
- `withdraw_items`: `withdraw_item_id, withdraw_id, product_id, item_name, quantity, unit, unit_price, total_price, details` (NO `size` or `issued_quantity` — `quantity` IS the issued qty)
- `return_items`: `return_item_id, return_id, product_id, item_name, returned_quantity, condition_status, unit, unit_price, total_price, details`
- `admin_settings`: `id, setting_key, setting_value, updated_at`

## KEY ENDPOINTS
- `/admin/settings` — Settings page (GET/POST)
- `/api/settings` — Settings API (GET)
- `/returns/returnable-items/<withdraw_id>` — Returnable items for a withdrawal
- Login: `login_user(username, password)` in `crud_users.py`

---

## COLOR PALETTE
| Token | Hex | Usage |
|---|---|---|
| Sidebar bg | `#f7f0e8` | Warm cream |
| Nav-btn default | white→`#f4f4f4` gradient | Rounded 10px cards |
| Nav-btn active/hover | `#e1f3fe`→`#cbebfe` gradient | Sky blue |
| Accent blue | `#53c5f1` | Borders, focus, toggles |
| Header bg | `#aae0f7` | Light sky blue |
| Body bg | `#eaf3f8` | Pale blue-gray |
| Section title | `#0d47a1` | Deep navy |
| Save/green | `#81c784`/`#4caf50` | Submit buttons |
| Cancel/red | `#e57373`/`#ef5350` | Cancel buttons |

---

## QUICK COMMANDS
- Start Flask: `python App.py` (from project root)
- Reset passwords: `python -c "import sys,os; sys.path.insert(0,os.path.join('CRUD_Operations','User_Authentication_and_Management')); from db import get_db_connection; conn=get_db_connection(); cur=conn.cursor(); cur.execute('UPDATE users SET password=%s', ('123',)); conn.commit(); cur.close(); conn.close()"`
- Clear caches: `Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force`
- Check JS syntax: `node --check <file>`
- Check Python syntax: `python -m py_compile <file>`
