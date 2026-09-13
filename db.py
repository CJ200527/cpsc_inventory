"""db.py — Central MySQL connector (Study Guide)
Provides get_db_connection(): connects to Production_Inventory_db via mysql-connector-python.
Auto-creates DB if missing (1049). Used by all crud_* modules.
Credentials loaded from environment variables with XAMPP defaults.
"""

import os
import mysql.connector

def get_db_connection():
    """
    Establishes and returns a connection to the MySQL database.
    Auto-creates the database if it doesn't exist (helps on fresh XAMPP installs).
    Re-used by all CRUD functions across the system.
    """
    db_host = os.environ.get("DB_HOST", "localhost")
    db_user = os.environ.get("DB_USER", "root")
    db_pass = os.environ.get("DB_PASSWORD", "")
    db_name = os.environ.get("DB_NAME", "production_inventory_db")
    try:
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name
        )
        return conn
    except mysql.connector.Error as err:
        if err.errno == 1049:
            tmp = mysql.connector.connect(host=db_host, user=db_user, password=db_pass)
            cur = tmp.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            tmp.commit()
            cur.close()
            tmp.close()
            return mysql.connector.connect(
                host=db_host, user=db_user, password=db_pass, database=db_name
            )
        raise
