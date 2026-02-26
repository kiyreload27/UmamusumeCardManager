"""
Database query functions for Umamusume support cards
"""

import sqlite3
import os
import sys

import shutil

if getattr(sys, 'frozen', False):
    # In frozen state (exe), we need to ensure the database is in a writable location
    # sys.executable points to the .exe file
    base_dir = os.path.dirname(sys.executable)
    db_dir = os.path.join(base_dir, "database")
    DB_PATH = os.path.join(db_dir, "umamusume.db")
    
    # Function to check if DB needs seed data (only if totally empty of master data)
    def is_db_empty(path):
        try:
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            
            # Check cards - this is our primary indicator of master data
            cur.execute("SELECT COUNT(*) FROM support_cards")
            card_count = cur.fetchone()[0]
            
            conn.close()
            # ONLY overwrite if we have no card data at all. 
            # If we have cards but no tracks, we are an "old" user and should NOT be overwritten.
            return card_count == 0
        except:
            return True

    # Check state: Missing OR Empty
    should_copy_seed = False
    if not os.path.exists(DB_PATH):
        should_copy_seed = True
    elif is_db_empty(DB_PATH):
        # exists but empty - overwrite it
        should_copy_seed = True
        
    if should_copy_seed:
        try:
            # Ensure directory exists
            os.makedirs(db_dir, exist_ok=True)
            
            # Check for bundled seed database
            bundled_seed_path = os.path.join(sys._MEIPASS, "database", "umamusume_seed.db")
            
            if os.path.exists(bundled_seed_path):
                # Copy seed database to user location (overwrite if exists)
                shutil.copy2(bundled_seed_path, DB_PATH)
            # Else: will be initialized by get_conn -> init_database
            
        except Exception as e:
            pass
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "umamusume.db")

# Add VERSION import
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
try:
    from version import VERSION
except ImportError:
    VERSION = "2.1.0" # Fallback

_updates_checked = False

def get_conn():
    """Get database connection"""
    global _updates_checked
    
    # Initialize if missing
    if not os.path.exists(DB_PATH):
        init_database()
    
    # Check for updates and migrate if needed (only once per session)
    if not _updates_checked:
        _updates_checked = True
        run_migrations()
        check_for_updates()
        
    return sqlite3.connect(DB_PATH)

