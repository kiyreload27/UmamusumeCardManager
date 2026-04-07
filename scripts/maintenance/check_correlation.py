import sqlite3
import os

DB_PATH = os.path.join("database", "umamusume.db")

def check_correlation():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT card_id, name FROM support_cards ORDER BY card_id ASC LIMIT 1")
    first_card = cur.fetchone()
    print(f"First card: {first_card}")
    
    if first_card:
        # Check what events ID 1 points to
        cur.execute("SELECT event_name FROM support_events WHERE card_id = 1 LIMIT 1")
        first_event = cur.fetchone()
        print(f"First event for card_id 1: {first_event}")

    conn.close()

if __name__ == "__main__":
    check_correlation()
