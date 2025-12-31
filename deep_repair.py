import sqlite3
import os
import sys

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.gametora_scraper import scrape_support_card, sync_playwright
from db.db_queries import DB_PATH, repair_orphaned_data, cleanup_orphaned_data

def deep_repair():
    print("=" * 60)
    print("Umamusume Card Manager - Deep Database Repair")
    print("=" * 60)
    
    # 1. Run basic repair and cleanup
    print("\nStep 1: Cleaning up corrupted records...")
    repair_orphaned_data()
    cleanup_orphaned_data()
    
    # 2. Identify missing data
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT card_id, name, gametora_url 
        FROM support_cards 
        WHERE card_id NOT IN (SELECT DISTINCT card_id FROM support_events)
        AND rarity = 'SSR'
    """)
    ssr_missing = cur.fetchall()
    
    cur.execute("""
        SELECT card_id, name, gametora_url 
        FROM support_cards 
        WHERE card_id NOT IN (SELECT DISTINCT card_id FROM support_events)
        AND rarity != 'SSR'
    """)
    others_missing = cur.fetchall()
    
    total_missing = len(ssr_missing) + len(others_missing)
    if total_missing == 0:
        print("\n✅ No missing data detected. Your database is healthy!")
        conn.close()
        return

    print(f"\nDetected {total_missing} cards with missing event/skill data.")
    print(f"- SSR cards: {len(ssr_missing)}")
    print(f"- SR/R cards: {len(others_missing)}")
    
    print("\nStep 2: Re-scraping missing data from GameTora...")
    print("This may take some time depending on your internet connection.")
    print("Press Ctrl+C to stop at any time.")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # Prioritize SSRs
            to_process = ssr_missing + others_missing
            count = 0
            for card_id, name, url in to_process:
                count += 1
                percent = (count / total_missing) * 100
                print(f"[{count}/{total_missing} - {percent:.1f}%] Repairing: {name}")
                try:
                    scrape_support_card(page, url, conn)
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                
            browser.close()
    except KeyboardInterrupt:
        print("\n⚠️ Repair interrupted by user.")
    except Exception as e:
        print(f"\n❌ A fatal error occurred during scrape: {e}")
    finally:
        conn.close()
        
    print("\n" + "=" * 60)
    print("Repair process finished.")
    print("You can now restart the application.")
    print("=" * 60)

if __name__ == "__main__":
    deep_repair()
