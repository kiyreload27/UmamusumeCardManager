"""
GameTora Umamusume Support Card Scraper
Scrapes all support cards with their effects at key levels (1, 25, 40, 50)
Includes character art download
"""

import sqlite3
import time
import re
import os
import requests
import sys
from playwright.sync_api import sync_playwright

BASE_URL = "https://gametora.com"

if getattr(sys, 'frozen', False):
    # In frozen state, look in the same directory as the executable
    DB_PATH = os.path.join(os.path.dirname(sys.executable), "database", "umamusume.db")
    IMAGES_PATH = os.path.join(os.path.dirname(sys.executable), "images")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "umamusume.db")
    IMAGES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")

# Key levels to scrape (as requested by user)
KEY_LEVELS = [1, 25, 40, 50]

# Rarity mapping based on image filename
RARITY_MAP = {
    "rarity_01": "R",
    "rarity_02": "SR", 
    "rarity_03": "SSR"
}

# Type mapping based on image filename - uses utx_ico_obtain_XX pattern!
TYPE_MAP = {
    "obtain_00": "Speed",
    "obtain_01": "Stamina",
    "obtain_02": "Power",
    "obtain_03": "Guts",
    "obtain_04": "Wisdom",
    "obtain_05": "Friend",
    "obtain_06": "Group"
}

