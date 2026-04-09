import sqlite3
import os

DB_PATH = os.path.join("database", "umamusume.db")

def repair_db():
    if not os.path.exists(DB_PATH):
        return
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("Repairing database...")
    
    # 1. Remove all orphans
    cur.execute("DELETE FROM support_effects WHERE card_id NOT IN (SELECT card_id FROM support_cards)")
    print(f"Removed {cur.rowcount} orphaned effects")
    
    cur.execute("DELETE FROM support_hints WHERE card_id NOT IN (SELECT card_id FROM support_cards)")
    print(f"Removed {cur.rowcount} orphaned hints")
    
    cur.execute("DELETE FROM event_skills WHERE event_id NOT IN (SELECT event_id FROM support_events)")
    print(f"Removed {cur.rowcount} orphaned event skills")
    
    cur.execute("DELETE FROM support_events WHERE card_id NOT IN (SELECT card_id FROM support_cards)")
    print(f"Removed {cur.rowcount} orphaned events")
    
    # 2. Cleanup owned_cards and deck_slots
    cur.execute("DELETE FROM owned_cards WHERE card_id NOT IN (SELECT card_id FROM support_cards)")
    cur.execute("DELETE FROM deck_slots WHERE card_id NOT IN (SELECT card_id FROM support_cards)")
    
    conn.commit()
    conn.close()
    print("Repair complete.")

if __name__ == "__main__":
    repair_db()
