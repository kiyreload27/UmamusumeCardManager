"""
Database initialization module
Creates the SQLite database schema for Umamusume support cards
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "umamusume.db")

def get_conn():
    """Get database connection"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db(reset=False):
    """
    Initialize the database with schema
    
    Args:
        reset: If True, drops all existing tables first
    """
    conn = get_conn()
    cur = conn.cursor()
    
    if reset:
        print("Resetting database...")
        cur.execute("DROP TABLE IF EXISTS deck_slots")
        cur.execute("DROP TABLE IF EXISTS user_decks")
        cur.execute("DROP TABLE IF EXISTS event_skills")
        cur.execute("DROP TABLE IF EXISTS support_events")
        cur.execute("DROP TABLE IF EXISTS support_hints")
        cur.execute("DROP TABLE IF EXISTS support_effects")
        cur.execute("DROP TABLE IF EXISTS owned_cards")
        cur.execute("DROP TABLE IF EXISTS support_cards")
    
    # Support Cards - main card info
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rarity TEXT,
            card_type TEXT,
            max_level INTEGER DEFAULT 50,
            gametora_url TEXT UNIQUE,
            image_path TEXT
        )
    """)
    
    # Effects by level - stores effect values at each level
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_effects (
            effect_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            level INTEGER,
            effect_name TEXT,
            effect_value TEXT,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    # Support Hints - training skills that can be learned
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_hints (
            hint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            hint_name TEXT,
            hint_description TEXT,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    # Training Events
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            event_name TEXT,
            event_type TEXT,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    # Event Skills
    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_skills (
            skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            skill_name TEXT,
            FOREIGN KEY (event_id) REFERENCES support_events(event_id)
        )
    """)
    
    # User's owned cards - which cards the user personally owns
    cur.execute("""
        CREATE TABLE IF NOT EXISTS owned_cards (
            owned_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER UNIQUE,
            level INTEGER DEFAULT 50,
            limit_break INTEGER DEFAULT 0,
            owned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    # User's saved decks
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_decks (
            deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Cards in each deck (6 slots max)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deck_slots (
            slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER,
            card_id INTEGER,
            slot_position INTEGER,
            level INTEGER DEFAULT 50,
            FOREIGN KEY (deck_id) REFERENCES user_decks(deck_id),
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    # Create indexes for better query performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_effects_card_level ON support_effects(card_id, level)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hints_card ON support_hints(card_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_card ON support_events(card_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_type ON support_cards(card_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_rarity ON support_cards(rarity)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_owned_card ON owned_cards(card_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deck_slots ON deck_slots(deck_id)")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def migrate_add_image_path():
    """Add image_path column if it doesn't exist"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE support_cards ADD COLUMN image_path TEXT")
        conn.commit()
        print("Added image_path column")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.close()

if __name__ == "__main__":
    init_db(reset=True)
