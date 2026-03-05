"""
GameTora Umamusume Race Scraper (v2)
Scrapes all races from the race list page including detail modal data and badge images.
Downloads race banner images and stores them under assets/races/.
"""

import sqlite3
import time
import re
import os
import sys
import logging
import urllib.request
from datetime import datetime

# Ensure we can import from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from db.db_queries import get_conn, init_database, set_scraper_timestamp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://gametora.com"

# Where to save race banner images (relative to project root)
RACE_IMAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "races"
)


def ensure_image_dir():
    os.makedirs(RACE_IMAGES_DIR, exist_ok=True)


def download_image(url, filename):
    """Download an image to RACE_IMAGES_DIR. Returns relative path or None on failure."""
    try:
        dest = os.path.join(RACE_IMAGES_DIR, filename)
        if os.path.exists(dest):
            return os.path.join("assets", "races", filename)
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            with open(dest, 'wb') as f:
                f.write(resp.read())
        return os.path.join("assets", "races", filename)
    except Exception as e:
        logger.debug(f"Image download failed for {url}: {e}")
        return None


def _safe_filename(name_en, name_jp):
    """Create a filesystem-safe filename from race names."""
    raw = name_en or name_jp or "race"
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw).strip('_')
    return f"{safe[:60]}.png"


def scrape_all_races(page):
    """Scrape all races from the race list page, clicking Details for each"""
    logger.info("Loading race list page...")
    page.goto(f"{BASE_URL}/umamusume/races", timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)  # Extra wait for JS rendering

    # Scroll aggressively to load all lazy-loaded races
    logger.info("Scrolling to load all races...")
    for _ in range(40):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(350)

    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(600)
    for _ in range(20):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(300)

    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)

    # Count Details buttons
    detail_buttons = page.locator("text='Details'")
    count = detail_buttons.count()
    logger.info(f"Found {count} Details buttons to process")

    races = []

    for i in range(count):
        try:
            # Scroll to button and click
            btn = detail_buttons.nth(i)
            btn.scroll_into_view_if_needed()
            page.wait_for_timeout(120)
            btn.click()
            page.wait_for_timeout(450)  # wait for modal

            # Extract race data + image URL from modal
            race = page.evaluate("""
                () => {
                    const modals = Array.from(document.querySelectorAll('div[role="dialog"]')).filter(d => {
                        return d.innerText.length > 20 && d.innerText.length < 5000 && d.offsetParent !== null;
                    });

                    if (modals.length === 0) return null;
                    const modal = modals[modals.length - 1];

                    const text = modal.innerText;
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

                    // Grab race banner image URL
                    const imgs = Array.from(modal.querySelectorAll('img'));
                    let banner_url = '';
                    for (const img of imgs) {
                        const src = img.src || '';
                        if (src.includes('race_banner') || src.includes('thum_race')) {
                            banner_url = src;
                            break;
                        }
                    }
                    // Fallback: first img in modal
                    if (!banner_url && imgs.length > 0) {
                        banner_url = imgs[0].src || '';
                    }

                    const race = {
                        name_en: '', name_jp: '', grade: '', racetrack: '',
                        direction: '', participants: null, terrain: '',
                        distance_type: '', distance_meters: null,
                        season: '', time_of_day: '', race_date: '', race_class: '',
                        banner_url: banner_url
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
                            race.distance_type = line.replace(/Distance.*?(type\\)?)/i, '').trim() || nextLine;
                        }
                        if (line.includes('Distance') && (line.includes('meters') || line.includes('m)'))) {
                            const str = line.replace(/Distance.*?(meters?\\)?|m\\)?)/i, '').trim() || nextLine;
                            const num = parseInt(str.replace(/[^0-9]/g, ''));
                            if (!isNaN(num)) race.distance_meters = num;
                        }
                        if (line.startsWith('Season')) race.season = line.replace('Season', '').trim() || nextLine;
                        if (line.includes('Time of day') || line.includes('Time of Day')) {
                            race.time_of_day = line.replace(/Time of [Dd]ay/i, '').trim() || nextLine;
                        }
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

            # Close modal
            page.keyboard.press("Escape")
            page.mouse.click(10, 10)
            page.wait_for_timeout(200)

            if (i + 1) % 25 == 0:
                logger.info(f"Processed {i + 1}/{count} races")

        except Exception as e:
            logger.warning(f"Error scraping race {i}: {e}")
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)

    logger.info(f"Scraped {len(races)} races from details modals")
    return races


def download_race_images(races):
    """Download banner images for all races. Updates race dicts with local image_path."""
    ensure_image_dir()
    downloaded = 0
    for race in races:
        banner_url = race.get('banner_url', '')
        if not banner_url:
            race['image_path'] = None
            continue
        filename = _safe_filename(race.get('name_en'), race.get('name_jp'))
        local_path = download_image(banner_url, filename)
        race['image_path'] = local_path
        if local_path:
            downloaded += 1
    logger.info(f"Downloaded {downloaded}/{len(races)} race images")


def _add_image_path_column_if_missing(conn):
    """Migrate: add image_path column to races if not present."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(races)")
    cols = [row[1] for row in cur.fetchall()]
    if 'image_path' not in cols:
        cur.execute("ALTER TABLE races ADD COLUMN image_path TEXT")
        conn.commit()
        logger.info("Added image_path column to races table")


