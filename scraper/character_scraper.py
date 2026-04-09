"""
GameTora Umamusume Character Scraper
Scrapes all playable characters with their aptitude data and character portraits
Downloads character images locally
"""

import sqlite3
import time
import re
import os
import requests
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

# Character images path
if getattr(sys, 'frozen', False):
    ASSETS_PATH = os.path.join(os.path.dirname(sys.executable), "assets", "characters")
else:
    ASSETS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "characters")

# Thumbnail size for character images
CHARACTER_IMAGE_SIZE = (200, 200)


def scrape_character_list(page):
    """Scrape all character links from the list page"""
    logger.info("Loading character list page...")
    page.goto(f"{BASE_URL}/umamusume/characters", timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)  # Extra wait for JS rendering

    # Scroll to load all characters (lazy loading)
    logger.info("Scrolling to load all characters...")
    for i in range(30):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(400)

    # Scroll back up and down to ensure all loaded
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)
    for i in range(15):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(300)

    # Extract all character links
    links = page.evaluate("""
        () => {
            const links = Array.from(document.querySelectorAll('a[href*="/umamusume/characters/"]'))
                .map(a => a.href)
                .filter(href => href.match(/\\/characters\\/\\d+-/));
            return [...new Set(links)];
        }
    """)

    logger.info(f"Found {len(links)} characters")
    return sorted(links)


def extract_character_id(url):
    """Extract stable numeric ID from GameTora URL (e.g., 112901 from /characters/112901-almond-eye)"""
    match = re.search(r'/characters/(\d+)-', url)
    if match:
        return match.group(1)
    return None


def download_character_image(page, gametora_id, char_name):
    """Download the character's portrait image"""
    os.makedirs(ASSETS_PATH, exist_ok=True)

    try:
        # Find the main character image
        img_url = page.evaluate("""
            () => {
                const imgs = Array.from(document.querySelectorAll('img'));
                
                // Look for character portrait - usually a large image with the character
                const charImg = imgs.find(img => 
                    img.src.includes('chara_stand_') && img.src.includes('.png') && !img.src.includes('/thumb/')
                );
                
                // Fallback to thumbnail if full stand not found
                const thumbImg = imgs.find(img =>
                    img.src.includes('chara_stand_') && img.src.includes('.png') && img.src.includes('/thumb/')
                );
                
                return charImg ? charImg.src : (thumbImg ? thumbImg.src : null);
            }
        """)

        if img_url:
            # Clean filename
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', char_name)
            file_path = os.path.join(ASSETS_PATH, f"{gametora_id}_{safe_name}.png")

            # Skip if already exists
            if os.path.exists(file_path):
                return file_path

            # Download image
            response = requests.get(img_url, timeout=10)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"    Downloaded image: {safe_name}")
                return file_path
    except Exception as e:
        logger.warning(f"    Could not download image: {e}")

    return None


