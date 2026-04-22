"""
First-Run Dialog — PySide6 edition.
Shown once when the app has no card data.
Welcomes the user, explains features, and offers to run the scraper.
"""

import threading
import sys
import os
import subprocess

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget, QProgressBar, QPlainTextEdit
)
from PySide6.QtCore import Qt, Signal, QObject

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY, FONT_MONO,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_MD, RADIUS_LG,
    create_styled_button,
)
from db.db_queries import get_database_stats
from utils_playwright import get_persistent_browsers_path, ensure_playwright_browsers_path
ensure_playwright_browsers_path()


def _check_playwright():
    try:
        import playwright  # noqa
        return True, "✅ Playwright is installed"
    except ImportError:
        return False, "❌ Playwright not installed  (run: pip install playwright)"


def _check_chromium():
    browsers_root = get_persistent_browsers_path()
    if os.path.isdir(browsers_root):
        for dirpath, dirnames, filenames in os.walk(browsers_root):
            for fname in filenames:
                if fname.lower() in ("chrome.exe", "chromium.exe",
                                     "chrome-headless-shell.exe", "chrome", "chromium"):
                    return True, "✅ Chromium browser is installed"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser_path = p.chromium.executable_path
            if browser_path and os.path.exists(browser_path):
                return True, "✅ Chromium browser is installed"
    except Exception:
        pass
    return False, "❌ Chromium not installed  (click Install Browser below)"


class _Signals(QObject):
    log_line  = Signal(str)
    status    = Signal(str)
    done      = Signal(list)


