import sqlite3
import os

DB_PATH = os.path.join("database", "umamusume.db")

def check_counts():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM support_cards")
    print(f"support_cards: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(*) FROM support_events")
    print(f"support_events: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(*) FROM event_skills")
    print(f"event_skills: {cur.fetchone()[0]}")
    
    # Check sample card_id from events
    cur.execute("SELECT card_id FROM support_events LIMIT 1")
    sample_id = cur.fetchone()
    if sample_id:
        print(f"Sample card_id from events: {sample_id[0]}")
        cur.execute("SELECT name FROM support_cards WHERE card_id = ?", (sample_id[0],))
        card_name = cur.fetchone()
        print(f"Matching card name: {card_name}")
        
    conn.close()

if __name__ == "__main__":
    check_counts()
