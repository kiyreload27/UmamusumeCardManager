
import sqlite3
import os
import sys

# Add current dir to path to import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import resolve_image_path

DB_PATH = r"y:\Keith\umamusuma card application\database\umamusume.db"
print(f"Checking DB at: {DB_PATH}")

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT card_id, name, image_path FROM support_cards LIMIT 5")
    rows = cur.fetchall()
    
    print("\nVerifying Path Resolution:")
    for row in rows:
        card_id, name, original_path = row
        resolved = resolve_image_path(original_path)
        exists = os.path.exists(resolved) if resolved else False
        
        print(f"Card: {name}")
        print(f"  Original: {original_path}")
        print(f"  Resolved: {resolved}")
        print(f"  Exists:   {exists}")
        print("-" * 50)
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
