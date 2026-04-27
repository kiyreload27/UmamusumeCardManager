from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout
from PySide6.QtCore import Qt

from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT,
    TEXT_PRIMARY, TEXT_MUTED, ACCENT_PRIMARY,
    FONT_TITLE, FONT_BODY, FONT_SMALL,
    SPACING_MD, SPACING_LG, RADIUS_MD,
    create_styled_button
)

class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setFixedSize(500, 400)
        self.setStyleSheet(f"QDialog {{ background-color: {BG_DARKEST}; }}")
        
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        lay.setSpacing(SPACING_LG)

        # Header
        hdr = QLabel("⌨️ Keyboard Shortcuts")
        hdr.setFont(FONT_TITLE)
        hdr.setStyleSheet(f"color: {TEXT_PRIMARY};")
        lay.addWidget(hdr)

        # Content
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {BG_DARK}; border-radius: {RADIUS_MD}px;")
        f_lay = QVBoxLayout(frame)
        f_lay.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)

        grid = QGridLayout()
        grid.setSpacing(SPACING_MD)
        
        shortcuts = [
            ("Ctrl + F", "Focus search bar in Card Library or Skill Search"),
            ("Ctrl + 1-8", "Navigate between main views"),
            ("Ctrl + Shift + D", "Open Debug Panel"),
            ("Esc", "Close current dialog or popup"),
        ]

        for i, (keys, desc) in enumerate(shortcuts):
            k_lbl = QLabel(keys)
            k_lbl.setFont(FONT_BODY)
            k_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; background: {BG_MEDIUM}; padding: 4px 8px; border-radius: 4px;")
            k_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            d_lbl = QLabel(desc)
            d_lbl.setFont(FONT_BODY)
            d_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
            
            grid.addWidget(k_lbl, i, 0)
            grid.addWidget(d_lbl, i, 1)

        grid.setColumnStretch(1, 1)
        f_lay.addLayout(grid)
        lay.addWidget(frame)

        lay.addStretch()

        # Close
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        close_btn = create_styled_button(self, text="Close", command=self.accept, style_type="ghost", width=100)
        btn_lay.addWidget(close_btn)
        lay.addLayout(btn_lay)
