import mysql.connector

def get_db_connection():
    """
    Establishes and returns a connection to the MySQL database.
    Auto-creates the database if it doesn't exist.
    """
    try:
        conn = mysql.connector.connect(
            host="localhost", user="root", password="", database="Production_Inventory_db"
        )
        return conn
    except mysql.connector.Error as err:
        if err.errno == 1049:
            tmp = mysql.connector.connect(host="localhost", user="root", password="")
            cur = tmp.cursor()
            cur.execute("CREATE DATABASE IF NOT EXISTS Production_Inventory_db")
            tmp.commit()
            cur.close(); tmp.close()
            return mysql.connector.connect(host="localhost", user="root", password="", database="Production_Inventory_db")
        raise