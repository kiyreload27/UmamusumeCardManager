"""
Crash Dialog — shown when an unhandled exception occurs.
Provides a user-friendly message, the full traceback, and options to
copy the error to clipboard or open the log file.
"""

import sys
import os
import traceback as tb_module

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QFrame, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_MUTED,
    FONT_HEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_MONO,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_MD,
    create_styled_button,
)


class CrashDialog(QDialog):
    """Modal dialog shown after an unhandled exception."""

    def __init__(self, exc_type, exc_value, exc_tb, log_path: str = None, parent=None):
        super().__init__(parent)
        self.log_path = log_path
        self.traceback_text = "".join(tb_module.format_exception(exc_type, exc_value, exc_tb))

        self.setWindowTitle("Umamusume — Unexpected Error")
        self.resize(620, 500)
        self.setMinimumSize(500, 400)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        lay = QVBoxLayout(self)
        lay.setSpacing(SPACING_MD)
        lay.setContentsMargins(0, 0, 0, SPACING_LG)

        # Header band
        hdr = QFrame()
        hdr.setStyleSheet(f"background-color: {BG_ELEVATED}; border: none;")
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        title = QLabel("💥  Something went wrong")
        title.setFont(FONT_HEADER)
        title.setStyleSheet(f"color: {ACCENT_ERROR}; background: transparent;")
        hdr_lay.addWidget(title)

        sub = QLabel(
            "The application encountered an unexpected error. "
            "You can copy the details below and send them to the developer."
        )
        sub.setFont(FONT_SMALL)
        sub.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        sub.setWordWrap(True)
        hdr_lay.addWidget(sub)

        lay.addWidget(hdr)

        # Body
        body_lay = QVBoxLayout()
        body_lay.setContentsMargins(SPACING_LG, 0, SPACING_LG, 0)

        lbl = QLabel("Error details:")
        lbl.setFont(FONT_BODY_BOLD)
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        body_lay.addWidget(lbl)

        self.tb_box = QPlainTextEdit()
        self.tb_box.setFont(FONT_MONO)
        self.tb_box.setStyleSheet(
            f"background-color: {BG_MEDIUM}; color: {ACCENT_ERROR};"
            f"border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_MD}px; padding: 8px;"
        )
        self.tb_box.setPlainText(self.traceback_text)
        self.tb_box.setReadOnly(True)
        body_lay.addWidget(self.tb_box)

        lay.addLayout(body_lay)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(SPACING_LG, 0, SPACING_LG, 0)

        copy_btn = create_styled_button(None, text="📋 Copy to Clipboard",
                                        command=self._copy, style_type="accent")
        btn_row.addWidget(copy_btn)

        if self.log_path and os.path.exists(self.log_path):
            log_btn = create_styled_button(None, text="📄 Open Log File",
                                           command=self._open_log, style_type="default")
            btn_row.addWidget(log_btn)

        btn_row.addStretch()
        close_btn = create_styled_button(None, text="Close",
                                         command=self.accept, style_type="ghost")
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

    def _copy(self):
        QApplication.clipboard().setText(self.traceback_text)

    def _open_log(self):
        try:
            os.startfile(self.log_path)
        except Exception:
            import subprocess
            subprocess.Popen(["xdg-open", self.log_path])


def show_crash_dialog(exc_type, exc_value, exc_tb, log_path: str = None):
    """Show the crash dialog. Safe to call from sys.excepthook."""
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        dlg = CrashDialog(exc_type, exc_value, exc_tb, log_path)
        dlg.exec()
    except Exception:
        try:
            from PySide6.QtWidgets import QMessageBox
            msg = "".join(tb_module.format_exception(exc_type, exc_value, exc_tb))
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "Unexpected Error", msg[:2000])
        except Exception:
            pass
