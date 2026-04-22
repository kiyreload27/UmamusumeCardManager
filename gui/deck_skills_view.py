"""
Deck Skills View - Detailed breakdown of all skills in a deck or for a single card
PySide6 edition with compact collapsible skill rows, sticky card headers, and top summary bar
"""

import os
import sys
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QComboBox, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import (
    get_all_decks, get_deck_cards, get_card_by_id,
    get_hints, get_all_event_skills
)
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_WARNING, ACCENT_SUCCESS, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    get_type_icon, get_rarity_color
)

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
        if callback:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.callback:
            self.callback()
        super().mousePressEvent(event)


class CollapsibleSkillRow(QFrame):
    def __init__(self, skill, navigate_to_skill=None, parent=None):
        super().__init__(parent)
        self.skill = skill
        self.navigate_to_skill = navigate_to_skill
        self.expanded = False
        self.setStyleSheet("background: transparent;")
        
        self.is_golden = skill['golden']
        self.has_desc = bool(skill.get('desc'))
        
        if self.is_golden:
            self.src_color = ACCENT_WARNING
            self.prefix = "✨ "
            self.c_name = ACCENT_WARNING
            self.bg_normal = "#2a2200"
            self.bg_hover = "#3d3200"
        elif 'Event' in skill['source']:
            self.src_color = ACCENT_SECONDARY
            self.prefix = "◆ "
            self.c_name = TEXT_PRIMARY
            self.bg_normal = BG_MEDIUM
            self.bg_hover = BG_HIGHLIGHT
        else:
            self.src_color = ACCENT_INFO
            self.prefix = "• "
            self.c_name = TEXT_SECONDARY
            self.bg_normal = BG_MEDIUM
            self.bg_hover = BG_HIGHLIGHT

        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 1)
        lay.setSpacing(0)

        self.row_frame = QFrame()
        self.row_frame.setStyleSheet(f"background: {self.bg_normal}; border-radius: {RADIUS_SM}px;")
        if self.has_desc:
            self.row_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            
        r_lay = QHBoxLayout(self.row_frame)
        r_lay.setContentsMargins(SPACING_SM, 4, SPACING_SM, 4)

        n_lbl = ClickableLabel(f"{self.prefix}{self.skill['name']}", callback=self._on_name_click)
        fnt = FONT_BODY_BOLD if self.is_golden else FONT_SMALL
        n_lbl.setFont(fnt)
        n_lbl.setStyleSheet(f"color: {self.c_name}; border: none;")
        r_lay.addWidget(n_lbl, stretch=1)

        s_lbl = QLabel(self.skill['source'])
        s_lbl.setFont(FONT_TINY)
        s_lbl.setStyleSheet(f"color: {self.src_color}; background: {BG_DARK}; border-radius: {RADIUS_SM}px; padding: 0 4px;")
        r_lay.addWidget(s_lbl)
        
        lay.addWidget(self.row_frame)

        if self.has_desc:
            self.desc_lbl = QLabel(self.skill['desc'])
            self.desc_lbl.setFont(FONT_TINY)
            self.desc_lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none; padding: 2px {SPACING_LG}px 0 {SPACING_LG}px;")
            self.desc_lbl.setWordWrap(True)
            self.desc_lbl.hide()
            lay.addWidget(self.desc_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.has_desc:
            self.toggle_desc()
        super().mousePressEvent(event)

    def _on_name_click(self):
        if self.navigate_to_skill and not self.has_desc:
            self.navigate_to_skill(self.skill['name'])
        elif self.has_desc:
            self.toggle_desc()

    def toggle_desc(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.desc_lbl.show()
            self.row_frame.setStyleSheet(f"background: {self.bg_hover}; border-radius: {RADIUS_SM}px;")
        else:
            self.desc_lbl.hide()
            self.row_frame.setStyleSheet(f"background: {self.bg_normal}; border-radius: {RADIUS_SM}px;")


class DeckSkillsFrame(QWidget):
    """Frame for viewing combined skills of a deck or individual cards"""

    def __init__(self, parent=None, navigate_to_card_callback=None, navigate_to_skill_callback=None):
        super().__init__(parent)
        self.navigate_to_card = navigate_to_card_callback
        self.navigate_to_skill = navigate_to_skill_callback
        self.icon_cache = {}
        self.current_mode = "Deck"
        
        self._block_render_gen = 0
        self._block_render_queue = []

        self._build_ui()
        self.refresh_decks()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        main_lay.setSpacing(SPACING_LG)

        # ─── Top Control Bar ───
        ctrl_f = QFrame()
        ctrl_f.setStyleSheet(f".QFrame {{ background-color: {BG_ELEVATED}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        ctrl_lay = QHBoxLayout(ctrl_f)
        ctrl_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        d_lbl = QLabel("DECK")
        d_lbl.setFont(FONT_SMALL)
        d_lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        ctrl_lay.addWidget(d_lbl)

        self.deck_combo = QComboBox()
        self.deck_combo.setFixedWidth(280)
        self.deck_combo.currentTextChanged.connect(self.on_deck_selected_val)
        ctrl_lay.addWidget(self.deck_combo)
        
        ctrl_lay.addStretch()

        self.mode_label = QLabel("Showing skills for selected deck")
        self.mode_label.setFont(FONT_SMALL)
        self.mode_label.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        ctrl_lay.addWidget(self.mode_label)

        main_lay.addWidget(ctrl_f)

        # ─── Split Area ───
        split_w = QWidget()
        split_lay = QHBoxLayout(split_w)
        split_lay.setContentsMargins(0, 0, 0, 0)
        split_lay.setSpacing(SPACING_MD)

        # Summary Left
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet(f".QFrame {{ background-color: {BG_MEDIUM}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        sum_lay = QVBoxLayout(self.summary_frame)
        sum_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_LG)
        
        t_lbl = QLabel("TELEMETRY")
        t_lbl.setFont(FONT_SMALL)
        t_lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        sum_lay.addWidget(t_lbl)

        self.stats_total = QLabel("—  Skills")
        self.stats_total.setFont(FONT_BODY_BOLD)
        self.stats_total.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        sum_lay.addWidget(self.stats_total)

        self.stats_hints = QLabel("Hints: —")
        self.stats_hints.setFont(FONT_SMALL)
        self.stats_hints.setStyleSheet(f"color: {ACCENT_INFO}; border: none;")
        sum_lay.addWidget(self.stats_hints)

        self.stats_events = QLabel("Events: —")
        self.stats_events.setFont(FONT_SMALL)
        self.stats_events.setStyleSheet(f"color: {ACCENT_SECONDARY}; border: none;")
        sum_lay.addWidget(self.stats_events)

        self.stats_golden = QLabel("Golden: —")
        self.stats_golden.setFont(FONT_SMALL)
        self.stats_golden.setStyleSheet(f"color: {ACCENT_WARNING}; border: none;")
        sum_lay.addWidget(self.stats_golden)
        sum_lay.addStretch()

        split_lay.addWidget(self.summary_frame, stretch=1)

        # Results Right
        self.results_container = QFrame()
        self.results_container.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        res_lay = QVBoxLayout(self.results_container)
        res_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")
        
        self.cards_w = QWidget()
        self.cards_w.setStyleSheet("background: transparent;")
        self.cards_lay = QVBoxLayout(self.cards_w)
        self.cards_lay.setContentsMargins(0, 0, 0, 0)
        self.cards_lay.setSpacing(SPACING_SM)
        self.cards_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.cards_w)
        res_lay.addWidget(self.scroll_area)

        split_lay.addWidget(self.results_container, stretch=2)
        main_lay.addWidget(split_w, stretch=1)

    def refresh_decks(self):
        decks = get_all_decks()
        values = [f"{d[0]}: {d[1]}" for d in decks]
        self.deck_combo.blockSignals(True)
        self.deck_combo.clear()
        self.deck_combo.addItems(values)
        self.deck_combo.blockSignals(False)
        if values:
            self.deck_combo.setCurrentText(values[0])
            self.on_deck_selected_val(values[0])

    def on_deck_selected_val(self, value):
        if not value: return
        deck_id = int(value.split(':')[0])
        deck_name = value.split(': ')[1]

        self.current_mode = "Deck"
        self.mode_label.setText(f"Deck: {deck_name}")
        self.mode_label.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        self.show_deck_skills(deck_id)

    def _update_summary(self, total_skills, hint_count, event_count, golden_count):
        self.stats_total.setText(f"{total_skills}  Skills")
        self.stats_hints.setText(f"Hints: {hint_count}")
        self.stats_events.setText(f"Events: {event_count}")
        self.stats_golden.setText(f"✨ Golden: {golden_count}")

    def show_deck_skills(self, deck_id):
        clear_layout(self.cards_lay)
        self._block_render_gen += 1
        my_gen = self._block_render_gen

        deck_cards = get_deck_cards(deck_id)
        if not deck_cards:
            self._update_summary(0, 0, 0, 0)
            return

        card_data_list = []
        total_skills = 0
        hint_count = 0
        event_count = 0
        golden_count = 0

        for card_row in deck_cards:
            slot_pos, level, card_id, name, rarity, card_type, image_path = card_row
            card_full = get_card_by_id(card_id)
            is_owned = bool(card_full[7]) if card_full else False

            skills = []
            hints = get_hints(card_id)
            for h_name, h_desc in hints:
                skills.append({"name": h_name, "source": "Training Hint", "desc": h_desc, "golden": False})
                total_skills += 1
                hint_count += 1

            events = get_all_event_skills(card_id)
            for event in events:
                src = "Event"
                golden = False
                if event.get('is_gold', False):
                    src = "Event (Golden)"
                    golden = True
                    golden_count += 1
                else:
                    event_count += 1
                skills.append({"name": event['skill_name'], "source": src, "desc": event['details'], "golden": golden})
                total_skills += 1

            card_data_list.append((card_id, name, rarity, card_type, image_path, is_owned, skills))

        self._update_summary(total_skills, hint_count, event_count, golden_count)
        self._block_render_queue = card_data_list[:]
        QTimer.singleShot(0, lambda: self._process_block_queue(my_gen))

    def _process_block_queue(self, gen):
        if gen != self._block_render_gen or not self._block_render_queue:
            return

        card_id, name, rarity, card_type, image_path, is_owned, skills = self._block_render_queue.pop(0)
        self._render_card_block(card_id, name, rarity, card_type, image_path, is_owned, skills)

        if self._block_render_queue and gen == self._block_render_gen:
            QTimer.singleShot(25, lambda: self._process_block_queue(gen))

    def _render_card_block(self, card_id, name, rarity, card_type, image_path, is_owned, skills):
        bc = ACCENT_SUCCESS if is_owned else BG_LIGHT
        f = QFrame()
        f.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {bc}; border-radius: {RADIUS_MD}px; }}")
        self.cards_lay.addWidget(f)

        f_lay = QVBoxLayout(f)
        f_lay.setContentsMargins(0, 0, 0, 0)
        f_lay.setSpacing(0)

        # Sticky header
        hdr = QFrame()
        hdr.setStyleSheet(f"background: {BG_MEDIUM}; border-radius: {RADIUS_SM}px; border: none;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        
        img_lbl = QLabel()
        img_lbl.setFixedSize(44, 44)
        pix = self.icon_cache.get(card_id)
        if not pix:
            rp = resolve_image_path(image_path)
            if rp and os.path.exists(rp):
                try:
                    pix = QPixmap(rp).scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.icon_cache[card_id] = pix
                except: pass
        if pix:
            img_lbl.setPixmap(pix)
        hdr_lay.addWidget(img_lbl)

        info_lay = QVBoxLayout()
        info_lay.setContentsMargins(0, 0, 0, 0)
        info_lay.setSpacing(2)

        n_lbl = ClickableLabel(name, callback=lambda cid=card_id: self.navigate_to_card(cid) if self.navigate_to_card else None)
        n_lbl.setFont(FONT_SUBHEADER)
        n_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        info_lay.addWidget(n_lbl)

        owned_text = " · Owned ✓" if is_owned else ""
        meta_lbl = QLabel(f"{get_type_icon(card_type)} {card_type} · {rarity}{owned_text}")
        meta_lbl.setFont(FONT_TINY)
        meta_lbl.setStyleSheet(f"color: {get_rarity_color(rarity)}; border: none;")
        info_lay.addWidget(meta_lbl)
        hdr_lay.addLayout(info_lay, stretch=1)

        sk_cnt = QLabel(f"{len(skills)} skills")
        sk_cnt.setFont(FONT_TINY)
        sk_cnt.setStyleSheet(f"color: {TEXT_DISABLED}; background: {BG_LIGHT}; border-radius: 10px; padding: 2px 8px;")
        hdr_lay.addWidget(sk_cnt)

        f_lay.addWidget(hdr)

        if not skills:
            emp = QLabel("No notable skills found.")
            emp.setFont(FONT_SMALL)
            emp.setStyleSheet(f"color: {TEXT_MUTED}; border: none; padding: {SPACING_SM}px;")
            f_lay.addWidget(emp)
            return

        sk_cont = QWidget()
        sk_cont.setStyleSheet("background: transparent;")
        sk_lay = QVBoxLayout(sk_cont)
        sk_lay.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_SM)
        sk_lay.setSpacing(1)

        for skill in skills:
            row = CollapsibleSkillRow(skill, self.navigate_to_skill)
            sk_lay.addWidget(row)

        f_lay.addWidget(sk_cont)

    def set_card(self, card_id):
        card = get_card_by_id(card_id)
        if not card: return
        card_id, name, rarity, card_type, max_level, url, image_path, is_owned, owned_level = card

        self.current_mode = "Single"
        self.mode_label.setText(f"Card: {name}")
        self.mode_label.setStyleSheet(f"color: {ACCENT_SECONDARY}; border: none;")

        clear_layout(self.cards_lay)

        total_skills = 0
        hint_count = 0
        event_count = 0
        golden_count = 0
        skills = []

        hints = get_hints(card_id)
        for h_name, h_desc in hints:
            skills.append({"name": h_name, "source": "Training Hint", "desc": h_desc, "golden": False})
            total_skills += 1
            hint_count += 1

        events = get_all_event_skills(card_id)
        for event in events:
            src = "Event"
            golden = False
            if event.get('is_gold', False):
                src = "Event (Golden)"
                golden = True
                golden_count += 1
            else:
                event_count += 1
            skills.append({"name": event['skill_name'], "source": src, "desc": event['details'], "golden": golden})
            total_skills += 1

        self._render_card_block(card_id, name, rarity, card_type, image_path, is_owned, skills)
        self._update_summary(total_skills, hint_count, event_count, golden_count)
