"""
Update Dialog for UmamusumeCardManager — PySide6 edition
Modal dialog for checking and applying updates.
"""

import threading
import sys
import os
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPlainTextEdit, QWidget
)
from PySide6.QtCore import Qt, Signal, QObject

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from updater.update_checker import check_for_updates, download_update, apply_update, get_current_version
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT,
    ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL,
    SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_MD,
    create_styled_button,
)


class _Signals(QObject):
    check_done    = Signal(object)
    progress      = Signal(float, float, float)
    download_done = Signal(object)


class UpdateDialog(QDialog):
    def __init__(self, parent=None, on_close_callback: Optional[Callable] = None):
        super().__init__(parent)
        self.on_close_callback = on_close_callback
        self.update_info = None
        self.is_downloading = False
        self._sig = _Signals()
        self._sig.check_done.connect(self._on_check_done)
        self._sig.progress.connect(self._on_progress)
        self._sig.download_done.connect(self._on_download_done)

        self.setWindowTitle("Check for Updates")
        self.resize(520, 560)
        self.setMinimumSize(480, 480)
        self.setModal(True)
        self._build_ui()
        threading.Thread(target=lambda: self._sig.check_done.emit(check_for_updates()), daemon=True).start()

    def _build_ui(self):
        self.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        lay = QVBoxLayout(self)
        lay.setSpacing(SPACING_MD)
        lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)

        self.title_lbl = QLabel("🔄  Checking for Updates...")
        self.title_lbl.setFont(FONT_HEADER)
        self.title_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; background: transparent;")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.title_lbl)

        self.status_lbl = QLabel("Connecting to GitHub...")
        self.status_lbl.setFont(FONT_BODY)
        self.status_lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setWordWrap(True)
        lay.addWidget(self.status_lbl)

        self.cur_ver_lbl = QLabel(f"Current: v{get_current_version()}")
        self.cur_ver_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        lay.addWidget(self.cur_ver_lbl)

        self.new_ver_lbl = QLabel("Latest: checking...")
        self.new_ver_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        lay.addWidget(self.new_ver_lbl)

        self.notes_box = QPlainTextEdit("Checking for release notes...")
        self.notes_box.setFont(FONT_SMALL)
        self.notes_box.setStyleSheet(
            f"background-color: {BG_MEDIUM}; color: {TEXT_SECONDARY};"
            f"border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_MD}px; padding: 6px;"
        )
        self.notes_box.setReadOnly(True)
        self.notes_box.setMinimumHeight(160)
        lay.addWidget(self.notes_box, stretch=1)

        self.prog_widget = QWidget()
        prog_lay = QVBoxLayout(self.prog_widget)
        prog_lay.setContentsMargins(0, 0, 0, 0)
        self.prog_lbl = QLabel("")
        self.prog_lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        prog_lay.addWidget(self.prog_lbl)
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 0)
        self.prog_bar.setFixedHeight(10)
        prog_lay.addWidget(self.prog_bar)
        lay.addWidget(self.prog_widget)

        btn_row = QHBoxLayout()
        self.update_btn = create_styled_button(None, text="⬇️ Download & Install",
                                               command=self._start_download, style_type="accent")
        self.update_btn.hide()
        btn_row.addWidget(self.update_btn)
        btn_row.addStretch()
        self.close_btn = create_styled_button(None, text="Close",
                                              command=self.accept, style_type="default")
        btn_row.addWidget(self.close_btn)
        lay.addLayout(btn_row)

    def _on_check_done(self, info):
        self.prog_widget.hide()
        self.prog_bar.setRange(0, 100)
        self.update_info = info
        self.notes_box.setReadOnly(False)
        self.notes_box.clear()
        if info:
            self.title_lbl.setText("🎉 Update Available!")
            self.title_lbl.setStyleSheet(f"color: {ACCENT_SUCCESS}; background: transparent;")
            self.status_lbl.setText("A new version is available.")
            self.status_lbl.setStyleSheet(f"color: {ACCENT_SUCCESS}; background: transparent;")
            self.new_ver_lbl.setText(f"Latest: {info.get('new_version', '?')}")
            self.notes_box.setPlainText(info.get('release_notes', 'No notes.'))
            self.update_btn.show()
        else:
            self.title_lbl.setText("✅ You're Up to Date!")
            self.status_lbl.setText("You are running the latest version.")
            self.new_ver_lbl.setText(f"Latest: v{get_current_version()}")
            self.notes_box.setPlainText("You are using the latest version.\n\nEnjoy!")
        self.notes_box.setReadOnly(True)

    def _start_download(self):
        if self.is_downloading or not self.update_info:
            return
        self.is_downloading = True
        self.update_btn.setEnabled(False)
        self.update_btn.setText("Downloading...")
        self.close_btn.setEnabled(False)
        self.prog_bar.setRange(0, 100)
        self.prog_widget.show()

        def _dl():
            def _cb(dl, tot):
                if tot > 0:
                    self._sig.progress.emit(dl/tot, dl/1024/1024, tot/1024/1024)
            path = download_update(self.update_info['download_url'], _cb)
            self._sig.download_done.emit(path)

        threading.Thread(target=_dl, daemon=True).start()

    def _on_progress(self, pct, dl_mb, tot_mb):
        self.prog_bar.setValue(int(pct * 100))
        self.prog_lbl.setText(f"Downloaded: {dl_mb:.1f} MB / {tot_mb:.1f} MB ({int(pct*100)}%)")

    def _on_download_done(self, path):
        self.is_downloading = False
        self.close_btn.setEnabled(True)
        if path:
            self.title_lbl.setText("✅ Download Complete!")
            self.update_btn.setEnabled(True)
            self.update_btn.setText("🔄 Install & Restart")
            try:
                self.update_btn.clicked.disconnect()
            except Exception:
                pass
            self.update_btn.clicked.connect(lambda: self._install_update(path))
        else:
            self.title_lbl.setText("❌ Download Failed")
            self.update_btn.setEnabled(True)
            self.update_btn.setText("⬇️ Retry Download")

    def _install_update(self, path):
        self.update_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        if apply_update(path):
            self.title_lbl.setText("✅ Update Ready!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: os._exit(0))
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Manual Update Required",
                f"Downloaded: {path}\nPlease replace the current executable manually.")
            self.accept()

    def closeEvent(self, event):
        if self.on_close_callback:
            self.on_close_callback()
        super().closeEvent(event)
