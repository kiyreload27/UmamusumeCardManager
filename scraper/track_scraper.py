"""
GameTora Umamusume Racetrack Scraper
Scrapes all racetracks, their courses, and detailed course metadata
Downloads track images locally
"""

import sqlite3
import time
import re
import os
import json
import requests
import sys
import logging
from datetime import datetime

# Ensure we can import from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from db.db_queries import get_conn, init_database, set_scraper_timestamp
from PIL import Image
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://gametora.com"

# Track images path
if getattr(sys, 'frozen', False):
    ASSETS_PATH = os.path.join(os.path.dirname(sys.executable), "assets", "tracks")
else:
    ASSETS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "tracks")

# Thumbnail size for track images (fits within the app UI)
TRACK_IMAGE_SIZE = (300, 200)


def scrape_track_list(page):
    """Scrape all racetrack links and basic info from the list page"""
    logger.info("Loading racetrack list page...")
    page.goto(f"{BASE_URL}/umamusume/racetracks", timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)  # Extra wait for JS rendering

    # Scroll to ensure all content loads
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)

    # Extract track data from the page
    tracks = page.evaluate("""
        () => {
            const tracks = [];
            // Look for track links - they follow pattern /umamusume/racetracks/<name>
            const links = Array.from(document.querySelectorAll('a[href*="/umamusume/racetracks/"]'));
            
            for (const link of links) {
                const href = link.href || link.getAttribute('href');
                if (!href || href.endsWith('/racetracks') || href.endsWith('/racetracks/')) continue;
                
                // Skip if it's just the back link or non-track links
                const urlParts = href.split('/');
                const trackSlug = urlParts[urlParts.length - 1];
                if (!trackSlug || trackSlug === 'racetracks') continue;
                
                // Get the track name from the link text
                const name = link.textContent.trim();
                if (!name || name.length < 2) continue;
                
                // Try to find the track image
                let imgUrl = null;
                const img = link.querySelector('img') || 
                           link.parentElement?.querySelector('img') ||
                           link.closest('div')?.querySelector('img');
                if (img) {
                    imgUrl = img.src || img.getAttribute('src');
                }
                
                // Deduplicate by href
                if (!tracks.some(t => t.url === href)) {
                    tracks.push({
                        name: name,
                        url: href,
                        slug: trackSlug,
                        image_url: imgUrl
                    });
                }
            }
            return tracks;
        }
    """)

    logger.info(f"Found {len(tracks)} racetracks")
    return tracks


def scrape_track_detail(page, track_url):
    """Scrape a single track's detail page to get course list"""
    logger.info(f"  Loading track detail: {track_url}")
    page.goto(track_url, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # Scroll to load all content
    for _ in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)

    # Extract course list and track info
    track_data = page.evaluate("""
        () => {
            const data = {
                courses: [],
                location: null,
                direction: null
            };
            
            // Try to find track location/direction from page text
            const bodyText = document.body.innerText;
            
            // Look for direction indicators
            if (bodyText.includes('Left')) data.direction = 'Left';
            else if (bodyText.includes('Right')) data.direction = 'Right';
            else if (bodyText.includes('Straight')) data.direction = 'Straight';
            
            // Find course links - they contain distance and surface info
            // Pattern: "1200 m · Turf" or similar
            const allLinks = Array.from(document.querySelectorAll('a'));
            const courseLinks = allLinks.filter(a => {
                const text = a.textContent.trim();
                return text.match(/\\d+\\s*m\\s*[·.]\\s*(Turf|Dirt)/i);
            });
            
            for (const link of courseLinks) {
                const text = link.textContent.trim();
                const href = link.href || link.getAttribute('href') || '';
                
                // Parse distance and surface
                const match = text.match(/(\\d+)\\s*m\\s*[·.]\\s*(Turf|Dirt)/i);
                if (match) {
                    data.courses.push({
                        distance: parseInt(match[1]),
                        surface: match[2],
                        text: text,
                        url: href
                    });
                }
            }
            
            // If no links found, try looking for text-based course references
            if (data.courses.length === 0) {
                const textNodes = Array.from(document.querySelectorAll('div, span, p'));
                for (const node of textNodes) {
                    if (node.children.length > 0) continue;
                    const text = node.textContent.trim();
                    const match = text.match(/(\\d+)\\s*m\\s*[·.]\\s*(Turf|Dirt)/i);
                    if (match && !data.courses.some(c => c.distance === parseInt(match[1]) && c.surface === match[2])) {
                        data.courses.push({
                            distance: parseInt(match[1]),
                            surface: match[2],
                            text: text,
                            url: ''
                        });
                    }
                }
            }
            
            return data;
        }
    """)

    logger.info(f"    Found {len(track_data['courses'])} courses")
    return track_data


