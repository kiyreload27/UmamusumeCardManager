"""
Effects Search View - Search for effects across all owned cards
PySide6 edition with quick-filter chips, counts, sort toggle, and visual result cards
"""

import os
import sys
import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import search_owned_effects
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_INFO, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_button, create_styled_entry
)

# These must match (or be substrings of) the effect_name values stored in the DB:
# Fan Bonus, Friendship Bonus, Mood Effect, Race Bonus, Hint Lv Up, Hint Rate,
# Training Effectiveness, Specialty Rate, Starting Bond, Wisdom Friendship Recovery
QUICK_FILTERS = [
    "Friendship Bonus", "Mood Effect", "Race Bonus", "Fan Bonus",
    "Training Effectiveness", "Specialty Rate", "Hint Rate", "Hint Lv Up"
]

def clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                clear_layout(item.layout())

class ClickableLabel(QLabel):
    def __init__(self, text, callback=None, parent=None):
        super().__init__(text, parent)
        self.callback = callback
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.callback:
            self.callback()
        super().mousePressEvent(event)


class EffectsFrame(QWidget):
    """Spectral rail + canvas"""

    def __init__(self, parent=None, navigate_to_card_callback=None):
        super().__init__(parent)
        self.navigate_to_card = navigate_to_card_callback
        self.icon_cache = {}
        self.sort_high_to_low = True
        self._chip_buttons = {}
        self.result_widgets = []
        
        self._build_ui()
        QTimer.singleShot(300, self._load_chip_counts)

    def _build_ui(self):
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        main_lay.setSpacing(SPACING_LG)

        # ─── Left Rail ───
        rail = QFrame()
        rail.setFixedWidth(260)
        rail.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        rail_lay = QVBoxLayout(rail)
        rail_lay.setContentsMargins(SPACING_MD, SPACING_LG, SPACING_MD, SPACING_LG)
        
        l1 = QLabel("SPECTRUM")
        l1.setFont(FONT_TINY)
        l1.setStyleSheet(f"color: {ACCENT_SECONDARY}; border: none;")
        rail_lay.addWidget(l1)
        
        l2 = QLabel("Quick bands")
        l2.setFont(FONT_HEADER)
        l2.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        rail_lay.addWidget(l2)
        
        chips_frame = QFrame()
        chips_frame.setStyleSheet("background: transparent; border: none;")
        chips_lay = QVBoxLayout(chips_frame)
        chips_lay.setContentsMargins(0, SPACING_LG, 0, 0)
        chips_lay.setSpacing(SPACING_SM)

        for term in QUICK_FILTERS:
            btn = QPushButton(term)
            btn.setFixedHeight(30)
            btn.setFont(FONT_TINY)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_MEDIUM}; color: {TEXT_MUTED};
                    border: none; border-radius: 15px;
                }}
                QPushButton:hover {{ background-color: {BG_HIGHLIGHT}; }}
            """)
            btn.clicked.connect(lambda _, t=term: self._quick_search(t))
            chips_lay.addWidget(btn)
            self._chip_buttons[term] = btn
        
        rail_lay.addWidget(chips_frame)
        rail_lay.addStretch()
        main_lay.addWidget(rail)

        # ─── Main Content ───
        center_w = QWidget()
        center_lay = QVBoxLayout(center_w)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(SPACING_MD)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)

        t_row = QHBoxLayout()
        t_row.setContentsMargins(0, 0, 0, 0)
        t1 = QLabel("Effect resonance")
        t1.setFont(FONT_HEADER)
        t1.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        t_row.addWidget(t1)
        t_row.addStretch()
        t2 = QLabel("Owned cards only")
        t2.setFont(FONT_SMALL)
        t2.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        t_row.addWidget(t2)
        hdr_lay.addLayout(t_row)

        s_row = QHBoxLayout()
        s_row.setContentsMargins(0, SPACING_MD, 0, 0)
        self.search_entry = create_styled_entry(None, placeholder="Type an effect name...")
        self.search_entry.returnPressed.connect(self.perform_search)
        s_row.addWidget(self.search_entry, stretch=1)
        
        self.sort_btn = create_styled_button(None, text="High", command=self._toggle_sort, style_type="secondary", width=70)
        s_row.addWidget(self.sort_btn)
        
        search_btn = create_styled_button(None, text="Scan", command=self.perform_search, style_type="accent", width=100)
        s_row.addWidget(search_btn)
        hdr_lay.addLayout(s_row)
        
        center_lay.addWidget(hdr)

        # Results area
        res_frame = QFrame()
        res_frame.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        res_lay = QVBoxLayout(res_frame)
        res_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        r_hdr = QHBoxLayout()
        rh1 = QLabel("Results")
        rh1.setFont(FONT_SUBHEADER)
        rh1.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        r_hdr.addWidget(rh1)
        r_hdr.addStretch()
        self.status_label = QLabel("")
        self.status_label.setFont(FONT_TINY)
        self.status_label.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        r_hdr.addWidget(self.status_label)
        res_lay.addLayout(r_hdr)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")
        self.grid_w = QWidget()
        self.grid_w.setStyleSheet("background: transparent;")
        self.grid_lay = QGridLayout(self.grid_w)
        self.grid_lay.setContentsMargins(0, 0, 0, 0)
        self.grid_lay.setSpacing(SPACING_SM)
        self.grid_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.grid_w)
        
        res_lay.addWidget(self.scroll_area, stretch=1)
        center_lay.addWidget(res_frame, stretch=1)

        main_lay.addWidget(center_w, stretch=1)

    def _load_chip_counts(self):
        for term, chip in self._chip_buttons.items():
            try:
                results = search_owned_effects(term)
                count = len(results)
                chip.setText(f"{term} ({count})" if count else term)
            except Exception:
                pass

    def _toggle_sort(self):
        self.sort_high_to_low = not self.sort_high_to_low
        self.sort_btn.setText("High" if self.sort_high_to_low else "Low")
        if self.grid_lay.count() > 0:
            self.perform_search()

    def _quick_search(self, term):
        self.search_entry.setText(term)
        self.perform_search()

    def parse_value(self, value_str):
        try:
            clean = re.sub(r'[^\d.-]', '', str(value_str))
            return float(clean)
        except:
            return -999999.0

    def _get_value_color(self, value_str):
        val_str = str(value_str)
        if '%' in val_str:
            try:
                num = int(val_str.replace('%', '').replace('+', ''))
                if num >= 20: return ACCENT_WARNING
                elif num >= 10: return ACCENT_PRIMARY
                else: return ACCENT_SECONDARY
            except: pass
        elif val_str.lstrip('+-').isdigit():
            return ACCENT_SUCCESS
        return ACCENT_INFO

    def perform_search(self):
        term = self.search_entry.text().strip()
        if not term:
            QMessageBox.warning(self, "Search", "Please enter a search term")
            return

        clear_layout(self.grid_lay)

        results = search_owned_effects(term)
        if not results:
            self.status_label.setText("No matching effects found among owned cards.")
            return

        processed = []
        for r in results:
            val_num = self.parse_value(r[4])
            processed.append({'data': r, 'sort_val': val_num})
        
        processed.sort(key=lambda x: x['sort_val'], reverse=self.sort_high_to_low)

        row, col = 0, 0
        count = 0
        for item in processed:
            if count >= 100:
                self.status_label.setText(f"Showing top 100 of {len(processed)} results")
                break
            count += 1

            r = item['data']
            card_id, card_name, image_path, effect_name, effect_value, level = r

            f = QFrame()
            f.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_MD}px; }}")
            self.grid_lay.addWidget(f, row, col)

            f_lay = QHBoxLayout(f)
            f_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
            f_lay.setSpacing(SPACING_SM)

            img_lbl = QLabel()
            img_lbl.setFixedSize(48, 48)
            pix = self.icon_cache.get(card_id)
            if not pix:
                rp = resolve_image_path(image_path)
                if rp and os.path.exists(rp):
                    try:
                        pix = QPixmap(rp).scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.icon_cache[card_id] = pix
                    except: pass
            if pix:
                img_lbl.setPixmap(pix)
            f_lay.addWidget(img_lbl)

            info_lay = QVBoxLayout()
            info_lay.setContentsMargins(0, 0, 0, 0)
            info_lay.setSpacing(2)

            h_row = QHBoxLayout()
            h_row.setContentsMargins(0, 0, 0, 0)
            n_lbl = ClickableLabel(card_name, callback=lambda cid=card_id: self.navigate_to_card(cid) if self.navigate_to_card else None)
            n_lbl.setFont(FONT_SMALL)
            n_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
            h_row.addWidget(n_lbl, stretch=1)

            l_lbl = QLabel(f"Lv{level}")
            l_lbl.setFont(FONT_TINY)
            l_lbl.setStyleSheet(f"color: {ACCENT_SUCCESS}; background-color: {BG_MEDIUM}; border-radius: 4px; padding: 2px 6px;")
            h_row.addWidget(l_lbl)
            info_lay.addLayout(h_row)

            e_row = QHBoxLayout()
            e_row.setContentsMargins(0, 0, 0, 0)
            e_lbl = QLabel(effect_name)
            e_lbl.setFont(FONT_TINY)
            e_lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
            e_row.addWidget(e_lbl, stretch=1)

            v_lbl = QLabel(str(effect_value))
            v_lbl.setFont(FONT_SMALL)
            v_lbl.setStyleSheet(f"color: {self._get_value_color(effect_value)}; border: none;")
            e_row.addWidget(v_lbl)
            info_lay.addLayout(e_row)

            f_lay.addLayout(info_lay, stretch=1)

            col += 1
            if col > 3:  # 4 columns
                col = 0
                row += 1

        self.status_label.setText(f"Found {len(processed)} matches")

    def set_card(self, card_id):
        pass
