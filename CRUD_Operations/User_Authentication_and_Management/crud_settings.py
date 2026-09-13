"""crud_settings.py — System Settings (key-value store)
Admin-configurable settings stored in `admin_settings` table.
Loaded per-request or cached in Flask `g`. Thread-safe reads, atomic upsert writes.
"""

from db import get_db_connection

DEFAULT_SETTINGS = {
    # Branding
    "institution_name": "Camiguin Polytechnic State College",
    "institution_address": "Balbagon, Mambajao, Camiguin",
    "app_title": "CPSC Production Inventory Management",
    "logo_file": "cpsc_logo.png",
    "footer_text": "@ CPSC Production Office",
    # Theme
    "theme_mode": "light",
    "primary_color": "#53c5f1",
    # Business Rules
    "product_categories": "Consumables,Tools,Equipment",
    "returnable_categories": "Tools,Equipment",
    "default_fund_source": "Fund 05",
    "currency_symbol": "₱",
    "currency_code": "PHP",
    "default_unit": "pcs",
    "default_size": "N/A",
    "phone_regex": "^09[0-9]{9}$",
    "phone_hint": "Must be 11 digits starting with 09",
    # Stock Alerts
    "default_reorder_level": "10",
    "cat_reorder_consumables": "10",
    "cat_reorder_tools": "5",
    "cat_reorder_equipment": "5",
    "auto_approve_unserviceable": "true",
    # Dashboard Limits
    "top_items_limit": "5",
    "activity_feed_limit": "8",
    "dashboard_snapshot_limit": "10",
    "all_time_lookback_months": "6",
    # UI
    "toast_duration_ms": "4000",
    "animation_lock_ms": "1800",
    "date_format": "Month Day, Year | h:mm AM/PM",
}


def _table_exists(cur, name):
    cur.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s", (name,))
    return cur.fetchone()[0] > 0


def ensure_settings_table():
    conn = None; cur = None
    try:
        conn = get_db_connection(); cur = conn.cursor()
        if not _table_exists(cur, "admin_settings"):
            cur.execute("""
                CREATE TABLE admin_settings (
                    setting_key VARCHAR(100) PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    except Exception as e:
        print(f"[ensure_settings_table] {e}")
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


def init_default_settings():
    conn = None; cur = None
    try:
        conn = get_db_connection(); cur = conn.cursor()
        for k, v in DEFAULT_SETTINGS.items():
            cur.execute("INSERT IGNORE INTO admin_settings (setting_key, setting_value) VALUES (%s, %s)", (k, v))
        conn.commit()
    except Exception as e:
        print(f"[init_default_settings] {e}")
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


def get_all_settings():
    conn = None; cur = None
    try:
        conn = get_db_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT setting_key, setting_value FROM admin_settings")
        rows = cur.fetchall()
        settings = dict(DEFAULT_SETTINGS)
        for r in rows:
            settings[r['setting_key']] = r['setting_value']
        return settings
    except Exception as e:
        print(f"[get_all_settings] {e}")
        return dict(DEFAULT_SETTINGS)
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


def get_setting(key, default=None):
    conn = None; cur = None
    try:
        conn = get_db_connection(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT setting_value FROM admin_settings WHERE setting_key=%s", (key,))
        row = cur.fetchone()
        return row['setting_value'] if row else DEFAULT_SETTINGS.get(key, default)
    except Exception as e:
        print(f"[get_setting] {e}")
        return DEFAULT_SETTINGS.get(key, default)
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass


def save_settings(settings_dict):
    conn = None; cur = None
    try:
        conn = get_db_connection(); cur = conn.cursor()
        for k, v in settings_dict.items():
            cur.execute("""
                INSERT INTO admin_settings (setting_key, setting_value)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE setting_value=%s
            """, (k, str(v), str(v)))
        conn.commit()
        return True
    except Exception as e:
        print(f"[save_settings] {e}")
        try: conn.rollback()
        except: pass
        return False
    finally:
        if cur:
            try: cur.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass
