
import sqlite3
import os

DB_PATH = r"y:\Keith\umamusuma card application\database\umamusume.db"
print(f"Checking DB at: {DB_PATH}")

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT card_id, name, image_path FROM support_cards LIMIT 5")
    rows = cur.fetchall()
    
    print("\nSample Card Data:")
    for row in rows:
        print(f"ID: {row[0]}, Name: {row[1]}, Path: {row[2]}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
