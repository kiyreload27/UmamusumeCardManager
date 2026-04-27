"""
Deck Builder Frame
Build decks with 6 cards and view combined effects with breakdown
PySide6 edition with visual slot cards, drag-and-drop, export/import, and comparison
"""

import json
import sys
import os
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QComboBox, QPushButton, QCheckBox, QLineEdit,
    QMessageBox, QFileDialog, QTextEdit
)
from PySide6.QtCore import Qt, QTimer, Signal, QMimeData
from PySide6.QtGui import QPixmap, QCursor, QDrag

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import (
    get_all_cards, get_all_decks, create_deck, delete_deck,
    add_card_to_deck, remove_card_from_deck, get_deck_cards,
    get_effects_at_level, export_single_deck, import_single_deck
)
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    get_type_icon, get_rarity_color, create_styled_entry
)
from gui.deck_comparison import show_deck_comparison

def clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()
            else: clear_layout(item.layout())

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

class DraggableCardFrame(QFrame):
    clicked = Signal(int)
    doubleClicked = Signal(int)
    
    def __init__(self, card_id, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            self.clicked.emit(self.card_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit(self.card_id)
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not self.drag_start_pos:
            return
            
        if (event.pos() - self.drag_start_pos).manhattanLength() < 5:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(str(self.card_id))
        drag.setMimeData(mime)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap.scaled(100, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        p = event.pos()
        drag.setHotSpot(type(p)(p.x() // 2, p.y() // 2))
        
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        drag.exec(Qt.DropAction.CopyAction)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

class CardSlot(QFrame):
    """Visual component for a single card slot with premium styling"""
    def __init__(self, index, remove_callback, level_callback, on_drop_callback=None, parent=None):
        super().__init__(parent)
        self.index = index
        self.remove_callback = remove_callback
        self.level_callback = level_callback
        self.on_drop = on_drop_callback
        self._is_occupied = False
        
        self.setAcceptDrops(True)
        
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._toggle_pulse)
        self._pulse_state = False

        self._build_ui()

    def _toggle_pulse(self):
        if self._is_occupied: return
        self._pulse_state = not self._pulse_state
        c = BG_LIGHT if self._pulse_state else BG_DARK
        self.setStyleSheet(f"CardSlot {{ background: {BG_DARK}; border: 1px solid {c}; border-radius: {RADIUS_MD}px; }}")

    def _build_ui(self):
        self.setStyleSheet(f"CardSlot {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_MD}px; }}")
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_XS, SPACING_XS)
        lay.setSpacing(SPACING_XS)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t_lay = QHBoxLayout()
        t_lay.setContentsMargins(0, 0, 0, 0)
        self.slot_label = QLabel(f"#{self.index + 1}")
        self.slot_label.setFont(FONT_TINY)
        self.slot_label.setStyleSheet(f"color: {TEXT_MUTED}; background: {BG_LIGHT}; border-radius: {RADIUS_SM}px; padding: 0 4px;")
        t_lay.addWidget(self.slot_label)
        t_lay.addStretch()
        lay.addLayout(t_lay)

        self.image_label = QLabel("＋")
        self.image_label.setFont(FONT_HEADER)
        self.image_label.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        self.image_label.setFixedSize(60, 60)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.name_label = QLabel("Empty")
        self.name_label.setFont(FONT_TINY)
        self.name_label.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.name_label)

        self.ctrl_w = QWidget()
        self.ctrl_w.setStyleSheet("background: transparent;")
        c_lay = QHBoxLayout(self.ctrl_w)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(2)

        self.level_combo = QComboBox()
        self.level_combo.setFixedWidth(72)
        self.level_combo.setStyleSheet(
            f"QComboBox {{ color: {TEXT_PRIMARY}; background: {BG_DARK}; padding: 2px 4px; min-height: 20px; }}"
        )
        self.level_combo.currentTextChanged.connect(self._on_level_change)
        c_lay.addWidget(self.level_combo)

        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setFont(FONT_BODY_BOLD)
        self.remove_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {ACCENT_ERROR}; border: none; padding: 0; }} QPushButton:hover {{ background: {BG_HIGHLIGHT}; border-radius: {RADIUS_SM}px; }}")
        self.remove_btn.clicked.connect(lambda: self.remove_callback(self.index))
        c_lay.addWidget(self.remove_btn)

        lay.addWidget(self.ctrl_w)
        self.ctrl_w.hide()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            if not self._is_occupied:
                self.setStyleSheet(f"CardSlot {{ background: {BG_DARK}; border: 2px solid {ACCENT_PRIMARY}; border-radius: {RADIUS_MD}px; }}")

    def dragLeaveEvent(self, event):
        if not self._is_occupied:
            self.setStyleSheet(f"CardSlot {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_MD}px; }}")

    def dropEvent(self, event):
        if event.mimeData().hasText():
            card_id = int(event.mimeData().text())
            if self.on_drop:
                self.on_drop(self.index, card_id)
            event.acceptProposedAction()

    def set_card(self, card_data):
        self.pulse_timer.stop()
        if not card_data:
            self.reset()
            return

        card_id, name, rarity, card_type, image_path, level = card_data
        self._is_occupied = True

        if rarity == 'SSR':
            valid_levels = [50, 45, 40, 35, 30]
            max_lvl = 50
        elif rarity == 'SR':
            valid_levels = [45, 40, 35, 30, 25]
            max_lvl = 45
        else:
            valid_levels = [40, 35, 30, 25, 20]
            max_lvl = 40

        try: level = int(level)
        except: level = max_lvl
        if level not in valid_levels: level = max_lvl

        d_name = name if len(name) < 10 else name[:9] + "…"
        self.name_label.setText(d_name)
        self.name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")

        r_border = {'SSR': ACCENT_WARNING, 'SR': TEXT_SECONDARY, 'R': BG_HIGHLIGHT}.get(rarity, BG_LIGHT)
        self.setStyleSheet(f"CardSlot {{ background: {BG_ELEVATED}; border: 1px solid {r_border}; border-radius: {RADIUS_MD}px; }}")

        rp = resolve_image_path(image_path)
        if rp and os.path.exists(rp):
            try:
                pix = QPixmap(rp).scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(pix)
            except: self.image_label.setText("⚠️")
        else:
            self.image_label.setText("⚠️")
            self.image_label.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")

        self.level_combo.blockSignals(True)
        self.level_combo.clear()
        self.level_combo.addItems([str(l) for l in valid_levels])
        self.level_combo.setCurrentText(str(level))
        self.level_combo.blockSignals(False)
        
        self.ctrl_w.show()

    def reset(self):
        self._is_occupied = False
        self.name_label.setText("Empty")
        self.name_label.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("＋")
        self.image_label.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        self.setStyleSheet(f"CardSlot {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_MD}px; }}")
        self.ctrl_w.hide()
        self.pulse_timer.start(800)

    def _on_level_change(self, value):
        if value:
            self.level_callback(self.index, int(value))


