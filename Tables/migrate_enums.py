"""
Migration script: Update ENUM values for purchase_orders.status
and add missing columns to deliveries table.
Run once: python Tables/migrate_enums.py
"""
import mysql.connector

conn = mysql.connector.connect(
    host="localhost", user="root", password="", database="Production_Inventory_db"
)
cursor = conn.cursor()

# 1. Update purchase_orders.status ENUM
print("Updating purchase_orders.status ENUM...")
try:
    cursor.execute("""
        ALTER TABLE purchase_orders
        MODIFY COLUMN status ENUM(
            'Pending PO Approval', 'Approved', 'Issued', 'Delivered',
            'Cancelled', 'Completed', 'Partial', 'Partially Delivered', 'Pending'
        ) DEFAULT 'Pending PO Approval'
    """)
    print("  -> purchase_orders.status ENUM updated successfully.")
except Exception as e:
    print(f"  -> Skipped (may already be correct): {e}")

# 2. Add missing columns to deliveries table if they don't exist
print("Checking deliveries table columns...")
try:
    cursor.execute("SHOW COLUMNS FROM deliveries LIKE 'iar_number'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE deliveries ADD COLUMN iar_number VARCHAR(50) AFTER delivery_number")
        print("  -> Added iar_number column")
    else:
        print("  -> iar_number already exists")
except Exception as e:
    print(f"  -> iar_number: {e}")

try:
    cursor.execute("SHOW COLUMNS FROM deliveries LIKE 'inspected_by'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE deliveries ADD COLUMN inspected_by VARCHAR(100) AFTER iar_number")
        print("  -> Added inspected_by column")
    else:
        print("  -> inspected_by already exists")
except Exception as e:
    print(f"  -> inspected_by: {e}")

try:
    cursor.execute("SHOW COLUMNS FROM deliveries LIKE 'supply_officer'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE deliveries ADD COLUMN supply_officer VARCHAR(100) AFTER inspected_by")
        print("  -> Added supply_officer column")
    else:
        print("  -> supply_officer already exists")
except Exception as e:
    print(f"  -> supply_officer: {e}")

try:
    cursor.execute("SHOW COLUMNS FROM deliveries LIKE 'is_partial'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE deliveries ADD COLUMN is_partial TINYINT(1) DEFAULT 0 AFTER supply_officer")
        print("  -> Added is_partial column")
    else:
        print("  -> is_partial already exists")
except Exception as e:
    print(f"  -> is_partial: {e}")

conn.commit()
cursor.close()
conn.close()
print("Migration complete.")
