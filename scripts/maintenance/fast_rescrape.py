import sqlite3
import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.gametora_scraper import scrape_support_card, sync_playwright

DB_PATH = os.path.join("database", "umamusume.db")

def fast_rescrape():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Find cards that have NO events
    cur.execute("""
        SELECT card_id, name, gametora_url 
        FROM support_cards 
        WHERE card_id NOT IN (SELECT DISTINCT card_id FROM support_events)
        AND rarity = 'SSR'
    """)
    cards_to_rescrape = cur.fetchall()
    
    print(f"Found {len(cards_to_rescrape)} SSR cards missing event data.")
    
    if not cards_to_rescrape:
        conn.close()
        return
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        count = 0
        for card_id, name, url in cards_to_rescrape:
            count += 1
            print(f"[{count}/{len(cards_to_rescrape)}] Re-scraping: {name}")
            try:
                # We need to pass the same connection or use a different scraper function
                # The existing scrape_support_card re-inserts the card too.
                # Since we fixed the scraper to use INSERT OR IGNORE, it's safe!
                from scraper.gametora_scraper import scrape_support_card
                scrape_support_card(page, url, conn)
            except Exception as e:
                print(f"  Error: {e}")
            
            if count % 10 == 0:
                print("--- Progress Checkpoint ---")
                
        browser.close()
    
    conn.close()
    print("Fast re-scrape complete.")

if __name__ == "__main__":
    fast_rescrape()
