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
# 1. PURCHASE REQUEST TABLES
# ---------------------------------------------------------
create_pr_header = """
CREATE TABLE IF NOT EXISTS purchase_requests (
    pr_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    pr_number VARCHAR(50) NOT NULL UNIQUE,
    date_requested TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    total_price DECIMAL(12, 2) DEFAULT 0.00,
    has_po TINYINT(1) DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES Users(id)
);
"""

create_pr_items = """
CREATE TABLE IF NOT EXISTS pr_items (
    pr_item_id INT AUTO_INCREMENT PRIMARY KEY,
    pr_id INT NOT NULL,
    user_id INT NOT NULL,
    supplier_id INT NOT NULL,
    product_id INT NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    unit VARCHAR(20),
    details TEXT,
    size VARCHAR(20),
    price DECIMAL(10, 2) NOT NULL,
    quantity INT NOT NULL,
    total_price DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id)
);
"""

# ---------------------------------------------------------
# 2. PURCHASE ORDER TABLES
# ---------------------------------------------------------
create_po_header = """
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id INT AUTO_INCREMENT PRIMARY KEY,
    pr_id INT NOT NULL,
    supplier_id INT NOT NULL,
    user_id INT NOT NULL,
    po_number VARCHAR(50) NOT NULL UNIQUE,
    date_ordered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Pending PO Approval', 'Approved', 'Issued', 'Delivered', 'Cancelled', 'Completed', 'Partial') DEFAULT 'Pending PO Approval',
    total_price DECIMAL(12, 2) DEFAULT 0.00,
    FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id),
    FOREIGN KEY (user_id) REFERENCES Users(id)
);
"""

create_po_items = """
CREATE TABLE IF NOT EXISTS po_items (
    po_item_id INT AUTO_INCREMENT PRIMARY KEY,
    po_id INT NOT NULL,
    pr_id INT NOT NULL,
    user_id INT NOT NULL,
    supplier_id INT NOT NULL,
    product_id INT NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    unit VARCHAR(20),
    details TEXT,
    size VARCHAR(20),
    price DECIMAL(10, 2) NOT NULL,
    quantity INT NOT NULL,
    total_price DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
    FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id)
);
"""

# ---------------------------------------------------------
# 3. DELIVERY TABLES
# ---------------------------------------------------------
create_delivery_header = """
CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id INT AUTO_INCREMENT PRIMARY KEY,
    approved_by INT,
    po_id INT NOT NULL,
    pr_id INT NOT NULL,
    user_id INT NOT NULL,
    supplier_id INT NOT NULL,
    delivery_number VARCHAR(50) NOT NULL UNIQUE,
    iar_number VARCHAR(50),
    inspected_by VARCHAR(100),
    supply_officer VARCHAR(100),
    is_partial TINYINT(1) DEFAULT 0,
    delivery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remarks TEXT,
    status ENUM('Pending', 'Received', 'Incomplete') DEFAULT 'Received',
    FOREIGN KEY (approved_by) REFERENCES Users(id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id)
);
"""

create_delivery_items = """
CREATE TABLE IF NOT EXISTS delivery_items (
    delivery_items_id INT AUTO_INCREMENT PRIMARY KEY,
    delivery_id INT NOT NULL,
    po_id INT NOT NULL,
    pr_id INT NOT NULL,
    user_id INT NOT NULL,
    supplier_id INT NOT NULL,
    product_id INT NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    ordered_quantity INT NOT NULL,
    received_quantity INT NOT NULL,
    category VARCHAR(50),
    details TEXT,
    unit VARCHAR(20),
    size VARCHAR(20),
    price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (delivery_id) REFERENCES deliveries(delivery_id) ON DELETE CASCADE,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id)
);
"""

# Execute all table creations in logical sequence
print("Creating Purchase Request tables...")
cursor.execute(create_pr_header)
cursor.execute(create_pr_items)

print("Creating Purchase Order tables...")
cursor.execute(create_po_header)
cursor.execute(create_po_items)

print("Creating Delivery tables...")
cursor.execute(create_delivery_header)
cursor.execute(create_delivery_items)

conn.commit()
print("PR, PO, and Delivery tables created successfully!")

cursor.close()
conn.close()