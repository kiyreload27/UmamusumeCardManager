import sqlite3
import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.gametora_scraper import scrape_support_card, sync_playwright
from db.db_queries import get_conn

def test_golden_perk():
    print("Testing Golden Perk Scraping for Fine Motion...")
    url = "https://gametora.com/umamusume/supports/30010-fine-motion"
    
    conn = get_conn()
    cur = conn.cursor()
    
    # 1. Clean previous data for this specific card
    cur.execute("SELECT card_id FROM support_cards WHERE gametora_url = ?", (url,))
    row = cur.fetchone()
    if row:
        card_id = row[0]
        cur.execute("DELETE FROM event_skills WHERE event_id IN (SELECT event_id FROM support_events WHERE card_id = ?)", (card_id,))
        cur.execute("DELETE FROM support_events WHERE card_id = ?", (card_id,))
        conn.commit()
    
    # 2. Scrape
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        success = scrape_support_card(page, url, conn)
        print(f"Scrape success: {success}")
        browser.close()
    
    # 3. Verify results
    cur.execute("""
        SELECT se.event_name, es.skill_name, es.is_gold
        FROM support_events se
        JOIN event_skills es ON se.event_id = es.event_id
        JOIN support_cards sc ON se.card_id = sc.card_id
        WHERE sc.gametora_url = ?
    """, (url,))
    
    skills = cur.fetchall()
    print(f"\nSkills found for Kitasan Black:")
    found_gold = False
    for event_name, skill_name, is_gold in skills:
        status = "✨ GOLD" if is_gold else "Normal"
        print(f"- [{status}] {event_name}: {skill_name}")
        if is_gold: found_gold = True
    
    if found_gold:
        print("\n✅ SUCCESS: Golden Perk identified correctly!")
    else:
        print("\n❌ FAILURE: No golden perks found.")
        
    conn.close()

if __name__ == "__main__":
    test_golden_perk()
