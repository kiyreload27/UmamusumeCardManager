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

MAPS_PATH = os.path.join(ASSETS_PATH, 'maps')

# Thumbnail size for track images (fits within the app UI)
TRACK_IMAGE_SIZE = (300, 200)
MAP_IMAGE_SIZE = (1000, 600)  # Course maps are wider


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
    """Scrape a single track's detail page to get ALL courses and their metadata.
    
    GameTora lists courses as h2 headings (e.g. '1200 m・Turf') with a Japanese
    middle dot (U+30FB). ALL course data is inline on the same page — no navigation
    needed. Each course section contains Phases, Corners, Straights, and Other data.
    """
    logger.info(f"  Loading track detail: {track_url}")
    page.goto(track_url, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # Scroll to ensure all lazy-loaded content is rendered
    for _ in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)

    # Extract ALL courses and their metadata in a single JS call
    track_data = page.evaluate("""
        () => {
            const data = {
                courses: [],
                location: null
            };

            // Find all h2 course headings using Japanese middle dot
            const h2s = Array.from(document.querySelectorAll('h2'));
            const courseH2s = h2s.filter(h => {
                const t = h.textContent.trim();
                return /\\d+\\s*m\\s*[\\u30FB\\u00B7]\\s*(Turf|Dirt)/i.test(t);
            });

            for (const h2 of courseH2s) {
                const headerText = h2.textContent.trim();
                const hMatch = headerText.match(/(\\d+)\\s*m\\s*[\\u30FB\\u00B7]\\s*(Turf|Dirt)/i);
                if (!hMatch) continue;

                const distance = parseInt(hMatch[1]);
                const surface = hMatch[2];

                // Collect text and links from h2's siblings until the next course h2.
                const parent = h2.parentElement;
                const siblings = Array.from(parent.children);
                const myIdx = siblings.indexOf(h2);
                let sectionText = '';
                let mapImageUrl = null;
                for (let j = myIdx; j < siblings.length; j++) {
                    if (j > myIdx && siblings[j].tagName === 'H2') break;
                    
                    const sib = siblings[j];
                    sectionText += (sib.innerText || '') + '\\n';
                    
                    // Look for the "Version for download" link
                    const links = sib.querySelectorAll('a');
                    for (const a of links) {
                        if (a.textContent.includes('Version for download')) {
                            mapImageUrl = a.href;
                        }
                    }
                }

                // "Version for download" separates viz labels from actual data
                const vIdx = sectionText.indexOf('Version for download');
                const dataText = vIdx !== -1 ? sectionText.substring(vIdx) : sectionText;

                // Locate data sub-section boundaries
                const phasesIdx = dataText.indexOf('Phases');
                const cornersIdx = dataText.indexOf('Corners');
                const straightsIdx = dataText.indexOf('Straights');
                // Find 'Other' AFTER Straights to avoid matching label text
                const otherIdx = straightsIdx !== -1
                    ? dataText.indexOf('Other', straightsIdx + 10)
                    : dataText.lastIndexOf('Other');

                const phaseBlock = (phasesIdx !== -1 && cornersIdx > phasesIdx)
                    ? dataText.substring(phasesIdx, cornersIdx) : '';
                const cornerBlock = (cornersIdx !== -1 && straightsIdx > cornersIdx)
                    ? dataText.substring(cornersIdx, straightsIdx) : '';
                const straightBlock = (straightsIdx !== -1 && otherIdx > straightsIdx)
                    ? dataText.substring(straightsIdx, otherIdx)
                    : (straightsIdx !== -1 ? dataText.substring(straightsIdx) : '');
                const otherBlock = otherIdx !== -1 ? dataText.substring(otherIdx) : '';

                // ── Phases ──
                const phases = {};
                const phaseNames = ['Early-Race', 'Mid-Race', 'Late-Race', 'Last Spurt'];
                for (const phase of phaseNames) {
                    const re = new RegExp(
                        phase + '[\\\\s\\\\S]*?Start:\\\\s*(\\\\d+)\\\\s*m[\\\\s\\\\S]*?End:\\\\s*(\\\\d+)\\\\s*m', 'i'
                    );
                    const m = phaseBlock.match(re);
                    if (m) {
                        phases[phase] = { start: parseInt(m[1]), end: parseInt(m[2]) };
                    }
                }

                // ── Corners ──
                const corners = [];
                const cornerRe = /Corner\\s*(\\d+)[\\s\\S]*?Start:\\s*(\\d+)\\s*m[\\s\\S]*?End:\\s*(\\d+)\\s*m/gi;
                let cm;
                while ((cm = cornerRe.exec(cornerBlock)) !== null) {
                    corners.push({
                        name: 'Corner ' + cm[1],
                        start: parseInt(cm[2]),
                        end: parseInt(cm[3])
                    });
                }

                // ── Straights ──
                const straights = [];
                const strRe = /Straight\\s*(\\d+)[\\s\\S]*?Start:\\s*(\\d+)\\s*m[\\s\\S]*?End:\\s*(\\d+)\\s*m/gi;
                let sm;
                while ((sm = strRe.exec(straightBlock)) !== null) {
                    straights.push({
                        name: 'Straight ' + sm[1],
                        start: parseInt(sm[2]),
                        end: parseInt(sm[3])
                    });
                }

                // ── Other ──
                const other = {};
                const pkRe = /Position\\s*Keep[\\s\\S]*?Start:\\s*(\\d+)\\s*m[\\s\\S]*?End:\\s*(\\d+)\\s*m/i;
                const pkM = otherBlock.match(pkRe);
                if (pkM) {
                    other['position_keep'] = { start: parseInt(pkM[1]), end: parseInt(pkM[2]) };
                }

                const spurtRe = /Spurt[\\s\\S]*?Start:\\s*(\\d+)\\s*m/i;
                const spM = otherBlock.match(spurtRe);
                if (spM) {
                    other['spurt'] = { start: parseInt(spM[1]) };
                    const rest = otherBlock.substring(otherBlock.indexOf(spM[0]) + spM[0].length);
                    const noteRe = /^\\s*(Final Corner|Corner|Straight)/im;
                    const noteM = rest.match(noteRe);
                    if (noteM) other['spurt']['note'] = noteM[1];
                }

                const statRe = /Stat\\s*Thresholds[\\s\\S]*?\\n\\s*(.+)/i;
                const stM = otherBlock.match(statRe);
                if (stM) {
                    other['stat_thresholds'] = stM[1].trim();
                }

                // ── Final straight length ──
                let finalStraightLen = null;
                if (straights.length > 0) {
                    const last = straights[straights.length - 1];
                    finalStraightLen = (last.end - last.start) + ' m';
                }

                data.courses.push({
                    distance,
                    surface,
                    text: headerText,
                    direction: null,
                    corner_count: corners.length,
                    final_straight_length: finalStraightLen,
                    slope_info: null,
                    phases,
                    corners,
                    straights,
                    other,
                    map_image_url: mapImageUrl,
                    raw_text: dataText.substring(0, 3000)
                });
            }

            return data;
        }
    """)

    logger.info(f"    Found {len(track_data['courses'])} courses")
    return track_data


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


