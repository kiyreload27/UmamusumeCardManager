import sqlite3
import os

DB_PATH = os.path.join("database", "umamusume.db")

def check_effects_card_ids():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT DISTINCT card_id FROM support_effects LIMIT 10")
    print(f"Distinct card_ids in support_effects: {[row[0] for row in cur.fetchall()]}")
    
    conn.close()

if __name__ == "__main__":
    check_effects_card_ids()
