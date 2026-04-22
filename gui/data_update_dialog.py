"""
Data Update Dialog — PySide6 edition.
Allows users to re-run any scraper from within the app.
Shows last-run timestamps, prerequisite checks and a live log console.
"""

import threading
import subprocess
import sys
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget, QProgressBar, QPlainTextEdit
)
from PySide6.QtCore import Qt, Signal, QObject

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_playwright import get_persistent_browsers_path, ensure_playwright_browsers_path
ensure_playwright_browsers_path()

from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY, FONT_MONO,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
    create_styled_button,
)


def _check_playwright():
    try:
        import playwright  # noqa
        return True, "✅ Playwright installed"
    except ImportError:
        return False, "❌ Playwright not installed"


def _check_chromium():
    browsers_root = get_persistent_browsers_path()
    if os.path.isdir(browsers_root):
        for _, _, filenames in os.walk(browsers_root):
            for fname in filenames:
                if fname.lower() in ("chrome.exe", "chromium.exe",
                                     "chrome-headless-shell.exe", "chrome", "chromium"):
                    return True, "✅ Chromium installed"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
            if path and os.path.exists(path):
                return True, "✅ Chromium installed"
    except Exception:
        pass
    return False, "❌ Chromium not installed"


def _get_scraper_timestamps() -> dict:
    try:
        from db.db_queries import get_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT scraper_type, last_run_timestamp FROM scraper_meta")
        rows = {r[0]: r[1] for r in cur.fetchall()}
        conn.close()
        return rows
    except Exception:
        return {}


def _fmt_ts(ts) -> str:
    if not ts:
        return "Never run"
    try:
        return datetime.fromisoformat(ts).strftime("%Y-%m-%d  %H:%M")
    except Exception:
        return str(ts)


SCRAPERS = [
    {"key": "cards",      "label": "Support Cards", "icon": "🃏",
     "desc": "All support card stats, effects, hints and events from GameTora",
     "module": "scraper.gametora_scraper",   "fn": "run_scraper",           "time_key": "cards"},
    {"key": "tracks",     "label": "Racetracks",    "icon": "🏟",
     "desc": "Track names, locations, course distances, surfaces and phases",
     "module": "scraper.track_scraper",      "fn": "run_track_scraper",     "time_key": "tracks"},
    {"key": "characters", "label": "Characters",    "icon": "🐴",
     "desc": "Character aptitude data (surface, distance, running style)",
     "module": "scraper.character_scraper",  "fn": "run_character_scraper", "time_key": "characters"},
    {"key": "races",      "label": "Races",         "icon": "🏁",
     "desc": "Individual race details, grades, terrain and badge images",
     "module": "scraper.race_scraper",       "fn": "run_race_scraper",      "time_key": "races"},
]


class _Signals(QObject):
    log_line = Signal(str)
    status   = Signal(str)
    done     = Signal(list)


