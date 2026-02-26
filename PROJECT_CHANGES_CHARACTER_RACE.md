# Character & Race Scraper — Changes Documentation

## Overview
Added **character aptitude scraping** and **race detail scraping** from GameTora, with two new GUI tabs to browse the data. All changes are **additive-only** — existing user data (owned cards, decks, etc.) is never touched.

---

## New Files

### Scrapers
| File | Purpose |
|------|---------|
| `scraper/character_scraper.py` | Scrapes all playable characters from `gametora.com/umamusume/characters`, including name, portrait image, and aptitude data (Surface/Distance/Strategy grades) |
| `scraper/race_scraper.py` | Scrapes all races from `gametora.com/umamusume/races`, clicking each "Details" modal to extract racetrack, grade, terrain, distance, direction, participants, season, time of day |

### GUI Views
| File | Purpose |
|------|---------|
| `gui/character_view.py` | **🐴 Characters** tab — 2-panel layout with scrollable character grid (images + mini aptitude badges) and detail panel with color-coded aptitude grades |
| `gui/race_view.py` | **🏁 Races** tab — Filterable race list (by grade/terrain/distance) with detail panel showing all race properties |

---

## Modified Files

### `db/db_queries.py`
- Added `characters` table (16 columns including aptitude grades)
- Added `races` table (16 columns including race details)
- Added `sync_from_seed()` logic for characters and races (wrapped in try/except for backwards compatibility)
- Added query functions: `get_all_characters()`, `get_character_count()`, `get_all_races()`, `get_race_count()`
- Added indexes for performance

### `gui/main_window.py`
- Imported `CharacterViewFrame` and `RaceViewFrame`
- Added `🐴 Characters` and `🏁 Races` tabs

### `main.py`
- Added `--scrape-characters` and `--scrape-races` CLI flags
- Added `run_character_scraper()` and `run_race_scraper()` functions

---

## Data Safety for Updates

All changes follow the existing safe-update pattern:

1. **`CREATE TABLE IF NOT EXISTS`** — New tables are only created if they don't already exist
2. **`ON CONFLICT` upserts** — Re-running scrapers updates data without duplicating
3. **`sync_from_seed()`** — Character and race data sync is wrapped in `try/except sqlite3.OperationalError` so it gracefully handles:
   - Old seed databases that don't have these tables yet
   - Users who haven't run the new scrapers yet
4. **User data is never deleted** — `owned_cards`, `user_decks`, `deck_slots` tables are completely untouched

---

## CLI Commands

```bash
# Launch GUI (default)
python main.py

# Run character scraper
python main.py --scrape-characters

# Run race scraper
python main.py --scrape-races

# Existing scraper commands still work
python main.py --scrape           # Support cards
python main.py --scrape-tracks    # Racetracks
```

---

## Database Schema

### `characters` table
| Column | Type | Description |
|--------|------|-------------|
| character_id | INTEGER PK | Auto-increment ID |
| name | TEXT | Character name |
| gametora_id | TEXT UNIQUE | Stable ID from GameTora URL |
| gametora_url | TEXT | Full GameTora URL |
| image_path | TEXT | Path to downloaded portrait |
| turf_aptitude | TEXT | Letter grade (S-G) |
| dirt_aptitude | TEXT | Letter grade (S-G) |
| short_aptitude | TEXT | Letter grade (S-G) |
| mile_aptitude | TEXT | Letter grade (S-G) |
| medium_aptitude | TEXT | Letter grade (S-G) |
| long_aptitude | TEXT | Letter grade (S-G) |
| runner_aptitude | TEXT | Letter grade (S-G) |
| leader_aptitude | TEXT | Letter grade (S-G) |
| betweener_aptitude | TEXT | Letter grade (S-G) |
| chaser_aptitude | TEXT | Letter grade (S-G) |
| is_active | INTEGER | Soft delete flag |

### `races` table
| Column | Type | Description |
|--------|------|-------------|
| race_id | INTEGER PK | Auto-increment ID |
| name_en | TEXT | English race name |
| name_jp | TEXT | Japanese race name |
| grade | TEXT | GI, GII, GIII, OP, Pre-OP |
| racetrack | TEXT | Track/venue name |
| direction | TEXT | Left, Right, or Straight |
| participants | INTEGER | Max runners |
| terrain | TEXT | Turf or Dirt |
| distance_type | TEXT | Short, Mile, Medium, Long |
| distance_meters | INTEGER | Exact distance in meters |
| season | TEXT | Spring, Summer, Autumn, Winter |
| time_of_day | TEXT | Day, Evening, Night |
| race_date | TEXT | When the race occurs |
| race_class | TEXT | Eligibility class |
| gametora_url | TEXT UNIQUE | Dedup key |
| is_active | INTEGER | Soft delete flag |
