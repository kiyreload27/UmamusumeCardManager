"""
Skill Search View - Find cards by the skills they teach
PySide6 edition with filterable skill list, keyword category bar, and rich card results
"""

import os
import sys
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QLineEdit, QPushButton, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_unique_skills, get_cards_with_skill
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY, ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    get_type_icon, get_rarity_color, create_styled_entry
)


SKILL_CATEGORIES = {
    "All":         [],
    "Speed":       ["speed", "acceleration", "escape", "start dash", "leading"],
    "Stamina":     ["stamina", "recovery", "heal", "recover", "second wind"],
    "Power":       ["power", "strength", "push"],
    "Guts":        ["guts", "tenac", "endur", "persist"],
    "Wisdom":      ["wisdom", "vision", "eye", "foresight", "strategic"],
    "Corner":      ["corner", "curve", "bend", "turn"],
    "Final":       ["final", "straight", "spurt", "last", "end close"],
    "Positioning": ["position", "pass", "overtake", "outside", "inside", "between", "leader", "chaser", "runner"],
    "Golden":      [],
}

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


class SkillSearchFrame(QWidget):
    """Frame for searching skills and finding cards that have them"""

    def __init__(self, parent=None, navigate_to_card_callback=None):
        super().__init__(parent)
        self.navigate_to_card = navigate_to_card_callback
        self.all_skills = []
        self.icon_cache = {}
        self.current_skill = None
        self.skill_widgets = []
        self.result_widgets = []
        self.active_category = "All"

        self._skill_render_gen = 0
        self._card_render_gen = 0
        self._skill_render_queue = []
        self._card_render_queue = []

        self._build_ui()
        self.load_skills()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        main_lay.setSpacing(SPACING_SM)

        # ─── Top Strip ───
        top_strip = QFrame()
        top_strip.setStyleSheet(f".QFrame {{ background-color: {BG_ELEVATED}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        top_lay = QVBoxLayout(top_strip)
        top_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        t = QLabel("LEXICON")
        t.setFont(FONT_SUBHEADER)
        t.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        title_row.addWidget(t)
        title_row.addStretch()
        self.skill_count_label = QLabel("")
        self.skill_count_label.setFont(FONT_TINY)
        self.skill_count_label.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        title_row.addWidget(self.skill_count_label)
        top_lay.addLayout(title_row)

        self.search_entry = create_styled_entry(None, placeholder="Filter skills in the index…")
        self.search_entry.textChanged.connect(self.filter_skills)
        top_lay.addWidget(self.search_entry)

        cat_frame = QFrame()
        cat_frame.setStyleSheet("background: transparent; border: none;")
        cat_lay = QHBoxLayout(cat_frame)
        cat_lay.setContentsMargins(0, 0, 0, 0)
        cat_lay.setSpacing(4)
        cat_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._cat_buttons = {}
        for cat in SKILL_CATEGORIES:
            btn = QPushButton(cat)
            btn.setFixedHeight(24)
            btn.setFont(FONT_TINY)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if cat == "All":
                btn.setStyleSheet(f"background-color: {ACCENT_PRIMARY}; color: {TEXT_PRIMARY}; border: none; border-radius: 12px; padding: 0 10px;")
            else:
                btn.setStyleSheet(f"background-color: {BG_MEDIUM}; color: {TEXT_MUTED}; border: none; border-radius: 12px; padding: 0 10px;")
            btn.clicked.connect(lambda _, c=cat: self._set_category(c))
            cat_lay.addWidget(btn)
            self._cat_buttons[cat] = btn

        top_lay.addWidget(cat_frame)
        main_lay.addWidget(top_strip)

        # ─── Content Split ───
        content_w = QWidget()
        content_lay = QHBoxLayout(content_w)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(SPACING_SM)

        # Left: Index
        left_frame = QFrame()
        left_frame.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        l_hdr = QLabel("SKILL INDEX")
        l_hdr.setFont(FONT_SMALL)
        l_hdr.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        left_lay.addWidget(l_hdr)

        self.skill_scroll = QScrollArea()
        self.skill_scroll.setWidgetResizable(True)
        self.skill_scroll.setStyleSheet("border: none; background: transparent;")
        self.skill_list_w = QWidget()
        self.skill_list_w.setStyleSheet("background: transparent;")
        self.skill_list_lay = QVBoxLayout(self.skill_list_w)
        self.skill_list_lay.setContentsMargins(0, 0, 0, 0)
        self.skill_list_lay.setSpacing(1)
        self.skill_list_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.skill_scroll.setWidget(self.skill_list_w)
        left_lay.addWidget(self.skill_scroll)
        content_lay.addWidget(left_frame, stretch=1)

        # Right: Manifest
        right_frame = QFrame()
        right_frame.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        right_lay = QVBoxLayout(right_frame)
        right_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        
        r_hdr_row = QHBoxLayout()
        self.result_header = QLabel("Select a skill to see cards")
        self.result_header.setFont(FONT_SUBHEADER)
        self.result_header.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        r_hdr_row.addWidget(self.result_header)
        r_hdr_row.addStretch()
        self.owned_cb = QCheckBox("Owned only")
        self.owned_cb.setFont(FONT_SMALL)
        self.owned_cb.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        self.owned_cb.toggled.connect(self.on_filter_changed)
        r_hdr_row.addWidget(self.owned_cb)
        right_lay.addLayout(r_hdr_row)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setStyleSheet("border: none; background: transparent;")
        self.cards_w = QWidget()
        self.cards_w.setStyleSheet("background: transparent;")
        self.cards_lay = QVBoxLayout(self.cards_w)
        self.cards_lay.setContentsMargins(0, 0, 0, 0)
        self.cards_lay.setSpacing(SPACING_SM)
        self.cards_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_scroll.setWidget(self.cards_w)
        right_lay.addWidget(self.cards_scroll, stretch=1)

        self.stats_label = QLabel("")
        self.stats_label.setFont(FONT_TINY)
        self.stats_label.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_lay.addWidget(self.stats_label)

        content_lay.addWidget(right_frame, stretch=2)
        main_lay.addWidget(content_w, stretch=1)

    def _set_category(self, category):
        self.active_category = category
        for cat, btn in self._cat_buttons.items():
            if cat == category:
                btn.setStyleSheet(f"background-color: {ACCENT_PRIMARY}; color: {TEXT_PRIMARY}; border: none; border-radius: 12px; padding: 0 10px;")
            else:
                btn.setStyleSheet(f"background-color: {BG_MEDIUM}; color: {TEXT_MUTED}; border: none; border-radius: 12px; padding: 0 10px;")
        self.filter_skills()

    def load_skills(self):
        self.all_skills = get_all_unique_skills()
        self.update_skill_list(self._apply_category_filter(self.all_skills))

    def _apply_category_filter(self, skills):
        cat = self.active_category
        if cat == "All":
            return skills

        keywords = SKILL_CATEGORIES.get(cat, [])

        if cat == "Golden":
            result = []
            for item in skills:
                if isinstance(item, tuple):
                    _, is_golden = item
                    if is_golden: result.append(item)
            return result

        result = []
        for item in skills:
            if isinstance(item, tuple):
                skill_name, _ = item
            else:
                skill_name = item
            name_lower = skill_name.lower()
            if any(kw in name_lower for kw in keywords):
                result.append(item)
        return result

    def _select_skill_widget(self, skill_name, widget):
        for w in self.skill_widgets:
            w.setStyleSheet("background: transparent; border: none; text-align: left; padding-left: 8px;")
        widget.setStyleSheet(f"background: {BG_HIGHLIGHT}; border: none; border-radius: {RADIUS_SM}px; text-align: left; padding-left: 8px;")
        self.on_skill_selected(skill_name)

    def update_skill_list(self, items):
        self._skill_render_gen += 1
        my_gen = self._skill_render_gen

        clear_layout(self.skill_list_lay)
        self.skill_widgets.clear()

        display_items = items  # No cap — chunked renderer handles performance
        self.skill_count_label.setText(f"{len(items)} skills")
        self._skill_render_queue = display_items[:]
        QTimer.singleShot(0, lambda: self._process_skill_queue(my_gen))

    def _process_skill_queue(self, gen):
        if gen != self._skill_render_gen or not self._skill_render_queue:
            return

        chunk = self._skill_render_queue[:15]
        self._skill_render_queue = self._skill_render_queue[15:]

        for item in chunk:
            if isinstance(item, tuple):
                skill_name, is_golden = item
            else:
                skill_name, is_golden = item, False

            color = ACCENT_WARNING if is_golden else TEXT_PRIMARY
            prefix = "✨ " if is_golden else "•  "

            btn = QPushButton(f"{prefix}{skill_name}")
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Using custom style to left-align text in QPushButton
            btn.setStyleSheet("background: transparent; border: none; text-align: left; padding-left: 8px;")
            if is_golden:
                btn.setFont(FONT_BODY_BOLD)
            else:
                btn.setFont(FONT_BODY)
            
            # Since QPushButton text color via stylesheet might override dynamic selection, 
            # we embed color in HTML or apply it to the stylesheet
            btn.setStyleSheet(f"background: transparent; border: none; text-align: left; padding-left: 8px; color: {color};")
            
            btn.clicked.connect(lambda _, n=skill_name, b=btn: self._select_skill_widget(n, b))
            self.skill_list_lay.addWidget(btn)
            self.skill_widgets.append(btn)

        if self._skill_render_queue and gen == self._skill_render_gen:
            QTimer.singleShot(10, lambda: self._process_skill_queue(gen))

    def filter_skills(self):
        search = self.search_entry.text().lower()
        category_filtered = self._apply_category_filter(self.all_skills)

        if not search:
            self.update_skill_list(category_filtered)
            return

        filtered = []
        for item in category_filtered:
            if isinstance(item, tuple):
                skill_name, is_golden = item
                if search in skill_name.lower() or (search == "golden" and is_golden):
                    filtered.append(item)
            else:
                if search in item.lower():
                    filtered.append(item)

        self.update_skill_list(filtered)

    def on_filter_changed(self):
        if self.current_skill:
            self.show_cards_for_skill(self.current_skill)

    def on_skill_selected(self, skill_name):
        self.current_skill = skill_name
        self.show_cards_for_skill(skill_name)

    def show_cards_for_skill(self, skill_name):
        self.current_skill = skill_name
        self._card_render_gen += 1
        my_gen = self._card_render_gen

        self.result_header.setText(f"Cards with  ✨ {skill_name}")
        clear_layout(self.cards_lay)

        cards = get_cards_with_skill(skill_name)
        owned_only = self.owned_cb.isChecked()

        filtered_cards = []
        for card in cards:
            if owned_only and not card.get('is_owned'):
                continue
            filtered_cards.append(card)

        self.stats_label.setText("Loading...")
        self._card_render_queue = filtered_cards[:]
        self._card_render_count = 0
        QTimer.singleShot(0, lambda: self._process_card_queue(my_gen))

    def _process_card_queue(self, gen):
        if gen != self._card_render_gen or not self._card_render_queue:
            if gen == self._card_render_gen:
                self.stats_label.setText(f"Found {self._card_render_count} cards teaching ✨ {self.current_skill}")
            return

        chunk = self._card_render_queue[:8]
        self._card_render_queue = self._card_render_queue[8:]

        for card in chunk:
            self._card_render_count += 1
            card_id = card['card_id']
            card_type = card.get('type') or card.get('card_type') or 'Unknown'
            rarity = card.get('rarity') or 'Unknown'
            is_owned = card.get('is_owned')

            bg_color = BG_ELEVATED if is_owned else BG_DARK
            border_color = ACCENT_SUCCESS if is_owned else BG_LIGHT

            f = QFrame()
            f.setStyleSheet(f".QFrame {{ background-color: {bg_color}; border: 1px solid {border_color}; border-radius: {RADIUS_MD}px; }}")
            self.cards_lay.addWidget(f)

            f_lay = QHBoxLayout(f)
            f_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
            f_lay.setSpacing(SPACING_SM)

            img_lbl = QLabel()
            img_lbl.setFixedSize(44, 44)
            pix = self.icon_cache.get(card_id)
            if not pix:
                rp = resolve_image_path(card.get('image_path', ''))
                if rp and os.path.exists(rp):
                    try:
                        pix = QPixmap(rp).scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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
            n_lbl = ClickableLabel(card.get('name', 'Unknown'), callback=lambda cid=card_id: self.navigate_to_card(cid) if self.navigate_to_card else None)
            n_lbl.setFont(FONT_SMALL)
            n_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
            h_row.addWidget(n_lbl, stretch=1)

            meta_txt = f"{get_type_icon(card_type)} {card_type}"
            m_lbl = QLabel(meta_txt)
            m_lbl.setFont(FONT_TINY)
            m_lbl.setStyleSheet(f"color: {get_rarity_color(rarity)}; border: none;")
            h_row.addWidget(m_lbl)
            info_lay.addLayout(h_row)

            source = card.get('source', '')
            golden = card.get('is_gold', False)
            if golden:
                source = f"✨ GOLDEN {source.replace('✨ GOLDEN ', '')}"

            if source:
                source_color = ACCENT_WARNING if golden else (ACCENT_SECONDARY if 'Event' in source else ACCENT_INFO)
                s_lbl = QLabel(source)
                s_lbl.setFont(FONT_TINY)
                s_lbl.setStyleSheet(f"color: {source_color}; border: none;")
                info_lay.addWidget(s_lbl)

            details_text = card.get('details', '')
            if details_text:
                d_lbl = QLabel(details_text)
                d_lbl.setFont(FONT_TINY)
                d_lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
                d_lbl.setWordWrap(True)
                info_lay.addWidget(d_lbl)

            f_lay.addLayout(info_lay, stretch=1)

        if self._card_render_queue and gen == self._card_render_gen:
            QTimer.singleShot(10, lambda: self._process_card_queue(gen))

    def set_card(self, card_id):
        pass
