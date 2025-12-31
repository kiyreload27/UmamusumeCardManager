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
import os

# Ensure we can import from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from db.db_queries import get_conn, init_database

BASE_URL = "https://gametora.com"

if getattr(sys, 'frozen', False):
    # In frozen state, look in the same directory as the executable
    IMAGES_PATH = os.path.join(os.path.dirname(sys.executable), "images")
else:
    IMAGES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")

# Key levels to scrape (limit break milestones)
KEY_LEVELS = [20, 25, 30, 35, 40, 45, 50]

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

def scrape_all_support_links(page):
    """Scrape all support card links from the list page"""
    print("Loading support card list...")
    page.goto(f"{BASE_URL}/umamusume/supports", timeout=60000)
    page.wait_for_load_state("networkidle")
    
    # Tick "Show Upcoming Supports" checkbox if it exists
    print("Checking for 'Show Upcoming Supports' checkbox...")
    checkbox_ticked = page.evaluate("""
        () => {
            // Look for checkbox or toggle related to "upcoming" or "future" supports
            const labels = Array.from(document.querySelectorAll('label, span, div'));
            const checkboxLabel = labels.find(el => 
                el.textContent.toLowerCase().includes('upcoming') && 
                el.textContent.toLowerCase().includes('support')
            );
            
            if (checkboxLabel) {
                // Try to find associated checkbox/input
                let checkbox = checkboxLabel.querySelector('input[type="checkbox"]');
                if (!checkbox) {
                    // Look for checkbox nearby
                    const parent = checkboxLabel.closest('div, label');
                    if (parent) {
                        checkbox = parent.querySelector('input[type="checkbox"]');
                    }
                }
                
                if (checkbox && !checkbox.checked) {
                    checkbox.click();
                    return true;
                }
            }
            
            // Alternative: Look for any checkbox with "upcoming" in nearby text
            const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
            for (const cb of checkboxes) {
                const text = cb.closest('label, div')?.textContent?.toLowerCase() || '';
                if (text.includes('upcoming') && text.includes('support') && !cb.checked) {
                    cb.click();
                    return true;
                }
            }
            
            return false;
        }
    """)
    
    if checkbox_ticked:
        print("  ✓ Ticked 'Show Upcoming Supports' checkbox")
        page.wait_for_timeout(1000)  # Wait for page to update
    else:
        print("  ℹ 'Show Upcoming Supports' checkbox not found or already ticked")
    
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

def extract_stable_id_from_url(url):
    """Extract stable numeric ID from GameTora URL (e.g., 30022 from /supports/30022-mejiro-mcqueen)"""
    match = re.search(r'/supports/(\d+)-', url)
    if match:
        return match.group(1)
    return None

