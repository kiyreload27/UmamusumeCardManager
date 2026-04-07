# Changelog

All notable changes to the Umamusume Support Card Manager will be documented in this file.

## [25.0.0] - 2026-04-07

### ✨ Major Features
- **Native EXE Scraper Support:** You can now run the web scraper directly from the `.exe`! The app detects if you need a Chromium browser and offers a seamless "Install Browser" button to download it automatically without touching an external terminal.
- **Background Update Checker:** The application now silently checks for GitHub updates 2 seconds after launching and highlights the "Check for Updates" button if a new version is released.
- **Bug Reporting Integration:** The `Ctrl+Shift+D` Diagnostics panel now has a "Report a Bug" button that directs you perfectly to the GitHub issue tracker to paste your debug info.

### 💄 Modern UI Refactor
- Switched to a collapsible **Sidebar Navigation** system, grouping tasks logically into *Collection*, *Planning*, and *Reference*.
- Implemented a unified Glassmorphism aesthetic via a comprehensive design token system (`gui/theme.py`).
- Added graceful "Empty State" UI screens for when no cards or data are loaded.

### 🛠️ Developer & Stability Improvements
- **Automated `.exe` Assembly:** Running `python build.py` now bundles Playwright dynamically, injects a security hash, and outputs a clean standalone app.
- **Crash Reliability:** Replaced abrupt app closures with a beautiful, graceful global Crash Dialog displaying a trace payload to send to devs.
- **Repository Structure:** Migrated to standard architecture—scripts live under `scripts/`, documentation unifies into `docs/`.

---
## [24.1.0] - 2026-03-18

### 🏇 Race Calendar — Distance Filter
- **Distance type chips**: Four toggle chips (`Short` / `Mile` / `Med` / `Long`) are now displayed in the top-right of the race calendar header. Click a chip to exclude that distance category from eligible race suggestions; click again to re-enable it. Active chips are highlighted in indigo; inactive chips turn grey.
- **Minimum grade threshold**: A new `Min Grade` dropdown (`S / A / B / C / D`, default `C`) lets you raise or lower the aptitude bar for both terrain and distance. For example, setting it to `A` limits suggestions to races where your character holds at least an A rating in both the surface and distance type.
- Both filters apply instantly (150 ms debounce) and affect the `+` button suggestions, the `⛔ Apt` warning indicator on empty slots, and the `🔄` cycle button on filled slots.

---

## [24.0.1] - 2026-03-17

### 🐛 Bug Fixes
- **Race Calendar**: Fixed a critical issue where the executable (frozen) build would silently fail to synchronize track and race data from the seed database, resulting in an unresponsive `+` button and empty race selection calendar.

---

## [24.0.0] - 2026-03-16

### 🎨 Complete UI Redesign & Modernization
- **New Warm Theme**: Replaced the previous cold indigo palette with a warmer, more readable charcoal and rose gold design system (`theme.py`) to reduce eye strain and better match the source material aesthetic.
- **Collapsible Sidebar Navigation**: Replaced the top tab bar with a collapsible left sidebar (`main_window.py`), grouping views into Collection, Planning, and Reference categories for easier access.
- **Deck Builder Overhaul**: Completely redesigned the layout to feature a 2x3 card slot grid and an effect summary sidebar alongside the card browser, fixing a layout crash that prevented loading.
- **Card Library Improvements**: Switched to a cleaner 3-column grid layout with top-header filters, and fixed an issue where owned cards rendered incorrectly large.
- **Collection Dashboard**: Redesigned to feature large metric cards and canvas-based radial progress rings for rarity breakdown.
- **Better Information Density**: Redesigned effects, hints/skills, and deck skills views with tighter layouts, smaller chips, and grouped blocks to prioritize scannability.
- **Race Calendar Polish**: Enhanced slot sizing, tighter padding, and added grade-colored visual accents for a crisp 4x6 grid.

---

## [23.0.0] - 2026-03-16

### 🏟️ Tracks — Enhanced Search
- **Search by course type**: The existing search bar in the Tracks tab now matches course attributes, not just track names
  - **Distance**: type `long`, `medium`, `mile`, `sprint`, or `short` to show only tracks that have courses of that distance category
  - **Surface**: type `turf` or `dirt` to filter to tracks with those course types
  - **Direction**: type `left`, `right`, or `straight` to filter by course turn direction
  - Track name and location still match as before
- Course data is pre-loaded at startup so filtering is instant with no extra DB queries
- Updated search placeholder to `Search by name, turf, long, dirt…` to hint at the new capabilities

---

## [22.0.0] - 2026-03-04

