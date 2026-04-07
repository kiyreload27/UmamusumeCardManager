# Technical Change Summary: Racetrack Scraper & Course Map Visualization

## 📅 Date: 2026-02-25

## 📋 Overview
This update introduces a comprehensive racetrack management system, including automated web scraping of course metadata, local image storage, and a rich 3-panel GUI for data exploration.

---

## 🛠️ Database Changes (`db/db_queries.py`)
- **New Tables**:
  - `tracks`: Stores racetrack names, location, and local image paths.
  - `courses`: Stores detailed technical data for each course (Phases, Corners, Straights, Slopes).
  - `scraper_meta`: Tracks the last run time of different scraper types.
- **New Columns**:
  - `courses.map_image_path`: Stores the path to high-quality course visualization maps.
- **Migration Logic**: Added additive `ALTER TABLE` and `CREATE TABLE IF NOT EXISTS` statements to `init_database` and `run_migrations` to ensure data safety for existing users.

---

## 🕷️ Scraper Implementation (`scraper/track_scraper.py`)
- **Automatic Discovery**: Scrapes the list of all racetracks from GameTora.
- **Deep Metadata Extraction**: 
  - Uses Playwright to parse inline metadata for 100+ courses.
  - Correctly handles Japanese character sets (middle dots) and complex DOM structures.
  - Extracts race phases (Start/End m), corner locations, and straightaway lengths.
- **Image Pipeline**:
  - Downloads track thumbnails to `assets/tracks/`.
  - Extracts "Version for download" URLs to fetch high-res course maps into `assets/tracks/maps/`.
  - Implements image resizing (Pillow) to optimize UI performance and disk space.

---

## 🖼️ GUI Development (`gui/track_view.py`)
- **3-Panel Layout**:
  - **Left**: Searchable list of all racetracks with real-time filtering.
  - **Middle**: Racetrack hero image and a list of available courses (Turf/Dirt) with direction icons.
  - **Right**: Deep-dive detail panel showing:
    - **Course Map**: High-res visualization at the top.
    - **Overview**: Distance, surface, and slope info.
    - **Phases**: Interactive breakdown of Early/Mid/Late/Spurt sections.
    - **Structure**: Corner and Straight lists with exact meter ranges.

---

## 🚀 Integration & Build
- **CLI**: Added `python main.py --scrape-tracks` to trigger the racetrack scraper independently.
- **Main App**: Registered the new "🏟️ Track" tab in `main_window.py`.
- **Executable**: Updated `UmamusumeCardManager.spec` to bundle the new `assets/` directory.
