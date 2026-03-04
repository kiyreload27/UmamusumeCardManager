# AGENTS.md

This file provides guidance to AI agents (Warp, Gemini, etc.) when working with code in this repository.

## Project Overview

Umamusume Support Card Manager — a Python desktop app (CustomTkinter GUI) that manages support cards, decks, characters, racetracks, and races for the game Umamusume. Data is scraped from GameTora and stored in a local SQLite database. The app is distributed as a single-file Windows executable via PyInstaller.

## Commands

### Run the app
```
python main.py
```

### Run individual scrapers
```
python main.py --scrape              # Support cards
python main.py --scrape-tracks       # Racetracks/courses
python main.py --scrape-characters   # Character aptitudes
python main.py --scrape-races        # Race details
```

### Build the executable
```
python build.py
```
This runs `scripts/prepare_release_db.py` (creates a seed database stripped of user data) then PyInstaller with `UmamusumeCardManager.spec`.

### Install dependencies
```
pip install -r requirements.txt
```
Key runtime deps: `playwright`, `beautifulsoup4`, `requests`, `Pillow`. The GUI uses `customtkinter` (imported but not in requirements.txt). Scrapers require Playwright browser installation (`playwright install`).

## Architecture

### Data flow
GameTora website → `scraper/` (Playwright + BeautifulSoup) → SQLite DB (`database/umamusume.db`) → `db/db_queries.py` → `gui/` views

### Database layer (`db/`)
- **`db_init.py`**: Schema definitions and migrations (used during development/reset). `DB_PATH` is relative to project root.
- **`db_queries.py`**: All query functions used by the GUI and scrapers. Contains its own `init_database()` with the complete schema, migration logic (`run_migrations()`), seed database sync (`sync_from_seed()`), and orphan data repair. This is the primary DB module at runtime — `db_init.py` is mostly legacy.
- **`get_conn()`** in `db_queries.py` is the single entry point for DB connections. On first call per session it runs migrations and update checks.
- The DB has two modes: development (path relative to source) and frozen/exe (path relative to `sys.executable`, with seed DB copied from `sys._MEIPASS`).

### Database tables
- **Master data** (populated by scrapers): `support_cards`, `support_effects`, `support_hints`, `support_events`, `event_skills`, `tracks`, `courses`, `characters`, `races`
- **User data** (preserved across updates): `owned_cards`, `user_decks`, `deck_slots`
- **Metadata**: `system_metadata` (tracks app version for seed sync), `scraper_meta` (last scrape timestamps)
- Cards are linked by `gametora_url` (stable identifier from GameTora). Effects are stored per card per level (levels 20/25/30/35/40/45/50). Events and skills have a two-level hierarchy: `support_events` → `event_skills`.

### Scraper modules (`scraper/`)
Each scraper uses Playwright to render JavaScript-heavy GameTora pages, then extracts data with `page.evaluate()` JavaScript and BeautifulSoup. They share common patterns: navigate, wait for network idle, scroll for lazy-loaded content, parse DOM, insert into DB.

- `gametora_scraper.py`: Scrapes all support cards, effects at key levels, hints, events, event skills, and downloads card art images to `images/`.
- `track_scraper.py`: Scrapes racetracks and course details (distance, surface, slope, phases JSON).
- `character_scraper.py`: Scrapes character aptitude data (surface, distance, running style).
- `race_scraper.py`: Scrapes individual race details (grade, terrain, participants, etc.).

### GUI (`gui/`)
Built with **CustomTkinter** (ctk) for modern widgets. Uses a sidebar navigation layout with grouped sections. Views are lazily loaded on first access.

- `main_window.py`: Root window with grouped sidebar navigation (Collection / Planning / Reference), dynamic window title, keyboard shortcuts (`Ctrl+1-7`), and cross-view communication via callbacks.
- `theme.py`: Centralized design system — indigo/violet color palette, glassmorphism surface layers (`BG_DARKEST` through `BG_ELEVATED`), spacing tokens (`SPACING_XS` through `SPACING_2XL`), radius tokens (`RADIUS_SM` through `RADIUS_FULL`), typography scale (`FONT_DISPLAY` through `FONT_MONO`), race grade colors (`GRADE_COLORS`), and 10+ widget factory functions (`create_styled_button`, `create_styled_entry`, `create_card_frame`, `create_glass_frame`, `create_section_header`, `create_badge`, `create_stat_bar`, `create_divider`, `create_icon_label`, etc.).
- Views: `card_view.py` (card library with segmented level control, ownership toggle), `effects_view.py` (effect search with quick-filter chips), `deck_builder.py` (6-slot deck with effects breakdown table), `hints_skills_view.py` (skill search with source badges), `deck_skills_view.py` (deck skill breakdown by card), `track_view.py` (3-panel track/course browser), `race_calendar_view.py` (character aptitude calendar with grade-colored race slots).
- `update_dialog.py`: In-app update flow (check GitHub releases, download, self-replace via batch script).
- Legacy: `deck_view.py` (small helper popup, largely unused).

### Versioning
`version.py` is the single source of truth for `VERSION`, `APP_NAME`, and `GITHUB_REPO`. The version is embedded in the seed DB during build and compared at runtime for data sync.

### Image handling
`utils.py` provides `resolve_image_path()` which searches multiple locations (PyInstaller `_MEIPASS`, exe directory, source `images/` folder) to resolve image filenames stored as relative paths in the DB.

### Build & distribution
- `UmamusumeCardManager.spec`: PyInstaller spec bundles `images/`, `assets/`, `database/umamusume_seed.db`, `version.py`, and `updater/` into a single `.exe` (console=False).
- `scripts/prepare_release_db.py`: Copies the dev DB to a seed DB, strips user data (`owned_cards`, `user_decks`, `deck_slots`), injects version into `system_metadata`, and vacuums.
- The updater downloads a new `.exe` from GitHub Releases and replaces itself via a generated batch script.

### Frozen vs. development mode
Many modules check `getattr(sys, 'frozen', False)` to switch between development paths (relative to `__file__`) and frozen paths (relative to `sys.executable` / `sys._MEIPASS`). When modifying path logic, always handle both modes.

## Conventions
- All DB access goes through functions in `db/db_queries.py` — never use raw `sqlite3.connect()` in GUI code.
- New DB columns are added via try/except `ALTER TABLE` migrations in `run_migrations()` (idempotent pattern).
- GUI widget styling **must** use constants and factories from `gui/theme.py`. Never hardcode colors, fonts, or spacing — use the token system (`BG_DARK`, `SPACING_SM`, `RADIUS_MD`, `FONT_BODY`, etc.).
- Views use chunked rendering (processing widgets in batches of 5-10 via `after()`) with generation counters for cancellation to maintain UI responsiveness.
- Scraper image filenames use the pattern `{gametora_stable_id}_{safe_card_name}.png`.
- `config/settings.py` exists but is mostly unused at runtime — `db_queries.py` and individual modules define their own paths and constants.