def get_conn():
    """Get database connection"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_database():
    """Initialize fresh database with schema"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Drop existing tables for fresh start (preserve user data)
    cur.execute("DROP TABLE IF EXISTS event_skills")
    cur.execute("DROP TABLE IF EXISTS support_events")
    cur.execute("DROP TABLE IF EXISTS support_hints")
    cur.execute("DROP TABLE IF EXISTS support_effects")
    cur.execute("DROP TABLE IF EXISTS support_cards")
    
    # Create tables
    cur.execute("""
        CREATE TABLE support_cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rarity TEXT,
            card_type TEXT,
            max_level INTEGER DEFAULT 50,
            gametora_url TEXT UNIQUE,
            image_path TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE support_effects (
            effect_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            level INTEGER,
            effect_name TEXT,
            effect_value TEXT,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE support_hints (
            hint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            hint_name TEXT,
            hint_description TEXT,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE support_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            event_name TEXT,
            event_type TEXT,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE event_skills (
            skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            skill_name TEXT,
            FOREIGN KEY (event_id) REFERENCES support_events(event_id)
        )
    """)
    
    # User tables - create if not exist (preserve user data)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS owned_cards (
            owned_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER UNIQUE,
            level INTEGER DEFAULT 50,
            limit_break INTEGER DEFAULT 0,
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_decks (
            deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deck_slots (
            slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER,
            card_id INTEGER,
            slot_position INTEGER,
            level INTEGER DEFAULT 50,
            FOREIGN KEY (deck_id) REFERENCES user_decks(deck_id),
            FOREIGN KEY (card_id) REFERENCES support_cards(card_id)
        )
    """)
    
    # Create indexes for performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_effects_card_level ON support_effects(card_id, level)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hints_card ON support_hints(card_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_card ON support_events(card_id)")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def scrape_all_support_links(page):
    """Scrape all support card links from the list page"""
    print("Loading support card list...")
    page.goto(f"{BASE_URL}/umamusume/supports", timeout=60000)
    page.wait_for_load_state("networkidle")
    
    # Scroll to load all cards (lazy loading) - more scrolls for complete list
    print("Scrolling to load all cards...")
    for i in range(30):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(400)
    
    # Scroll back up and down to ensure all loaded
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)
    for i in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(300)
    
    # Extract all card links
    links = page.evaluate("""
        () => {
            const links = Array.from(document.querySelectorAll('a[href*="/umamusume/supports/"]'))
                .map(a => a.href)
                .filter(href => href.match(/\\/supports\\/\\d+-/));
            return [...new Set(links)];
        }
    """)
    
    print(f"Found {len(links)} support cards")
    return sorted(links)

def parse_rarity_from_image(img_src):
    """Extract rarity from image source URL"""
    if not img_src:
        return "R"  # Default to R if not found
    for key, rarity in RARITY_MAP.items():
        if key in img_src:
            return rarity
    return "R"  # Default to R

def parse_type_from_image(img_src):
    """Extract type from image source URL"""
    if not img_src:
        return "Unknown"
    for key, card_type in TYPE_MAP.items():
        if key in img_src:
            return card_type
    return "Unknown"

def get_max_level_for_rarity(rarity):
    """Get maximum level based on rarity"""
    if rarity == "SSR":
        return 50
    elif rarity == "SR":
        return 45
    else:  # R
        return 40

def download_card_image(page, card_id, card_name):
    """Download the card's character art image"""
    os.makedirs(IMAGES_PATH, exist_ok=True)
    
    try:
        # Find the main card image
        img_url = page.evaluate("""
            () => {
                // Look for the main card image - usually a large character portrait
                const imgs = Array.from(document.querySelectorAll('img'));
                
                // Find images that might be the card art (usually larger images with character names)
                const cardImg = imgs.find(img => 
                    img.src.includes('/supports/') || 
                    img.src.includes('/cards/') ||
                    (img.width > 100 && img.height > 100 && img.src.includes('umamusume'))
                );
                
                // Also look for images in the infobox
                const infoboxImg = document.querySelector('[class*="infobox"] img');
                
                return cardImg ? cardImg.src : (infoboxImg ? infoboxImg.src : null);
            }
        """)
        
        if img_url:
            # Clean filename
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', card_name)
            file_path = os.path.join(IMAGES_PATH, f"{card_id}_{safe_name}.png")
            
            # Download image
            response = requests.get(img_url, timeout=10)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return file_path
    except Exception as e:
        print(f"    Warning: Could not download image: {e}")
    
    return None

def scrape_support_card(page, url, conn, max_retries=3):
    """Scrape a single support card with key levels and retries"""
    
    for attempt in range(max_retries):
        try:
            page.goto(url, timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)  # Extra wait for JS rendering
            
            # Extract basic card info including type
            card_data = page.evaluate("""
                () => {
                    const h1 = document.querySelector('h1');
                    const title = h1 ? h1.textContent.trim() : '';
                    
                    // Find rarity image
                    const imgs = Array.from(document.querySelectorAll('img'));
                    const rarityImg = imgs.find(i => i.src.includes('rarity'));
                    
                    // Find type image - uses utx_ico_obtain pattern
                    const typeImg = imgs.find(i => i.src.includes('obtain_0'));
                    
                    return {
                        title: title,
                        rarityImgSrc: rarityImg ? rarityImg.src : null,
                        typeImgSrc: typeImg ? typeImg.src : null
                    };
                }
            """)
            
            # Parse name from title (remove rarity and "Support Card")
            full_title = card_data['title']
            name = re.sub(r'\s*\(SSR\)|\s*\(SR\)|\s*\(R\)', '', full_title)
            name = name.replace('Support Card', '').strip()
            
            if not name:
                print(f"  Warning: Empty name, skipping")
                return False
            
            rarity = parse_rarity_from_image(card_data['rarityImgSrc'])
            card_type = parse_type_from_image(card_data['typeImgSrc'])
            max_level = get_max_level_for_rarity(rarity)
            
            print(f"Scraping: {name} | {rarity} | {card_type} | Max Level: {max_level}")
            
            cur = conn.cursor()
            
            # Insert card
            cur.execute("""
                INSERT OR REPLACE INTO support_cards (name, rarity, card_type, max_level, gametora_url)
                VALUES (?, ?, ?, ?, ?)
            """, (name, rarity, card_type, max_level, url))
            conn.commit()
            
            cur.execute("SELECT card_id FROM support_cards WHERE gametora_url = ?", (url,))
            card_id = cur.fetchone()[0]
            
            # Download character art
            image_path = download_card_image(page, card_id, name)
            if image_path:
                cur.execute("UPDATE support_cards SET image_path = ? WHERE card_id = ?", (image_path, card_id))
                conn.commit()
            
            # Clear existing effects for this card (in case of re-scrape)
            cur.execute("DELETE FROM support_effects WHERE card_id = ?", (card_id,))
            cur.execute("DELETE FROM support_hints WHERE card_id = ?", (card_id,))
            cur.execute("DELETE FROM event_skills WHERE event_id IN (SELECT event_id FROM support_events WHERE card_id = ?)", (card_id,))
            cur.execute("DELETE FROM support_events WHERE card_id = ?", (card_id,))
            
            # Scrape effects at key levels only
            scrape_effects_key_levels(page, card_id, max_level, cur)
            
            # Scrape hints
            scrape_hints(page, card_id, cur)
            
            # Scrape events
            scrape_events(page, card_id, cur)
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"  Retrying...")
                time.sleep(1)
            else:
                print(f"  All retries failed for {url}")
                return False

