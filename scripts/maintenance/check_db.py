import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "umamusume.db")

def check_schema():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("PRAGMA table_info(event_skills)")
        columns = [row[1] for row in cur.fetchall()]
        print(f"Columns in event_skills: {columns}")
        
        cur.execute("SELECT COUNT(*) FROM event_skills")
        count = cur.fetchone()[0]
        print(f"Total skills in event_skills: {count}")
        
        cur.execute("SELECT DISTINCT skill_name FROM event_skills WHERE is_gold = 1 LIMIT 5")
        gold_skills = cur.fetchall()
        print(f"Golden skills samples: {gold_skills}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_schema()
