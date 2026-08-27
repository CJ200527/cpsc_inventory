import mysql.connector

# 1. Connect to MySQL and select database
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="Production_Inventory_db"
)
cursor = conn.cursor()

# ---------------------------------------------------------
# 1. CENTRAL INVENTORY ITEMS TABLE
# ---------------------------------------------------------
create_items_table = """
CREATE TABLE IF NOT EXISTS items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    delivery_id INT,
    po_id INT,
    pr_id INT,
    user_id INT,
    supplier_id INT,
    product_id INT NOT NULL,
    item_number VARCHAR(50),
    item_name VARCHAR(100) NOT NULL,
    item_quantity INT NOT NULL DEFAULT 0,
    item_category VARCHAR(50),
    item_details TEXT,
    item_unit VARCHAR(20),
    item_size VARCHAR(20),
    item_price DECIMAL(10, 2) DEFAULT 0.00,
    item_total_price DECIMAL(12, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (delivery_id) REFERENCES deliveries(delivery_id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id)
);
"""

# ---------------------------------------------------------
# 2. WITHDRAW TABLE (STOCK-OUT)
# ---------------------------------------------------------
create_withdraw_table = """
CREATE TABLE IF NOT EXISTS withdraw (
    withdraw_id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT,
    delivery_id INT,
    po_id INT,
    pr_id INT,
    user_id INT NOT NULL,
    supplier_id INT,
    product_id INT NOT NULL,
    approved_by INT,
    withdraw_number VARCHAR(50) NOT NULL UNIQUE,
    withdraw_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quantity INT NOT NULL,
    purpose VARCHAR(255),
    remarks TEXT,
    status ENUM('Pending', 'Approved', 'Rejected', 'Completed') DEFAULT 'Pending',
    approved_date DATETIME,
    FOREIGN KEY (item_id) REFERENCES items(item_id),
    FOREIGN KEY (delivery_id) REFERENCES deliveries(delivery_id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id),
    FOREIGN KEY (approved_by) REFERENCES Users(id)
);
"""

# ---------------------------------------------------------
# 3. RETURN TABLE (STOCK-IN RETURN)
# ---------------------------------------------------------
# Note: 'returns' is used because 'RETURN' is a reserved SQL keyword in MySQL
create_return_table = """
CREATE TABLE IF NOT EXISTS returns (
    return_id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT,
    delivery_id INT,
    po_id INT,
    pr_id INT,
    user_id INT NOT NULL,
    supplier_id INT,
    product_id INT NOT NULL,
    approved_by INT,
    return_number VARCHAR(50) NOT NULL UNIQUE,
    return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quantity INT NOT NULL,
    reason_return VARCHAR(255),
    status_return ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    remarks TEXT,
    approved_date DATETIME,
    FOREIGN KEY (item_id) REFERENCES items(item_id),
    FOREIGN KEY (delivery_id) REFERENCES deliveries(delivery_id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id),
    FOREIGN KEY (approved_by) REFERENCES Users(id)
);
"""

# Execute table creations in order
print("Creating 'items' table...")
cursor.execute(create_items_table)

print("Creating 'withdraw' table...")
cursor.execute(create_withdraw_table)

print("Creating 'returns' table...")
cursor.execute(create_return_table)

conn.commit()
print("Inventory Items, Withdraw, and Returns tables created successfully!")

cursor.close()
conn.close()