def set_level(page, target_level):
    """Set the page to a specific level using JavaScript to click buttons"""
    
    # Use JavaScript to handle all the clicking - need to check children.length === 0 
    # and wait for level text to change after each click
    actual_level = page.evaluate("""
        async (targetLevel) => {
            // Get current level from the page
            const getLevel = () => {
                const el = Array.from(document.querySelectorAll('div')).find(d => 
                    d.textContent.trim().startsWith('Level ') && d.children.length === 0
                );
                if (!el) {
                    const text = document.body.innerText;
                    const match = text.match(/Level\\s*(\\d+)/i);
                    return match ? parseInt(match[1]) : 30;
                }
                return parseInt(el.textContent.replace('Level ', '').trim());
            };
            
            // Find a button by its exact text - MUST check children.length === 0
            const clickButton = (text) => {
                const btns = Array.from(document.querySelectorAll('div'));
                const btn = btns.find(d => d.textContent.trim() === text && d.children.length === 0);
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            };
            
            let currentLevel = getLevel();
            
            // Navigate to target level
            while (currentLevel !== targetLevel) {
                let btnText;
                if (currentLevel > targetLevel) {
                    const diff = currentLevel - targetLevel;
                    btnText = diff >= 5 ? '-5' : '-1';
                } else {
                    const diff = targetLevel - currentLevel;
                    btnText = diff >= 5 ? '+5' : '+1';
                }
                
                if (!clickButton(btnText)) {
                    // Button not found, we might be at max/min level
                    break;
                }
                
                // CRITICAL: Wait for level text to actually change
                const startLevel = currentLevel;
                let start = Date.now();
                while (Date.now() - start < 1000) {
                    await new Promise(r => setTimeout(r, 50));
                    const newLevel = getLevel();
                    if (newLevel !== startLevel) {
                        currentLevel = newLevel;
                        break;
                    }
                }
                
                // If we're stuck, break out
                if (currentLevel === startLevel) {
                    break;
                }
            }
            
            // Final wait for effects to update
            await new Promise(r => setTimeout(r, 200));
            return getLevel();
        }
    """, target_level)
    
    return actual_level