def download_course_map_image(img_url, track_name, distance, surface):
    """Download and resize a course map image"""
    os.makedirs(MAPS_PATH, exist_ok=True)

    if not img_url:
        return None

    # Clean filename: Track_Distance_Surface.png
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', f"{track_name}_{distance}m_{surface}")
    file_path = os.path.join(MAPS_PATH, f"{safe_name}.png")

    # Skip if already exists
    if os.path.exists(file_path):
        return file_path

    try:
        # Download
        response = requests.get(img_url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # No thumbnail resize for maps to keep detail, just ensure it's not insane
            if img.size[0] > MAP_IMAGE_SIZE[0]:
                img.thumbnail(MAP_IMAGE_SIZE, Image.Resampling.LANCZOS)

            # Save as PNG
            img.save(file_path, 'PNG')
            logger.info(f"    Downloaded map: {safe_name}.png")
            return file_path
        else:
            logger.warning(f"    Failed to download map: HTTP {response.status_code}")
    except Exception as e:
        logger.warning(f"    Could not download map for {track_name} {distance}m: {e}")

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


def save_course_to_db(conn, track_id, course, metadata, track_url, map_image_path=None):
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
                map_image_path = COALESCE(?, map_image_path),
                is_active = 1
            WHERE course_id = ?
        """, (direction, corner_count, final_straight, slope_info,
              phases_json, corners_json, straights_json, other_json,
              raw_json, course_url, map_image_path, existing[0]))
        logger.info(f"    Updated course: {distance}m {surface}")
        is_new = False
    else:
        # Insert new course
        cur.execute("""
            INSERT INTO courses (track_id, distance, surface, direction,
                                corner_count, final_straight_length, slope_info,
                                phases_json, corners_json, straights_json,
                                other_json, raw_metadata_json, gametora_url, map_image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (track_id, distance, surface, direction,
              corner_count, final_straight, slope_info,
              phases_json, corners_json, straights_json,
              other_json, raw_json, course_url, map_image_path))
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

                # Save each course (metadata is already embedded from scrape_track_detail)
                for course in track_detail['courses']:
                    try:
                        # Download course map image
                        map_image_path = download_course_map_image(
                            course.get('map_image_url'), 
                            track['name'], 
                            course['distance'], 
                            course['surface']
                        )
                        
                        is_new = save_course_to_db(conn, track_id, course, course, track['url'], map_image_path)
                        if is_new:
                            courses_added += 1
                        else:
                            courses_updated += 1
                    except Exception as e:
                        logger.error(f"    Error saving course {course['distance']}m {course['surface']}: {e}")
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
