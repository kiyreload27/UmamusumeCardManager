import sqlite3
import os

DB_PATH = os.path.join("database", "umamusume.db")

def check_event_card_ids():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT DISTINCT card_id FROM support_events LIMIT 20")
    ids = [row[0] for row in cur.fetchall()]
    print(f"Distinct card_ids in support_events: {ids}")
    
    cur.execute("SELECT card_id, name FROM support_cards WHERE card_id IN (1, 2, 3, 4, 5)")
    print(f"Cards with IDs 1-5: {cur.fetchall()}")
    
    conn.close()

if __name__ == "__main__":
    check_event_card_ids()