def scrape_character_detail(page, url):
    """Scrape a single character's detail page for aptitude data"""
    logger.info(f"  Loading character: {url}")
    page.goto(url, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)  # Extra wait for JS rendering

    # Scroll down to ensure aptitude section loads
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(300)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)

    # Extract character data including aptitudes
    data = page.evaluate("""
        () => {
            const result = {
                name: '',
                aptitudes: {}
            };

            // Get character name from h1
            const h1 = document.querySelector('h1');
            if (h1) {
                result.name = h1.textContent.trim();
            }

            // Extract aptitude data
            // The aptitude section shows letter grades (S, A, B, C, D, E, F, G)
            // for Surface (Turf/Dirt), Distance (Short/Mile/Medium/Long), Strategy (Runner/Leader/Betweener/Chaser)
            
            const bodyText = document.body.innerText;
            
            // Method 1: Look for aptitude-related text patterns
            const aptCategories = {
                // Surface
                'Turf': null,
                'Dirt': null,
                // Distance
                'Short': null,
                'Mile': null,
                'Medium': null,
                'Long': null,
                // Strategy (may appear as different names)
                'Runner': null,
                'Leader': null,
                'Betweener': null,
                'Chaser': null
            };
            
            // Method 2: Look for elements containing aptitude grades near category labels
            const textContent = document.body.innerText;
            
            // First pass: Direct DOM traversal for structured infoboxes (like the Strategy section)
            // The DOM has <div class="...bold_text...">Strategy</div>
            // Followed by a row of <div class="...row_split..."><div>Label</div><div>Grade</div></div>
            const boldTexts = Array.from(document.querySelectorAll('div[class*="bold_text"]'));
            for (const bt of boldTexts) {
                const title = bt.textContent.trim();
                // If it's the "Strategy" section, look at the next sibling row
                if (title === 'Strategy') {
                    const parentRow = bt.closest('div[class*="row"]');
                    if (parentRow && parentRow.nextElementSibling) {
                        const nextRow = parentRow.nextElementSibling;
                        const splits = nextRow.querySelectorAll('div[class*="row_split"]');
                        splits.forEach(split => {
                            const kids = split.children;
                            if (kids.length >= 2) {
                                const label = kids[0].textContent.trim();
                                const grade = kids[1].textContent.trim();
                                if (aptCategories.hasOwnProperty(label)) {
                                    aptCategories[label] = grade;
                                }
                            }
                        });
                    }
                }
            }
            
            // Second pass: general proximity scan for remaining ones
            const allDivs = Array.from(document.querySelectorAll('div, span, td'));
            const gradePattern = /^[A-G]$/;
            const sGradePattern = /^S$/;
            
            for (const category of Object.keys(aptCategories)) {
                if (aptCategories[category]) continue; // Skip if already found
                
                const catElements = allDivs.filter(el => {
                    return el.textContent.trim() === category && el.children.length === 0;
                });
                
                for (const catEl of catElements) {
                    let container = catEl.parentElement;
                    let attempts = 0;
                    while (container && attempts < 5) {
                        const children = Array.from(container.querySelectorAll('div, span, td'));
                        const gradeEl = children.find(c => {
                            const t = c.textContent.trim();
                            return (gradePattern.test(t) || sGradePattern.test(t)) && c !== catEl;
                        });
                        
                        if (gradeEl) {
                            aptCategories[category] = gradeEl.textContent.trim();
                            break;
                        }
                        container = container.parentElement;
                        attempts++;
                    }
                    if (aptCategories[category]) break;
                }
            }
            
            // Method 3: Regex fallback
            for (const cat of Object.keys(aptCategories)) {
                if (aptCategories[cat]) continue;
                const regex = new RegExp(cat + '\\\\s*:?\\\\s*([SABCDEFG])', 'i');
                const match = textContent.match(regex);
                if (match) {
                    aptCategories[cat] = match[1].toUpperCase();
                }
            }
            
            result.aptitudes = aptCategories;
            return result;
        }
    """)

    return data


def save_character_to_db(conn, gametora_id, url, name, aptitudes, image_path):
    """Save or update a character in the database"""
    cur = conn.cursor()

    # Use INSERT OR REPLACE keyed on gametora_id
    cur.execute("""
        INSERT INTO characters (name, gametora_id, gametora_url, image_path,
                                turf_aptitude, dirt_aptitude,
                                short_aptitude, mile_aptitude, medium_aptitude, long_aptitude,
                                runner_aptitude, leader_aptitude, betweener_aptitude, chaser_aptitude,
                                is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(gametora_id) DO UPDATE SET
            name = ?,
            gametora_url = ?,
            image_path = COALESCE(?, image_path),
            turf_aptitude = COALESCE(?, turf_aptitude),
            dirt_aptitude = COALESCE(?, dirt_aptitude),
            short_aptitude = COALESCE(?, short_aptitude),
            mile_aptitude = COALESCE(?, mile_aptitude),
            medium_aptitude = COALESCE(?, medium_aptitude),
            long_aptitude = COALESCE(?, long_aptitude),
            runner_aptitude = COALESCE(?, runner_aptitude),
            leader_aptitude = COALESCE(?, leader_aptitude),
            betweener_aptitude = COALESCE(?, betweener_aptitude),
            chaser_aptitude = COALESCE(?, chaser_aptitude),
            is_active = 1
    """, (
        name, gametora_id, url, image_path,
        aptitudes.get('Turf'), aptitudes.get('Dirt'),
        aptitudes.get('Short'), aptitudes.get('Mile'), aptitudes.get('Medium'), aptitudes.get('Long'),
        aptitudes.get('Runner'), aptitudes.get('Leader'), aptitudes.get('Betweener'), aptitudes.get('Chaser'),
        # ON CONFLICT update values:
        name, url, image_path,
        aptitudes.get('Turf'), aptitudes.get('Dirt'),
        aptitudes.get('Short'), aptitudes.get('Mile'), aptitudes.get('Medium'), aptitudes.get('Long'),
        aptitudes.get('Runner'), aptitudes.get('Leader'), aptitudes.get('Betweener'), aptitudes.get('Chaser'),
    ))

    conn.commit()


