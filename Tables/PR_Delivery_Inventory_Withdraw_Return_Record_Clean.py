"""PR_Delivery_Inventory_Withdraw_Return_Record_Clean.py — Partial test-data reset.

Deletes ALL records EXCEPT `users` and `products`, zeroes product stock
(so no ghost stock remains from the deleted movements), and resets every
cleared table's AUTO_INCREMENT to 1 (product numbering continues from MAX+1).

Safe to re-run (idempotent): missing tables are skipped, not errors.

Run:  python Tables/PR_Delivery_Inventory_Withdraw_Return_Record_Clean.py
      (requires XAMPP MySQL running; root with no password, like db.py)
"""

import mysql.connector

DB_NAME = "production_inventory_db"

# Transaction tables wiped by this script (`users` and `products` are kept).
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
]


def _table_exists(cursor, table_name):
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def _count(cursor, table_name):
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    return cursor.fetchone()[0]


def run_cleanup():
    """Wipe test data (keep users + products) and refresh auto-numbers."""
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

        # Products stay, but their stock must go back to zero so the deleted
        # deliveries/movements leave no ghost stock behind.
        if _table_exists(cursor, "products"):
            cursor.execute("UPDATE products SET current_stock = 0, quantity = 0")
            print("product rows kept; stock zeroed to remove ghost stock")
            cursor.execute("ALTER TABLE `products` AUTO_INCREMENT = 1")

        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()

        print("---- verification ----")
        for table in ["users", "products"] + CLEAR_TABLES:
            if _table_exists(cursor, table):
                print(f"{table}: {_count(cursor, table)} row(s)")
        print("Record clean done: users + products kept, counters refreshed.")
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
