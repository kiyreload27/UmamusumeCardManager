"""
Main entry point for Umamusume Support Card Manager.
"""

import argparse
import sys
import os
import logging
import logging.handlers

# ──────────────────────────────────────────────────────────────────────────────
# CRITICAL: set PLAYWRIGHT_BROWSERS_PATH before *any* playwright import runs.
# In a frozen EXE, Playwright extracts to a fresh _MEIxxxxx temp dir each
# launch and looks for browsers relative to that dir.  Browsers installed by
# the user would never be found.  Pinning to a persistent directory fixes this.
# ──────────────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils_playwright import ensure_playwright_browsers_path
ensure_playwright_browsers_path()


# ──────────────────────────────────────────────────────────────────────────────
# Logging infrastructure
# ──────────────────────────────────────────────────────────────────────────────

def get_log_path() -> str:
    """Return the resolved path for app.log.
    - Frozen (.exe): %APPDATA%/UmamusumeCardManager/logs/app.log
    - Source:        <project_root>/logs/app.log
    """
    if getattr(sys, 'frozen', False):
        if sys.platform == "win32":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
        else:
            base = os.environ.get(
                "XDG_STATE_HOME",
                os.path.join(os.path.expanduser("~"), ".local", "state")
            )
        log_dir = os.path.join(base, "UmamusumeCardManager", "logs")
    else:
        root = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(root, "logs")

    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "app.log")