def scrape_course_metadata(page, track_url, course):
    """Scrape detailed metadata for a specific course from the track page.
    
    On GameTora, courses are shown as sections on the track page itself.
    Each course has a metadata table with Phases, Corners, Straights, Other info.
    """
    # The course detail is typically shown on the same track page when scrolled
    # or it might be a separate section. We need to find the course section
    # and extract the metadata table.
    
    course_distance = course['distance']
    course_surface = course['surface']
    
    logger.info(f"    Scraping metadata for {course_distance}m {course_surface}...")

    # Navigate to the track page with the course anchor if needed  
    course_url = course.get('url', '')
    if course_url and course_url.startswith('http'):
        page.goto(course_url, timeout=60000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
    
    # Scroll to make sure the course content is loaded
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(400)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)

    # Extract course metadata by looking for the section with matching distance/surface
    metadata = page.evaluate("""
        (params) => {
            const { distance, surface } = params;
            const courseLabel = distance + ' m · ' + surface;
            const altLabel = distance + ' m \\u00b7 ' + surface;
            
            const result = {
                direction: null,
                corner_count: 0,
                final_straight_length: null,
                slope_info: null,
                phases: {},
                corners: [],
                straights: [],
                other: {},
                raw_text: ''
            };
            
            // Find the course section - look for h2/h3/div with the course title
            const allElements = Array.from(document.querySelectorAll('h1, h2, h3, h4, div, span'));
            let sectionRoot = null;
            
            for (const el of allElements) {
                const text = el.textContent.trim();
                if ((text === courseLabel || text === altLabel || 
                     text.includes(distance + ' m') && text.includes(surface)) &&
                    el.children.length <= 2) {
                    // Found the course header - look for the metadata container
                    sectionRoot = el;
                    break;
                }
            }
            
            if (!sectionRoot) {
                // Try broader search
                const bodyText = document.body.innerText;
                if (bodyText.includes(courseLabel) || bodyText.includes(altLabel)) {
                    result.raw_text = 'Course found but could not isolate section';
                }
                return result;
            }
            
            // Find the metadata container - it's usually in a parent or sibling section
            let container = sectionRoot.parentElement;
            let attempts = 0;
            while (container && attempts < 10) {
                const inner = container.innerText;
                if (inner.includes('Phases') && inner.includes('Corners') && 
                    (inner.includes('Straights') || inner.includes('Straight'))) {
                    break;
                }
                container = container.parentElement;
                attempts++;
            }
            
            if (!container || attempts >= 10) {
                // Try finding the metadata by looking at all visible text after the course header
                result.raw_text = 'Metadata container not found';
                return result;
            }
            
            const fullText = container.innerText;
            result.raw_text = fullText.substring(0, 3000);
            
            // Parse Direction
            const dirMatch = fullText.match(/Direction[:\\s]*(Left|Right|Straight)/i);
            if (dirMatch) result.direction = dirMatch[1];
            
            // Parse Phases
            const phaseNames = ['Early-Race', 'Mid-Race', 'Late-Race', 'Last Spurt'];
            for (const phase of phaseNames) {
                const phaseRegex = new RegExp(phase + '[\\\\s\\\\S]*?Start:\\\\s*(\\\\d+)\\\\s*m[\\\\s\\\\S]*?End:\\\\s*(\\\\d+)\\\\s*m', 'i');
                const match = fullText.match(phaseRegex);
                if (match) {
                    result.phases[phase] = {
                        start: parseInt(match[1]),
                        end: parseInt(match[2])
                    };
                }
            }
            
            // Parse Corners
            const cornerRegex = /Corner\\s*(\\d+)\\s*[\\s\\S]*?Start:\\s*(\\d+)\\s*m[\\s\\S]*?End:\\s*(\\d+)\\s*m/gi;
            let cornerMatch;
            const cornerText = fullText;
            const cornerMatches = cornerText.match(/Corner\\s*\\d+/gi);
            if (cornerMatches) {
                result.corner_count = cornerMatches.length;
                
                // Try to extract each corner's data
                for (const cm of cornerMatches) {
                    const num = cm.match(/\\d+/)[0];
                    const cornerPattern = new RegExp('Corner\\\\s*' + num + '[\\\\s\\\\S]*?Start:\\\\s*(\\\\d+)\\\\s*m[\\\\s\\\\S]*?End:\\\\s*(\\\\d+)\\\\s*m', 'i');
                    const cd = fullText.match(cornerPattern);
                    if (cd) {
                        result.corners.push({
                            name: 'Corner ' + num,
                            start: parseInt(cd[1]),
                            end: parseInt(cd[2])
                        });
                    }
                }
            }
            
            // Parse Straights
            const straightRegex = /Straight\\s*(\\d+)[\\s\\S]*?Start:\\s*(\\d+)\\s*m[\\s\\S]*?End:\\s*(\\d+)\\s*m/gi;
            let straightMatch;
            while ((straightMatch = straightRegex.exec(fullText)) !== null) {
                result.straights.push({
                    name: 'Straight ' + straightMatch[1],
                    start: parseInt(straightMatch[2]),
                    end: parseInt(straightMatch[3])
                });
            }
            
            // Parse Final Straight
            const finalMatch = fullText.match(/Final\\s*(?:Straight|Spurt)[\\s\\S]*?(\\d+)\\s*m/i);
            if (finalMatch) {
                result.final_straight_length = finalMatch[1] + ' m';
            }
            
            // Parse Other section
            // Position Keep
            const pkMatch = fullText.match(/Position\\s*Keep[\\s\\S]*?Start:\\s*(\\d+)\\s*m[\\s\\S]*?End:\\s*(\\d+)\\s*m/i);
            if (pkMatch) {
                result.other['position_keep'] = {
                    start: parseInt(pkMatch[1]),
                    end: parseInt(pkMatch[2])
                };
            }
            
            // Spurt
            const spurtMatch = fullText.match(/Spurt[\\s\\S]*?Start:\\s*(\\d+)\\s*m/i);
            if (spurtMatch) {
                result.other['spurt'] = {
                    start: parseInt(spurtMatch[1]),
                    note: ''
                };
                // Check for Final Corner note
                const fcMatch = fullText.match(/Spurt[\\s\\S]*?(Final\\s*Corner)/i);
                if (fcMatch) {
                    result.other['spurt']['note'] = fcMatch[1];
                }
            }
            
            // Stat Thresholds
            const statMatch = fullText.match(/Stat\\s*Thresholds[\\s\\S]*?([\\w\\s]+?)(?=\\n|$)/i);
            if (statMatch) {
                result.other['stat_thresholds'] = statMatch[1].trim();
            }
            
            // Slope info
            const slopeMatch = fullText.match(/(Uphill|Downhill|Flat)[\\s\\S]*?(\\d+)\\s*m/i);
            if (slopeMatch) {
                result.slope_info = slopeMatch[0].substring(0, 100);
            }
            
            return result;
        }
    """, {"distance": course_distance, "surface": course_surface})

    return metadata


