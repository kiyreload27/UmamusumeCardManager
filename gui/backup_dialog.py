"""
Backup & Restore Dialog — PySide6 edition
Export/import user data (owned cards, decks) as JSON files.
"""

import json
import os
import sys
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import export_user_data, import_user_data
from version import VERSION
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_MD,
    create_styled_button,
)


class BackupDialog(QDialog):
    """Dialog for exporting and importing user data backups."""

    def __init__(self, parent=None, on_restore_callback=None):
        super().__init__(parent)
        self.on_restore = on_restore_callback
        self.setWindowTitle("Backup & Restore")
        self.resize(480, 460)
        self.setFixedSize(480, 460)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet(f"background-color: {BG_DARK}; border: none;")
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_MD)

        title = QLabel("💾  Backup & Restore")
        title.setFont(FONT_HEADER)
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        hdr_lay.addWidget(title)

        sub = QLabel("Export your owned cards, decks, and notes to a file,\nor restore from a previous backup.")
        sub.setFont(FONT_SMALL)
        sub.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        sub.setWordWrap(True)
        hdr_lay.addWidget(sub)
        lay.addWidget(hdr)

        # Body
        body_lay = QVBoxLayout()
        body_lay.setContentsMargins(SPACING_LG, SPACING_SM, SPACING_LG, SPACING_LG)
        body_lay.setSpacing(SPACING_SM)

        # Export card
        body_lay.addWidget(self._make_section(
            "📤  Export Backup",
            "Save your owned cards, decks, and notes to a JSON file.",
            "Export to File...", self._export, style_type="accent"
        ))

        # Import card
        body_lay.addWidget(self._make_section(
            "📥  Restore from Backup",
            "Load a backup file. This will REPLACE all existing user data.",
            "📂  Restore from File...", self._import,
            style_type="danger", warning=True
        ))

        self.status_lbl = QLabel("")
        self.status_lbl.setFont(FONT_SMALL)
        self.status_lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        self.status_lbl.setWordWrap(True)
        body_lay.addWidget(self.status_lbl)

        body_lay.addStretch()

        close_btn = create_styled_button(None, text="Close",
                                         command=self.accept, style_type="ghost",
                                         width=100, height=32)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_btn)
        body_lay.addLayout(close_row)

        lay.addLayout(body_lay)

    def _make_section(self, title, desc, btn_text, btn_cmd, style_type="default", warning=False):
        frame = QFrame()
        frame.setStyleSheet(
            f".QFrame {{ background-color: {BG_MEDIUM}; border: 1px solid {BG_LIGHT};"
            f"border-radius: {RADIUS_MD}px; }}"
        )
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        inner.setSpacing(SPACING_XS)

        t = QLabel(title)
        t.setFont(FONT_BODY_BOLD)
        t.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        inner.addWidget(t)

        d = QLabel(desc)
        d.setFont(FONT_TINY)
        color = ACCENT_WARNING if warning else TEXT_MUTED
        d.setStyleSheet(f"color: {color}; background: transparent;")
        inner.addWidget(d)

        btn = create_styled_button(None, text=btn_text, command=btn_cmd,
                                   style_type=style_type, height=36)
        btn.setFixedWidth(200)
        inner.addWidget(btn)
        return frame

    def _export(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"uma_backup_{timestamp}.json"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Backup", default_name,
            "JSON files (*.json);;All files (*.*)"
        )
        if not filepath:
            return
        try:
            data = export_user_data()
            data['_meta'] = {
                'app': 'UmamusumeCardManager',
                'exported_at': datetime.now().isoformat(),
                'version': VERSION
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            owned = len(data.get('owned_cards', []))
            decks = len(data.get('decks', []))
            notes = len(data.get('notes', []))
            self._set_status(f"✅ Exported: {owned} owned cards, {decks} decks, {notes} notes", ACCENT_SUCCESS)
        except Exception as e:
            self._set_status(f"❌ Export failed: {e}", ACCENT_ERROR)

    def _import(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Backup", "",
            "JSON files (*.json);;All files (*.*)"
        )
        if not filepath:
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self._set_status(f"❌ Invalid backup file: {e}", ACCENT_ERROR)
            return

        owned = len(data.get('owned_cards', []))
        decks = len(data.get('decks', []))
        notes = len(data.get('notes', []))
        export_date = data.get('_meta', {}).get('exported_at', 'Unknown')

        confirm = QMessageBox.question(
            self, "Confirm Restore",
            f"This will REPLACE all your current data with:\n\n"
            f"  • {owned} owned cards\n"
            f"  • {decks} decks\n"
            f"  • {notes} notes/tags\n\n"
            f"Exported: {export_date}\n\nAre you sure? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            summary = import_user_data(data)
            self._set_status(
                f"✅ Restored: {summary['owned']} cards, {summary['decks']} decks, "
                f"{summary['notes']} notes ({summary['skipped']} skipped)",
                ACCENT_SUCCESS
            )
            if self.on_restore:
                self.on_restore()
        except Exception as e:
            self._set_status(f"❌ Restore failed: {e}", ACCENT_ERROR)

    def _set_status(self, text: str, color: str):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {color}; background: transparent;")


def show_backup_dialog(parent=None, on_restore_callback=None):
    """Convenience function — show backup dialog and exec."""
    dlg = BackupDialog(parent, on_restore_callback)
    dlg.exec()
