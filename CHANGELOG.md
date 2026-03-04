# Changelog

All notable changes to the Umamusume Support Card Manager will be documented in this file.

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
