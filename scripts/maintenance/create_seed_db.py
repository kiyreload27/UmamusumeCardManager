import sqlite3
import os
import shutil

def create_seed_db():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'database', 'umamusume.db')
    seed_path = os.path.join(base_dir, 'database', 'umamusume_seed.db')
    
    if not os.path.exists(db_path):
        print(f"Source database not found: {db_path}")
        return

    print(f"Creating seed database from {db_path}...")
    shutil.copy2(db_path, seed_path)
    
    conn = sqlite3.connect(seed_path)
    cur = conn.cursor()
    
    # Delete user-specific data
    print("Cleaning user data...")
    cur.execute("DELETE FROM owned_cards")
    cur.execute("DELETE FROM user_decks")
    cur.execute("DELETE FROM deck_slots")
    
    conn.commit()
    conn.close()
    
    # Optional: Vacuum to reduce size (must be outside transaction)
    conn2 = sqlite3.connect(seed_path)
    conn2.execute("VACUUM")
    conn2.close()
    
    print(f"Success! New seed database created at: {seed_path}")
    print(f"Size: {os.path.getsize(seed_path) / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    create_seed_db()
