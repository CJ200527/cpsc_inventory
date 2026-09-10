"""Database_Cleanup.py — Full test-data reset (keeps logins).

Deletes ALL records EXCEPT `users` (including `products`) and resets every
cleared table's AUTO_INCREMENT to 1, so the next inserts restart at ID 1.

Safe to re-run (idempotent): missing tables are skipped, not errors.

Run:  python Tables/Database_Cleanup.py
      (requires XAMPP MySQL running; root with no password, like db.py)
"""

import mysql.connector

DB_NAME = "production_inventory_db"

# Every table wiped by this script (`users` is the only keeper).
CLEAR_TABLES = [
    "pr_items",
    "purchase_requests",
    "delivery_items",
    "deliveries",
    "items",
    "withdraw_items",
    "withdraw",
    "return_items",
    "return",
    "stock_movements",
    "products",
]


def _table_exists(cursor, table_name):
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def _count(cursor, table_name):
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    return cursor.fetchone()[0]


def run_cleanup():
    """Wipe all test data (keep users) and refresh auto-numbers."""
    conn = mysql.connector.connect(host="localhost", user="root", password="")
    cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.execute(f"USE {DB_NAME}")
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")

        for table in CLEAR_TABLES:
            if _table_exists(cursor, table):
                cursor.execute(f"DELETE FROM `{table}`")
                print(f"cleared {table}: {cursor.rowcount} row(s) removed")
                cursor.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = 1")
            else:
                print(f"skipped {table}: table not found")

        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()

        print("---- verification ----")
        for table in ["users"] + CLEAR_TABLES:
            if _table_exists(cursor, table):
                print(f"{table}: {_count(cursor, table)} row(s)")
        print("Database cleanup done: only users kept, counters refreshed.")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    run_cleanup()