def run_migrations():
    """Ensure database schema is up to date by adding missing columns"""
    print("Checking for database migrations...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Add is_gold to event_skills
    try:
        cur.execute("ALTER TABLE event_skills ADD COLUMN is_gold INTEGER DEFAULT 0")
        print("Added is_gold column to event_skills")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    # 2. Add is_or to event_skills
    try:
        cur.execute("ALTER TABLE event_skills ADD COLUMN is_or INTEGER DEFAULT 0")
        print("Added is_or column to event_skills")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # 3. Add image_path to support_cards
    try:
        cur.execute("ALTER TABLE support_cards ADD COLUMN image_path TEXT")
        print("Added image_path column to support_cards")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    # 4. Add map_image_path to courses
    try:
        cur.execute("ALTER TABLE courses ADD COLUMN map_image_path TEXT")
        print("Added map_image_path column to courses")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    conn.commit()
    repair_image_paths(conn)
    conn.close()

def repair_image_paths(conn):
    """Attempt to populate missing image_path for existing cards in old databases"""
    print("Checking for missing image paths to repair...")
    cur = conn.cursor()
    
    # Find cards with missing image paths but have a URL
    cur.execute("SELECT card_id, name, gametora_url FROM support_cards WHERE image_path IS NULL OR image_path = ''")
    to_repair = cur.fetchall()
    
    if not to_repair:
        return
        
    import re
    repaired_count = 0
    
    for card_id, name, url in to_repair:
        if not url: continue
        
        # Extract ID from URL (e.g., 30154 from .../supports/30154-mejiro-ramonu)
        match = re.search(r'/supports/(\d+)-', url)
        if match:
            stable_id = match.group(1)
            # Create safe filename matching scraper logic
            safe_name = re.sub(r'[<>:"/\\\\|?*]', '_', name)
            filename = f"{stable_id}_{safe_name}.png"
            
            # Update DB with images/filename
            cur.execute("UPDATE support_cards SET image_path = ? WHERE card_id = ?", 
                       (f"images/{filename}", card_id))
            repaired_count += 1
            
    if repaired_count > 0:
        conn.commit()
        print(f"Successfully repaired {repaired_count} image paths!")

def check_for_updates():
    """Check if database version matches app version, sync if outdated"""
    if getattr(sys, 'frozen', False):
        bundled_seed_path = os.path.join(sys._MEIPASS, "database", "umamusume_seed.db")
        if not os.path.exists(bundled_seed_path):
            return 
            
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            # Check for metadata table
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_metadata'")
            if not cur.fetchone():
                # No metadata, likely old version. Create it.
                cur.execute("CREATE TABLE IF NOT EXISTS system_metadata (key TEXT PRIMARY KEY, value TEXT)")
                cur.execute("INSERT OR REPLACE INTO system_metadata (key, value) VALUES (?, ?)", ('app_version', "0.0.0"))
                conn.commit()
                db_version = "0.0.0"
            else:
                cur.execute("SELECT value FROM system_metadata WHERE key='app_version'")
                row = cur.fetchone()
                db_version = row[0] if row else "0.0.0"
            
            conn.close()
            
            # Compare versions (simple string compare works for semver if zero-padded, but valid enough here)
            # Or just check inequality. If different, try to update.
            if db_version != VERSION:
                sync_from_seed(bundled_seed_path)
            
            # Always ensure data integrity
            repair_orphaned_data()
            cleanup_orphaned_data()
                
        except Exception as e:
            import traceback
            print(f"Update check failed: {e}\n{traceback.format_exc()}")

def sync_from_seed(seed_path):
    """Merge new data from seed into user database"""
    print(f"Syncing database from {seed_path}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Attach seed database
        cur.execute("ATTACH DATABASE ? AS seed", (seed_path,))
        
        # 1. Insert New Cards (match by gametora_url)
        # We assume gametora_url is unique and stable
        cur.execute("""
            INSERT INTO main.support_cards (name, rarity, card_type, max_level, gametora_url, image_path)
            SELECT name, rarity, card_type, max_level, gametora_url, image_path
            FROM seed.support_cards
            WHERE gametora_url NOT IN (SELECT gametora_url FROM main.support_cards)
        """)
        
        # 2. Sync Child Tables
        # Since effects/hints/events don't have stable IDs, we wipe and re-import them for ALL cards.
        # But we must map seed_card_id to main_card_id.
        
        # First, ensure we don't break foreign keys temporarily
        cur.execute("PRAGMA foreign_keys = OFF")
        
        # Tracks and courses are master data, sync them completely
        # Delete courses first due to foreign key
        cur.execute("DELETE FROM main.courses")
        cur.execute("DELETE FROM main.tracks")
        
        tables_to_sync = ['support_effects', 'support_hints', 'support_events', 'event_skills']
        for table in tables_to_sync:
            cur.execute(f"DELETE FROM main.{table}")
            
        # Migrate Support Effects
        # Map: seed.card_id -> gametora_url -> main.card_id
        cur.execute("""
            INSERT INTO main.support_effects (card_id, level, effect_name, effect_value)
            SELECT m.card_id, s.level, s.effect_name, s.effect_value
            FROM seed.support_effects s
            JOIN seed.support_cards sc ON s.card_id = sc.card_id
            JOIN main.support_cards m ON sc.gametora_url = m.gametora_url
        """)
        
        # Migrate Support Hints
        cur.execute("""
            INSERT INTO main.support_hints (card_id, hint_name, hint_description)
            SELECT m.card_id, s.hint_name, s.hint_description
            FROM seed.support_hints s
            JOIN seed.support_cards sc ON s.card_id = sc.card_id
            JOIN main.support_cards m ON sc.gametora_url = m.gametora_url
        """)
        
        # Migrate Support Events
        # We need to preserve event_id mapping for event_skills? 
        # Actually no, we deleted event_skills too.
        # But we need to insert events first to get new IDs, then insert skills linking to those new IDs?
        # That's tricky in SQL. 
        # Easier: Insert events, then resolving event_id is hard without a map.
        # Alternative: Just copy the tables matching on card_id if we assume card_ids are consistent?
        # If user has same cards as seed, IDs might be consistent.
        # But if we added a card in the middle, IDs shift.
        # Let's assume we can just drop event/skills for now or try to match them.
        # The logic below is complex for events+skills because of the 2-level hierarchy.
        
        # Strategy for Events/Skills:
        # Since we just deleted them, we can re-insert.
        # But main.event_id will be auto-incremented.
        # We need to insert event, get ID, then insert skill? No, bulk insert.
        # We can't easily map seed.event_id to main.event_id in bulk SQL across DBs easily without a temp table.
        
        # Simplified Approach for Events/Skills:
        # Iterate in Python? Slower but safer.
        pass # Placeholder for python logic below
        
        # Update Version
        cur.execute("INSERT OR REPLACE INTO system_metadata (key, value) VALUES (?, ?)", ('app_version', VERSION))
        
        conn.commit()
        
        # Python Logic for Events/Skills
        # Fetch all events from seed with their card's gametora_url
        cur.execute("""
            SELECT sc.gametora_url, se.event_name, se.event_type, se.event_id
            FROM seed.support_events se
            JOIN seed.support_cards sc ON se.card_id = sc.card_id
        """)
        seed_events = cur.fetchall()
        
        # Prepare Skill map: seed_event_id -> list of (skill_name, is_gold, is_or)
        cur.execute("SELECT event_id, skill_name, is_gold, is_or FROM seed.event_skills")
        seed_skills = {}
        for ev_id, sk_name, is_gold, is_or in cur.fetchall():
            if ev_id not in seed_skills: seed_skills[ev_id] = []
            seed_skills[ev_id].append((sk_name, is_gold, is_or))
            
        # Main Card Map: gametora_url -> main_card_id
        cur.execute("SELECT gametora_url, card_id FROM main.support_cards")
        url_to_main_id = dict(cur.fetchall())
        
        for url, ev_name, ev_type, seed_ev_id in seed_events:
            if url in url_to_main_id:
                main_card_id = url_to_main_id[url]
                # Insert Event
                cur.execute("INSERT INTO main.support_events (card_id, event_name, event_type) VALUES (?, ?, ?)", 
                            (main_card_id, ev_name, ev_type))
                new_event_id = cur.lastrowid
                
                # Insert Skills
                if seed_ev_id in seed_skills:
                    for sk_name, is_gold, is_or in seed_skills[seed_ev_id]:
                        cur.execute("INSERT INTO main.event_skills (event_id, skill_name, is_gold, is_or) VALUES (?, ?, ?, ?)",
                                    (new_event_id, sk_name, is_gold, is_or))

        # Sync Tracks
        cur.execute("""
            INSERT INTO main.tracks (track_id, name, location, image_path, image_url, gametora_url, is_active)
            SELECT track_id, name, location, image_path, image_url, gametora_url, is_active
            FROM seed.tracks
        """)
        
        # Sync Courses
        cur.execute("""
            INSERT INTO main.courses (course_id, track_id, distance, surface, direction, corner_count, 
                                     final_straight_length, slope_info, weather_data, phases_json, 
                                     corners_json, straights_json, other_json, raw_metadata_json, 
                                     gametora_url, map_image_path, is_active)
            SELECT course_id, track_id, distance, surface, direction, corner_count, 
                   final_straight_length, slope_info, weather_data, phases_json, 
                   corners_json, straights_json, other_json, raw_metadata_json, 
                   gametora_url, map_image_path, is_active
            FROM seed.courses
        """)

        cur.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        conn.close()
        print(f"Database sync complete. Updated to version {VERSION}")
        
    except Exception as e:
        print(f"Sync failed: {e}")

def init_database():
    """Initialize fresh database with schema"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create tables
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
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_hints (
            hint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            hint_name TEXT,
            hint_description TEXT,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            event_name TEXT,
            event_type TEXT,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_skills (
            skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            skill_name TEXT,
            is_gold INTEGER DEFAULT 0,
            is_or INTEGER DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES support_events(event_id)
        )
    """)
    
    # Run migrations to ensure all columns exist
    run_migrations()
    
    # User tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS owned_cards (
            owned_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER UNIQUE,
            level INTEGER DEFAULT 50,
            limit_break INTEGER DEFAULT 0,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_decks (
            deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
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
    
    # ── Track tables (additive only — no existing tables modified) ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            track_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            location TEXT,
            image_path TEXT,
            image_url TEXT,
            gametora_url TEXT UNIQUE,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            course_id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER,
            distance INTEGER,
            surface TEXT,
            direction TEXT,
            corner_count INTEGER,
            final_straight_length TEXT,
            slope_info TEXT,
            weather_data TEXT,
            phases_json TEXT,
            corners_json TEXT,
            straights_json TEXT,
            other_json TEXT,
            raw_metadata_json TEXT,
            gametora_url TEXT UNIQUE,
            map_image_path TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scraper_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scraper_type TEXT UNIQUE,
            last_run_timestamp TEXT
        )
    """)
    
    # Create indexes for performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_effects_card_level ON support_effects(card_id, level)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hints_card ON support_hints(card_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_card ON support_events(card_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_courses_track ON courses(track_id)")
    
    conn.commit()
    conn.close()

# ============================================
# Card Queries
# ============================================

def get_all_cards(rarity_filter=None, type_filter=None, search_term=None, owned_only=False):
    """
    Get all support cards with optional filtering
    """
    conn = get_conn()
    cur = conn.cursor()
    
    query = """
        SELECT sc.card_id, sc.name, sc.rarity, sc.card_type, sc.max_level, sc.image_path,
               CASE WHEN oc.card_id IS NOT NULL THEN 1 ELSE 0 END as is_owned,
               oc.level as owned_level
        FROM support_cards sc
        LEFT JOIN owned_cards oc ON sc.card_id = oc.card_id
        WHERE 1=1
    """
    params = []
    
    if rarity_filter:
        query += " AND sc.rarity = ?"
        params.append(rarity_filter)
    
    if type_filter:
        query += " AND sc.card_type = ?"
        params.append(type_filter)
    
    if search_term:
        query += " AND sc.name LIKE ?"
        params.append(f"%{search_term}%")
    
    if owned_only:
        query += " AND oc.card_id IS NOT NULL"
    
    query += " ORDER BY sc.rarity DESC, sc.name"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_card_by_id(card_id):
    """Get a single card by ID"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT sc.card_id, sc.name, sc.rarity, sc.card_type, sc.max_level, sc.gametora_url, sc.image_path,
               CASE WHEN oc.card_id IS NOT NULL THEN 1 ELSE 0 END as is_owned,
               oc.level as owned_level
        FROM support_cards sc
        LEFT JOIN owned_cards oc ON sc.card_id = oc.card_id
        WHERE sc.card_id = ?
    """, (card_id,))
    row = cur.fetchone()
    conn.close()
    return row

def get_card_count():
    """Get total number of cards in database"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM support_cards")
    count = cur.fetchone()[0]
    conn.close()
    return count

