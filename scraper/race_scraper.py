"""
GameTora Umamusume Race Scraper
Scrapes all races from the race list page including detail modal data
"""

import sqlite3
import time
import re
import os
import sys
import logging
from datetime import datetime

# Ensure we can import from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from db.db_queries import get_conn, init_database, set_scraper_timestamp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://gametora.com"


def scrape_all_races(page):
    """Scrape all races from the race list page, clicking Details for each"""
    logger.info("Loading race list page...")
    page.goto(f"{BASE_URL}/umamusume/races", timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)  # Extra wait for JS rendering

    # Scroll to load all races (lazy loading)
    logger.info("Scrolling to load all races...")
    for i in range(30):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(400)

    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)
    for i in range(15):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(300)

    # Better approach: Python-driven loop to avoid JS timeouts
    logger.info("Extracting race data...")
    
    # 1. Parse list data first
    list_data = page.evaluate("""
        () => {
            const rows = [];
            const links = Array.from(document.querySelectorAll('a[href*="/umamusume/races/"]'));
            
            links.forEach(link => {
                const href = link.href;
                if (href.endsWith('/races') || href.endsWith('/races/')) return;
                
                const container = link.closest('tr, div[class]');
                if (container) {
                    rows.push({
                        url: href,
                        text: container.innerText.substring(0, 500)
                    });
                }
            });
            return rows;
        }
    """)
    
    # 2. Get locators for all Details buttons
    detail_buttons = page.locator("text='Details'")
    count = detail_buttons.count()
    logger.info(f"Found {count} Details buttons to process")
    
    races = []
    
    for i in range(count):
        try:
            # Scroll to the button and click it
            btn = detail_buttons.nth(i)
            btn.scroll_into_view_if_needed()
            page.wait_for_timeout(100)
            btn.click()
            page.wait_for_timeout(400)  # Wait for modal animation
            
            # Extract data from the modal
            race = page.evaluate("""
                () => {
                    const modals = Array.from(document.querySelectorAll('div[role="dialog"]')).filter(d => {
                        // Find the modal that is visible
                        return d.innerText.length > 20 && d.innerText.length < 3000 && d.offsetParent !== null;
                    });
                    
                    if (modals.length === 0) return null;
                    
                    // If multiple, just take the last one in DOM (usually the active one)
                    const modal = modals[modals.length - 1];
                    
                    const text = modal.innerText;
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                    
                    const race = {
                        name_en: '', name_jp: '', grade: '', racetrack: '',
                        direction: '', participants: null, terrain: '',
                        distance_type: '', distance_meters: null,
                        season: '', time_of_day: '', race_date: '', race_class: ''
                    };
                    
                    for (let j = 0; j < lines.length; j++) {
                        const line = lines[j];
                        const nextLine = j + 1 < lines.length ? lines[j + 1] : '';
                        
                        if (j === 0 && !line.includes(':') && !line.includes('Racetrack')) race.name_jp = line;
                        if (j === 1 && !line.includes(':') && !line.includes('Racetrack')) race.name_en = line;
                        
                        if (line.startsWith('Racetrack')) race.racetrack = line.replace('Racetrack', '').trim() || nextLine;
                        if (line.startsWith('Direction')) race.direction = line.replace('Direction', '').trim() || nextLine;
                        if (line.startsWith('Participants')) {
                            const num = parseInt(line.replace('Participants', '').trim() || nextLine);
                            if (!isNaN(num)) race.participants = num;
                        }
                        if (line.startsWith('Grade')) race.grade = line.replace('Grade', '').trim() || nextLine;
                        if (line.startsWith('Terrain')) race.terrain = line.replace('Terrain', '').trim() || nextLine;
                        
                        if (line.includes('Distance') && line.includes('type')) {
                            race.distance_type = line.replace(/Distance.*?(type\)?)/i, '').trim() || nextLine;
                        }
                        if (line.includes('Distance') && (line.includes('meters') || line.includes('m)'))) {
                            const str = line.replace(/Distance.*?(meters?\)?|m\)?)/i, '').trim() || nextLine;
                            const num = parseInt(str.replace(/[^0-9]/g, ''));
                            if (!isNaN(num)) race.distance_meters = num;
                        }
                        if (line.startsWith('Season')) race.season = line.replace('Season', '').trim() || nextLine;
                        if (line.includes('Time of day') || line.includes('Time of Day')) {
                            race.time_of_day = line.replace(/Time of [Dd]ay/i, '').trim() || nextLine;
                        }
                        // Simple heuristic for Schedule/Date
                        if (line === 'Schedule') {
                            race.race_class = nextLine;
                            if (j + 2 < lines.length) race.race_date = lines[j + 2];
                        }
                    }
                    
                    if (!race.grade) {
                        const match = text.match(/(G[I1]{1,3}|GII|GIII|OP|Pre-OP)/);
                        if (match) race.grade = match[1];
                    }
                    
                    if (!race.distance_meters) {
                        const match = text.match(/(\\d{3,4})\\s*m/);
                        if (match) race.distance_meters = parseInt(match[1]);
                    }
                    
                    if (!race.distance_type && race.distance_meters) {
                        if (race.distance_meters <= 1400) race.distance_type = 'Short';
                        else if (race.distance_meters <= 1800) race.distance_type = 'Mile';
                        else if (race.distance_meters <= 2400) race.distance_type = 'Medium';
                        else race.distance_type = 'Long';
                    }
                    
                    return race;
                }
            """)
            
            if race and (race.get('name_en') or race.get('name_jp') or race.get('racetrack')):
                races.append(race)
                
            # Close the modal
            page.keyboard.press("Escape")
            page.mouse.click(10, 10)  # Click outside just in case
            page.wait_for_timeout(200)
            
            if (i + 1) % 25 == 0:
                logger.info(f"Processed {i + 1}/{count} races")
                
        except Exception as e:
            logger.warning(f"Error scraping race {i}: {e}")
            # Ensure modal is closed before continuing
            page.keyboard.press("Escape")
            page.wait_for_timeout(100)

    logger.info(f"Scraped {len(races)} races from details, {len(list_data)} from list")
    return races, list_data


