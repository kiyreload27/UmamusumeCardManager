import sqlite3
import shutil
import os
import sys

# Add parent dir to path to find version.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from version import VERSION

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
SOURCE_DB = os.path.join(DB_DIR, "umamusume.db")
SEED_DB = os.path.join(DB_DIR, "umamusume_seed.db")

def create_seed_db():
    print(f"Source DB: {SOURCE_DB}")
    print(f"Target Seed DB: {SEED_DB}")
    print(f"Injecting Version: {VERSION}")
    
    if not os.path.exists(SOURCE_DB):
        print("Error: Source database not found!")
        return
    
    # Copy file
    print("Copying database...")
    shutil.copy2(SOURCE_DB, SEED_DB)
    
    # Connect to seed DB and wipe user data
    print("Cleaning user data...")
    conn = sqlite3.connect(SEED_DB)
    cur = conn.cursor()
    
    try:
        # Wipe user tables
        cur.execute("DELETE FROM owned_cards")
        cur.execute("DELETE FROM deck_slots")
        cur.execute("DELETE FROM user_decks")
        # Ensure ID sequences reset
        cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('owned_cards', 'user_decks', 'deck_slots')")
        
        # Verify card data remains
        cur.execute("SELECT COUNT(*) FROM support_cards")
        card_count = cur.fetchone()[0]
        print(f"Preserved {card_count} support cards.")
        
        # Add Metadata Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cur.execute("INSERT OR REPLACE INTO system_metadata (key, value) VALUES (?, ?)", ('app_version', VERSION))
        
        conn.commit()
        
        # Optimize size
        print("Vacuuming database...")
        cur.execute("VACUUM")
        
        print("Seed database created successfully!")
        
    except Exception as e:
        print(f"Error cleaning database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_seed_db()