def save_races_to_db(conn, races):
    """Save all races to the database, including image_path."""
    _add_image_path_column_if_missing(conn)
    cur = conn.cursor()
    added = 0
    errors = 0

    for race in races:
        name_en = race.get('name_en', '').strip()
        name_jp = race.get('name_jp', '').strip()
        key = f"{name_en}_{name_jp}_{race.get('distance_meters', '')}_{race.get('racetrack', '')}"
        gametora_url = f"gametora://race/{key}"
        image_path = race.get('image_path')

        try:
            cur.execute("""
                INSERT INTO races (name_en, name_jp, grade, racetrack, direction,
                                   participants, terrain, distance_type, distance_meters,
                                   season, time_of_day, race_date, race_class, gametora_url,
                                   is_active, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
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
                    is_active = 1,
                    image_path = COALESCE(?, image_path)
            """, (
                name_en, name_jp, race.get('grade', ''), race.get('racetrack', ''),
                race.get('direction', ''), race.get('participants'),
                race.get('terrain', ''), race.get('distance_type', ''),
                race.get('distance_meters'), race.get('season', ''),
                race.get('time_of_day', ''), race.get('race_date', ''),
                race.get('race_class', ''), gametora_url, image_path,
                # ON CONFLICT values:
                name_en or None, name_jp or None, race.get('grade') or None,
                race.get('racetrack') or None, race.get('direction') or None,
                race.get('participants'), race.get('terrain') or None,
                race.get('distance_type') or None, race.get('distance_meters'),
                race.get('season') or None, race.get('time_of_day') or None,
                race.get('race_date') or None, race.get('race_class') or None,
                image_path or None,
            ))
            added += 1
        except Exception as e:
            logger.warning(f"  Error saving race '{name_en}': {e}")
            errors += 1

    conn.commit()
    return added, errors


def run_race_scraper():
    """Main entry point: scrape all races with images"""
    print("=" * 60)
    print("GameTora Umamusume Race Scraper v2 (with Images)")
    print("=" * 60)

    logger.info("Initializing database...")
    init_database()

    conn = get_conn()
    _add_image_path_column_if_missing(conn)

    with sync_playwright() as p:
        logger.info("Launching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        races = scrape_all_races(page)
        browser.close()

    if not races:
        print("No races scraped — page may have changed structure.")
        conn.close()
        return

    print(f"\nDownloading race images ({len(races)} races)...")
    download_race_images(races)

    print(f"\nSaving {len(races)} races to database...")
    added, errors = save_races_to_db(conn, races)

    set_scraper_timestamp('races', datetime.now().isoformat())
    conn.close()

    imgs_saved = sum(1 for r in races if r.get('image_path'))
    print("\n" + "=" * 60)
    print("Race Scraping Complete!")
    print(f"  Races saved:        {added}")
    print(f"  Images downloaded:  {imgs_saved}")
    print(f"  Errors:             {errors}")
    print(f"  Images folder:      {RACE_IMAGES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    run_race_scraper()
