import sqlite3
import os

DB_PATH = os.path.join("database", "umamusume.db")

def check_orphans():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if event_id exists in support_events
    cur.execute("""
        SELECT COUNT(*) 
        FROM event_skills es
        LEFT JOIN support_events se ON es.event_id = se.event_id
        WHERE se.event_id IS NULL
    """)
    orphans = cur.fetchone()[0]
    print(f"Orphaned skills (no matching event): {orphans}")
    
    # Check if card_id exists in support_cards
    cur.execute("""
        SELECT COUNT(*) 
        FROM support_events se
        LEFT JOIN support_cards sc ON se.card_id = sc.card_id
        WHERE sc.card_id IS NULL
    """)
    orphaned_events = cur.fetchone()[0]
    print(f"Orphaned events (no matching card): {orphaned_events}")
    
    conn.close()

if __name__ == "__main__":
    check_orphans()
