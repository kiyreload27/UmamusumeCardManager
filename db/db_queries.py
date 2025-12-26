"""
Database query functions for Umamusume support cards
"""

import sqlite3
import os
import sys

if getattr(sys, 'frozen', False):
    # In frozen state (exe), we need to ensure the database is in a writable location
    # sys.executable points to the .exe file
    base_dir = os.path.dirname(sys.executable)
    db_dir = os.path.join(base_dir, "database")
    DB_PATH = os.path.join(db_dir, "umamusume.db")
    
    # If database doesn't exist in writable location, copy it from the bundle
    if not os.path.exists(DB_PATH):
        try:
            # sys._MEIPASS is where PyInstaller extracts bundled files
            bundled_db_path = os.path.join(sys._MEIPASS, "database", "umamusume.db")
            
            if os.path.exists(bundled_db_path):
                # Ensure directory exists
                os.makedirs(db_dir, exist_ok=True)
                
                # Copy the file
                import shutil
                shutil.copy2(bundled_db_path, DB_PATH)
        except Exception as e:
            # Fallback or error logging if copy fails
            # If copy fails, we might still try to use the one next to exe or fail gracefully
            pass
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "umamusume.db")

def get_conn():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

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
    """Get all events and their skills for a card"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT se.event_name, es.skill_name
        FROM support_events se
        LEFT JOIN event_skills es ON se.event_id = es.event_id
        WHERE se.card_id = ?
        ORDER BY se.event_name, es.skill_name
    """, (card_id,))
    
    result = {}
    for event_name, skill_name in cur.fetchall():
        if event_name not in result:
            result[event_name] = []
        if skill_name:
            result[event_name].append(skill_name)
    
    conn.close()
    return result

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
    cur.execute("SELECT COUNT(*) FROM owned_cards")
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
    
    cur.execute("SELECT COUNT(*) FROM owned_cards")
    stats['owned_cards'] = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM user_decks")
    stats['saved_decks'] = cur.fetchone()[0]
    
    conn.close()
    return stats
