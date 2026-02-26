# 🏁 Project Update: Racetracks, Dynamic UI, and Data Safety
**Version 15.1.0 — February 25, 2026**

This document provides a comprehensive summary of all major updates, technical implementation details, and distribution instructions for the latest release of the Umamusume Support Card Manager.

---

## 🌟 New Features

### 🏟️ Track tab Implementation
A brand-new, 3-panel browser for racetracks and course data:
- **Left Panel**: Searchable list of all racetracks with real-time filtering.
- **Middle Panel**: Racetrack overview with high-quality thumbnails and a list of available courses (Turf/Dirt) with direction/distance icons.
- **Right Panel**: Deep-dive technical breakdown for the selected course, including:
  - **Dynamic Course Maps**: High-resolution visualization scaling based on window size.
  - **Metrical Breakdown**: Exact meter ranges for Phases (Early/Mid/Late/Spurt), Corners, and Straights.
  - **Environmental Details**: Slope information, weather patterns, and specific terrain notes.

### 📱 Responsive UI Scaling & High-Res Support
- **Adaptive Resolution**: The app now detects 1080p+ screens on launch and scales the initial window size and panel widths for a balanced look.
- **Dynamic Map Resizing**: Course maps automatically grow or shrink to fill available space, ensuring maximum readability on both laptop screens and 4K monitors.
- **Balanced Layout**: Panel widths have been adjusted to prevent "wasted space" on wide displays.

---

## 🛠️ Technical Implementation

### 🕷️ Intelligent Scraper (`scraper/track_scraper.py`)
- **Playwright-Powered**: Automates data extraction from GameTora, handling complex DOM structures and asynchronous content.
- **Rich Media Discovery**: Automatically finds and downloads "Version for download" map images.
- **Resilient Logic**: Uses idempotent patterns (INSERT/UPDATE) so the scraper can be re-run safely at any time to refresh data.

### 🗄️ Database Architecture (`db/db_queries.py`)
- **New Master Tables**: `tracks` and `courses` store the scraped data without affecting existing user data.
- **System Metadata**: `scraper_meta` and `system_metadata` track versions and runtimes to ensure smooth migrations.
- **Additive Evolution**: All changes use `CREATE TABLE IF NOT EXISTS` and additive `ALTER TABLE` commands, making the update 100% safe for existing databases.

---

## 🛡️ Data Safety & Distribution

### 🔒 User Data Protection
The most critical part of this update is ensuring **your data stays intact**:
- **Protected Seeding**: The `is_db_empty` logic was refactored to check only for master card data. It **will not** overwrite an existing database just because tracks are missing.
- **Robust Synchronization**: The `sync_from_seed` function has been expanded to automatically merge new racetrack and course data into your existing database on first launch of v15.1.0, while strictly preserving your `owned_cards` and `user_decks`.

### 🚀 Distribution Instructions for Friends
1.  **Shared the Build**: Send your friends the new `UmamusumeCardManager.exe` found in the `dist/` folder.
2.  **No Scraping Needed**: The build is fully bundled with the latest racetrack database and 1150+ course map images.
3.  **Just Launch**: On launch, their existing database will automatically upgrade to include the new Track features without losing their deck progress.

---

## 🐛 Bug Fixes
- **Scroll Conflict Fixed**: Resolved a conflict between window resize listeners and scrollable frames that made scrolling "sticky" or non-responsive.
- **Recursive Scroll Propagation**: Implemented a helper to ensure mouse wheel events correctly reach the scroll panels even when hovering over maps or labels.
- **Data Loss Risk Resolved**: Tightened initialization checks to prevent accidental overwrites of existing user databases.

---

**Built with ❤️ for Umamusume fans.**