### 🎴 Race Calendar Improvements
- **Race Badge Images**: Each calendar slot now displays the race's own badge image (scraped from GameTora) instead of the generic track photo
- **Race Name Label**: Race name is now shown between the badge image and the terrain/distance row for clarity
- **Senior Year Full Coverage**: Senior Year calendar now correctly shows Classic Class races (Japan Cup, Arima Kinen, Tenno Sho Autumn, etc.) since Senior Year horses are eligible for those races — all 12 months now have schedulable races
- **Image Resolution**: `resolve_image_path()` now handles `assets/races/` and `assets/tracks/` subdirectories and resolves relative paths from project root (works both in source and bundled exe)

### 🕷️ Race Scraper (v2)
- Re-scrapes all **376 races** from GameTora (previously missed ~150 Senior Year races due to insufficient scrolling)
- Downloads race **badge images** (`assets/races/`) for each race during scraping
- Stores `image_path` in the `races` table for direct badge display
- `get_all_races()` now returns `COALESCE(r.image_path, t.image_path)` — race badge preferred, track photo as fallback

### 🗄️ Database
- Added `image_path TEXT` column to `races` table (auto-migrated on first launch)

---

## [21.0.0] - 2026-03-04

### 🐛 Bug Fixes

#### Deck Builder — Level Display (Definitive Fix)
- **Root cause identified**: `CTkComboBox.configure(state='disabled')` was re-rendering the widget from its bound `StringVar`, which still held the stale default `"50"` — resetting the display even after `set()` was called
- **Fix**: `level_var` is now set **before** any `configure()` calls, and set again **after** `toggle_controls()`, guaranteeing the correct level is always shown regardless of widget state transitions
- Added `int()` coercion guard on the level value from SQLite (handles potential float/None return)
- R cards now correctly display level 40 max, SR shows 45, SSR shows 50

#### Backup & Restore Dialog
- **Restore button was invisible**: `style_type='ghost'` rendered the button with near-invisible text on the dark background
- Button replaced with an explicit `CTkButton` styled with amber border/text, making it clearly visible
- Dialog height increased from 420px to 500px to prevent content clipping

---

## [20.0.0] - 2026-03-04

### 🐛 Bug Fixes

#### Deck Builder — Rarity Filter
- **Root cause**: `CTkSegmentedButton` does not update a bound `tk.StringVar` — the filter was always reading `"All"` regardless of the selected segment
- **Fix**: `filter_cards()` now calls `self.rarity_seg.get()` directly on the widget, bypassing the stale variable
- Removed the now-unused `self.rarity_var` StringVar

#### Deck Builder — Load Deck Auto-Repair
- `load_deck()` now detects and corrects any cards stored with a level exceeding their rarity maximum (legacy data fix)
- Corrected levels are written back to the database permanently on first load

#### Deck Builder — Effects Box Empty for R Cards
- `update_effects_breakdown()` now caps the level by rarity before fetching effects, so R cards at level 40 correctly populate the effects panel

---

## [19.0.0] - 2026-03-04

### 🎨 UI Improvements
- **Tab Bar Centred**: Main navigation tab bar is now horizontally centred (`anchor="n"`) instead of left-aligned
- **Timeline & Upgrade Tabs Removed**: Removed the unfinished "Timeline" and "Upgrade" planning tabs from the navigation to reduce clutter

### 🗺️ Race Calendar
- **Track Thumbnails**: Race cards in the Tracks view now display a 56×38px thumbnail of the track image next to the track name, with in-memory caching and an initials fallback

### 🎴 Deck Builder
- **Rarity Segmented Filter Added**: New `All / SSR / SR / R` segmented button filter in the Deck Builder card browser (foundation for the fix in v20)

---

## [18.0.0] - 2026-03-04


### 🎨 Complete UI/UX Overhaul
- **Responsive Sizing**: The app dynamically scales to screens, gracefully handling both full-screen and smaller 900x600 windows.
- **Collapsible Sidebar**: New toggle ("☰") minimizes the sidebar to icons only, freeing up precious screen real-estate.
- **Adaptive Layouts**:
  - The **Card Library** list panel and details panel can now dynamically resize.
  - Added a collapsible detail panel (◀/▶ button) that lets the card grid expand to use the full window width.
- **Aesthetic Improvements**: Rounded corners, new themed accents, and better typography spacing across all views.

### 📊 Collection Progress Dashboard (Phase 4)
- **New Default View**: The app now launches to a comprehensive dashboard summarizing your collection.
- Includes total card counts, ownership percentage, and missing card tracking.
- Visual completion progress bars breakdown your collection by:
  - **Rarity** (SSR, SR, R)
  - **Card Type** (Speed, Stamina, Power, Guts, Intelligence, Group)

### 📅 Training Event Timeline (Phase 4)
- New **Planning > Timeline** view to explore training events for specific cards.
- Visual timeline with distinct nodes for events, branching choices, and skill acquisition paths.
- Color-coded choices highlight stat gains and unique skill unlocks.

### 📈 Card Upgrade Planner (Phase 4)
- New **Planning > Upgrade** view to compare card stats at different levels (e.g., Lv30 vs Lv50).
- Side-by-side diff table instantly shows stat improvements (green) and losses (red).
- Displays the level requirements for unlocking Unique Effects.