class DeckBuilderFrame(QWidget):
    """Deck builder with combined effects breakdown, drag-and-drop, export/import, and comparison"""

    navigate_to_card = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_deck_id = None
        self.deck_slots = [None] * 6
        self.icon_cache = {}
        self.selected_av_card_id = None

        self._card_render_gen = 0
        self._card_render_queue = []
        self._all_rendered_cards = {}
        self._search_after_id = None
        self.effects_sort_desc = True

        self._build_ui()
        self.refresh_decks()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        main_lay.setSpacing(SPACING_MD)

        # ─── Top Strip ───
        deck_ctrl = QFrame()
        deck_ctrl.setStyleSheet(f".QFrame {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        dc_lay = QVBoxLayout(deck_ctrl)
        dc_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        d_row1 = QHBoxLayout()
        d_lbl = QLabel("ASSEMBLY")
        d_lbl.setFont(FONT_SUBHEADER)
        d_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        d_row1.addWidget(d_lbl)

        self.deck_combo = QComboBox()
        self.deck_combo.setFixedWidth(220)
        self.deck_combo.currentTextChanged.connect(self.on_deck_selected_val)
        d_row1.addWidget(self.deck_combo)

        ren_btn = QPushButton("✏️")
        ren_btn.setFixedSize(28, 28)
        ren_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {TEXT_MUTED}; border: none; padding: 0; }} QPushButton:hover {{ color: {ACCENT_PRIMARY}; }}")
        ren_btn.clicked.connect(self.rename_current_deck)
        d_row1.addWidget(ren_btn)

        n_btn = QPushButton("➕ New")
        n_btn.setFixedWidth(80)
        n_btn.clicked.connect(self.create_new_deck)
        d_row1.addWidget(n_btn)

        del_btn = QPushButton("🗑️")
        del_btn.setFixedSize(36, 30)
        del_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {TEXT_MUTED}; border: none; padding: 0; }} QPushButton:hover {{ color: {ACCENT_ERROR}; }}")
        del_btn.clicked.connect(self.delete_current_deck)
        d_row1.addWidget(del_btn)

        d_row1.addStretch()

        self.deck_count_label = QLabel("0 / 6")
        self.deck_count_label.setFont(FONT_BODY_BOLD)
        self.deck_count_label.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        d_row1.addWidget(self.deck_count_label)
        dc_lay.addLayout(d_row1)

        d_row2 = QHBoxLayout()
        for t, c in [("⚖️ Compare", self._show_comparison), ("📤 Export", self._export_deck), ("📥 Import", self._import_deck), ("📋 Copy", self._copy_deck)]:
            btn = QPushButton(t)
            btn.setFont(FONT_TINY)
            btn.setFixedHeight(28)
            btn.setStyleSheet(f"QPushButton {{ background: {BG_MEDIUM}; color: {TEXT_MUTED}; border: none; border-radius: {RADIUS_SM}px; padding: 0 10px; }} QPushButton:hover {{ background: {BG_HIGHLIGHT}; }}")
            btn.clicked.connect(c)
            d_row2.addWidget(btn)
        d_row2.addStretch()
        dc_lay.addLayout(d_row2)

        self.slots_frame = QFrame()
        self.slots_frame.setStyleSheet("background: transparent; border: none;")
        s_lay = QGridLayout(self.slots_frame)
        s_lay.setContentsMargins(0, 0, 0, 0)
        s_lay.setSpacing(SPACING_SM)
        
        self.card_slots = []
        for i in range(6):
            r, c = i // 3, i % 3
            slot = CardSlot(i, self.remove_from_slot, self.on_slot_level_changed, on_drop_callback=self._on_card_dropped)
            slot.name_label.callback = lambda idx=i: self._slot_name_clicked(idx)
            s_lay.addWidget(slot, r, c)
            self.card_slots.append(slot)
            s_lay.setColumnStretch(c, 1)

        dc_lay.addWidget(self.slots_frame)
        main_lay.addWidget(deck_ctrl)

        # ─── Split Area ───
        split_w = QWidget()
        split_lay = QHBoxLayout(split_w)
        split_lay.setContentsMargins(0, 0, 0, 0)
        split_lay.setSpacing(SPACING_MD)

        # Browser Left
        bp = QFrame()
        bp.setStyleSheet(f".QFrame {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        bp_lay = QVBoxLayout(bp)
        bp_lay.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)

        bp_hdr = QHBoxLayout()
        l_lbl = QLabel("Card reservoir")
        l_lbl.setFont(FONT_HEADER)
        l_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        bp_hdr.addWidget(l_lbl)
        bp_hdr.addStretch()
        r_lbl = QLabel("drag → slot")
        r_lbl.setFont(FONT_TINY)
        r_lbl.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        bp_hdr.addWidget(r_lbl)
        bp_lay.addLayout(bp_hdr)

        f_row = QHBoxLayout()
        self.search_entry = create_styled_entry(None, placeholder="Search...")
        self.search_entry.textChanged.connect(self._schedule_filter)
        f_row.addWidget(self.search_entry, stretch=1)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"])
        self.type_combo.currentTextChanged.connect(lambda _: self.filter_cards())
        f_row.addWidget(self.type_combo)
        bp_lay.addLayout(f_row)

        r_row = QHBoxLayout()
        r_l = QLabel("Rarity:")
        r_l.setFont(FONT_TINY)
        r_l.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        r_row.addWidget(r_l)
        
        self.rarity_combo = QComboBox()
        self.rarity_combo.addItems(["All", "SSR", "SR", "R"])
        self.rarity_combo.currentTextChanged.connect(lambda _: self.filter_cards())
        r_row.addWidget(self.rarity_combo)
        
        self.owned_cb = QCheckBox("Owned Only")
        self.owned_cb.setFont(FONT_TINY)
        self.owned_cb.toggled.connect(self.filter_cards)
        r_row.addWidget(self.owned_cb)
        bp_lay.addLayout(r_row)

        self.card_scroll = QScrollArea()
        self.card_scroll.setWidgetResizable(True)
        self.card_scroll.setStyleSheet("border: none; background: transparent;")
        self.card_w = QWidget()
        self.card_w.setStyleSheet("background: transparent;")
        self.card_lay = QVBoxLayout(self.card_w)
        self.card_lay.setContentsMargins(0, 0, 0, 0)
        self.card_lay.setSpacing(SPACING_XS)
        self.card_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.card_scroll.setWidget(self.card_w)
        bp_lay.addWidget(self.card_scroll, stretch=1)

        add_btn = QPushButton("➕  Add to Deck")
        add_btn.setFixedHeight(34)
        add_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT_PRIMARY}; color: {BG_DARKEST}; border-radius: {RADIUS_MD}px; font-weight: bold; }} QPushButton:hover {{ background: #5a6edb; }}")
        add_btn.clicked.connect(self.add_selected_to_deck)
        bp_lay.addWidget(add_btn)

        split_lay.addWidget(bp, stretch=1)

        # Effects Right
        rp = QFrame()
        rp.setStyleSheet(f".QFrame {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        rp_lay = QVBoxLayout(rp)
        rp_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)

        eh_row = QHBoxLayout()
        eh_l = QLabel("Telemetry stack")
        eh_l.setFont(FONT_SUBHEADER)
        eh_l.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        eh_row.addWidget(eh_l)

        self.score_badge = ClickableLabel("Score: —", callback=self._show_score_breakdown)
        self.score_badge.setFont(FONT_BODY_BOLD)
        self.score_badge.setStyleSheet(f"color: {ACCENT_WARNING}; background: {BG_MEDIUM}; border-radius: 14px; padding: 0 12px;")
        self.score_badge.setFixedHeight(28)
        eh_row.addWidget(self.score_badge)
        eh_row.addStretch()

        u_l = QLabel("✨ Unique Effects")
        u_l.setFont(FONT_SMALL)
        u_l.setStyleSheet(f"color: {ACCENT_SECONDARY}; border: none;")
        eh_row.addWidget(u_l)
        rp_lay.addLayout(eh_row)

        self.table_scroll = QScrollArea()
        self.table_scroll.setWidgetResizable(True)
        self.table_scroll.setStyleSheet(f"background: {BG_DARKEST}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_SM}px;")
        self.table_w = QWidget()
        self.table_w.setStyleSheet("background: transparent;")
        self.table_lay = QGridLayout(self.table_w)
        self.table_lay.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_XS, SPACING_XS)
        self.table_lay.setSpacing(1)
        self.table_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.table_scroll.setWidget(self.table_w)
        rp_lay.addWidget(self.table_scroll, stretch=2)

        self.unique_text = QTextEdit()
        self.unique_text.setFixedHeight(120)
        self.unique_text.setReadOnly(True)
        self.unique_text.setStyleSheet(f"background: {BG_DARKEST}; border: 1px solid {BG_LIGHT}; color: {TEXT_PRIMARY}; border-radius: {RADIUS_SM}px;")
        rp_lay.addWidget(self.unique_text, stretch=1)

        split_lay.addWidget(rp, stretch=2)
        main_lay.addWidget(split_w, stretch=1)

        QTimer.singleShot(200, self.filter_cards)

    def _schedule_filter(self):
        if self._search_after_id:
            return
        self._search_after_id = QTimer.singleShot(300, self.filter_cards)

    def filter_cards(self):
        self._search_after_id = None
        self._card_render_gen += 1
        my_gen = self._card_render_gen

        clear_layout(self.card_lay)
        self._all_rendered_cards.clear()

        tv = self.type_combo.currentText()
        rv = self.rarity_combo.currentText()
        sv = self.search_entry.text()
        ov = self.owned_cb.isChecked()

        tf = tv if tv != "All" else None
        rf = rv if rv != "All" else None
        sf = sv if sv else None

        cards = get_all_cards(rarity_filter=rf, type_filter=tf, search_term=sf, owned_only=ov)
        self._card_render_queue = list(cards)
        QTimer.singleShot(0, lambda: self._process_card_queue(my_gen))

    def _process_card_queue(self, gen):
        if gen != self._card_render_gen or not self._card_render_queue: return

        chunk = self._card_render_queue[:15]
        self._card_render_queue = self._card_render_queue[15:]

        for card in chunk:
            card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level = card
            self._all_rendered_cards[card_id] = card

            f = DraggableCardFrame(card_id)
            f.setObjectName(f"card_{card_id}")
            f.clicked.connect(self._select_av_card)
            f.doubleClicked.connect(lambda _: self.add_selected_to_deck())
            
            sel = (card_id == self.selected_av_card_id)
            bc = ACCENT_PRIMARY if sel else BG_LIGHT
            bg = BG_ELEVATED if sel else BG_DARK
            f.setStyleSheet(f".QFrame {{ background: {bg}; border: 1px solid {bc}; border-radius: {RADIUS_SM}px; }}")
            
            self.card_lay.addWidget(f)

            lay = QHBoxLayout(f)
            lay.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_XS, SPACING_XS)
            lay.setSpacing(SPACING_XS)

            img = self.icon_cache.get(card_id)
            if not img:
                rp = resolve_image_path(image_path)
                if rp and os.path.exists(rp):
                    try:
                        img = QPixmap(rp).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.icon_cache[card_id] = img
                    except: pass
            
            i_lbl = QLabel()
            i_lbl.setFixedSize(36, 36)
            if img: i_lbl.setPixmap(img)
            lay.addWidget(i_lbl)

            info = QVBoxLayout()
            info.setContentsMargins(0, 0, 0, 0)
            info.setSpacing(2)

            n_lbl = QLabel(name)
            n_lbl.setFont(FONT_BODY_BOLD)
            n_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
            info.addWidget(n_lbl)

            m_lbl = QLabel(f"{get_type_icon(card_type)} {card_type} · {rarity}")
            m_lbl.setFont(FONT_TINY)
            m_lbl.setStyleSheet(f"color: {get_rarity_color(rarity)}; border: none;")
            info.addWidget(m_lbl)
            
            lay.addLayout(info, stretch=1)

        if self._card_render_queue and gen == self._card_render_gen:
            QTimer.singleShot(10, lambda: self._process_card_queue(gen))

    def _select_av_card(self, card_id):
        self.selected_av_card_id = card_id
        for i in range(self.card_lay.count()):
            w = self.card_lay.itemAt(i).widget()
            if w:
                is_sel = (w.card_id == card_id)
                bc = ACCENT_PRIMARY if is_sel else BG_LIGHT
                bg = BG_ELEVATED if is_sel else BG_DARK
                w.setStyleSheet(f".QFrame {{ background: {bg}; border: 1px solid {bc}; border-radius: {RADIUS_SM}px; }}")

    def _on_card_dropped(self, slot_index, card_id):
        if not self.current_deck_id:
            QMessageBox.warning(self, "No Deck", "Select or create a deck first.")
            return
        if card_id in self.deck_slots:
            QMessageBox.information(self, "Duplicate", "This card is already in the deck.")
            return

        if self.deck_slots[slot_index] is not None:
            remove_card_from_deck(self.current_deck_id, slot_index)

        level = self._get_card_level(card_id)
        add_card_to_deck(self.current_deck_id, card_id, slot_index, level)
        self.load_deck()

    def _export_deck(self):
        if not self.current_deck_id: return
        dd = export_single_deck(self.current_deck_id)
        if not dd: return
        fp, _ = QFileDialog.getSaveFileName(self, "Export Deck", f"deck_{dd['name'].replace(' ', '_')}.json", "JSON files (*.json)")
        if not fp: return
        dd['_format'] = 'uma_deck_v1'
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(dd, f, indent=2, ensure_ascii=False)

    def _import_deck(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Import Deck", "", "JSON files (*.json);;All files (*.*)")
        if not fp: return
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                dd = json.load(f)
        except Exception as e: return
        
        did, m, t = import_single_deck(dd)
        self.current_deck_id = did
        self.refresh_decks()
        self.deck_combo.setCurrentText(f"{did}: {dd.get('name', 'Imported')}")
        self.load_deck()

    def _copy_deck(self):
        if not self.current_deck_id: return
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication
        cb = QApplication.clipboard()
        text = [f"Deck: {self.deck_combo.currentText().split(': ', 1)[-1]}"]
        for i in range(6):
            if self.deck_slots[i]:
                name = self.card_slots[i].name_label.text()
                lvl = self.card_slots[i].level_combo.currentText()
                text.append(f"#{i+1}: {name} (Lv{lvl})")
        cb.setText("\n".join(text))
        QMessageBox.information(self, "Copied", "Deck text copied to clipboard!")

    def _show_comparison(self):
        show_deck_comparison(self.window(), current_deck_id=self.current_deck_id)

    def refresh_decks(self):
        decks = get_all_decks()
        vals = [f"{d[0]}: {d[1]}" for d in decks]
        self.deck_combo.blockSignals(True)
        self.deck_combo.clear()
        self.deck_combo.addItems(vals)
        self.deck_combo.blockSignals(False)
        if vals and not self.current_deck_id:
            self.deck_combo.setCurrentText(vals[0])
            self.on_deck_selected_val(vals[0])
        elif not vals:
            self.deck_combo.setCurrentText("")

    def on_deck_selected_val(self, value):
        if value:
            self.current_deck_id = int(value.split(':')[0])
            self.load_deck()

    def load_deck(self):
        if not self.current_deck_id: return
        for s in self.card_slots: s.reset()
        self.deck_slots = [None] * 6

        dc = get_deck_cards(self.current_deck_id)
        for c in dc:
            sp, lvl, cid, n, r, ct, ip = c
            if 0 <= sp < 6:
                cl = min(lvl, self._rarity_max_level(r))
                if cl != lvl:
                    add_card_to_deck(self.current_deck_id, cid, sp, cl)
                    lvl = cl
                self.deck_slots[sp] = cid
                self.card_slots[sp].set_card((cid, n, r, ct, ip, lvl))

        self.update_deck_count()
        self.update_effects_breakdown()

    def create_new_deck(self):
        from PySide6.QtWidgets import QInputDialog
        n, ok = QInputDialog.getText(self, "New Deck", "Enter deck name:")
        if ok and n:
            did = create_deck(n)
            self.current_deck_id = did
            self.refresh_decks()
            self.deck_combo.setCurrentText(f"{did}: {n}")
            self.load_deck()

    def rename_current_deck(self):
        if not self.current_deck_id: return
        from PySide6.QtWidgets import QInputDialog
        from db.db_queries import rename_deck
        current_name = self.deck_combo.currentText().split(': ', 1)[-1]
        n, ok = QInputDialog.getText(self, "Rename Deck", "Enter new deck name:", text=current_name)
        if ok and n:
            rename_deck(self.current_deck_id, n)
            self.refresh_decks()
            self.deck_combo.setCurrentText(f"{self.current_deck_id}: {n}")

    def delete_current_deck(self):
        if self.current_deck_id:
            r = QMessageBox.question(self, "Delete Deck", "Are you sure you want to delete this deck?")
            if r == QMessageBox.StandardButton.Yes:
                delete_deck(self.current_deck_id)
                self.current_deck_id = None
                self.deck_combo.setCurrentText("")
                self.refresh_decks()
                for s in self.card_slots: s.reset()
                self.deck_slots = [None] * 6
                self.update_deck_count()
                self.update_effects_breakdown()

    @staticmethod
    def _rarity_max_level(rarity):
        if rarity == 'SSR': return 50
        elif rarity == 'SR': return 45
        return 40

    def _get_card_level(self, card_id_or_data):
        if isinstance(card_id_or_data, int): cd = self._all_rendered_cards.get(card_id_or_data)
        else:
            cd = card_id_or_data
            if cd: self._all_rendered_cards[cd[0]] = cd

        if cd:
            r = cd[2]
            ml = self._rarity_max_level(r)
            ol = cd[7]
            if ol: return min(int(ol), ml)
            return ml
        return 50

    def add_selected_to_deck(self):
        if not self.current_deck_id: return
        if not self.selected_av_card_id: return
        cid = self.selected_av_card_id
        if cid in self.deck_slots: return

        lvl = self._get_card_level(cid)
        for i in range(6):
            if self.deck_slots[i] is None:
                add_card_to_deck(self.current_deck_id, cid, i, lvl)
                self.load_deck()
                return

    def remove_from_slot(self, index):
        if self.current_deck_id and self.deck_slots[index]:
            remove_card_from_deck(self.current_deck_id, index)
            self.deck_slots[index] = None
            self.card_slots[index].reset()
            self.update_deck_count()
            self.update_effects_breakdown()

    def _slot_name_clicked(self, index):
        if self.deck_slots[index]:
            self.navigate_to_card.emit(self.deck_slots[index])

    def update_deck_count(self):
        c = sum(1 for s in self.deck_slots if s is not None)
        self.deck_count_label.setText(f"{c} / 6")

    def on_slot_level_changed(self, index, new_level):
        if self.current_deck_id and self.deck_slots[index]:
            cid = self.deck_slots[index]
            add_card_to_deck(self.current_deck_id, cid, index, new_level)
            self.update_effects_breakdown()

    def update_effects_breakdown(self):
        clear_layout(self.table_lay)
        self.unique_text.clear()

        if not self.current_deck_id:
            self.unique_text.setText("No deck selected")
            return

        ci = []
        for i in range(6):
            if self.deck_slots[i]:
                l = int(self.card_slots[i].level_combo.currentText())
                ci.append((self.deck_slots[i], l))
            else: ci.append(None)

        ae = {}
        ue = []

        for i, inf in enumerate(ci):
            if inf:
                cid, lvl = inf
                cn = self.card_slots[i].name_label.text()
                r = next((row[2] for row in self._all_rendered_cards.values() if row[0] == cid), None)
                if r: lvl = min(lvl, self._rarity_max_level(r))
                
                eff = get_effects_at_level(cid, lvl)
                for n, v in eff:
                    if n == "Unique Effect":
                        ue.append(f"• {cn}:\n  {v}\n")
                        continue
                    if n not in ae: ae[n] = ['-'] * 6
                    ae[n][i] = v

        if ue: self.unique_text.setText("\n".join(ue))
        else: self.unique_text.setText("\nNo unique effects in this deck.")

        hdrs = ["Effect", "Total"] + [f"#{i+1}" for i in range(6)]
        
        def toggle_sort():
            self.effects_sort_desc = not self.effects_sort_desc
            self.update_effects_breakdown()

        for c, t in enumerate(hdrs):
            if t == "Total":
                l = ClickableLabel(t + (" ▼" if self.effects_sort_desc else " ▲"), callback=toggle_sort)
            else:
                l = QLabel(t)
            l.setFont(FONT_BODY_BOLD)
            l.setStyleSheet(f"color: {TEXT_PRIMARY}; background: {BG_MEDIUM}; padding: {SPACING_XS}px; border-radius: {RADIUS_SM}px;")
            self.table_lay.addWidget(l, 0, c)

        # Collect rows
        rows = []
        for en, vs in ae.items():
            tot = 0
            ip = False
            for v in vs:
                if v and str(v).strip() != '-':
                    if '%' in str(v): ip = True
                    try: tot += float(str(v).replace('%', '').replace('+', ''))
                    except: pass
            rows.append((en, vs, tot, ip))
            
        # Sort
        if not hasattr(self, 'effects_sort_desc'): self.effects_sort_desc = True
        rows.sort(key=lambda x: x[2], reverse=self.effects_sort_desc)

        ri = 1
        for en, vs, tot, ip in rows:
            ts = f"{tot:.0f}%" if ip else (f"+{tot:.0f}" if tot > 0 else str(int(tot)))

            l_en = QLabel(en)
            l_en.setFont(FONT_BODY)
            l_en.setStyleSheet(f"color: {TEXT_SECONDARY}; border: none;")
            l_en.setToolTip("Effect: " + en)
            self.table_lay.addWidget(l_en, ri, 0)

            l_ts = QLabel(ts)
            l_ts.setFont(FONT_BODY_BOLD)
            l_ts.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
            self.table_lay.addWidget(l_ts, ri, 1)

            for i, v in enumerate(vs):
                l_v = QLabel(str(v))
                l_v.setFont(FONT_TINY)
                l_v.setStyleSheet(f"color: {TEXT_DISABLED if v == '-' else TEXT_PRIMARY}; border: none;")
                self.table_lay.addWidget(l_v, ri, 2+i)
            
            ri += 1

        def pn(v):
            try: return float(str(v).replace('%', '').replace('+', ''))
            except: return 0.0
        def gt(ek):
            for n, vs in ae.items():
                if ek.lower() in n.lower(): return sum(pn(v) for v in vs if v and v != '-')
            return 0.0

        fr = gt('Friendship')
        tr = gt('Training')
        hr = gt('Hint Rate')
        rb = gt('Race Bonus')
        sc = int(fr * 2 + tr + hr + rb)
        self.last_score_breakdown = (fr, tr, hr, rb, sc)

        if sc > 0:
            c = ACCENT_SUCCESS if sc >= 300 else (ACCENT_WARNING if sc >= 150 else TEXT_MUTED)
            self.score_badge.setText(f"Score: {sc}")
            self.score_badge.setStyleSheet(f"color: {c}; background: {BG_DARK}; border: 1px solid {c}; border-radius: 14px; padding: 0 12px;")
            self.score_badge.mousePressEvent = lambda e: self._show_score_breakdown()
        else:
            self.score_badge.setText("Score: —")
            self.score_badge.setStyleSheet(f"color: {TEXT_MUTED}; background: {BG_MEDIUM}; border-radius: 14px; padding: 0 12px;")
            self.score_badge.mousePressEvent = None

    def _show_score_breakdown(self):
        if not hasattr(self, 'last_score_breakdown') or self.last_score_breakdown[4] == 0: return
        fr, tr, hr, rb, sc = self.last_score_breakdown
        msg = f"Friendship ×2: {fr*2}\nTraining: {tr}\nHint Rate: {hr}\nRace Bonus: {rb}\n\nTotal Score: {sc}"
        QMessageBox.information(self, "Score Breakdown", msg)