def download_track_image(img_url, track_name):
    """Download and resize a track image"""
    os.makedirs(ASSETS_PATH, exist_ok=True)

    if not img_url:
        logger.warning(f"    No image URL for {track_name}")
        return None

    # Clean filename
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', track_name)
    file_path = os.path.join(ASSETS_PATH, f"{safe_name}.png")

    # Skip if already exists
    if os.path.exists(file_path):
        logger.info(f"    Image already exists: {safe_name}.png")
        return file_path

    try:
        # Download
        response = requests.get(img_url, timeout=15)
        if response.status_code == 200:
            # Resize to fit within app
            img = Image.open(BytesIO(response.content))
            img.thumbnail(TRACK_IMAGE_SIZE, Image.Resampling.LANCZOS)

            # Save as PNG
            img.save(file_path, 'PNG')
            logger.info(f"    Downloaded & resized: {safe_name}.png ({img.size[0]}x{img.size[1]})")
            return file_path
        else:
            logger.warning(f"    Failed to download image: HTTP {response.status_code}")
    except Exception as e:
        logger.warning(f"    Could not download image for {track_name}: {e}")

    return None


def save_track_to_db(conn, track_data, image_path):
    """Save or update a track in the database"""
    cur = conn.cursor()

    name = track_data['name']
    url = track_data['url']
    image_url = track_data.get('image_url')

    # Insert or update track
    cur.execute("""
        INSERT INTO tracks (name, image_path, image_url, gametora_url)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            image_path = COALESCE(?, image_path),
            image_url = COALESCE(?, image_url),
            gametora_url = ?,
            is_active = 1
    """, (name, image_path, image_url, url,
          image_path, image_url, url))

    conn.commit()

    # Get track_id
    cur.execute("SELECT track_id FROM tracks WHERE name = ?", (name,))
    track_id = cur.fetchone()[0]

    return track_id