def extract_effects(page):
    """Extract effects from current page state using proper DOM selectors"""
    effects = page.evaluate("""
        () => {
            const effects = [];
            
            // Method 1: Try to find effects using the specific class structure
            const effectContainers = document.querySelectorAll('[class*="effect__"]');
            
            effectContainers.forEach(container => {
                const text = container.innerText.trim();
                if (text.includes('Unlocked at level')) return;
                
                const fullText = text.split('\\n').join(' ');
                
                const patterns = [

                    // Basic Stats
                    { regex: /Speed Bonus\\s*(\\d+)/, name: 'Speed Bonus' },
                    { regex: /Stamina Bonus\\s*(\\d+)/, name: 'Stamina Bonus' },
                    { regex: /Power Bonus\\s*(\\d+)/, name: 'Power Bonus' },
                    { regex: /Guts Bonus\\s*(\\d+)/, name: 'Guts Bonus' },
                    { regex: /Wisdom Bonus\\s*(\\d+)/, name: 'Wisdom Bonus' },
                    { regex: /Wit Bonus\\s*(\\d+)/, name: 'Wisdom Bonus' }, // Alias Wit -> Wisdom
                    { regex: /Skill Pts Bonus\\s*(\\d+)/, name: 'Skill Pts Bonus' },
                    
                    // Initial Stats
                    { regex: /Initial Speed\\s*(\\d+)/, name: 'Initial Speed' },
                    { regex: /Initial Stamina\\s*(\\d+)/, name: 'Initial Stamina' },
                    { regex: /Initial Power\\s*(\\d+)/, name: 'Initial Power' },
                    { regex: /Initial Guts\\s*(\\d+)/, name: 'Initial Guts' },
                    { regex: /Initial Wisdom\\s*(\\d+)/, name: 'Initial Wisdom' },
                    { regex: /Initial Wit\\s*(\\d+)/, name: 'Initial Wisdom' }, // Alias Wit -> Wisdom

                    // Special Bonuses
                    { regex: /Friendship Bonus\\s*(\\d+%?)/, name: 'Friendship Bonus' },
                    { regex: /Mood Effect\\s*(\\d+%?)/, name: 'Mood Effect' },
                    { regex: /Motivation Effect\\s*(\\d+%?)/, name: 'Motivation Effect' },
                    { regex: /Training Effectiveness\\s*(\\d+%?)/, name: 'Training Effectiveness' },
                    { regex: /Race Bonus\\s*(\\d+%?)/, name: 'Race Bonus' },
                    { regex: /Fan Bonus\\s*(\\d+%?)/, name: 'Fan Bonus' },
                    
                    // Hints
                    { regex: /Hint Rate\\s*(\\d+%?)/, name: 'Hint Rate' },
                    { regex: /Hint Frequency\\s*(\\d+%?)/, name: 'Hint Rate' }, // Alias Frequency -> Rate
                    { regex: /Hint Lv Up\\s*(\\d+%?)/, name: 'Hint Lv Up' },
                    { regex: /Hint Levels\\s*Lv\\s*(\\d+)/, name: 'Hint Lv Up' }, // Alias Hint Levels -> Hint Lv Up
                    
                    // Specialty/Bond
                    { regex: /Starting Bond\\s*(\\d+)/, name: 'Starting Bond' },
                    { regex: /Initial Friendship Gauge\\s*(\\d+)/, name: 'Starting Bond' }, // Alias -> Starting Bond
                    { regex: /Specialty Rate\\s*(\\d+%?)/, name: 'Specialty Rate' },
                    { regex: /Specialty Priority\\s*(\\d+)/, name: 'Specialty Rate' }, // Alias Priority -> Rate (usually same concept)
                    
                    // Recovery/Usage
                    { regex: /Race Status\\s*(\\d+)/, name: 'Race Status' },
                    { regex: /Energy Discount\\s*(\\d+%?)/, name: 'Energy Discount' },
                    { regex: /Wit Friendship Recovery\\s*(\\d+)/, name: 'Wisdom Friendship Recovery' },
                    
                    // Catch-all Unique
                    { regex: /Unique Effect\\s*(.*)/, name: 'Unique Effect' },
                ];

                
                for (const p of patterns) {
                    const match = fullText.match(p.regex);
                    if (match && !effects.some(e => e.name === p.name)) {
                        effects.push({ name: p.name, value: match[1] });
                    }
                }
            });
            
            // Method 2: Fallback - scan entire page text
            if (effects.length === 0) {
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                
                const simplePatterns = [
                    /^(Friendship Bonus)\\s*(\\d+%?)$/,
                    /^(Mood Effect)\\s*(\\d+%?)$/,
                    /^(Race Bonus)\\s*(\\d+%?)$/,
                    /^(Fan Bonus)\\s*(\\d+%?)$/,
                    /^(Training Effectiveness)\\s*(\\d+%?)$/,
                ];
                
                for (const line of lines) {
                    const trimmed = line.trim();
                    for (const pattern of simplePatterns) {
                        const match = trimmed.match(pattern);
                        if (match && !effects.some(e => e.name === match[1])) {
                            effects.push({ name: match[1], value: match[2] });
                        }
                    }
                }
            }
            
            return effects;
        }
    """)
    return effects

