"""
Launcher Window — PySide6 edition.
Mirrors the original LauncherWindow (ctk.CTk) layout exactly:
  • Accent band top strip
  • Hero section: wordmark + version + primary CTA
  • 2×2 mission grid (Open App, Database Scrapers, Backup, Check Updates)
  • Footer

After the window closes, main.py reads launcher.next_action:
  'app'   → open MainWindow
  'exit'  → quit
"""

import sys
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER,
    FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_MD, RADIUS_LG,
    create_styled_button,
)

try:
    from version import VERSION
except ImportError:
    VERSION = "?"

from utils import resolve_image_path


def _styled_btn(parent, text, style_type="default", h=40) -> QPushButton:
    btn = create_styled_button(parent, text=text, style_type=style_type, height=h)
    return btn


class LauncherWindow(QMainWindow):
    """Entry-point window shown before the main app."""

    def __init__(self):
        super().__init__()
        self.next_action = 'exit'   # read by main.py after exec()

        self.setWindowTitle("Umamusume Support Card Manager")
        self.setFixedSize(520, 560)
        
        try:
            icon_path = resolve_image_path("umaappicon.png")
            if icon_path and os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )

        self._build_ui()
        self._center()

    # ─── Layout ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Accent band ──
        band = QFrame()
        band.setFixedHeight(4)
        band.setStyleSheet(
            f"background: qlineargradient("
            f"x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_SECONDARY});"
        )
        outer.addWidget(band)

        # ── Hero section ──
        hero = QWidget()
        hero.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        hero_lay = QVBoxLayout(hero)
        hero_lay.setContentsMargins(SPACING_XL, SPACING_XL, SPACING_XL, SPACING_LG)
        hero_lay.setSpacing(SPACING_SM)

        wordmark = QLabel("🐴  Umamusume")
        wordmark.setFont(FONT_DISPLAY)
        wordmark.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        hero_lay.addWidget(wordmark)

        sub = QLabel("Support Card Manager")
        sub.setFont(FONT_SUBHEADER)
        sub.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        hero_lay.addWidget(sub)

        ver = QLabel(f"v{VERSION}")
        ver.setFont(FONT_TINY)
        ver.setStyleSheet(f"color: {TEXT_DISABLED}; background: transparent;")
        hero_lay.addWidget(ver)

        hero_lay.addSpacing(SPACING_MD)

        init_btn = create_styled_button(
            hero, text="▶  Launch App",
            command=self._launch_app,
            style_type="accent", height=44
        )
        init_btn.setMinimumWidth(200)
        hero_lay.addWidget(init_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        outer.addWidget(hero)

        # ── Divider ──
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {BG_LIGHT};")
        outer.addWidget(div)

        # ── Mission grid (2×2) ──
        grid_widget = QWidget()
        grid_widget.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARKEST}; }}")
        grid_lay = QVBoxLayout(grid_widget)
        grid_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        grid_lay.setSpacing(SPACING_SM)

        lbl = QLabel("QUICK ACTIONS")
        lbl.setFont(FONT_TINY)
        lbl.setStyleSheet(f"color: {TEXT_DISABLED}; background: transparent; letter-spacing: 2px;")
        grid_lay.addWidget(lbl)

        row1 = QHBoxLayout()
        row1.setSpacing(SPACING_SM)
        row2 = QHBoxLayout()
        row2.setSpacing(SPACING_SM)

        self._add_action_card(row1, "🗄️", "Database Scrapers", "Re-fetch card data from GameTora", self._open_scrapers)
        self._add_action_card(row1, "💾", "Backup & Restore", "Export or import your collection", self._open_backup)
        self._add_action_card(row2, "🔄", "Check for Updates", "See if a newer version is available", self._open_updates)
        self._add_action_card(row2, "🛠", "Diagnostics", "View debug info and logs", self._open_debug)

        grid_lay.addLayout(row1)
        grid_lay.addLayout(row2)
        outer.addWidget(grid_widget, stretch=1)

        # ── Footer ──
        footer = QFrame()
        footer.setFixedHeight(36)
        footer.setStyleSheet(f"background-color: {BG_DARK}; border-top: 1px solid {BG_LIGHT};")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(SPACING_LG, 0, SPACING_LG, 0)

        footer_lbl = QLabel("© Umamusume Support Card Manager  ·  Data from GameTora")
        footer_lbl.setFont(FONT_TINY)
        footer_lbl.setStyleSheet(f"color: {TEXT_DISABLED}; background: transparent;")
        footer_lay.addWidget(footer_lbl)
        footer_lay.addStretch()

        outer.addWidget(footer)

    def _add_action_card(self, layout, icon: str, title: str, desc: str, callback):
        """Create a small action card and add it to the given QHBoxLayout."""
        card = QFrame()
        card.setStyleSheet(
            f".QFrame {{ background-color: {BG_MEDIUM}; border: 1px solid {BG_LIGHT};"
            f"border-radius: {RADIUS_MD}px; }}"
            f".QFrame:hover {{ border-color: {ACCENT_PRIMARY}; }}"
        )
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setFixedHeight(88)

        inner = QVBoxLayout(card)
        inner.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        inner.setSpacing(2)

        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(FONT_HEADER)
        icon_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; background: transparent;")
        top_row.addWidget(icon_lbl)
        top_row.addStretch()
        inner.addLayout(top_row)

        title_lbl = QLabel(title)
        title_lbl.setFont(FONT_BODY_BOLD)
        title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        inner.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setFont(FONT_TINY)
        desc_lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        inner.addWidget(desc_lbl)

        # Make entire card clickable
        card.mousePressEvent = lambda event, cb=callback: cb()

        layout.addWidget(card)

    # ─── Navigation helpers ───────────────────────────────────────────────────

    def _launch_app(self):
        self.next_action = 'app'
        self.close()

    def _open_scrapers(self):
        try:
            from gui.data_update_dialog import DataUpdateDialog
            dlg = DataUpdateDialog(self)
            dlg.exec()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open scraper dialog:\n{e}")

    def _open_backup(self):
        try:
            from gui.backup_dialog import BackupDialog
            dlg = BackupDialog(self)
            dlg.exec()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open backup dialog:\n{e}")

    def _open_updates(self):
        try:
            from gui.update_dialog import UpdateDialog
            dlg = UpdateDialog(self)
            dlg.exec()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open update dialog:\n{e}")

    def _open_debug(self):
        try:
            from gui.debug_panel import DebugPanel
            dlg = DebugPanel(self)
            dlg.exec()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open debug panel:\n{e}")

    # ─── Utilities ───────────────────────────────────────────────────────────

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        geom = self.frameGeometry()
        geom.moveCenter(screen.center())
        self.move(geom.topLeft())

    def closeEvent(self, event):
        # If user clicked X without choosing 'app', stay 'exit'
        super().closeEvent(event)
