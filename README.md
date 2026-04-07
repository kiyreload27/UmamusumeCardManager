# Umamusume Support Card Manager

![GitHub release](https://img.shields.io/github/v/release/kiyreload27/UmamusumeCardManager)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A powerful, standalone desktop application for managing support cards, tracking collections, and planning training runs in *Umamusume: Pretty Derby*. Built with a sleek, modern UI, it offers an all-in-one experience without needing an internet connection.

---

## ✨ Features

- 🃏 **Card Library:** Browse all support cards, search by name/type/rarity, and mark cards as owned.
- 🎴 **Deck Builder:** Build and save optimal 6-card training decks, compare their total combined effects, and export/import deck sets.
- 🔎 **Effect & Skill Search:** Instantly find cards that provide specific effects (e.g., "Friendship Bonus") or search across all built-in card and hint skills.
- 📅 **Race Calendar:** Visually plan your character's race schedule, complete with aptitude warnings so you only run in optimal races.
- 🏟 **Track Browser:** Browse through every in-game racetrack, checking course details, slopes, and positioning phases.
- 📊 **Dashboard:** Get a visual overview of your collection progress broken down by rarity and type.
- 💾 **Native Backup:** Export and import your owned cards, decks, and notes cleanly via a single portable JSON file.
- 🔄 **Fully Native Updating:** Check for app updates inside the client, or update your database directly from GameTora without needing a separate python environment!

---

## 📸 Overview

<details>
<summary><b>Click to Expand Screenshots</b></summary>

### Card Library
<img src="docs/screenshots/card tab.png" width="800">

### Deck Builder
<img src="docs/screenshots/Deck Builder tab.png" width="800">

### Effects Search
<img src="docs/screenshots/Effects tab.png" width="800">

### Skill Database
<img src="docs/screenshots/Skills Tab.png" width="800">

### Race Calendar
<img src="docs/screenshots/Race Calendar.png" width="800">

### Track Browser
<img src="docs/screenshots/Track Tab.png" width="800">

</details>

---

## 🚀 Quick Start (Windows EXE)

The easiest way to use the app is to just download the standalone portable executable:

1. Download the latest `UmamusumeCardManager.exe` from the [Releases page](https://github.com/kiyreload27/UmamusumeCardManager/releases).
2. Run the `.exe`! No installation or configuration required.
3. On first launch, you will see a welcome screen. Click **Install Browser** to automatically fetch the background drivers required to pull the absolute latest game data right onto your machine!

> **Note:** The app ships with a pre-built static database. However, you can seamlessly run the internal scraper by clicking **📥 Update Data** on your sidebar anytime new cards are released. 

---

## 💻 Running from Source (Developers)

If you'd like to extend the application, modify the UI, or run it through terminal:

### Prerequisites
- Python 3.11 or higher
- Windows OS (Linux/Mac support via source only)

```bash
# Clone the repository
git clone https://github.com/kiyreload27/UmamusumeCardManager.git
cd UmamusumeCardManager

# Install dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser (required for scrapers)
playwright install chromium

# Launch the GUI
python main.py
```

### Scraping Operations
If you are running from source, you can bypass the GUI updater and force internal database rebuilds via CLI arguments:
```bash
python main.py --scrape              # Core support cards data
python main.py --scrape-tracks       # Racetracks and course physics
python main.py --scrape-characters   # Character affinities
python main.py --scrape-races        # Individual race rosters
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+1` through `Ctrl+9` | Instantly switch between sidebar views |
| `Ctrl+F` | Focus the search bar (Card Library) |
| `↑ / ↓` | Navigate card lists |
| `Enter` | Select the currently highlighted card |
| `Escape` | Clear search / exit bulk mode |
| `Ctrl+Shift+D` | Open the **Diagnostics Panel** |

---

## 🛠 Diagnostics & Logs

If something goes wrong, the app generates detailed logs natively:

- **Windows EXE Users:** `%APPDATA%\UmamusumeCardManager\logs\app.log`
- **Source Users:** `logs/app.log`

> **Note:** Pressing `Ctrl+Shift+D` inside the app brings up the Diagnostic Panel, where you can instantly read your database stats, browse the live log console, and officially **"Report a Bug"** directly to GitHub.

---

## 📁 Repository Structure (For Contributors)

The architecture is cleanly separated into GUI layers, sqlite operations, scraping scripts, and compiled utilities:

```
.
├── main.py                  # Entry point — logging, crash handler, CLI args
├── version.py               # Single source of truth for version + build date
├── build.py                 # Build script (PyInstaller, SQLite stripping, SHA hash injection)
├── requirements.txt         # Python dependencies
├── UmamusumeCardManager.spec  # PyInstaller spec logic (Bundles Playwright drivers!)
├── gui/
│   ├── main_window.py       # Root window, collapsible sidebar, background threads
│   ├── theme.py             # Design system — colors, fonts, spacing, widget factories
│   ├── first_run_dialog.py  # First-launch welcome + in-app Playwright installer
│   ├── debug_panel.py       # Ctrl+Shift+D diagnostics & bug reporting
│   └── ...                  # Views (card_view, deck_builder, race_calendar)
├── db/
│   └── db_queries.py        # Centralized DB access (migrations, query layer)
├── scraper/                 # Playwright DOM parsing targeting GameTora
├── updater/                 # GitHub release API parsing + auto-upgrade batch logic
├── scripts/                 
│   ├── maintenance/         # Developer tools for DB repairing
│   └── tests/               # Script sandboxes
├── docs/                    # Screenshots and changelogs
├── database/                # SQLite database runtime dir
├── images/                  # Extracted Gametora splash art
└── assets/                  # High-res racetrack & badge assets
```

### Contributor Code Standards
- **Database Routing:** All DB access MUST go through `db/db_queries.py`. **Never** use raw `sqlite3.connect()` globally.
- **Migrations:** When adding DB columns, implement them natively in `run_migrations()` using idempotent `try/except ALTER TABLE` patterns.
- **Aesthetic Enforcement:** We utilize a central stylesheet. Hardcoded hex colors and font sizes are rejected. Always import definitions (e.g. `FONT_HEADER`, `BG_DARK`) from `gui/theme.py`.

---

## ⚙️ Building the Portable EXE

When you're ready to create a compiled release, run:
```bash
python build.py
```
*This automates stripping user-specific saves from the internal SQLite seed, bundles Playwright packages, invokes PyInstaller, and prints out a SHA256 security hash for GitHub Release attestation.*

---

## License

MIT License. See [LICENSE](LICENSE) for more details.