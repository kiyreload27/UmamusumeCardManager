import sqlite3
import os

# Project root database
DB_PATH = os.path.join("database", "umamusume.db")

def check_local_db():
    if not os.path.exists(DB_PATH):
        print("Local DB not found")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MIN(card_id), MAX(card_id) FROM support_cards")
    print(f"Local support_cards range: {cur.fetchone()}")
    cur.execute("SELECT MIN(card_id), MAX(card_id) FROM support_events")
    print(f"Local support_events range: {cur.fetchone()}")
    conn.close()

if __name__ == "__main__":
    check_local_db()
