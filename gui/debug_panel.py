"""
Diagnostic / Debug Panel — PySide6 edition.
Accessible via Ctrl+Shift+D or the Logs button in the chrome bar.
Shows app state, DB info, log tail.
"""

import sys
import os
import platform
import sqlite3
import webbrowser
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTabWidget, QScrollArea, QWidget,
    QPlainTextEdit, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_MONO,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_MD, RADIUS_LG,
    create_styled_button,
)


def _get_db_path() -> str:
    try:
        from db.db_queries import DB_PATH
        return DB_PATH
    except Exception:
        return "Unknown"


def _get_log_path() -> str:
    try:
        from main import get_log_path
        return get_log_path()
    except Exception:
        pass
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(appdata, "UmamusumeCardManager", "logs", "app.log")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "logs", "app.log")


def _read_log_tail(log_path: str, lines: int = 100) -> str:
    try:
        if not os.path.exists(log_path):
            return "(Log file not found)"
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return "".join(tail)
    except Exception as e:
        return f"(Could not read log: {e})"


def _get_db_stats() -> dict:
    stats = {}
    db_path = _get_db_path()
    try:
        if os.path.exists(db_path):
            stats["db_size"] = f"{os.path.getsize(db_path) / 1024:.1f} KB"
        else:
            stats["db_size"] = "File not found"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for table, label in [
            ("support_cards", "Total Cards"),
            ("owned_cards",   "Owned Cards"),
            ("user_decks",    "Saved Decks"),
            ("tracks",        "Racetracks"),
            ("characters",    "Characters"),
            ("races",         "Races"),
        ]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[label] = cur.fetchone()[0]
            except Exception:
                stats[label] = "—"
        try:
            cur.execute("SELECT scraper_type, last_run_timestamp FROM scraper_meta")
            for stype, ts in cur.fetchall():
                stats[f"Last scrape: {stype}"] = ts or "Never"
        except Exception:
            pass
        try:
            cur.execute("SELECT value FROM system_metadata WHERE key='app_version'")
            row = cur.fetchone()
            stats["DB app_version"] = row[0] if row else "—"
        except Exception:
            stats["DB app_version"] = "—"
        conn.close()
    except Exception as e:
        stats["error"] = str(e)
    return stats


def _build_diagnostics_text() -> str:
    try:
        from version import VERSION, APP_NAME, BUILD_DATE
    except ImportError:
        VERSION, APP_NAME, BUILD_DATE = "?", "UmamusumeCardManager", "unknown"
    db_path = _get_db_path()
    log_path = _get_log_path()
    db_stats = _get_db_stats()
    log_tail = _read_log_tail(log_path, lines=20)
    lines = [
        "=" * 60,
        f"  {APP_NAME} — Diagnostic Report",
        f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60, "",
        "[ App ]",
        f"  Version:    v{VERSION}  (built {BUILD_DATE})",
        f"  Mode:       {'Frozen EXE' if getattr(sys, 'frozen', False) else 'Python Source'}",
        f"  Python:     {sys.version}",
        f"  Platform:   {platform.system()} {platform.release()} ({platform.machine()})",
        "", "[ Database ]",
        f"  Path:       {db_path}",
    ]
    for k, v in db_stats.items():
        lines.append(f"  {k+':':24} {v}")
    lines += ["", "[ Logs ]", f"  Log path:   {log_path}", "",
              "[ Last 20 log lines ]", log_tail, "=" * 60]
    return "\n".join(lines)


def _make_kv_row(parent, label, value, val_color=None):
    row = QWidget(parent)
    row.setStyleSheet("background: transparent;")
    rl = QHBoxLayout(row)
    rl.setContentsMargins(0, 1, 0, 1)
    lbl = QLabel(label + ":")
    lbl.setFont(FONT_SMALL)
    lbl.setStyleSheet(f"color: {TEXT_MUTED}; min-width: 130px;")
    rl.addWidget(lbl)
    val = QLabel(str(value))
    val.setFont(FONT_SMALL)
    col = val_color or TEXT_PRIMARY
    val.setStyleSheet(f"color: {col}; background: transparent;")
    val.setWordWrap(True)
    rl.addWidget(val, stretch=1)
    return row