# ============================================
# Effect Queries
# ============================================

def get_effects_at_level(card_id, level):
    """Get all effects for a card at a specific level"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT effect_name, effect_value
        FROM support_effects
        WHERE card_id = ? AND level = ?
        ORDER BY effect_name
    """, (card_id, level))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_effects(card_id):
    """Get all effects for a card at all levels"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT level, effect_name, effect_value
        FROM support_effects
        WHERE card_id = ?
        ORDER BY level, effect_name
    """, (card_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_unique_effect_names(card_id):
    """Get list of unique effect names for a card"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT effect_name
        FROM support_effects
        WHERE card_id = ?
        ORDER BY effect_name
    """, (card_id,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def search_owned_effects(search_term):
    """
    Search for effects among owned cards.
    Returns list of (card_id, card_name, image_path, effect_name, effect_value, level)
    """
    conn = get_conn()
    cur = conn.cursor()
    
    # We need to join support_effects with owned_cards to get the level
    # But wait, owned_cards has a level column. support_effects stores effects for specific levels.
    # So we need to match support_effects.level with owned_cards.level
    # OR find the effect for the closest level <= owned level (if effects aren't stored for every single level)
    # The current DB schema seems to store effects for specific levels (1, 5, 10, ...).
    # If a card is level 49, `get_effects_at_level` usually queries for exact level match.
    # Let's check `get_effects_at_level` implementation: "WHERE card_id = ? AND level = ?"
    # So if I have a card at level 49, and effects are only defined at 45 and 50, query for 49 returns nothing?
    # That would be a bug or assumption in the current app.
    # Let's look at `update_progression_table` in `effects_view.py`. It does some "nearest level" logic.
    # For this search feature, to be robust, we should probably fetch ALL effects for the card
    # and filter for the one active at the owned level.
    # OR, assuming the scraper/DB populates "current" effects effectively.
    # Actually, the most robust way in SQL for "value at level X" given sparse data is complex.
    # However, let's assume for now we want exact matches or we'll handle the "effective level" logic in Python?
    # No, that's too slow for search.
    # Let's look at how `get_effects_at_level` is used.
    # It is used in `update_current_effects` with `self.level_var.get()`.
    # It expects an exact match.
    # So we should probably join on `oc.level`.
    
    query = """
        SELECT sc.card_id, sc.name, sc.image_path, se.effect_name, se.effect_value, oc.level
        FROM owned_cards oc
        JOIN support_cards sc ON oc.card_id = sc.card_id
        JOIN support_effects se ON oc.card_id = se.card_id AND oc.level = se.level
        WHERE se.effect_name LIKE ?
        ORDER BY sc.name
    """
    
    cur.execute(query, (f"%{search_term}%",))
    rows = cur.fetchall()
    conn.close()
    return rows

# ============================================
# Hint Queries
# ============================================

def get_hints(card_id):
    """Get all hints for a card"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT hint_name, hint_description
        FROM support_hints
        WHERE card_id = ?
        ORDER BY hint_name
    """, (card_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ============================================
# Event Queries
# ============================================

def get_events(card_id):
    """Get all events for a card"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT event_id, event_name, event_type
        FROM support_events
        WHERE card_id = ?
        ORDER BY event_name
    """, (card_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_event_skills(card_id):
    """Get all skills from training events for a card"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT se.event_name, es.skill_name, es.is_gold, es.is_or
        FROM support_events se
        JOIN event_skills es ON se.event_id = es.event_id
        WHERE se.card_id = ?
    """, (card_id,))
    
    # Group by event
    events = {}
    for event_name, skill_name, is_gold, is_or in cur.fetchall():
        if event_name not in events:
            events[event_name] = {'skills': [], 'or_skills': []}
        
        prefix = "✨ " if is_gold else ""
        if is_or:
            events[event_name]['or_skills'].append(f"{prefix}{skill_name}")
        else:
            events[event_name]['skills'].append(f"{prefix}{skill_name}")
            
    results = []
    for event_name, data in events.items():
        event_skills = []
        if data['or_skills']:
            event_skills.append(" (OR) ".join(data['or_skills']))
        event_skills.extend(data['skills'])
        
        details = f"({', '.join(event_skills)})" if event_skills else ""
        results.append({
            'card_id': card_id,
            'source': 'Event',
            'skill_name': event_name,
            'details': details
        })
        
    conn.close()
    return results

# ============================================
# Owned Cards (Collection) Queries
# ============================================

def is_card_owned(card_id):
    """Check if a card is owned"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM owned_cards WHERE card_id = ?", (card_id,))
    result = cur.fetchone() is not None
    conn.close()
    return result

def set_card_owned(card_id, owned=True, level=50):
    """Set a card as owned or not owned"""
    conn = get_conn()
    cur = conn.cursor()
    
    if owned:
        cur.execute("""
            INSERT OR REPLACE INTO owned_cards (card_id, level)
            VALUES (?, ?)
        """, (card_id, level))
    else:
        cur.execute("DELETE FROM owned_cards WHERE card_id = ?", (card_id,))
    
    conn.commit()
    conn.close()

def update_owned_card_level(card_id, level):
    """Update the level of an owned card"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE owned_cards SET level = ? WHERE card_id = ?", (level, card_id))
    conn.commit()
    conn.close()

def get_owned_cards():
    """Get all owned cards"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT sc.card_id, sc.name, sc.rarity, sc.card_type, oc.level, sc.image_path
        FROM owned_cards oc
        JOIN support_cards sc ON oc.card_id = sc.card_id
        ORDER BY sc.rarity DESC, sc.name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_owned_count():
    """Get count of owned cards"""
    conn = get_conn()
    cur = conn.cursor()
    # Use JOIN to ensure only valid cards are counted
    cur.execute("""
        SELECT COUNT(*) 
        FROM owned_cards oc
        JOIN support_cards sc ON oc.card_id = sc.card_id
    """)
    count = cur.fetchone()[0]
    conn.close()
    return count

# ============================================
# Deck Queries
# ============================================

def create_deck(name):
    """Create a new deck"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO user_decks (deck_name) VALUES (?)", (name,))
    deck_id = cur.lastrowid
    conn.commit()
    conn.close()
    return deck_id

def get_all_decks():
    """Get all saved decks"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT deck_id, deck_name, created_at FROM user_decks ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_deck(deck_id):
    """Delete a deck and its slots"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM deck_slots WHERE deck_id = ?", (deck_id,))
    cur.execute("DELETE FROM user_decks WHERE deck_id = ?", (deck_id,))
    conn.commit()
    conn.close()