def run_character_scraper():
    """Main entry point: scrape all characters and their aptitude data"""
    print("=" * 60)
    print("GameTora Umamusume Character Scraper")
    print("=" * 60)

    # Initialize database (additive only — safe for existing data)
    logger.info("Initializing database (additive tables only)...")
    init_database()

    # Create assets directory
    os.makedirs(ASSETS_PATH, exist_ok=True)

    conn = get_conn()
    chars_added = 0
    chars_updated = 0
    errors = 0

    with sync_playwright() as p:
        logger.info("Launching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Get all character links
        links = scrape_character_list(page)

        if not links:
            logger.error("No characters found! The page structure may have changed.")
            browser.close()
            conn.close()
            return

        print(f"\nFound {len(links)} characters. Starting detailed scrape...\n")

        for i, url in enumerate(links, 1):
            gametora_id = extract_character_id(url)
            if not gametora_id:
                logger.warning(f"  Could not extract ID from {url}, skipping")
                errors += 1
                continue

            print(f"\n[{i}/{len(links)}] ", end="")

            try:
                # Scrape character detail
                data = scrape_character_detail(page, url)

                name = data.get('name', '').strip()
                if not name:
                    logger.warning(f"  Empty name for {url}, skipping")
                    errors += 1
                    continue

                aptitudes = data.get('aptitudes', {})
                apt_count = sum(1 for v in aptitudes.values() if v)

                print(f"{name} | Aptitudes: {apt_count}/10")

                # Download character image
                image_path = download_character_image(page, gametora_id, name)

                # Save to database (relative path for portability)
                db_image_path = f"assets/characters/{os.path.basename(image_path)}" if image_path else None
                save_character_to_db(conn, gametora_id, url, name, aptitudes, db_image_path)
                chars_added += 1

                # Log aptitude data
                if aptitudes:
                    surface = f"Turf:{aptitudes.get('Turf', '?')} Dirt:{aptitudes.get('Dirt', '?')}"
                    distance = f"Short:{aptitudes.get('Short', '?')} Mile:{aptitudes.get('Mile', '?')} Mid:{aptitudes.get('Medium', '?')} Long:{aptitudes.get('Long', '?')}"
                    strategy = f"Runner:{aptitudes.get('Runner', '?')} Leader:{aptitudes.get('Leader', '?')} Betw:{aptitudes.get('Betweener', '?')} Chaser:{aptitudes.get('Chaser', '?')}"
                    logger.info(f"    {surface}")
                    logger.info(f"    {distance}")
                    logger.info(f"    {strategy}")

                time.sleep(0.5)  # Be respectful to the server

            except Exception as e:
                logger.error(f"  Error processing character: {e}")
                errors += 1

            if i % 25 == 0:
                print(f"\n{'=' * 40}")
                print(f"Progress: {i}/{len(links)} ({i * 100 // len(links)}%)")
                print(f"Success: {chars_added}, Errors: {errors}")
                print(f"{'=' * 40}")

        browser.close()

    # Update scraper timestamp
    set_scraper_timestamp('characters', datetime.now().isoformat())

    conn.close()

    # Print summary
    print("\n" + "=" * 60)
    print("Character Scraping Complete!")
    print(f"  Characters scraped: {chars_added}")
    print(f"  Errors:             {errors}")
    print(f"  Images stored in:   {ASSETS_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    run_character_scraper()
