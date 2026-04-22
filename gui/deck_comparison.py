"""
Deck Comparison Dialog
Compare the combined effects of two decks side by side
PySide6 edition
"""

import os
import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QComboBox, QPushButton, QWidget
)
from PySide6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_decks, get_deck_combined_effects
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_SM, RADIUS_MD, RADIUS_LG
)

def clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()
            else: clear_layout(item.layout())

class DeckComparisonDialog(QDialog):
    """Compare two decks side by side with effect diffs"""

    def __init__(self, parent=None, current_deck_id=None):
        super().__init__(parent)
        self.setWindowTitle("Deck Comparison")
        self.resize(750, 600)
        self.setMinimumSize(650, 500)
        self.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")

        self.decks = get_all_decks()
        self.current_deck_id = current_deck_id

        self._build_ui()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet(f"background: {BG_DARK};")
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        
        t_lbl = QLabel("⚖️  Deck Comparison")
        t_lbl.setFont(FONT_HEADER)
        t_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        hdr_lay.addWidget(t_lbl)
        main_lay.addWidget(hdr)

        # Selectors
        sel_f = QFrame()
        sel_f.setStyleSheet("background: transparent; border: none;")
        sel_lay = QHBoxLayout(sel_f)
        sel_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        vals = [f"{d[0]}: {d[1]}" for d in self.decks]

        a_l = QLabel("Deck A:")
        a_l.setFont(FONT_BODY_BOLD)
        a_l.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        sel_lay.addWidget(a_l)

        self.deck_a_combo = QComboBox()
        self.deck_a_combo.setFixedWidth(220)
        self.deck_a_combo.addItems(vals)
        sel_lay.addWidget(self.deck_a_combo)

        vs_l = QLabel("vs")
        vs_l.setFont(FONT_BODY_BOLD)
        vs_l.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        sel_lay.addWidget(vs_l)

        b_l = QLabel("Deck B:")
        b_l.setFont(FONT_BODY_BOLD)
        b_l.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        sel_lay.addWidget(b_l)

        self.deck_b_combo = QComboBox()
        self.deck_b_combo.setFixedWidth(220)
        self.deck_b_combo.addItems(vals)
        sel_lay.addWidget(self.deck_b_combo)

        sel_lay.addStretch()

        cmp_btn = QPushButton("Compare")
        cmp_btn.setFixedWidth(90)
        cmp_btn.setFixedHeight(32)
        cmp_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT_PRIMARY}; color: {BG_DARKEST}; border-radius: {RADIUS_SM}px; font-weight: bold; }}")
        cmp_btn.clicked.connect(self._compare)
        sel_lay.addWidget(cmp_btn)

        main_lay.addWidget(sel_f)

        if self.current_deck_id and vals:
            for v in vals:
                if v.startswith(f"{self.current_deck_id}:"):
                    self.deck_a_combo.setCurrentText(v)
                    break
            if len(vals) > 1:
                if vals[0].startswith(f"{self.current_deck_id}:"):
                    self.deck_b_combo.setCurrentText(vals[1])
                else:
                    self.deck_b_combo.setCurrentText(vals[0])

        # Results
        res_f = QFrame()
        res_f.setStyleSheet("background: transparent; border: none;")
        res_lay = QVBoxLayout(res_f)
        res_lay.setContentsMargins(SPACING_LG, 0, SPACING_LG, SPACING_LG)

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setStyleSheet(f"QScrollArea {{ background: {BG_DARKEST}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        
        self.res_w = QWidget()
        self.res_w.setStyleSheet("background: transparent;")
        self.grid_lay = QGridLayout(self.res_w)
        self.grid_lay.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_XS, SPACING_XS)
        self.grid_lay.setSpacing(1)
        self.grid_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.grid_lay.setColumnStretch(0, 2)
        self.grid_lay.setColumnStretch(1, 1)
        self.grid_lay.setColumnStretch(2, 1)
        self.grid_lay.setColumnStretch(3, 1)

        self.results_scroll.setWidget(self.res_w)
        res_lay.addWidget(self.results_scroll)
        main_lay.addWidget(res_f, stretch=1)

    def _parse_effect_value(self, value_str):
        try: return float(str(value_str).replace('%', '').replace('+', ''))
        except: return 0.0

    def _compare(self):
        clear_layout(self.grid_lay)

        val_a = self.deck_a_combo.currentText()
        val_b = self.deck_b_combo.currentText()

        if not val_a or not val_b: return

        da_id = int(val_a.split(':')[0])
        db_id = int(val_b.split(':')[0])

        eff_a = get_deck_combined_effects(da_id)
        eff_b = get_deck_combined_effects(db_id)

        all_eff = sorted(set(list(eff_a.keys()) + list(eff_b.keys())))

        hdrs = ["Effect", "Deck A", "Deck B", "Diff"]
        for c, t in enumerate(hdrs):
            l = QLabel(t)
            l.setFont(FONT_BODY_BOLD)
            l.setStyleSheet(f"color: {TEXT_PRIMARY}; background: {BG_MEDIUM}; padding: {SPACING_XS}px; border-radius: {RADIUS_SM}px;")
            self.grid_lay.addWidget(l, 0, c)

        for ri, en in enumerate(all_eff, start=1):
            ta = eff_a.get(en, {}).get('total', 0)
            tb = eff_b.get(en, {}).get('total', 0)
            diff = tb - ta

            bda = eff_a.get(en, {}).get('breakdown', [])
            bdb = eff_b.get(en, {}).get('breakdown', [])
            isp = any('%' in str(v) for bd in [bda, bdb] for _, v in bd)

            fmt = lambda v: f"{v:.0f}%" if isp else (f"{v:+.0f}" if v != 0 else "0")

            if diff > 0:
                dc = ACCENT_SUCCESS
                dt = f"+{diff:.0f}{'%' if isp else ''}"
            elif diff < 0:
                dc = ACCENT_ERROR
                dt = f"{diff:.0f}{'%' if isp else ''}"
            else:
                dc = TEXT_DISABLED
                dt = "—"

            l_name = QLabel(en)
            l_name.setFont(FONT_BODY)
            l_name.setStyleSheet(f"color: {TEXT_SECONDARY}; border: none;")
            self.grid_lay.addWidget(l_name, ri, 0)

            l_a = QLabel(fmt(ta))
            l_a.setFont(FONT_BODY_BOLD)
            l_a.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
            self.grid_lay.addWidget(l_a, ri, 1)

            l_b = QLabel(fmt(tb))
            l_b.setFont(FONT_BODY_BOLD)
            l_b.setStyleSheet(f"color: {ACCENT_SECONDARY}; border: none;")
            self.grid_lay.addWidget(l_b, ri, 2)

            l_d = QLabel(dt)
            l_d.setFont(FONT_BODY_BOLD)
            l_d.setStyleSheet(f"color: {dc}; border: none;")
            self.grid_lay.addWidget(l_d, ri, 3)

def show_deck_comparison(parent, current_deck_id=None):
    DeckComparisonDialog(parent, current_deck_id).exec()