def add_card_to_deck(deck_id, card_id, slot_position, level=50):
    """Add a card to a deck slot"""
    conn = get_conn()
    cur = conn.cursor()
    # Remove existing card in that slot
    cur.execute("DELETE FROM deck_slots WHERE deck_id = ? AND slot_position = ?", (deck_id, slot_position))
    # Add new card
    cur.execute("""
        INSERT INTO deck_slots (deck_id, card_id, slot_position, level)
        VALUES (?, ?, ?, ?)
    """, (deck_id, card_id, slot_position, level))
    conn.commit()
    conn.close()

def remove_card_from_deck(deck_id, slot_position):
    """Remove a card from a deck slot"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM deck_slots WHERE deck_id = ? AND slot_position = ?", (deck_id, slot_position))
    conn.commit()
    conn.close()

def get_deck_cards(deck_id):
    """Get all cards in a deck with their effects"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT ds.slot_position, ds.level, sc.card_id, sc.name, sc.rarity, sc.card_type, sc.image_path
        FROM deck_slots ds
        JOIN support_cards sc ON ds.card_id = sc.card_id
        WHERE ds.deck_id = ?
        ORDER BY ds.slot_position
    """, (deck_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_deck_combined_effects(deck_id):
    """
    Get combined effects for all cards in a deck
    Returns dict: {effect_name: {'total': value, 'breakdown': [(card_name, value), ...]}}
    """
    conn = get_conn()
    cur = conn.cursor()
    
    # Get cards in deck with their levels
    cur.execute("""
        SELECT ds.card_id, ds.level, sc.name
        FROM deck_slots ds
        JOIN support_cards sc ON ds.card_id = sc.card_id
        WHERE ds.deck_id = ?
    """, (deck_id,))
    deck_cards = cur.fetchall()
    
    combined = {}
    
    for card_id, level, card_name in deck_cards:
        # Get effects for this card at this level
        cur.execute("""
            SELECT effect_name, effect_value
            FROM support_effects
            WHERE card_id = ? AND level = ?
        """, (card_id, level))
        
        for effect_name, effect_value in cur.fetchall():
            if effect_name not in combined:
                combined[effect_name] = {'total': 0, 'breakdown': []}
            
            # Parse value (remove % and convert to number)
            try:
                num_value = float(effect_value.replace('%', '').replace('+', ''))
            except:
                num_value = 0
            
            combined[effect_name]['total'] += num_value
            combined[effect_name]['breakdown'].append((card_name, effect_value))
    
    conn.close()
    return combined

# ============================================
# Statistics
# ============================================

def get_database_stats():
    """Get statistics about the database"""
    conn = get_conn()
    cur = conn.cursor()
    
    stats = {}
    
    cur.execute("SELECT COUNT(*) FROM support_cards")
    stats['total_cards'] = cur.fetchone()[0]
    
    cur.execute("SELECT rarity, COUNT(*) FROM support_cards GROUP BY rarity")
    stats['by_rarity'] = dict(cur.fetchall())
    
    cur.execute("SELECT card_type, COUNT(*) FROM support_cards GROUP BY card_type")
    stats['by_type'] = dict(cur.fetchall())
    
    cur.execute("SELECT COUNT(*) FROM support_effects")
    stats['total_effects'] = cur.fetchone()[0]
    
    # Use JOIN to ensure only valid cards are counted
    cur.execute("""
        SELECT COUNT(*) 
        FROM owned_cards oc
        JOIN support_cards sc ON oc.card_id = sc.card_id
    """)
    stats['owned_cards'] = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM user_decks")
    stats['saved_decks'] = cur.fetchone()[0]
    
    conn.close()
    return stats

def repair_orphaned_data():
    """
    Attempt to repair orphaned data where card_id mapping was lost 
    but can be recovered by matching card names or URLs if available.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Check if we have orphans
        cur.execute("SELECT COUNT(*) FROM support_events WHERE card_id NOT IN (SELECT card_id FROM support_cards)")
        orphan_count = cur.fetchone()[0]
        
        if orphan_count > 0:
            print(f"Detected {orphan_count} orphaned training events. Attempting recovery by card name...")
            
            # This is complex because we don't know the name of the card the orphaned event belonged to 
            # UNLESS we can find a previous state. 
            # MOST LIKELY: This happened during a failed sync where card_ids were from the seed.
            # If so, we might not be able to recover without re-scraping.
            pass

        # A more common issue: support_cards duplicated due to INSERT OR REPLACE
        # Let's ensure no duplicates exist based on URL
        cur.execute("SELECT gametora_url, COUNT(*) as c FROM support_cards GROUP BY gametora_url HAVING c > 1")
        dupes = cur.fetchall()
        if dupes:
            print(f"Found {len(dupes)} duplicate card entries. Cleaning up...")
            for url, count in dupes:
                # Keep the one with highest ID (most recent)
                cur.execute("SELECT card_id FROM support_cards WHERE gametora_url = ? ORDER BY card_id DESC", (url,))
                ids = [r[0] for r in cur.fetchall()]
                keep_id = ids[0]
                toss_ids = ids[1:]
                
                # Update references in other tables before deleting
                for table in ['owned_cards', 'deck_slots', 'support_effects', 'support_hints', 'support_events']:
                    cur.execute(f"UPDATE {table} SET card_id = ? WHERE card_id IN ({','.join(['?']*len(toss_ids))})", 
                                [keep_id] + toss_ids)
                
                cur.execute(f"DELETE FROM support_cards WHERE card_id IN ({','.join(['?']*len(toss_ids))})", toss_ids)
            conn.commit()
            
    except Exception as e:
        print(f"Repair failed: {e}")
    finally:
        conn.close()

