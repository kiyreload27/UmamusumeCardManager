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

    # First, extract basic info for all races from the list view
    logger.info("Extracting race data from page...")
    races = page.evaluate("""
        async () => {
            const races = [];
            
            // Find all "Details" buttons/links on the page
            const detailButtons = Array.from(document.querySelectorAll('button, a, div')).filter(el => {
                const text = el.textContent.trim();
                return text === 'Details' && el.children.length === 0;
            });
            
            console.log('Found ' + detailButtons.length + ' Details buttons');
            
            for (let idx = 0; idx < detailButtons.length; idx++) {
                const btn = detailButtons[idx];
                
                try {
                    // Scroll into view and click
                    btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                    await new Promise(r => setTimeout(r, 200));
                    btn.click();
                    await new Promise(r => setTimeout(r, 800));
                    
                    // Find the modal/popup that appeared
                    const modals = Array.from(document.querySelectorAll('div')).filter(d => {
                        const style = window.getComputedStyle(d);
                        const zIndex = parseInt(style.zIndex) || 0;
                        return zIndex > 50 && d.innerText.length > 20 && d.innerText.length < 3000;
                    });
                    
                    if (modals.length > 0) {
                        // Get the topmost modal
                        const modal = modals.sort((a, b) => {
                            const zA = parseInt(window.getComputedStyle(a).zIndex) || 0;
                            const zB = parseInt(window.getComputedStyle(b).zIndex) || 0;
                            return zB - zA;
                        })[0];
                        
                        const modalText = modal.innerText;
                        const lines = modalText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                        
                        const race = {
                            name_en: '',
                            name_jp: '',
                            grade: '',
                            racetrack: '',
                            direction: '',
                            participants: null,
                            terrain: '',
                            distance_type: '',
                            distance_meters: null,
                            season: '',
                            time_of_day: '',
                            race_date: '',
                            race_class: ''
                        };
                        
                        // Parse modal content - look for key-value pairs
                        for (let i = 0; i < lines.length; i++) {
                            const line = lines[i];
                            const nextLine = i + 1 < lines.length ? lines[i + 1] : '';
                            
                            // Try to extract race names from first few lines
                            if (i === 0 && !line.includes(':') && !line.includes('Racetrack')) {
                                race.name_jp = line;
                            }
                            if (i === 1 && !line.includes(':') && !line.includes('Racetrack')) {
                                race.name_en = line;
                            }
                            
                            // Key-value parsing
                            if (line.startsWith('Racetrack') || line === 'Racetrack') {
                                // Value might be on next line or after the label
                                const val = line.replace('Racetrack', '').trim();
                                race.racetrack = val || nextLine;
                            }
                            if (line.startsWith('Direction') || line === 'Direction') {
                                const val = line.replace('Direction', '').trim();
                                race.direction = val || nextLine;
                            }
                            if (line.startsWith('Participants') || line === 'Participants') {
                                const val = line.replace('Participants', '').trim();
                                const numStr = val || nextLine;
                                const num = parseInt(numStr);
                                if (!isNaN(num)) race.participants = num;
                            }
                            if (line.startsWith('Grade') || line === 'Grade') {
                                const val = line.replace('Grade', '').trim();
                                race.grade = val || nextLine;
                            }
                            if (line.startsWith('Terrain') || line === 'Terrain') {
                                const val = line.replace('Terrain', '').trim();
                                race.terrain = val || nextLine;
                            }
                            if (line.includes('Distance') && (line.includes('type') || line.includes('(type)'))) {
                                const val = line.replace(/Distance.*?(type\)?)/i, '').trim();
                                race.distance_type = val || nextLine;
                            }
                            if (line.includes('Distance') && (line.includes('meters') || line.includes('(meters)') || line.includes('(m)'))) {
                                const val = line.replace(/Distance.*?(meters?\)?|m\)?)/i, '').trim();
                                const numStr = val || nextLine;
                                const num = parseInt(numStr.replace(/[^0-9]/g, ''));
                                if (!isNaN(num)) race.distance_meters = num;
                            }
                            if (line.startsWith('Season') || line === 'Season') {
                                const val = line.replace('Season', '').trim();
                                race.season = val || nextLine;
                            }
                            if (line.includes('Time of day') || line.includes('Time of Day') || line === 'Time of day') {
                                const val = line.replace(/Time of [Dd]ay/, '').trim();
                                race.time_of_day = val || nextLine;
                            }
                        }
                        
                        // Also try to get grade from badges/icons in modal
                        if (!race.grade) {
                            const gradeMatch = modalText.match(/(G[I1]{1,3}|GII|GIII|OP|Pre-OP)/);
                            if (gradeMatch) race.grade = gradeMatch[1];
                        }
                        
                        // Get distance if not yet found
                        if (!race.distance_meters) {
                            const distMatch = modalText.match(/(\d{3,4})\s*m/);
                            if (distMatch) race.distance_meters = parseInt(distMatch[1]);
                        }
                        
                        // Get distance type if not yet found
                        if (!race.distance_type) {
                            if (race.distance_meters) {
                                if (race.distance_meters <= 1400) race.distance_type = 'Short';
                                else if (race.distance_meters <= 1800) race.distance_type = 'Mile';
                                else if (race.distance_meters <= 2400) race.distance_type = 'Medium';
                                else race.distance_type = 'Long';
                            }
                        }
                        
                        // Only add if we got meaningful data
                        if (race.name_en || race.name_jp || race.racetrack) {
                            races.push(race);
                        }
                    }
                    
                    // Close the modal
                    document.body.click();
                    await new Promise(r => setTimeout(r, 300));
                    
                    // Also try pressing Escape
                    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                    await new Promise(r => setTimeout(r, 200));
                    
                } catch (err) {
                    console.log('Error scraping race ' + idx + ': ' + err.message);
                }
                
                // Progress logging
                if ((idx + 1) % 25 === 0) {
                    console.log('Processed ' + (idx + 1) + '/' + detailButtons.length + ' races');
                }
            }
            
            return races;
        }
    """)

    # Also try an alternative extraction approach: grab data from the table rows first
    # before relying solely on modals
    list_data = page.evaluate("""
        () => {
            const rows = [];
            // Look for table rows or list entries with race data
            const links = Array.from(document.querySelectorAll('a[href*="/umamusume/races/"]'));
            
            links.forEach(link => {
                const href = link.href;
                // Skip if it's just the main races page
                if (href.endsWith('/races') || href.endsWith('/races/')) return;
                
                const container = link.closest('tr, div[class]');
                if (container) {
                    const text = container.innerText;
                    rows.push({
                        url: href,
                        text: text.substring(0, 500)
                    });
                }
            });
            
            return rows;
        }
    """)

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
