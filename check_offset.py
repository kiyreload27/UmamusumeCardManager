import sqlite3
import os

DB_PATH = os.path.join("database", "umamusume.db")

def check_offset():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get first 5 SSR cards
    cur.execute("SELECT card_id, name, gametora_url FROM support_cards ORDER BY card_id ASC LIMIT 5")
    cards = cur.fetchall()
    print(f"Cards: {cards}")
    
    # Check if there are events referring to IDs 1, 2, 3...
    for i in range(1, 6):
        cur.execute("SELECT event_name FROM support_events WHERE card_id = ? LIMIT 1", (i,))
        ev = cur.fetchone()
        print(f"ID {i} events: {ev}")

    conn.close()

if __name__ == "__main__":
    check_offset()