def save_races_to_db(conn, races):
    """Save all races to the database"""
    cur = conn.cursor()
    added = 0
    updated = 0

    for race in races:
        name_en = race.get('name_en', '').strip()
        name_jp = race.get('name_jp', '').strip()

        # Generate a unique URL-like key for deduplication
        key = f"{name_en}_{name_jp}_{race.get('distance_meters', '')}_{race.get('racetrack', '')}"
        gametora_url = f"gametora://race/{key}"

        try:
            cur.execute("""
                INSERT INTO races (name_en, name_jp, grade, racetrack, direction,
                                   participants, terrain, distance_type, distance_meters,
                                   season, time_of_day, race_date, race_class, gametora_url, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(gametora_url) DO UPDATE SET
                    name_en = COALESCE(?, name_en),
                    name_jp = COALESCE(?, name_jp),
                    grade = COALESCE(?, grade),
                    racetrack = COALESCE(?, racetrack),
                    direction = COALESCE(?, direction),
                    participants = COALESCE(?, participants),
                    terrain = COALESCE(?, terrain),
                    distance_type = COALESCE(?, distance_type),
                    distance_meters = COALESCE(?, distance_meters),
                    season = COALESCE(?, season),
                    time_of_day = COALESCE(?, time_of_day),
                    race_date = COALESCE(?, race_date),
                    race_class = COALESCE(?, race_class),
                    is_active = 1
            """, (
                name_en, name_jp, race.get('grade', ''), race.get('racetrack', ''),
                race.get('direction', ''), race.get('participants'),
                race.get('terrain', ''), race.get('distance_type', ''),
                race.get('distance_meters'), race.get('season', ''),
                race.get('time_of_day', ''), race.get('race_date', ''),
                race.get('race_class', ''), gametora_url,
                # ON CONFLICT values:
                name_en or None, name_jp or None, race.get('grade') or None,
                race.get('racetrack') or None, race.get('direction') or None,
                race.get('participants'), race.get('terrain') or None,
                race.get('distance_type') or None, race.get('distance_meters'),
                race.get('season') or None, race.get('time_of_day') or None,
                race.get('race_date') or None, race.get('race_class') or None,
            ))
            added += 1
        except Exception as e:
            logger.warning(f"  Error saving race '{name_en}': {e}")
            updated += 1

    conn.commit()
    return added, updated


def run_race_scraper():
    """Main entry point: scrape all races"""
    print("=" * 60)
    print("GameTora Umamusume Race Scraper")
    print("=" * 60)

    # Initialize database (additive only — safe for existing data)
    logger.info("Initializing database (additive tables only)...")
    init_database()

    conn = get_conn()

    with sync_playwright() as p:
        logger.info("Launching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Scrape all races
        races, list_data = scrape_all_races(page)

        if not races:
            logger.warning("No races found from Details buttons. Trying alternative approach...")
            # The modal approach might not work perfectly, but we still have the list data
            print(f"  List data entries: {len(list_data)}")

        browser.close()

    if races:
        print(f"\nSaving {len(races)} races to database...")
        added, updated = save_races_to_db(conn, races)
    else:
        added, updated = 0, 0

    # Update scraper timestamp
    set_scraper_timestamp('races', datetime.now().isoformat())

    conn.close()

    # Print summary
    print("\n" + "=" * 60)
    print("Race Scraping Complete!")
    print(f"  Races saved:    {added}")
    print(f"  Errors:         {updated}")
    print("=" * 60)


if __name__ == "__main__":
    run_race_scraper()
