import sqlite3
import os

DB_PATH = os.path.join("database", "umamusume_seed.db")

def check_seed_db():
    if not os.path.exists(DB_PATH):
        print("Seed DB not found")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MIN(card_id), MAX(card_id) FROM support_cards")
    print(f"Seed support_cards range: {cur.fetchone()}")
    cur.execute("SELECT MIN(card_id), MAX(card_id) FROM support_events")
    print(f"Seed support_events range: {cur.fetchone()}")
    conn.close()

if __name__ == "__main__":
    check_seed_db()