class FirstRunDialog(QDialog):
    """One-time welcome dialog shown when the database has no card data."""

    def __init__(self, parent=None, on_complete_callback=None):
        super().__init__(parent)
        self.on_complete = on_complete_callback
        self._scrape_thread = None
        self._cancelled = False
        self._prereqs_ok = False

        self._sig = _Signals()
        self._sig.log_line.connect(self._append_log)
        self._sig.status.connect(self._set_status_ui)
        self._sig.done.connect(self._scrape_complete)

        self.setWindowTitle("Welcome to Umamusume Support Card Manager")
        self.resize(600, 680)
        self.setFixedSize(600, 680)
        self.setModal(True)
        self._build_ui()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        body_w = QWidget()
        body_w.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        body_lay = QVBoxLayout(body_w)
        body_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_MD)
        body_lay.setSpacing(SPACING_MD)
        scroll.setWidget(body_w)
        outer.addWidget(scroll, stretch=1)

        # Welcome header
        title = QLabel("🐴  Welcome!")
        title.setFont(FONT_DISPLAY)
        title.setStyleSheet(f"color: {ACCENT_PRIMARY}; background: transparent;")
        body_lay.addWidget(title)

        desc = QLabel(
            "Umamusume Support Card Manager helps you track your card collection, "
            "build decks, search skills and effects, and plan your race calendar —\n"
            "all in one place."
        )
        desc.setFont(FONT_BODY)
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        desc.setWordWrap(True)
        body_lay.addWidget(desc)

        # Feature highlights
        features = [
            ("🃏", "Card Library",  "Browse & own your support cards"),
            ("🎴", "Deck Builder",  "Build optimised 6-card decks"),
            ("🔎", "Effect Search", "Find cards by specific effects"),
            ("📅", "Race Calendar", "Plan your Uma's race schedule"),
            ("🏟", "Track Browser", "View all racetracks and courses"),
        ]
        feat_frame = QFrame()
        feat_frame.setStyleSheet(
            f".QFrame {{ background-color: {BG_MEDIUM}; border: 1px solid {BG_LIGHT};"
            f"border-radius: {RADIUS_LG}px; }}"
        )
        feat_lay = QVBoxLayout(feat_frame)
        feat_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        for icon, feat_title, feat_desc in features:
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 2)
            i_lbl = QLabel(icon)
            i_lbl.setFont(FONT_HEADER)
            i_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; min-width: 32px;")
            rl.addWidget(i_lbl)
            col = QWidget()
            col.setStyleSheet("background: transparent;")
            col_lay = QVBoxLayout(col)
            col_lay.setContentsMargins(SPACING_SM, 0, 0, 0)
            col_lay.setSpacing(0)
            t = QLabel(feat_title)
            t.setFont(FONT_BODY_BOLD)
            t.setStyleSheet(f"color: {TEXT_PRIMARY};")
            col_lay.addWidget(t)
            d = QLabel(feat_desc)
            d.setFont(FONT_TINY)
            d.setStyleSheet(f"color: {TEXT_MUTED};")
            col_lay.addWidget(d)
            rl.addWidget(col, stretch=1)
            feat_lay.addWidget(row)
        body_lay.addWidget(feat_frame)

        # Get card data section
        hdr2 = QLabel("📥  Get Card Data")
        hdr2.setFont(FONT_SUBHEADER)
        hdr2.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        body_lay.addWidget(hdr2)

        info = QLabel("The app fetches card data from GameTora. You need to run the scraper once to populate your database.")
        info.setFont(FONT_SMALL)
        info.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        info.setWordWrap(True)
        body_lay.addWidget(info)

        # Prerequisites
        prereq_frame = QFrame()
        prereq_frame.setStyleSheet(
            f".QFrame {{ background-color: {BG_MEDIUM}; border: 1px solid {BG_LIGHT};"
            f"border-radius: {RADIUS_MD}px; }}"
        )
        pre_lay = QVBoxLayout(prereq_frame)
        pre_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        pw_hdr = QLabel("Prerequisites")
        pw_hdr.setFont(FONT_BODY_BOLD)
        pw_hdr.setStyleSheet(f"color: {TEXT_PRIMARY};")
        pre_lay.addWidget(pw_hdr)

        pw_ok, pw_msg = _check_playwright()
        self._pw_lbl = QLabel(pw_msg)
        self._pw_lbl.setFont(FONT_SMALL)
        self._pw_lbl.setStyleSheet(f"color: {ACCENT_SUCCESS if pw_ok else ACCENT_ERROR};")
        pre_lay.addWidget(self._pw_lbl)

        cr_ok, cr_msg = _check_chromium() if pw_ok else (False, "⬜ Chromium (missing)")
        self._cr_lbl = QLabel(cr_msg)
        self._cr_lbl.setFont(FONT_SMALL)
        col = ACCENT_SUCCESS if cr_ok else (ACCENT_ERROR if pw_ok else TEXT_DISABLED)
        self._cr_lbl.setStyleSheet(f"color: {col};")
        pre_lay.addWidget(self._cr_lbl)

        if pw_ok and not cr_ok:
            install_row = QHBoxLayout()
            install_info = QLabel("Chromium is required to scrape game data.")
            install_info.setFont(FONT_SMALL)
            install_info.setStyleSheet(f"color: {TEXT_MUTED};")
            install_row.addWidget(install_info)
            install_row.addStretch()
            self._install_btn = create_styled_button(None, text="Install Browser",
                                                     command=self._install_chromium,
                                                     style_type="accent", height=28)
            install_row.addWidget(self._install_btn)
            pre_lay.addLayout(install_row)
        elif not pw_ok:
            cmd_lbl = QLabel("Run these commands in a terminal, then re-open the app:\n  pip install playwright\n  playwright install chromium")
            cmd_lbl.setFont(FONT_MONO)
            cmd_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
            pre_lay.addWidget(cmd_lbl)

        body_lay.addWidget(prereq_frame)

        # Button row
        btn_row = QHBoxLayout()
        self._recheck_btn = create_styled_button(None, text="🔄 Re-check",
                                                  command=self._recheck, style_type="default", height=36)
        btn_row.addWidget(self._recheck_btn)

        self._prereqs_ok = pw_ok and cr_ok
        self._scrape_btn = create_styled_button(
            None, text="▶  Scrape Card Data Now",
            command=self._start_scrape,
            style_type="accent" if self._prereqs_ok else "default",
            height=36
        )
        self._scrape_btn.setEnabled(self._prereqs_ok)
        btn_row.addWidget(self._scrape_btn)
        body_lay.addLayout(btn_row)

        # Progress area (hidden initially)
        self._prog_widget = QWidget()
        self._prog_widget.setStyleSheet("background: transparent;")
        prog_lay = QVBoxLayout(self._prog_widget)
        prog_lay.setContentsMargins(0, 0, 0, 0)

        self._prog_lbl = QLabel("Scraping support card data from GameTora...")
        self._prog_lbl.setFont(FONT_SMALL)
        self._prog_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        prog_lay.addWidget(self._prog_lbl)

        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, 0)
        self._prog_bar.setFixedHeight(10)
        prog_lay.addWidget(self._prog_bar)

        self._log_box = QPlainTextEdit()
        self._log_box.setFont(FONT_MONO)
        self._log_box.setStyleSheet(f"background: {BG_MEDIUM}; color: {TEXT_SECONDARY}; border-radius: {RADIUS_MD}px; padding: 6px;")
        self._log_box.setReadOnly(True)
        self._log_box.setFixedHeight(120)
        prog_lay.addWidget(self._log_box)
        self._prog_widget.hide()
        body_lay.addWidget(self._prog_widget)

        body_lay.addStretch()

        # Bottom bar
        bottom = QFrame()
        bottom.setStyleSheet(f"background-color: {BG_DARKEST}; border: none;")
        bottom_lay = QHBoxLayout(bottom)
        bottom_lay.setContentsMargins(SPACING_LG, SPACING_SM, SPACING_LG, SPACING_SM)
        bottom_lay.addStretch()
        self._skip_btn = create_styled_button(None, text="Skip — I'll set up later",
                                              command=self._skip, style_type="ghost")
        bottom_lay.addWidget(self._skip_btn)
        outer.addWidget(bottom)

    def _recheck(self):
        pw_ok, pw_msg = _check_playwright()
        self._pw_lbl.setText(pw_msg)
        self._pw_lbl.setStyleSheet(f"color: {ACCENT_SUCCESS if pw_ok else ACCENT_ERROR};")
        cr_ok, cr_msg = _check_chromium() if pw_ok else (False, "⬜ Chromium (check after installing Playwright)")
        self._cr_lbl.setText(cr_msg)
        col = ACCENT_SUCCESS if cr_ok else (ACCENT_ERROR if pw_ok else TEXT_DISABLED)
        self._cr_lbl.setStyleSheet(f"color: {col};")
        self._prereqs_ok = pw_ok and cr_ok
        self._scrape_btn.setEnabled(self._prereqs_ok)

    def _install_chromium(self):
        self._scrape_btn.setEnabled(False)
        self._recheck_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._prog_widget.show()
        self._prog_lbl.setText("Installing Chromium browser (this may take a few minutes)...")

        def _worker():
            try:
                from playwright._impl._driver import compute_driver_executable
                driver = compute_driver_executable()
                env = os.environ.copy()
                env["PLAYWRIGHT_BROWSERS_PATH"] = get_persistent_browsers_path()
                cmd = [driver[0], driver[1], "install", "--force", "chromium"]
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                for line in iter(process.stdout.readline, ''):
                    self._sig.log_line.emit(line.rstrip())
                process.stdout.close()
                process.wait()
                if process.returncode == 0:
                    self._sig.log_line.emit("\n✅ Chromium installed successfully!")
                    self._sig.done.emit([])
                else:
                    self._sig.log_line.emit(f"\n❌ Installation failed with code {process.returncode}")
                    self._sig.done.emit(["install_failed"])
            except Exception as e:
                self._sig.log_line.emit(f"\n❌ Error starting installer: {e}")
                self._sig.done.emit(["install_failed"])

        threading.Thread(target=_worker, daemon=True).start()

    def _start_scrape(self):
        if self._scrape_thread and self._scrape_thread.is_alive():
            return
        self._scrape_btn.setEnabled(False)
        self._scrape_btn.setText("Scraping…")
        self._recheck_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._prog_widget.show()
        self._scrape_thread = threading.Thread(target=self._run_scrapers, daemon=True)
        self._scrape_thread.start()

    def _run_scrapers(self):
        scrapers = [
            ("Support Cards", "scraper.gametora_scraper",    "run_scraper"),
            ("Racetracks",    "scraper.track_scraper",       "run_track_scraper"),
            ("Characters",    "scraper.character_scraper",   "run_character_scraper"),
            ("Races",         "scraper.race_scraper",        "run_race_scraper"),
        ]
        errors = []
        for label, module_path, fn_name in scrapers:
            if self._cancelled:
                break
            self._sig.status.emit(f"Scraping {label}…")
            self._sig.log_line.emit(f"\n► Starting {label} scraper…")
            try:
                import importlib
                mod = importlib.import_module(module_path)
                getattr(mod, fn_name)()
                self._sig.log_line.emit(f"  ✅ {label} done")
            except Exception as exc:
                self._sig.log_line.emit(f"  ❌ {label} failed: {exc}")
                errors.append(f"{label}: {exc}")
        self._sig.done.emit(errors)

    def _append_log(self, line: str):
        self._log_box.appendPlainText(line)

    def _set_status_ui(self, msg: str):
        self._prog_lbl.setText(msg)

    def _scrape_complete(self, errors: list):
        self._prog_bar.setRange(0, 1)
        self._prog_bar.setValue(1)
        if "install_failed" in errors:
            self._prog_lbl.setText("Installation failed. See log.")
            self._skip_btn.setEnabled(True)
            return
        if errors:
            self._prog_lbl.setText(f"Completed with {len(errors)} error(s) — see log above")
            self._scrape_btn.setEnabled(True)
            self._scrape_btn.setText("▶  Retry")
            self._skip_btn.setEnabled(True)
        else:
            self._prog_lbl.setText("✅ All done! Your database is ready.")
            self._scrape_btn.setEnabled(False)
            self._scrape_btn.setText("✅ Complete")
            self._skip_btn.setText("Open App →")
            self._skip_btn.setEnabled(True)
            self._skip_btn.setProperty("styleType", "accent")
            self._skip_btn.style().unpolish(self._skip_btn)
            self._skip_btn.style().polish(self._skip_btn)

    def _skip(self):
        self._cancelled = True
        self.accept()
        if self.on_complete:
            self.on_complete()


def should_show_first_run() -> bool:
    try:
        stats = get_database_stats()
        return stats.get('total_cards', 0) == 0
    except Exception:
        return False


def show_first_run_dialog(parent=None, on_complete_callback=None):
    """Show the welcome dialog. Caller should check should_show_first_run() first."""
    dlg = FirstRunDialog(parent, on_complete_callback)
    dlg.exec()