def cleanup_orphaned_data():
    """Remove references to non-existent cards in user data tables"""
    print("Cleaning up orphaned database records...")
    # Use direct connection to avoid recursion with get_conn()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # 1. Clean owned_cards
        cur.execute("""
            DELETE FROM owned_cards 
            WHERE card_id NOT IN (SELECT card_id FROM support_cards)
        """)
        if cur.rowcount > 0:
            print(f"Removed {cur.rowcount} orphaned owned card records.")
            
        # 2. Clean deck_slots
        cur.execute("""
            DELETE FROM deck_slots 
            WHERE card_id NOT IN (SELECT card_id FROM support_cards)
        """)
        if cur.rowcount > 0:
            print(f"Removed {cur.rowcount} orphaned deck slot records.")
            
        # 3. Clean detail tables
        cur.execute("DELETE FROM support_effects WHERE card_id NOT IN (SELECT card_id FROM support_cards)")
        cur.execute("DELETE FROM support_hints WHERE card_id NOT IN (SELECT card_id FROM support_cards)")
        cur.execute("DELETE FROM support_events WHERE card_id NOT IN (SELECT card_id FROM support_cards)")
        cur.execute("DELETE FROM event_skills WHERE event_id NOT IN (SELECT event_id FROM support_events)")
        
        conn.commit()
    except Exception as e:
        print(f"Cleanup failed: {e}")
    finally:
        conn.close()
