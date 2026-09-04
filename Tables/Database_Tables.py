"""Database_Tables.py — Streamlined Schema Builder (PR to Delivery Flow)
Creates all tables in dependency order: Users → Products → purchase_requests/pr_items → deliveries/delivery_items → inventory/withdraw/return.
Run: python Tables/Database_Tables.py (requires XAMPP MySQL running).
"""

import mysql.connector


def create_all_tables():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
    )
    cursor = conn.cursor()

    # Create Database if it doesn't exist
    cursor.execute("CREATE DATABASE IF NOT EXISTS production_inventory_db")
    cursor.execute("USE production_inventory_db")

    # 1. USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 2. PRODUCTS TABLE (Just-in-Time / Auto-populated Catalog)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INT AUTO_INCREMENT PRIMARY KEY,
        product_name VARCHAR(100) NOT NULL,
        category VARCHAR(50) DEFAULT 'General',
        details TEXT,
        unit VARCHAR(20) DEFAULT 'pcs',
        starting_stock INT DEFAULT 0,
        current_stock INT DEFAULT 0,
        size VARCHAR(20) DEFAULT 'N/A',
        price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
        quantity INT NOT NULL DEFAULT 0,
        reorder_level INT DEFAULT 10,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 3. PURCHASE REQUEST TABLES (PR Flow)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_requests (
        pr_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        pr_number VARCHAR(50) NOT NULL UNIQUE,
        fund_source VARCHAR(50) DEFAULT 'Fund 05',
        date_requested TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
        total_price DECIMAL(12, 2) DEFAULT 0.00,
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pr_items (
        pr_item_id INT AUTO_INCREMENT PRIMARY KEY,
        pr_id INT NOT NULL,
        user_id INT NOT NULL,
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
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 4. DELIVERY TABLES (Direct PR to Delivery, with external PO reference & supplier name)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deliveries (
        delivery_id INT AUTO_INCREMENT PRIMARY KEY,
        approved_by INT,
        pr_id INT NOT NULL,
        user_id INT NOT NULL,
        delivery_number VARCHAR(50) NOT NULL UNIQUE,
        iar_number VARCHAR(50),
        po_reference_number VARCHAR(50), 
        supplier_name VARCHAR(100) NOT NULL,
        inspected_by VARCHAR(100),
        supply_officer VARCHAR(100),
        is_partial TINYINT(1) DEFAULT 0,
        delivery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        remarks TEXT,
        status ENUM('Pending', 'Received', 'Incomplete') DEFAULT 'Pending',
        FOREIGN KEY (approved_by) REFERENCES users(id),
        FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS delivery_items (
        delivery_items_id INT AUTO_INCREMENT PRIMARY KEY,
        delivery_id INT NOT NULL,
        pr_id INT NOT NULL,
        user_id INT NOT NULL,
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
        FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 5. PHYSICAL LEDGER TABLE (ITEMS)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id INT AUTO_INCREMENT PRIMARY KEY,
        delivery_id INT,
        pr_id INT,
        user_id INT,
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
        FOREIGN KEY (pr_id) REFERENCES purchase_requests(pr_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 6. WITHDRAW TABLES (RIS Workflow)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdraw (
        withdraw_id INT AUTO_INCREMENT PRIMARY KEY,
        ris_number VARCHAR(50) NOT NULL UNIQUE,
        user_id INT NOT NULL,
        department VARCHAR(100) NOT NULL,
        purpose TEXT NOT NULL,
        status ENUM('Pending', 'Approved', 'Rejected', 'Issued') DEFAULT 'Pending',
        issued_by INT DEFAULT NULL,
        received_by VARCHAR(100) DEFAULT NULL,
        date_requested TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date_issued DATETIME DEFAULT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (issued_by) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdraw_items (
        withdraw_item_id INT AUTO_INCREMENT PRIMARY KEY,
        withdraw_id INT NOT NULL,
        product_id INT NOT NULL,
        item_name VARCHAR(100) NOT NULL,
        quantity INT NOT NULL,
        unit VARCHAR(20) DEFAULT NULL,
        unit_price DECIMAL(10, 2) DEFAULT 0.00,
        total_price DECIMAL(12, 2) DEFAULT 0.00,
        FOREIGN KEY (withdraw_id) REFERENCES withdraw(withdraw_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    

    # 7. STOCK MOVEMENTS TABLE (Audit Trail)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_movements (
        movement_id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL,
        reference_type VARCHAR(20) NOT NULL,
        reference_id INT NOT NULL,
        quantity_change INT NOT NULL,
        balance_after INT NOT NULL,
        user_id INT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    
# 8. RETURN TABLES (Linked to Withdraw for equipment/asset returns)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `return` (
        return_id INT AUTO_INCREMENT PRIMARY KEY,
        return_number VARCHAR(50) NOT NULL UNIQUE,
        withdraw_id INT DEFAULT NULL,
        user_id INT NOT NULL,
        department VARCHAR(100) DEFAULT NULL,
        reason TEXT DEFAULT NULL,
        status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
        approved_by INT DEFAULT NULL,
        date_returned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (withdraw_id) REFERENCES withdraw(withdraw_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (approved_by) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS return_items (
        return_item_id INT AUTO_INCREMENT PRIMARY KEY,
        return_id INT NOT NULL,
        product_id INT NOT NULL,
        item_name VARCHAR(100) NOT NULL,
        returned_quantity INT NOT NULL,
        condition_status ENUM('Serviceable', 'Unserviceable') DEFAULT 'Serviceable',
        unit VARCHAR(20) DEFAULT NULL,
        unit_price DECIMAL(10, 2) DEFAULT 0.00,
        total_price DECIMAL(12, 2) DEFAULT 0.00,
        FOREIGN KEY (return_id) REFERENCES `return`(return_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Streamlined PR-to-Delivery database & tables created successfully!")


if __name__ == "__main__":
    create_all_tables()