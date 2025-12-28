import sqlite3
import os

def debug_db():
    db_path = "database/umamusume.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("--- Database Debug ---")
    
    cur.execute("SELECT COUNT(*) FROM support_cards")
    print(f"Total support cards: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM owned_cards")
    owned_count = cur.fetchone()[0]
    print(f"Owned cards count: {owned_count}")

    cur.execute("""
        SELECT oc.card_id, sc.name
        FROM owned_cards oc
        LEFT JOIN support_cards sc ON oc.card_id = sc.card_id
    """)
    rows = cur.fetchall()
    
    print("\nOwned cards details:")
    for card_id, name in rows:
        print(f"  ID: {card_id}, Name: {name}")

    orphaned = [row[0] for row in rows if row[1] is None]
    if orphaned:
        print(f"\nFound {len(orphaned)} orphaned owned cards (Card IDs: {orphaned})")
    else:
        print("\nNo orphaned owned cards found.")

    conn.close()

if __name__ == "__main__":
    debug_db()