# Skill Search Queries
# ============================================

def get_all_unique_skills():
    """Get a sorted list of all unique skills from hints and events, with golden indicator"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get skills from hints
    cur.execute("SELECT DISTINCT hint_name FROM support_hints")
    hint_skills = {row[0] for row in cur.fetchall() if row[0]}
    
    # Get skills from events, marking which are golden
    cur.execute("SELECT DISTINCT skill_name, MAX(is_gold) as is_gold FROM event_skills GROUP BY skill_name")
    event_skills_data = cur.fetchall()
    event_skills = {}
    for skill_name, is_gold in event_skills_data:
        if skill_name:
            event_skills[skill_name] = bool(is_gold)
    
    # Combine and mark golden skills
    all_skills = []
    for skill in sorted(list(hint_skills.union(event_skills.keys()))):
        if skill in event_skills and event_skills[skill]:
            # Mark as golden
            all_skills.append((skill, True))  # (skill_name, is_golden)
        else:
            all_skills.append((skill, False))
    
    conn.close()
    return all_skills

def get_cards_with_skill(skill_name):
    """
    Find all cards that have a specific skill.
    Returns list of dicts:
    {
        'card_id': int,
        'name': str,
        'rarity': str,
        'type': str,
        'image_path': str,
        'source': str ('Hint' or 'Event: [Name]'),
        'details': str (description or event name)
    }
    """
    conn = get_conn()
    cur = conn.cursor()
    
    results = []
    seen_entries = set() # To avoid duplicates if same skill in multiple events
    
    # 1. Check Hints
    cur.execute("""
        SELECT sc.card_id, sc.name, sc.rarity, sc.card_type, sc.image_path, sh.hint_description,
               CASE WHEN oc.card_id IS NOT NULL THEN 1 ELSE 0 END as is_owned
        FROM support_hints sh
        JOIN support_cards sc ON sh.card_id = sc.card_id
        LEFT JOIN owned_cards oc ON sc.card_id = oc.card_id
        WHERE sh.hint_name = ?
    """, (skill_name,))
    
    for row in cur.fetchall():
        entry_key = (row[0], 'Hint')
        if entry_key not in seen_entries:
            results.append({
                'card_id': row[0],
                'name': row[1] or 'Unknown',
                'rarity': row[2] or 'Unknown',
                'type': row[3] or 'Unknown',  # Also include 'card_type' for compatibility
                'card_type': row[3] or 'Unknown',
                'image_path': row[4],
                'source': 'Training Hint',
                'details': row[5] or "Random hint event",
                'is_owned': bool(row[6])
            })
            seen_entries.add(entry_key)
            
    # 2. Check Event Skills (including golden perks)
    cur.execute("""
        SELECT sc.card_id, sc.name, sc.rarity, sc.card_type, sc.image_path, se.event_name, se.event_id,
               CASE WHEN oc.card_id IS NOT NULL THEN 1 ELSE 0 END as is_owned,
               es.is_gold
        FROM event_skills es
        JOIN support_events se ON es.event_id = se.event_id
        JOIN support_cards sc ON se.card_id = sc.card_id
        LEFT JOIN owned_cards oc ON sc.card_id = oc.card_id
        WHERE es.skill_name = ?
    """, (skill_name,))
    
    rows = cur.fetchall()
    for row in rows:
        card_id, name, rarity, card_type, image_path, event_name, event_id, is_owned, is_gold = row
        event_name = event_name.replace('\n', ' ').strip()
        
        # Format event skills (handle OR groups and gold skills)
        formatted_event_skills = []
        cur.execute("""
            SELECT skill_name, is_gold, is_or 
            FROM event_skills 
            WHERE event_id = ?
        """, (event_id,))
        
        skills_data = cur.fetchall()
        
        or_group_skills = []
        other_event_skills = []
        
        for s_name, s_is_gold, s_is_or in skills_data:
            prefix = "✨ " if s_is_gold else ""
            if s_is_or:
                or_group_skills.append(f"{prefix}{s_name}")
            else:
                other_event_skills.append(f"{prefix}{s_name}")
        
        if or_group_skills:
            formatted_event_skills.append(" (OR) ".join(or_group_skills))
        formatted_event_skills.extend(other_event_skills)
        
        # Create a nice string like "Event Name (Skill1, Skill2)"
        if formatted_event_skills:
            details = f"{event_name} ({', '.join(formatted_event_skills)})"
        elif event_name:
            details = f"{event_name} (Golden Perk)"
        else:
            details = "Golden Perk Event"
        
        # Mark source as GOLDEN if this is a golden skill
        source = "✨ GOLDEN Event" if is_gold else "Event"
        
        entry_key = (card_id, f'Event: {event_name}')
        
        if entry_key not in seen_entries:
            results.append({
                'card_id': card_id,
                'name': name or 'Unknown',
                'rarity': rarity or 'Unknown',
                'type': card_type or 'Unknown',  # Also include 'card_type' for compatibility
                'card_type': card_type or 'Unknown',
                'image_path': image_path,
                'source': source,
                'details': details or 'No details available',
                'is_owned': bool(is_owned),
                'is_gold': bool(is_gold)
            })
            seen_entries.add(entry_key)
    
    conn.close()
    
    # Sort by Rarity (SSR first), then Name
    rarity_map = {'SSR': 3, 'SR': 2, 'R': 1}
    results.sort(key=lambda x: (rarity_map.get(x['rarity'], 0), x['name']), reverse=True)
    
    return results

# ============================================
# Track Queries
# ============================================

def get_all_tracks():
    """Get all active tracks"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT t.track_id, t.name, t.location, t.image_path,
                   COUNT(c.course_id) as course_count
            FROM tracks t
            LEFT JOIN courses c ON t.track_id = c.track_id AND c.is_active = 1
            WHERE t.is_active = 1
            GROUP BY t.track_id
            ORDER BY t.name
        """)
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []  # Table doesn't exist yet
    conn.close()
    return rows

def get_track_courses(track_id):
    """Get all active courses for a track"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT course_id, distance, surface, direction, corner_count,
                   final_straight_length
            FROM courses
            WHERE track_id = ? AND is_active = 1
            ORDER BY surface, distance
        """, (track_id,))
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return rows

def get_course_detail(course_id):
    """Get full course detail including JSON metadata"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.course_id, c.distance, c.surface, c.direction,
                   c.corner_count, c.final_straight_length, c.slope_info,
                   c.weather_data, c.phases_json, c.corners_json,
                   c.straights_json, c.other_json, c.raw_metadata_json,
                   c.map_image_path, t.name as track_name
            FROM courses c
            JOIN tracks t ON c.track_id = t.track_id
            WHERE c.course_id = ?
        """, (course_id,))
        row = cur.fetchone()
    except sqlite3.OperationalError:
        row = None
    conn.close()
    return row

def get_scraper_timestamp(scraper_type):
    """Get last run timestamp for a scraper type"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT last_run_timestamp FROM scraper_meta WHERE scraper_type = ?", (scraper_type,))
        row = cur.fetchone()
        result = row[0] if row else None
    except sqlite3.OperationalError:
        result = None
    conn.close()
    return result

def set_scraper_timestamp(scraper_type, timestamp):
    """Set last run timestamp for a scraper type"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO scraper_meta (scraper_type, last_run_timestamp)
            VALUES (?, ?)
            ON CONFLICT(scraper_type) DO UPDATE SET last_run_timestamp = ?
        """, (scraper_type, timestamp, timestamp))
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()
