# 🧪 Testing Branch — UmamusumeCardManager

This branch contains the **PySide6 migration** of UmamusumeCardManager, replacing the original CustomTkinter GUI with a fully native Qt6 interface.

> **⚠️ This is a testing/development branch.**
> It may contain unstable code, visual regressions, or incomplete features. Do not use this as your primary install.

---

## What's Different From `main`

### GUI Framework
- Replaced **CustomTkinter** with **PySide6 (Qt6)**
- New centralised design system (`gui/design_system.py` + `gui/theme.py`) with design tokens (colours, spacing, radii, fonts)
- All views rewritten as `QWidget` subclasses; sidebar navigation preserved

### Bug Fixes Included In This Branch
| Area | Fix |
|---|---|
| Debug panel | `QTextCursor.MoveOperation.End` (was `QTextCursor.End` — PySide6 enum change) |
| Deck builder drag | `QPoint // int` unsupported → divide `.x()` / `.y()` separately |
| Deck builder slots | `✕` → `×` (universal glyph) + `padding: 0` override on 24×24 button |
| Filter chips | Widened from 40 → 56px + explicit `padding: 2px 6px` |
| All small icon buttons | Added `padding: 0` to override global `6px 14px` bleed-in |
| QComboBox arrow | `image: none` to prevent native `═` glyph fallback |
| QComboBox selection | `selection-color` changed from near-black → `TEXT_PRIMARY` (white) |
| Level combo | Widened from 50 → 72px with explicit padding/colour style |
| Race calendar slots | Three distinct visual states: `—` (no races), dashed (apt. too low), bordered + tooltip (eligible) |

---

## Running From Source

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for scrapers)
playwright install chromium

# Run the app
python main.py
```

> Python 3.10+ recommended. Tested on Windows 10/11.

---

## Known Issues / Still Being Tested

- [ ] QComboBox dropdown arrow is hidden (no visible indicator) — functional but not styled
- [ ] Some emoji characters may render inconsistently depending on Windows font cache
- [ ] Drag-and-drop in deck builder tested on Windows only
- [ ] Race calendar aptitude filtering relies on scraped data being present

---

## Reporting Issues

If you encounter a bug on this branch, please open an issue and include:
1. Your Python and PySide6 version (`python --version`, `pip show PySide6`)
2. The full traceback from the log file (`logs/app.log`)
3. Steps to reproduce

[Open an issue →](https://github.com/kiyreload27/UmamusumeCardManager/issues/new)
