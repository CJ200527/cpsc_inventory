from db import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("SHOW TABLES")
tables = cursor.fetchall()

print("Existing tables in the database:")
for table in tables:
    print(f" - {table[0]}")

cursor.close()
conn.close()