def save_course_to_db(conn, track_id, course, metadata, track_url):
    """Save or update a course in the database"""
    cur = conn.cursor()

    distance = course['distance']
    surface = course['surface']
    course_url = course.get('url', '') or f"{track_url}#{distance}-{surface}"

    direction = metadata.get('direction')
    corner_count = metadata.get('corner_count', 0)
    final_straight = metadata.get('final_straight_length')
    slope_info = metadata.get('slope_info')
    phases_json = json.dumps(metadata.get('phases', {})) if metadata.get('phases') else None
    corners_json = json.dumps(metadata.get('corners', [])) if metadata.get('corners') else None
    straights_json = json.dumps(metadata.get('straights', [])) if metadata.get('straights') else None
    other_json = json.dumps(metadata.get('other', {})) if metadata.get('other') else None
    raw_json = json.dumps({
        'raw_text': metadata.get('raw_text', ''),
        'distance': distance,
        'surface': surface
    })

    # Use a composite key for matching: track_id + distance + surface
    cur.execute("""
        SELECT course_id FROM courses 
        WHERE track_id = ? AND distance = ? AND surface = ?
    """, (track_id, distance, surface))
    existing = cur.fetchone()

    if existing:
        # Update existing course
        cur.execute("""
            UPDATE courses SET
                direction = COALESCE(?, direction),
                corner_count = COALESCE(?, corner_count),
                final_straight_length = COALESCE(?, final_straight_length),
                slope_info = COALESCE(?, slope_info),
                phases_json = COALESCE(?, phases_json),
                corners_json = COALESCE(?, corners_json),
                straights_json = COALESCE(?, straights_json),
                other_json = COALESCE(?, other_json),
                raw_metadata_json = ?,
                gametora_url = ?,
                is_active = 1
            WHERE course_id = ?
        """, (direction, corner_count, final_straight, slope_info,
              phases_json, corners_json, straights_json, other_json,
              raw_json, course_url, existing[0]))
        logger.info(f"    Updated course: {distance}m {surface}")
        is_new = False
    else:
        # Insert new course
        cur.execute("""
            INSERT INTO courses (track_id, distance, surface, direction,
                               corner_count, final_straight_length, slope_info,
                               phases_json, corners_json, straights_json,
                               other_json, raw_metadata_json, gametora_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (track_id, distance, surface, direction,
              corner_count, final_straight, slope_info,
              phases_json, corners_json, straights_json,
              other_json, raw_json, course_url))
        logger.info(f"    Added course: {distance}m {surface}")
        is_new = True

    conn.commit()
    return is_new


def run_track_scraper():
    """Main entry point: scrape all racetracks and their courses"""
    print("=" * 60)
    print("GameTora Umamusume Racetrack Scraper")
    print("=" * 60)

    # Initialize database (additive only — safe for existing data)
    logger.info("Initializing database (additive tables only)...")
    init_database()

    # Create assets directory
    os.makedirs(ASSETS_PATH, exist_ok=True)

    conn = get_conn()
    tracks_added = 0
    courses_added = 0
    courses_updated = 0
    errors = 0

    with sync_playwright() as p:
        logger.info("Launching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Get all track links
        tracks = scrape_track_list(page)

        if not tracks:
            logger.error("No tracks found! The page structure may have changed.")
            browser.close()
            conn.close()
            return

        print(f"\nFound {len(tracks)} racetracks. Starting detailed scrape...\n")

        for i, track in enumerate(tracks, 1):
            print(f"\n[{i}/{len(tracks)}] {track['name']}")
            print("-" * 40)

            try:
                # Download track image
                image_path = download_track_image(track.get('image_url'), track['name'])

                # Save track to DB
                track_id = save_track_to_db(conn, track, image_path)
                tracks_added += 1

                # Scrape track detail page for courses
                track_detail = scrape_track_detail(page, track['url'])

                if not track_detail['courses']:
                    logger.warning(f"  No courses found for {track['name']}")
                    continue

                # Mark courses that may have been removed
                cur = conn.cursor()
                existing_courses = cur.execute(
                    "SELECT course_id, distance, surface FROM courses WHERE track_id = ? AND is_active = 1",
                    (track_id,)
                ).fetchall()

                scraped_combos = set((c['distance'], c['surface']) for c in track_detail['courses'])
                for cid, dist, surf in existing_courses:
                    if (dist, surf) not in scraped_combos:
                        cur.execute("UPDATE courses SET is_active = 0 WHERE course_id = ?", (cid,))
                        logger.info(f"    Deprecated course: {dist}m {surf}")
                conn.commit()

                # Scrape each course's detailed metadata
                for course in track_detail['courses']:
                    try:
                        metadata = scrape_course_metadata(page, track['url'], course)
                        is_new = save_course_to_db(conn, track_id, course, metadata, track['url'])
                        if is_new:
                            courses_added += 1
                        else:
                            courses_updated += 1
                    except Exception as e:
                        logger.error(f"    Error scraping course {course['distance']}m {course['surface']}: {e}")
                        # Save with minimal data even if metadata scraping fails
                        try:
                            save_course_to_db(conn, track_id, course, {}, track['url'])
                            courses_added += 1
                        except Exception:
                            errors += 1

                time.sleep(0.5)  # Be respectful to the server

            except Exception as e:
                logger.error(f"  Error processing track {track['name']}: {e}")
                errors += 1

        browser.close()

    # Update scraper timestamp
    set_scraper_timestamp('tracks', datetime.now().isoformat())

    conn.close()

    # Print summary
    print("\n" + "=" * 60)
    print("Racetrack Scraping Complete!")
    print(f"  Tracks processed: {tracks_added}")
    print(f"  Courses added:    {courses_added}")
    print(f"  Courses updated:  {courses_updated}")
    print(f"  Errors:           {errors}")
    print(f"  Images stored in: {ASSETS_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    run_track_scraper()