class DebugPanel(QDialog):
    """In-app diagnostic panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🛠  Diagnostics")
        self.resize(720, 640)
        self.setMinimumSize(600, 500)
        self.setModal(False)
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        self.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        # Header band
        hdr = QFrame()
        hdr.setStyleSheet(f"background-color: {BG_ELEVATED}; border: none;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        title = QLabel("🛠  Diagnostics")
        title.setFont(FONT_HEADER)
        title.setStyleSheet(f"color: {ACCENT_PRIMARY}; background: transparent;")
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        for text, slot in [
            ("🔄 Refresh", self._refresh),
            ("📋 Copy All", self._copy_all),
            ("🐞 Report a Bug", lambda: webbrowser.open(
                "https://github.com/kiyreload27/UmamusumeCardManager/issues/new")),
        ]:
            b = create_styled_button(None, text=text, command=slot,
                                     style_type="ghost" if "Bug" in text else "default",
                                     height=32)
            hdr_lay.addWidget(b)

        lay.addWidget(hdr)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        lay.addWidget(self.tabs, stretch=1)

        # Overview tab
        self._ov_widget = QWidget()
        self._ov_widget.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        ov_scroll = QScrollArea()
        ov_scroll.setWidgetResizable(True)
        ov_scroll.setWidget(self._ov_widget)
        ov_scroll.setStyleSheet("border: none;")
        self._ov_lay = QVBoxLayout(self._ov_widget)
        self._ov_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._ov_lay.setSpacing(SPACING_MD)
        self._ov_lay.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        self.tabs.addTab(ov_scroll, "Overview")

        # Database tab
        self._db_widget = QWidget()
        self._db_widget.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        db_scroll = QScrollArea()
        db_scroll.setWidgetResizable(True)
        db_scroll.setWidget(self._db_widget)
        db_scroll.setStyleSheet("border: none;")
        self._db_lay = QVBoxLayout(self._db_widget)
        self._db_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._db_lay.setSpacing(SPACING_MD)
        self._db_lay.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        self.tabs.addTab(db_scroll, "Database")

        # Log tab
        self._log_box = QPlainTextEdit()
        self._log_box.setFont(FONT_MONO)
        self._log_box.setStyleSheet(
            f"background-color: {BG_DARKEST}; color: {TEXT_SECONDARY};"
            f"border: none; padding: 8px;"
        )
        self._log_box.setReadOnly(True)
        self.tabs.addTab(self._log_box, "Log File")

    def _section_frame(self, title: str) -> tuple:
        frame = QFrame()
        frame.setStyleSheet(
            f".QFrame {{ background-color: {BG_MEDIUM}; border: 1px solid {BG_LIGHT};"
            f"border-radius: {RADIUS_LG}px; }}"
        )
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        t = QLabel(title)
        t.setFont(FONT_BODY_BOLD)
        t.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        inner.addWidget(t)
        return frame, inner

    def _refresh(self):
        try:
            from version import VERSION, APP_NAME
        except ImportError:
            VERSION, APP_NAME = "?", "UmamusumeCardManager"
        try:
            from version import BUILD_DATE
        except ImportError:
            BUILD_DATE = "unknown"

        db_path = _get_db_path()
        log_path = _get_log_path()
        db_stats = _get_db_stats()

        # Clear overview
        while self._ov_lay.count():
            item = self._ov_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # App section
        app_frame, app_inner = self._section_frame("Application")
        for label, value in [
            ("Version", f"v{VERSION}  (built {BUILD_DATE})"),
            ("Mode", "Frozen EXE" if getattr(sys, 'frozen', False) else "Python Source"),
            ("Python", sys.version.split()[0]),
            ("Platform", f"{platform.system()} {platform.release()} ({platform.machine()})"),
        ]:
            app_inner.addWidget(_make_kv_row(app_frame, label, value))
        self._ov_lay.addWidget(app_frame)

        # Log section
        log_frame, log_inner = self._section_frame("Log File")
        log_inner.addWidget(_make_kv_row(log_frame, "Path", log_path, ACCENT_INFO))
        log_exists = os.path.exists(log_path)
        open_btn = create_styled_button(None, text="📄 Open Log in Editor",
                                        command=self._open_log, style_type="default", height=30)
        open_btn.setEnabled(log_exists)
        log_inner.addWidget(open_btn)
        self._ov_lay.addWidget(log_frame)

        # Clear db tab
        while self._db_lay.count():
            item = self._db_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        path_frame, path_inner = self._section_frame("Database Path")
        path_inner.addWidget(_make_kv_row(path_frame, "Path", db_path, ACCENT_INFO))
        self._db_lay.addWidget(path_frame)

        stats_frame, stats_inner = self._section_frame("Statistics")
        for label, value in db_stats.items():
            col = ACCENT_SUCCESS if isinstance(value, int) and value > 0 else TEXT_PRIMARY
            stats_inner.addWidget(_make_kv_row(stats_frame, label, value, col))
        self._db_lay.addWidget(stats_frame)

        # Log tab
        log_content = _read_log_tail(log_path, lines=100)
        self._log_box.setPlainText(log_content)
        self._log_box.moveCursor(QTextCursor.MoveOperation.End)

    def _open_log(self):
        log_path = _get_log_path()
        try:
            os.startfile(log_path)
        except Exception:
            import subprocess
            try:
                subprocess.Popen(["xdg-open", log_path])
            except Exception:
                pass

    def _copy_all(self):
        text = _build_diagnostics_text()
        QApplication.clipboard().setText(text)


def show_debug_panel(parent=None):
    """Open the diagnostic panel."""
    dlg = DebugPanel(parent)
    dlg.exec()
