import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
)
cursor = conn.cursor()

conn.cursor().execute("CREATE DATABASE IF NOT EXISTS Production_Inventory_db")
conn.database = "Production_Inventory_db"

create_table_users = """
CREATE TABLE IF NOT EXISTS Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(50) NOT NULL,
    Firstname VARCHAR(50) NOT NULL,
    Lastname VARCHAR(50) NOT NULL,
    MI VARCHAR(4) NOT NULL,
    fullname VARCHAR(255) NOT NULL,
    Role VARCHAR(50) NOT NULL DEFAULT 'Staff',
    Contact_Number VARCHAR(11) NOT NULL,
    Approved_By BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

create_table_supplier = """
CREATE TABLE IF NOT EXISTS Supplier (
    id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(100) NOT NULL,
    contact_person VARCHAR(100) NOT NULL,
    contact_number VARCHAR(11) NOT NULL,
    email VARCHAR(100) NOT NULL,
    street VARCHAR(100),
    barangay VARCHAR(100),
    municipality VARCHAR(100),
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Philippines',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

create_table_products = """
CREATE TABLE IF NOT EXISTS Products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_id INT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    details TEXT,
    unit VARCHAR(20) NOT NULL,
    size VARCHAR(20),
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    quantity INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES Supplier(id)
)
"""

cursor.execute(create_table_users)
conn.commit()
print("Users table created successfully.")

cursor.execute(create_table_supplier)
conn.commit()
print("Supplier table created successfully.")

cursor.execute(create_table_products)
conn.commit()
print("Products table created successfully.")

cursor.close()
conn.close()
    