def scrape_effects_key_levels(page, card_id, max_level, cur):
    """Scrape effects at key levels (1, 25, 40, 50)"""
    levels_to_scrape = [l for l in KEY_LEVELS if l <= max_level]
    
    for level in levels_to_scrape:
        actual_level = set_level(page, level)
        effects = extract_effects(page)
        
        for effect in effects:
            cur.execute("""
                INSERT INTO support_effects (card_id, level, effect_name, effect_value)
                VALUES (?, ?, ?, ?)
            """, (card_id, actual_level, effect['name'], effect['value']))
        
        print(f"  Level {actual_level}: {len(effects)} effects")

def scrape_hints(page, card_id, cur):
    """Scrape support hints/training skills"""
    hints = page.evaluate("""
        () => {
            const hints = [];
            const text = document.body.innerText;
            
            const hintsMatch = text.match(/Support [Hh]ints([\\s\\S]*?)(?:Training [Ee]vents|Skills from [Ee]vents|$)/);
            if (!hintsMatch) return hints;
            
            const hintsSection = hintsMatch[1];
            const lines = hintsSection.split('\\n');
            
            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed.length > 3 && trimmed.length < 60 && 
                    !trimmed.includes('Lv') && !trimmed.includes('%') &&
                    !trimmed.includes('Details') && trimmed[0] === trimmed[0].toUpperCase()) {
                    hints.push({ name: trimmed, description: '' });
                }
            }
            
            return hints.slice(0, 10);
        }
    """)
    
    for hint in hints:
        cur.execute("""
            INSERT INTO support_hints (card_id, hint_name, hint_description)
            VALUES (?, ?, ?)
        """, (card_id, hint.get('name', ''), hint.get('description', '')))
    
    if hints:
        print(f"  Found {len(hints)} hints")

def scrape_events(page, card_id, cur):
    """Scrape training events"""
    events = page.evaluate("""
        () => {
            const events = [];
            const text = document.body.innerText;
            
            const eventsMatch = text.match(/Training [Ee]vents([\\s\\S]*?)(?:$)/);
            if (!eventsMatch) return events;
            
            const eventsSection = eventsMatch[1];
            const lines = eventsSection.split('\\n');
            
            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed.length > 5 && trimmed.length < 80 && 
                    !trimmed.includes('%') && !trimmed.includes('Energy') &&
                    !trimmed.includes('bond') && !trimmed.includes('+') &&
                    trimmed[0] === trimmed[0].toUpperCase()) {
                    events.push({ name: trimmed, type: 'Event' });
                }
            }
            
            return events.slice(0, 15);
        }
    """)
    
    for event in events:
        cur.execute("""
            INSERT INTO support_events (card_id, event_name, event_type)
            VALUES (?, ?, ?)
        """, (card_id, event.get('name', ''), event.get('type', 'Unknown')))
    
    if events:
        print(f"  Found {len(events)} events")

def run_scraper():
    """Main scraper function"""
    print("=" * 60)
    print("GameTora Umamusume Support Card Scraper")
    print(f"Scraping effects at levels: {KEY_LEVELS}")
    print("=" * 60)
    
    # Initialize fresh database
    print("\nInitializing database...")
    init_database()
    
    # Create images directory
    os.makedirs(IMAGES_PATH, exist_ok=True)
    
    conn = get_conn()
    
    with sync_playwright() as p:
        print("\nLaunching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Get all card links
        links = scrape_all_support_links(page)
        
        print(f"\nStarting to scrape {len(links)} cards...")
        print("Including character art download.")
        print("This will take approximately 30-45 minutes.\n")
        
        success_count = 0
        fail_count = 0
        
        for i, url in enumerate(links, 1):
            print(f"\n[{i}/{len(links)}] ", end="")
            if scrape_support_card(page, url, conn):
                success_count += 1
            else:
                fail_count += 1
            
            time.sleep(0.3)
            
            if i % 50 == 0:
                print(f"\n{'='*40}")
                print(f"Progress: {i}/{len(links)} ({i*100//len(links)}%)")
                print(f"Success: {success_count}, Failed: {fail_count}")
                print(f"{'='*40}")
        
        browser.close()
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("Scraping Complete!")
    print(f"Successfully scraped: {success_count} cards")
    print(f"Failed: {fail_count} cards")
    print(f"Images saved to: {IMAGES_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    run_scraper()