def download_card_image(page, stable_id, card_name):
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
            # Clean filename - use stable ID from URL instead of card_id
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', card_name)
            if stable_id:
                file_path = os.path.join(IMAGES_PATH, f"{stable_id}_{safe_name}.png")
            else:
                # Fallback to name-only if no stable ID (shouldn't happen)
                file_path = os.path.join(IMAGES_PATH, f"{safe_name}.png")
            
            # Skip if already exists
            if os.path.exists(file_path):
                # print(f"  Art already exists, skipping download")
                return file_path
                
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
            
            # Extract stable ID from URL for image filename
            stable_id = extract_stable_id_from_url(url)
            
            # Download character art using stable ID
            image_path = download_card_image(page, stable_id, name)
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
    """Scrape effects at key levels based on card rarity/max level"""
    
    # Determine which levels to scrape based on max_level (rarity)
    if max_level == 50: # SSR
        levels_to_scrape = [30, 35, 40, 45, 50]
    elif max_level == 45: # SR
        levels_to_scrape = [25, 30, 35, 40, 45]
    else: # R (max 40)
        levels_to_scrape = [20, 25, 30, 35, 40]
    
    # Filter out any that might exceed max somehow (safety check)
    levels_to_scrape = [l for l in levels_to_scrape if l <= max_level]
    
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
    """Scrape the LAST chain event (Golden Perk) with OR options"""
    
    # Use a flag to avoid adding multiple console listeners
    if not hasattr(page, "_console_attached"):
        page.on("console", lambda msg: print(f"  [JS Console] {msg.text}") if "scrapping" not in msg.text.lower() else None)
        page._console_attached = True
    
    # 1. First, build a map of skills from the 'Skills from events' summary section
    # This helps us identify which skills are Rare (Gold)
    skill_rarity_map = page.evaluate("""
        () => {
            const map = {};
            // Rare skills use a specific class (e.g., kkspcu) while normal use another (e.g., gImSzc)
            // It's safer to find all skill containers in the summary section
            const sections = Array.from(document.querySelectorAll('div')).filter(d => d.innerText.startsWith('Skills from events'));
            if (sections.length === 0) return map;
            
            const containers = sections[0].parentElement.querySelectorAll('div[class*="sc-"]');
            containers.forEach(c => {
                const nameNode = c.querySelector('div[font-weight="bold"], span[font-weight="bold"]');
                const name = nameNode ? nameNode.innerText.trim() : c.innerText.split('\\n')[0].trim();
                if (name && name.length > 2) {
                    // Check if it has a gold-themed class or computed background color
                    const isGold = c.className.includes('kkspcu') || window.getComputedStyle(c).backgroundColor.includes('rgb(255, 193, 7)');
                    map[name] = isGold;
                }
            });
            return map;
        }
    """)
    
    
    # Scroll to the Events section specifically
    print("  Ensuring events are loaded...")
    page.evaluate("() => { const h = Array.from(document.querySelectorAll('h2, h1')).find(el => el.innerText.includes('Training Events')); if (h) h.scrollIntoView(); }")
    page.wait_for_timeout(1000)
    
    # 2. Scrape ONLY the LAST chain event (Golden Perk) with OR options
    golden_perk_data = page.evaluate("""
        async () => {
            console.log("Scraping Golden Perk (last chain event)...");
            
            // Find all chain event buttons
            const getChainEventButtons = () => {
                const buttons = [];
                const headers = Array.from(document.querySelectorAll('div, h2, h3, span')).filter(el => 
                    el.innerText.includes('Chain Events')
                );
                
                headers.forEach(header => {
                    const container = header.parentElement;
                    if (container) {
                        const btns = Array.from(container.querySelectorAll('button'));
                        btns.forEach(btn => {
                            const text = btn.innerText.trim();
                            const style = window.getComputedStyle(btn);
                            const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && btn.offsetWidth > 0;
                            
                            // Only chain events (contain '>')
                            if (isVisible && text && text.includes('>') && !text.includes('Events')) {
                                buttons.push(btn);
                            }
                        });
                    }
                });
                return buttons;
            };

            const buttons = getChainEventButtons();
            console.log(`Found ${buttons.length} chain event buttons`);
            
            if (buttons.length === 0) {
                return null;
            }
            
            // Find the button with the most '>' characters (the last chain event = Golden Perk)
            let goldenPerkButton = null;
            let maxArrows = 0;
            
            for (const btn of buttons) {
                const text = btn.innerText.trim();
                const arrowCount = (text.match(/>/g) || []).length;
                if (arrowCount > maxArrows) {
                    maxArrows = arrowCount;
                    goldenPerkButton = btn;
                }
            }
            
            if (!goldenPerkButton) {
                console.log("No golden perk button found");
                return null;
            }
            
            const eventName = goldenPerkButton.innerText.trim();
            console.log(`Found Golden Perk: ${eventName} (${maxArrows} arrows)`);
            
            try {
                // Click to open popover
                goldenPerkButton.scrollIntoViewIfNeeded ? goldenPerkButton.scrollIntoViewIfNeeded() : null;
                await new Promise(r => setTimeout(r, 100));
                goldenPerkButton.click();
                await new Promise(r => setTimeout(r, 600));
                
                // Find popover
                const popovers = Array.from(document.querySelectorAll('div')).filter(d => 
                    d.innerText.includes(eventName) && 
                    window.getComputedStyle(d).zIndex > 50 &&
                    d.innerText.length < 2500
                );
                
                if (popovers.length === 0) {
                    console.log(`Popover NOT found for ${eventName}`);
                    document.body.click();
                    return { name: eventName, type: 'Chain', skills: [] };
                }
                
                const pop = popovers[popovers.length - 1];
                console.log(`Found popover for ${eventName}`);
                
                // Check for OR structure - look for "Randomly either" or "or" divider
                const hasOrDivider = pop.querySelector('[class*="divider_or"]') !== null || 
                                     pop.innerText.includes('Randomly either') ||
                                     pop.innerText.toLowerCase().includes(' or ');
                
                // Find all skill names (purple/blue links)
                const skillLinks = Array.from(pop.querySelectorAll('span, a')).filter(el => 
                    el.innerText.length > 2 && 
                    !el.innerText.includes('Energy') && 
                    !el.innerText.includes('bond') &&
                    (window.getComputedStyle(el).color === 'rgb(102, 107, 255)' || 
                     el.className.includes('linkcolor'))
                );
                
                console.log(`Found ${skillLinks.length} potential skills in popover`);
                
                const skills = [];
                skillLinks.forEach(link => {
                    const skillName = link.innerText.trim();
                    if (skillName && skillName.length > 2 && !skills.some(s => s.name === skillName)) {
                        // If there's an OR divider, all skills in this popover are part of OR groups
                        const isOr = hasOrDivider;
                        skills.push({ name: skillName, is_or: isOr });
                    }
                });
                
                // Close popover
                document.body.click();
                await new Promise(r => setTimeout(r, 200));
                
                return { name: eventName, type: 'Chain', skills: skills };
                
            } catch (err) {
                console.log(`Error clicking ${eventName}: ${err.message}`);
                return { name: eventName, type: 'Chain', skills: [] };
            }
        }
    """)
    
    # 3. Store ONLY the golden perk in database
    if golden_perk_data:
        cur.execute("""
            INSERT INTO support_events (card_id, event_name, event_type)
            VALUES (?, ?, ?)
        """, (card_id, golden_perk_data['name'], golden_perk_data['type']))
        event_id = cur.lastrowid
        
        for skill in golden_perk_data['skills']:
            is_gold = 1 if skill_rarity_map.get(skill['name']) else 0
            cur.execute("""
                INSERT INTO event_skills (event_id, skill_name, is_gold, is_or)
                VALUES (?, ?, ?, ?)
            """, (event_id, skill['name'], is_gold, 1 if skill['is_or'] else 0))
        
        skill_count = len(golden_perk_data['skills'])
        or_count = sum(1 for s in golden_perk_data['skills'] if s['is_or'])
        print(f"  Golden Perk: {golden_perk_data['name']} ({skill_count} skills, {or_count} with OR)")
    else:
        print(f"  No Golden Perk found for this card")

def run_scraper():
    """ Run the web scraper to fetch card data from GameTora.com """
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
        print("This will take approximately 90-120 minutes.\n")
        
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
