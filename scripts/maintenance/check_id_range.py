import sqlite3
import os

DB_PATH = os.path.join("database", "umamusume.db")

def check_id_range():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT MIN(card_id), MAX(card_id) FROM support_cards")
    min_id, max_id = cur.fetchone()
    print(f"support_cards card_id range: {min_id} to {max_id}")
    
    cur.execute("SELECT MIN(card_id), MAX(card_id) FROM support_events")
    min_ev_id, max_ev_id = cur.fetchone()
    print(f"support_events card_id range: {min_ev_id} to {max_ev_id}")
    
    conn.close()

if __name__ == "__main__":
    check_id_range()