### 🐛 Bug Fixes
- **Deck Builder**: Fixed an issue where dropping a card into a deck slot would incorrectly override the card's level to 50 regardless of rarity/ownership.
- **Race Calendar**: Fixed a bug where characters were missing from the selection screen due to the database sync overriding new characters. Characters are now synced properly, and image paths correctly point to `assets/characters`.

## [17.0.0] - 2026-03-04

### 🚀 New Features

#### Recently Viewed Cards
- A **"🕒 Recent"** strip now appears at the top of the Card Library showing the last 10 cards you viewed
- Click any thumbnail to jump back to that card instantly
- Hover for card name tooltips
- Session-scoped — resets when you close the app

#### Keyboard Navigation
- **Ctrl+F** — Focus the search bar from anywhere
- **↑/↓ Arrow Keys** — Navigate through the card list (works from the search bar too)
- **Enter** — Select the highlighted card
- **Escape** — Progressively clears: search text → exits bulk mode → resets all filters

#### Bulk Ownership Toggle
- Click the **"☐ Select"** button in the Card Library to enter bulk selection mode
- Checkboxes appear on every card in the list
- **All / None** buttons for quick selection
- **✓ Mark Owned** and **✗ Unown** buttons to batch-update all selected cards in one click
- Press Escape to exit bulk mode

#### Cross-View Card Linking
- Card names are now **clickable** (shown in accent color with pointer cursor) in:
  - Effect Search results
  - Skill Search results
  - Deck Skills card blocks
- Clicking a card name **navigates to the Card Library** and auto-selects that card

#### Notes & Tags on Cards
- Add **personal notes** and **custom tags** to any card via the detail panel
- Tags appear as colored chips — click to filter the entire library by tag
- New "Tag" filter dropdown in the Card Library filter bar
- Data persists in the database across sessions

#### Backup & Restore User Data
- New **Backup/Restore** button in the sidebar footer
- **Export** all user data (owned cards, decks, deck slots, notes/tags) as a `.json` file
- **Import** a backup file to restore your collection — with overwrite confirmation
- Great for transferring data between machines or before updating

#### Advanced Multi-Filter for Cards
- New **"Effect"** dropdown filter in the Card Library
- Filter cards that have a specific effect (e.g., "Training Bonus", "Friendship Bonus")
- Combines with existing rarity, type, search, and owned-only filters for powerful compound queries

### 🔧 Technical Changes
- Added `set_cards_owned_bulk()` for efficient batch ownership operations
- Added `user_notes` table for card notes and tags
- Added `get_card_notes()`, `set_card_notes()`, `get_all_tags()`, `search_cards_by_tag()` query functions
- Added `export_user_data()` and `import_user_data()` for backup/restore
- Added `get_all_effect_names()` for populating the effect filter dropdown
- Extended `get_all_cards()` to support `effect_filter` parameter
- Added `export_single_deck()` and `import_single_deck()` for per-deck JSON export/import
- Added `navigate_to_card()` cross-view navigation to `MainWindow`
- Added `navigate_to_skill()` for cross-view skill navigation
- All views now accept `navigate_to_card_callback` parameter
- `DeckSkillsFrame` now accepts `navigate_to_skill_callback` — skill names are clickable

### 🎴 Deck Enhancements

#### Deck Comparison
- Compare two decks side-by-side with an effects diff table
- Green/red color-coded differences show which deck is better for each effect
- Accessible via **⚖️ Compare** button in the Deck Builder

#### Export/Import Decks
- **� Export** any deck to a portable `.json` file
- **📥 Import** a deck file to create a new deck (matches cards by URL)
- Great for sharing deck builds with friends

#### Cards With This Skill (from Deck View)
- Skill names in the Deck Skills view are now **clickable**
- Clicking a skill name switches to the Skill Search view and shows all cards with that skill

#### Drag-and-Drop Deck Building
- **Drag cards** from the browser directly onto deck slots
- Slots highlight when a card is hovered over them
- Drop onto an occupied slot to replace that card

### �📁 Files Changed
- `gui/card_view.py` — Recently viewed, keyboard nav, bulk ownership, notes/tags UI, effect filter
- `gui/main_window.py` — Cross-view navigation, backup button, skill navigation
- `gui/effects_view.py` — Clickable card names
- `gui/hints_skills_view.py` — Clickable card names
- `gui/deck_skills_view.py` — Clickable card names + clickable skill names
- `gui/backup_dialog.py` — **NEW** — Backup/restore dialog
- `gui/deck_comparison.py` — **NEW** — Side-by-side deck comparison
- `gui/deck_builder.py` — Drag-and-drop, export/import, comparison button
- `db/db_queries.py` — Bulk ownership, notes/tags, backup/restore, effect filter, deck export/import