def setup_logging(level_name: str = "INFO") -> str:
    """Configure root logger with console + rotating file handlers.
    Returns the resolved log file path.
    """
    level = getattr(logging, level_name.upper(), logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(fmt)
    root_logger.addHandler(console_handler)

    log_path = get_log_path()
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        root_logger.addHandler(file_handler)
    except Exception as e:
        logging.warning(f"Could not create log file at {log_path}: {e}")

    return log_path


# ──────────────────────────────────────────────────────────────────────────────
# Global exception hook
# ──────────────────────────────────────────────────────────────────────────────

_LOG_PATH: str = ""


def _global_exception_hook(exc_type, exc_value, exc_tb):
    """Catch unhandled exceptions, log them, and show a styled crash dialog."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    logging.critical(
        "Unhandled exception",
        exc_info=(exc_type, exc_value, exc_tb)
    )

    try:
        from gui.crash_dialog import show_crash_dialog
        show_crash_dialog(exc_type, exc_value, exc_tb, log_path=_LOG_PATH)
    except Exception:
        import traceback
        traceback.print_exception(exc_type, exc_value, exc_tb)


# ──────────────────────────────────────────────────────────────────────────────
# Path setup
# ──────────────────────────────────────────────────────────────────────────────

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Scraper runners (no GUI dependency — just show QMessageBox on error)
# ──────────────────────────────────────────────────────────────────────────────

def _show_error(title: str, message: str):
    """Show an error dialog — uses QMessageBox if QApplication exists."""
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, title, message)
    except Exception:
        print(f"ERROR — {title}\n{message}", file=sys.stderr)


def run_scraper():
    try:
        from scraper.gametora_scraper import run_scraper as scrape
        scrape()
    except Exception as e:
        import traceback
        error_msg = f"An error occurred while running the scraper:\n\n{e}\n\n{traceback.format_exc()}"
        logger.error(error_msg)
        _show_error("Scraper Error", error_msg)
        sys.exit(1)


def run_track_scraper():
    try:
        from scraper.track_scraper import run_track_scraper as scrape_tracks
        scrape_tracks()
    except Exception as e:
        import traceback
        error_msg = f"An error occurred while running the track scraper:\n\n{e}\n\n{traceback.format_exc()}"
        logger.error(error_msg)
        _show_error("Track Scraper Error", error_msg)
        sys.exit(1)


def run_character_scraper():
    try:
        from scraper.character_scraper import run_character_scraper as scrape_chars
        scrape_chars()
    except Exception as e:
        import traceback
        error_msg = f"An error occurred while running the character scraper:\n\n{e}\n\n{traceback.format_exc()}"
        logger.error(error_msg)
        _show_error("Character Scraper Error", error_msg)
        sys.exit(1)


def run_race_scraper():
    try:
        from scraper.race_scraper import run_race_scraper as scrape_races
        scrape_races()
    except Exception as e:
        import traceback
        error_msg = f"An error occurred while running the race scraper:\n\n{e}\n\n{traceback.format_exc()}"
        logger.error(error_msg)
        _show_error("Race Scraper Error", error_msg)
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# DB startup sanity check
# ──────────────────────────────────────────────────────────────────────────────

def _db_sanity_check() -> bool:
    """Verify the database can be opened. Returns False on critical failure."""
    try:
        from db.db_queries import DB_PATH, get_conn
        logger.info(f"Database path: {DB_PATH}")
        conn = get_conn()
        conn.execute("SELECT 1")
        conn.close()
        logger.info("Database sanity check passed")
        return True
    except Exception as e:
        logger.critical(f"Database sanity check FAILED: {e}")
        _show_error(
            "Database Error",
            f"Could not open the database:\n\n{e}\n\n"
            "Try deleting 'database/umamusume.db' and restarting."
        )
        return False


# ──────────────────────────────────────────────────────────────────────────────
# GUI runner — single QApplication instance, launcher then main window
# ──────────────────────────────────────────────────────────────────────────────

def run_gui():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    # Enable HiDPI before creating QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Umamusume Support Card Manager")
    app.setOrganizationName("UmamusumeCardManager")

    # Apply global stylesheet
    try:
        from gui.theme import STYLESHEET
        app.setStyleSheet(STYLESHEET)
    except Exception as e:
        logger.warning(f"Could not load stylesheet: {e}")

    # Set default font
    try:
        from gui.theme import FONT_BODY
        app.setFont(FONT_BODY)
    except Exception:
        pass

    try:
        from gui.launcher_window import LauncherWindow
        launcher = LauncherWindow()
        launcher.show()
        app.exec()

        next_action = getattr(launcher, 'next_action', 'exit')

        if next_action == 'app':
            from gui.main_window import MainWindow
            main_win = MainWindow()
            main_win.show()
            sys.exit(app.exec())

    except Exception as e:
        import traceback
        error_msg = f"An error occurred while launching the GUI:\n\n{e}\n\n{traceback.format_exc()}"
        logger.error(error_msg)
        _show_error("Application Error", error_msg)
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    global _LOG_PATH

    parser = argparse.ArgumentParser(
        description="Umamusume Support Card Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python main.py                      # Launch the GUI (default)
  python main.py --gui                # Launch the GUI
  python main.py --scrape             # Run the support card scraper
  python main.py --scrape-tracks      # Run the racetrack scraper
  python main.py --scrape-characters  # Run the character scraper
  python main.py --scrape-races       # Run the race scraper
  python main.py --log-level DEBUG    # Enable verbose logging
        """
    )

    parser.add_argument('--scrape',             action='store_true', help='Run the web scraper to fetch support card data')
    parser.add_argument('--scrape-tracks',      action='store_true', help='Run the racetrack scraper')
    parser.add_argument('--scrape-characters',  action='store_true', help='Run the character scraper')
    parser.add_argument('--scrape-races',       action='store_true', help='Run the race scraper')
    parser.add_argument('--gui',                action='store_true', help='Launch the GUI application (default)')
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Set logging verbosity (default: INFO)'
    )

    args = parser.parse_args()

    _LOG_PATH = setup_logging(args.log_level)
    sys.excepthook = _global_exception_hook

    try:
        from version import VERSION, APP_NAME, BUILD_DATE
    except ImportError:
        VERSION, APP_NAME, BUILD_DATE = "?", "UmamusumeCardManager", "unknown"

    import platform
    logger.info(f"{'='*60}")
    logger.info(f"  {APP_NAME} v{VERSION}  (built {BUILD_DATE})")
    logger.info(f"  Mode: {'Frozen EXE' if getattr(sys, 'frozen', False) else 'Python Source'}")
    logger.info(f"  Python: {sys.version.split()[0]}  |  {platform.system()} {platform.release()}")
    logger.info(f"  Log:    {_LOG_PATH}")
    logger.info(f"{'='*60}")

    if args.scrape:
        logger.info("Starting support card scraper...")
        run_scraper()
    elif args.scrape_tracks:
        logger.info("Starting racetrack scraper...")
        run_track_scraper()
    elif args.scrape_characters:
        logger.info("Starting character scraper...")
        run_character_scraper()
    elif args.scrape_races:
        logger.info("Starting race scraper...")
        run_race_scraper()
    else:
        logger.info("Launching Umamusume Support Card Manager...")
        if not _db_sanity_check():
            sys.exit(1)
        run_gui()


if __name__ == "__main__":
    main()