# Umamusume Support Card Manager

A desktop tool for managing support cards and planning training runs in Umamusume: Pretty Derby.

---

## Features

| Feature | Description |
|---|---|
| 🃏 **Card Library** | Browse all support cards, search by name/type/rarity, mark cards as owned |
| 🎴 **Deck Builder** | Build and save 6-card decks, compare effect totals, export/import deck files |
| 🔎 **Effect Search** | Find cards that have a specific effect (e.g. "Friendship Bonus") |
| 📜 **Skill Search** | Search across all card skills and hint skills |
| 📊 **Deck Skills** | See every skill your current deck can teach in one view |
| 📅 **Race Calendar** | Plan your Uma's race schedule with aptitude warnings |
| 🏟 **Track Browser** | Browse all racetracks and course details |
| 📊 **Dashboard** | Visual overview of your collection progress by rarity and type |
| 💾 **Backup / Restore** | Export and import your owned cards, decks, and notes as a JSON file |
| 🔄 **Auto-Updater** | Check for and install new releases directly within the app |
| 🛠 **Diagnostics** | Built-in debug panel for troubleshooting (`Ctrl+Shift+D`) |

---

## Quick Start (Windows EXE)

1. Download the latest `UmamusumeCardManager.exe` from the [Releases page](../../releases)
2. Run the `.exe` — no installation required
3. On first launch you'll see a welcome screen. Click **Skip** if you already have a database, or follow the instructions to populate card data

> **The app ships with a pre-built database.** You normally don't need to run the scraper manually unless you want the very latest cards.

---

## First-Time Setup — Populating Card Data (Developers / Advanced Users)

If you're running from source or want to re-scrape fresh data:

### Prerequisites
- Python 3.11 or higher
- Playwright + Chromium browser

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser
playwright install chromium
```

### Scraping
```bash
# Scrape support cards (main data, takes ~5-10 min)
python main.py --scrape

# Scrape racetracks and courses
python main.py --scrape-tracks

# Scrape character aptitude data
python main.py --scrape-characters

# Scrape individual race details
python main.py --scrape-races
```

---

## Running from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the GUI
python main.py

# Enable verbose debug logging
python main.py --log-level DEBUG
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+1` through `Ctrl+9` | Switch between views |
| `Ctrl+F` | Focus the search bar (Card Library) |
| `↑ / ↓` | Navigate card list |
| `Enter` | Select highlighted card |
| `Escape` | Clear search / exit bulk mode |
| `Ctrl+Shift+D` | Open Diagnostics panel |

---

## Log Files

When something goes wrong, the app writes detailed logs to:

- **Windows EXE:** `%APPDATA%\UmamusumeCardManager\logs\app.log`
- **Running from source:** `logs/app.log` (relative to the project folder)

To view the log from within the app, press `Ctrl+Shift+D` → **Open Log in Notepad**.

---

## Frequently Asked Questions

**Q: Why is the card list empty?**  
A: The database needs to be populated by running the scraper. Press `Ctrl+Shift+D` to check your database stats, or follow the [First-Time Setup](#first-time-setup) instructions above.

**Q: How do I update the app?**  
A: Click **🔄 Check for Updates** in the sidebar. The app will download and install the latest release automatically.

**Q: How do I back up my data?**  
A: Click **💾 Backup / Restore** in the sidebar and choose **Export to File**. This saves your owned cards, decks, and notes as a `.json` file.

**Q: Something crashed — how do I report it?**  
A: Open the diagnostics panel (`Ctrl+Shift+D`), click **Copy All**, and paste that into a GitHub issue or send it to the developer.

**Q: The app opened but has an error — what do I do?**  
A: Check the log file at `%APPDATA%\UmamusumeCardManager\logs\app.log`. If you're in contact with the developer, they may ask you to open `Ctrl+Shift+D` and share the diagnostics output.

---

## Project Structure (for developers)

```
.
├── main.py                  # Entry point — logging, crash handler, CLI args
├── version.py               # Single source of truth for version + build date
├── build.py                 # Build script (injects build date, runs PyInstaller, prints SHA256)
├── requirements.txt         # Python dependencies
├── UmamusumeCardManager.spec  # PyInstaller spec
├── gui/
│   ├── main_window.py       # Root window, collapsible sidebar, navigation
│   ├── theme.py             # Design system — colors, fonts, spacing, widget factories
│   ├── collection_dashboard.py
│   ├── card_view.py
│   ├── effects_view.py
│   ├── deck_builder.py
│   ├── hints_skills_view.py
│   ├── deck_skills_view.py
│   ├── track_view.py
│   ├── race_calendar_view.py
│   ├── first_run_dialog.py  # First-launch welcome + in-app scraper
│   ├── debug_panel.py       # Ctrl+Shift+D diagnostics panel
│   ├── crash_dialog.py      # Global unhandled exception dialog
│   ├── update_dialog.py
│   └── backup_dialog.py
├── db/
│   ├── db_queries.py        # All DB access — migrations, seed sync, query functions
│   └── db_init.py           # Legacy schema (use db_queries for runtime)
├── scraper/                 # Playwright-based GameTora scrapers
├── updater/                 # GitHub release checker + self-update logic
├── scripts/                 # Build utilities (prepare_release_db.py)
├── database/                # SQLite database files
├── images/                  # Card art images (scraped)
└── assets/                  # Track photos, character images, race badges
```

### Conventions (for contributors)

- All DB access goes through `db/db_queries.py` — never raw `sqlite3.connect()` in GUI code
- New DB columns: use `try/except ALTER TABLE` in `run_migrations()` (idempotent pattern)
- GUI styling: **always** use constants and factories from `gui/theme.py` — no hardcoded colors/fonts
- Views use chunked rendering (`after()` + generation counter) for UI responsiveness

---

## Building the EXE

```bash
python build.py
```

This will:
1. Inject today's date as `BUILD_DATE` into `version.py`
2. Run `scripts/prepare_release_db.py` (creates a seed DB stripped of user data)
3. Run PyInstaller with `UmamusumeCardManager.spec`
4. Print the SHA256 of the output `.exe` (paste this into your release notes)
5. Restore `version.py` to `BUILD_DATE = "dev"`

---

## License

MIT