class DataUpdateDialog(QDialog):
    """In-app scraper launcher dialog."""

    def __init__(self, parent=None, on_complete_callback=None):
        super().__init__(parent)
        self.on_complete = on_complete_callback
        self._running = False
        self._cancelled = False
        self._thread = None
        self._prereqs_ok = False
        self._scraper_btns = {}

        self._sig = _Signals()
        self._sig.log_line.connect(self._append_log)
        self._sig.status.connect(self._set_status_ui)
        self._sig.done.connect(self._done_ui)

        self.setWindowTitle("Update Card Data")
        self.resize(620, 700)
        self.setMinimumSize(560, 560)
        self.setModal(True)
        self._build_ui()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet(f"background-color: {BG_ELEVATED}; border: none;")
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        t = QLabel("📥  Update Card Data")
        t.setFont(FONT_HEADER)
        t.setStyleSheet(f"color: {ACCENT_PRIMARY};")
        hdr_lay.addWidget(t)
        sub = QLabel("Re-run any scraper to fetch the latest data from GameTora.\nYour owned cards, decks, and notes are never affected.")
        sub.setFont(FONT_SMALL)
        sub.setStyleSheet(f"color: {TEXT_MUTED};")
        hdr_lay.addWidget(sub)
        outer.addWidget(hdr)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        body_w = QWidget()
        body_w.setStyleSheet(f"background: transparent;")
        self._body_lay = QVBoxLayout(body_w)
        self._body_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        self._body_lay.setSpacing(SPACING_SM)
        scroll.setWidget(body_w)
        outer.addWidget(scroll, stretch=1)

        self._build_prereqs()
        self._build_scraper_cards()

        # Progress area (hidden)
        self._prog_widget = QWidget()
        self._prog_widget.setStyleSheet(f"background: transparent;")
        pw_lay = QVBoxLayout(self._prog_widget)
        pw_lay.setContentsMargins(SPACING_LG, 0, SPACING_LG, SPACING_SM)

        self._prog_lbl = QLabel("")
        self._prog_lbl.setFont(FONT_SMALL)
        self._prog_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        pw_lay.addWidget(self._prog_lbl)

        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, 0)
        self._prog_bar.setFixedHeight(10)
        pw_lay.addWidget(self._prog_bar)

        self._log_box = QPlainTextEdit()
        self._log_box.setFont(FONT_MONO)
        self._log_box.setStyleSheet(f"background: {BG_DARKEST}; color: {TEXT_SECONDARY}; border-radius: {RADIUS_MD}px; padding: 6px;")
        self._log_box.setReadOnly(True)
        self._log_box.setFixedHeight(130)
        pw_lay.addWidget(self._log_box)
        self._prog_widget.hide()
        outer.addWidget(self._prog_widget)

        # Footer
        footer = QFrame()
        footer.setStyleSheet(f"background-color: {BG_DARKEST}; border: none;")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(SPACING_LG, SPACING_SM, SPACING_LG, SPACING_SM)
        footer_lay.addStretch()
        self._close_btn = create_styled_button(None, text="Close",
                                               command=self._close, style_type="ghost")
        footer_lay.addWidget(self._close_btn)
        outer.addWidget(footer)

    def _build_prereqs(self):
        pw_ok, pw_msg = _check_playwright()
        cr_ok, cr_msg = _check_chromium() if pw_ok else (False, "⬜ Chromium  (missing)")
        self._prereqs_ok = pw_ok and cr_ok

        prereq_row = QHBoxLayout()
        pw_lbl = QLabel(pw_msg)
        pw_lbl.setFont(FONT_SMALL)
        pw_lbl.setStyleSheet(f"color: {ACCENT_SUCCESS if pw_ok else ACCENT_ERROR};")
        prereq_row.addWidget(pw_lbl)

        cr_lbl = QLabel(cr_msg)
        cr_lbl.setFont(FONT_SMALL)
        col = ACCENT_SUCCESS if cr_ok else (ACCENT_ERROR if pw_ok else TEXT_DISABLED)
        cr_lbl.setStyleSheet(f"color: {col};")
        prereq_row.addWidget(cr_lbl)
        prereq_row.addStretch()
        self._body_lay.addLayout(prereq_row)

        if not self._prereqs_ok:
            info = QFrame()
            info.setStyleSheet(f".QFrame {{ background-color: {BG_LIGHT}; border-radius: {RADIUS_SM}px; }}")
            info_lay = QHBoxLayout(info)
            info_lay.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
            if pw_ok and not cr_ok:
                info_lbl = QLabel("Chromium browser is required to scrape game data.")
                info_lbl.setFont(FONT_SMALL)
                info_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
                info_lay.addWidget(info_lbl)
                info_lay.addStretch()
                self._install_btn = create_styled_button(None, text="Install Browser",
                                                          command=self._install_chromium,
                                                          style_type="accent", height=28)
                info_lay.addWidget(self._install_btn)
            else:
                cmd_lbl = QLabel("Install prerequisites then re-open:\n  pip install playwright    →    playwright install chromium")
                cmd_lbl.setFont(FONT_MONO)
                cmd_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
                info_lay.addWidget(cmd_lbl)
            self._body_lay.addWidget(info)

    def _build_scraper_cards(self):
        timestamps = _get_scraper_timestamps()

        # Run All card
        all_card = QFrame()
        all_card.setStyleSheet(
            f".QFrame {{ background-color: {BG_MEDIUM}; border: 1px solid {ACCENT_PRIMARY};"
            f"border-radius: {RADIUS_LG}px; }}"
        )
        all_lay = QHBoxLayout(all_card)
        all_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        ra_lbl = QLabel("Run All Scrapers")
        ra_lbl.setFont(FONT_BODY_BOLD)
        ra_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        all_lay.addWidget(ra_lbl)
        ra_desc = QLabel("Runs cards → tracks → characters → races in sequence")
        ra_desc.setFont(FONT_TINY)
        ra_desc.setStyleSheet(f"color: {TEXT_MUTED};")
        all_lay.addWidget(ra_desc, stretch=1)
        self._run_all_btn = create_styled_button(
            None, text="▶  Run All",
            command=lambda: self._start(list(SCRAPERS)),
            style_type="accent" if self._prereqs_ok else "default",
            height=34, width=110
        )
        self._run_all_btn.setEnabled(self._prereqs_ok)
        all_lay.addWidget(self._run_all_btn)
        self._body_lay.addWidget(all_card)

        # Individual cards
        for s in SCRAPERS:
            ts = _fmt_ts(timestamps.get(s["time_key"]))
            card = QFrame()
            card.setStyleSheet(
                f".QFrame {{ background-color: {BG_MEDIUM}; border: 1px solid {BG_LIGHT};"
                f"border-radius: {RADIUS_MD}px; }}"
            )
            cl = QHBoxLayout(card)
            cl.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

            left = QWidget()
            left.setStyleSheet("background: transparent;")
            ll = QVBoxLayout(left)
            ll.setContentsMargins(0, 0, 0, 0)
            ll.setSpacing(2)

            t_row = QHBoxLayout()
            icon_l = QLabel(s["icon"])
            icon_l.setFont(FONT_BODY)
            icon_l.setStyleSheet(f"color: {ACCENT_PRIMARY};")
            t_row.addWidget(icon_l)
            title_l = QLabel(s["label"])
            title_l.setFont(FONT_BODY_BOLD)
            title_l.setStyleSheet(f"color: {TEXT_PRIMARY};")
            t_row.addWidget(title_l)
            t_row.addStretch()
            ll.addLayout(t_row)

            desc_l = QLabel(s["desc"])
            desc_l.setFont(FONT_TINY)
            desc_l.setStyleSheet(f"color: {TEXT_MUTED};")
            desc_l.setWordWrap(True)
            ll.addWidget(desc_l)

            ts_l = QLabel(f"Last run: {ts}")
            ts_l.setFont(FONT_TINY)
            ts_l.setStyleSheet(f"color: {TEXT_DISABLED};")
            ll.addWidget(ts_l)

            cl.addWidget(left, stretch=1)

            btn = create_styled_button(
                None, text="▶  Run",
                command=lambda sc=s: self._start([sc]),
                style_type="default" if self._prereqs_ok else "ghost",
                height=32, width=80
            )
            btn.setEnabled(self._prereqs_ok)
            self._scraper_btns[s["key"]] = btn
            cl.addWidget(btn)
            self._body_lay.addWidget(card)

    # ─── Installer ───────────────────────────────────────────────────────────

    def _install_chromium(self):
        self._running = True
        self._close_btn.setEnabled(False)
        if hasattr(self, '_install_btn'):
            self._install_btn.setEnabled(False)
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

    # ─── Scraper runner ───────────────────────────────────────────────────────

    def _start(self, scrapers: list):
        if self._running:
            return
        self._running = True
        self._cancelled = False
        self._run_all_btn.setEnabled(False)
        self._run_all_btn.setText("Running…")
        for btn in self._scraper_btns.values():
            btn.setEnabled(False)
        self._close_btn.setEnabled(False)
        self._prog_widget.show()
        self._log_box.clear()
        self._thread = threading.Thread(
            target=self._run_scrapers, args=(scrapers,), daemon=True
        )
        self._thread.start()

    def _run_scrapers(self, scrapers: list):
        errors = []
        for s in scrapers:
            if self._cancelled:
                break
            self._sig.status.emit(f"Scraping {s['label']}…")
            self._sig.log_line.emit(f"\n► {s['label']} scraper starting…")
            try:
                import importlib
                mod = importlib.import_module(s["module"])
                getattr(mod, s["fn"])()
                self._sig.log_line.emit(f"  ✅ {s['label']} complete")
            except Exception as exc:
                self._sig.log_line.emit(f"  ❌ {s['label']} failed: {exc}")
                errors.append(f"{s['label']}: {exc}")
        self._sig.done.emit(errors)

    def _append_log(self, line: str):
        self._log_box.appendPlainText(line)

    def _set_status_ui(self, msg: str):
        self._prog_lbl.setText(msg)

    def _done_ui(self, errors: list):
        self._running = False
        self._prog_bar.setRange(0, 1)
        self._prog_bar.setValue(1)

        if "install_failed" in errors:
            self._prog_lbl.setText("Installation failed. See log.")
            self._close_btn.setEnabled(True)
            return

        if errors:
            self._prog_lbl.setText(f"Completed with {len(errors)} error(s) — see log above")
        else:
            self._prog_lbl.setText("✅ All done! Data updated successfully.")

        self._run_all_btn.setEnabled(True)
        self._run_all_btn.setText("▶  Run All")
        for btn in self._scraper_btns.values():
            btn.setEnabled(self._prereqs_ok)
        self._close_btn.setEnabled(True)

        if self.on_complete:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self.on_complete)

    def _close(self):
        self._cancelled = True
        self.accept()
        if self.on_complete and not self._running:
            self.on_complete()

    def closeEvent(self, event):
        self._cancelled = True
        super().closeEvent(event)


def show_data_update_dialog(parent=None, on_complete_callback=None):
    dlg = DataUpdateDialog(parent, on_complete_callback)
    dlg.exec()
