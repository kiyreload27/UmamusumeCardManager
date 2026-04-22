"""
Card List View - Browse and search support cards with ownership management
PySide6 edition with grid layout, inline detail panel, filters, bulk ownership toggle.
"""

import os
import sys
import logging
from collections import OrderedDict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QLineEdit, QComboBox, QCheckBox, QPushButton,
    QPlainTextEdit, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QEvent, QObject
from PySide6.QtGui import QPixmap, QIcon, QShortcut, QKeySequence, QFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import (
    get_all_cards, get_card_by_id, get_effects_at_level,
    set_card_owned, update_owned_card_level,
    set_cards_owned_bulk, get_card_notes, set_card_notes,
    get_all_tags, get_all_effect_names
)
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY, FONT_MONO, FONT_FAMILY,
    RARITY_COLORS, TYPE_COLORS, TYPE_ICONS,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_button, create_styled_entry,
    get_rarity_color, get_type_color, get_type_icon
)


_recent_cards = []
MAX_RECENT = 10
_ICON_CACHE_MAX = 400
_FILTER_DEBOUNCE_MS = 260
_POPULATE_CHUNK = 12


def clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                clear_layout(item.layout())


class SearchEventFilter(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.view = parent

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Down:
                self.view._handle_arrow_key('down')
                return True
            elif key == Qt.Key.Key_Up:
                self.view._handle_arrow_key('up')
                return True
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                self.view._handle_enter()
                return True
        return False


class ClickableFrame(QFrame):
    def __init__(self, card_id, parent_view, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.parent_view = parent_view

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.parent_view.bulk_mode:
                self.parent_view.on_select(self.card_id)
        super().mousePressEvent(event)


class CardListFrame(QWidget):
    """Frame containing card list with search/filter, ownership, and details panel"""

    def __init__(self, parent=None, on_card_selected_callback=None, on_stats_updated_callback=None,
                 navigate_to_card_callback=None):
        super().__init__(parent)
        self.on_card_selected = on_card_selected_callback
        self.on_stats_updated = on_stats_updated_callback
        self.navigate_to_card_callback = navigate_to_card_callback

        self.cards = []
        self.filtered_cards = []
        self.current_card_id = None
        self.selected_level = 50
        self.icon_cache = OrderedDict()
        self._tree_gen = 0
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self._run_debounced_filter)
        self._queue_cards = []

        self.current_page = 0
        self.items_per_page = 40
        self.selected_index = -1

        self.bulk_mode = False
        self.bulk_selected_ids = set()
        self.card_checkboxes = {}
        self.card_widgets = []

        self.details_visible = True

        self._build_ui()
        self.load_cards()
        self._bind_keyboard()

    def _bind_keyboard(self):
        QShortcut(QKeySequence("Ctrl+F"), self, self.search_entry.setFocus)
        QShortcut(QKeySequence("Esc"), self, self._handle_escape)

    def _on_search_changed(self, text):
        self._filter_timer.start(_FILTER_DEBOUNCE_MS)

    def _run_debounced_filter(self):
        self.filter_cards()

    def _handle_escape(self):
        if self.bulk_mode:
            self._toggle_bulk_mode()
            return
        if self.search_entry.text():
            self.search_entry.clear()
            return
        self.reset_filters()

    def _handle_arrow_key(self, direction):
        if not self.filtered_cards:
            return
        page_size = self.items_per_page
        page_cards_count = min(page_size, len(self.filtered_cards) - self.current_page * page_size)

        if direction == 'down':
            self.selected_index += 3  # 3 columns in Qt grid vs 2 in Tkinter grid
            if self.selected_index >= page_cards_count:
                max_page = max(0, (len(self.filtered_cards) - 1) // self.items_per_page)
                if self.current_page < max_page:
                    self.current_page += 1
                    self.selected_index = 0
                    self.populate_tree()
                else:
                    self.selected_index = page_cards_count - 1
                return
        elif direction == 'up':
            self.selected_index -= 3
            if self.selected_index < 0:
                if self.current_page > 0:
                    self.current_page -= 1
                    new_count = min(page_size, len(self.filtered_cards) - self.current_page * page_size)
                    self.selected_index = new_count - 1
                    self.populate_tree()
                else:
                    self.selected_index = 0
                return

        self._highlight_selected()

    def _highlight_selected(self):
        for i, widget in enumerate(self.card_widgets):
            if i == self.selected_index:
                widget.setStyleSheet(
                    f".QFrame {{ background-color: {BG_DARK}; border: 2px solid {ACCENT_PRIMARY}; border-radius: {RADIUS_MD}px; }}"
                )
            else:
                card_idx = self.current_page * self.items_per_page + i
                if card_idx < len(self.filtered_cards):
                    is_owned = self.filtered_cards[card_idx][6]
                    bc = ACCENT_SUCCESS if is_owned else BG_LIGHT
                    bg = BG_ELEVATED if is_owned else BG_DARK
                    widget.setStyleSheet(
                        f".QFrame {{ background-color: {bg}; border: 1px solid {bc}; border-radius: {RADIUS_MD}px; }}"
                    )

    def _handle_enter(self):
        if 0 <= self.selected_index < len(self.card_widgets):
            card_idx = self.current_page * self.items_per_page + self.selected_index
            if card_idx < len(self.filtered_cards):
                card_id = self.filtered_cards[card_idx][0]
                self.on_select(card_id)

    # ─── UI BUILDING ─────────────────────────────────────────────────────────

    def _build_ui(self):
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        main_lay.setSpacing(SPACING_MD)

        # Left Dock
        self.dock_frame = QFrame()
        self.dock_frame.setFixedWidth(240)
        self.dock_frame.setStyleSheet(
            f".QFrame {{ background-color: {BG_ELEVATED}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}"
        )
        dock_lay = QVBoxLayout(self.dock_frame)
        dock_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        t = QLabel("CATALOGUE")
        t.setFont(FONT_SUBHEADER)
        t.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        dock_lay.addWidget(t)

        st = QLabel("Vector filters")
        st.setFont(FONT_TINY)
        st.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        dock_lay.addWidget(st)

        self.search_entry = create_styled_entry(self.dock_frame, placeholder="Search cards…")
        self.search_entry.textChanged.connect(self._on_search_changed)
        self.search_filter = SearchEventFilter(self)
        self.search_entry.installEventFilter(self.search_filter)
        dock_lay.addWidget(self.search_entry)

        self._build_filters(dock_lay)
        dock_lay.addStretch()

        main_lay.addWidget(self.dock_frame)

        # Center area
        self.center_frame = QWidget()
        center_lay = QVBoxLayout(self.center_frame)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(SPACING_SM)

        # Header with count + detail toggle
        self.list_header = QFrame()
        self.list_header.setStyleSheet(
            f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_MD}px; }}"
        )
        lh_lay = QHBoxLayout(self.list_header)
        lh_lay.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        self.count_label = QLabel("0 cards")
        self.count_label.setFont(FONT_TINY)
        self.count_label.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        lh_lay.addWidget(self.count_label)
        lh_lay.addStretch()
        self.detail_toggle_btn = create_styled_button(None, text="◀", width=32, height=32,
                                                      command=self._toggle_detail_panel, style_type="ghost")
        lh_lay.addWidget(self.detail_toggle_btn)
        center_lay.addWidget(self.list_header)

        # Recent strip
        self.recent_frame = QFrame()
        self.recent_frame.setStyleSheet("background: transparent;")
        self.recent_lay = QHBoxLayout(self.recent_frame)
        self.recent_lay.setContentsMargins(SPACING_MD, 0, SPACING_MD, 0)
        self.recent_lay.setSpacing(SPACING_XS)
        center_lay.addWidget(self.recent_frame)

        # Bulk action bar
        self.bulk_action_frame = QFrame()
        self.bulk_action_frame.setStyleSheet(f"background-color: {BG_DARK}; border-radius: {RADIUS_SM}px;")
        ba_lay = QHBoxLayout(self.bulk_action_frame)
        ba_lay.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        self.bulk_count_label = QLabel("0 selected")
        self.bulk_count_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        ba_lay.addWidget(self.bulk_count_label)
        ba_lay.addWidget(create_styled_button(None, text="All", width=40, height=26,
                                              command=self._select_all, style_type="ghost"))
        ba_lay.addWidget(create_styled_button(None, text="None", width=40, height=26,
                                              command=self._deselect_all, style_type="ghost"))
        ba_lay.addStretch()
        ba_lay.addWidget(create_styled_button(None, text="✓ Mark Owned", width=90, height=26,
                                              command=lambda: self._bulk_set_owned(True), style_type="accent"))
        ba_lay.addWidget(create_styled_button(None, text="✗ Unown", width=70, height=26,
                                              command=lambda: self._bulk_set_owned(False), style_type="danger"))
        self.bulk_action_frame.hide()
        center_lay.addWidget(self.bulk_action_frame)

        # Pagination
        self.pagination_frame = QFrame()
        self.pagination_frame.setStyleSheet("background: transparent;")
        pg_lay = QHBoxLayout(self.pagination_frame)
        pg_lay.setContentsMargins(SPACING_MD, 0, SPACING_MD, 0)
        self.btn_prev = create_styled_button(None, text="◀", width=36, height=28,
                                             command=self.prev_page, style_type="ghost")
        pg_lay.addWidget(self.btn_prev)
        self.page_label = QLabel("Page 1 / 1")
        self.page_label.setFont(FONT_TINY)
        self.page_label.setStyleSheet(f"color: {TEXT_MUTED};")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pg_lay.addWidget(self.page_label, stretch=1)
        self.btn_next = create_styled_button(None, text="▶", width=36, height=28,
                                             command=self.next_page, style_type="ghost")
        pg_lay.addWidget(self.btn_next)
        center_lay.addWidget(self.pagination_frame)

        # Scroll grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"background: {BG_DARK}; border-radius: {RADIUS_LG}px;")
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        self.grid_layout.setSpacing(SPACING_SM)
        self.scroll_area.setWidget(self.grid_container)
        center_lay.addWidget(self.scroll_area, stretch=1)

        main_lay.addWidget(self.center_frame, stretch=3)

        # Details Panel
        self.details_frame = QFrame()
        self.details_frame.setMinimumWidth(300)
        self.details_frame.setStyleSheet(
            f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}"
        )
        self._build_details(self.details_frame)
        main_lay.addWidget(self.details_frame, stretch=2)

    def _build_filters(self, layout):
        r_lbl = QLabel("Rarity")
        r_lbl.setFont(FONT_TINY)
        r_lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        layout.addWidget(r_lbl)
        self._rarity_var = "All"
        self._rarity_btns = {}
        for rarity in ["All", "SSR", "SR", "R"]:
            btn = QPushButton(rarity)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, r=rarity: self._set_rarity(r))
            layout.addWidget(btn)
            self._rarity_btns[rarity] = btn
        self._sync_rarity_dock()

        layout.addWidget(QLabel("Type"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"])
        self.type_combo.currentTextChanged.connect(lambda _: self.filter_cards())
        layout.addWidget(self.type_combo)

        layout.addWidget(QLabel("Effect"))
        self.effect_combo = QComboBox()
        self.effect_combo.addItem("All Effects")
        self.effect_combo.currentTextChanged.connect(lambda _: self.filter_cards())
        layout.addWidget(self.effect_combo)

        layout.addWidget(QLabel("Tag"))
        self.tag_combo = QComboBox()
        self.tag_combo.addItem("All Tags")
        self.tag_combo.currentTextChanged.connect(lambda _: self.filter_cards())
        layout.addWidget(self.tag_combo)

        self._refresh_filter_dropdowns()

        self.owned_only_cb = QCheckBox("Owned only")
        self.owned_only_cb.toggled.connect(lambda _: self.filter_cards())
        layout.addWidget(self.owned_only_cb)

        self.bulk_toggle_btn = create_styled_button(None, text="☐ Batch select",
                                                    command=self._toggle_bulk_mode, style_type="ghost")
        layout.addWidget(self.bulk_toggle_btn)

        rst_btn = create_styled_button(None, text="Reset filters", command=self.reset_filters, style_type="ghost")
        layout.addWidget(rst_btn)

        # Style labels uniformly
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if isinstance(w, QLabel) and w.text() in ("Type", "Effect", "Tag"):
                w.setFont(FONT_TINY)
                w.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")

    def _build_details(self, frame):
        outer_lay = QVBoxLayout(frame)
        outer_lay.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        lay.setSpacing(SPACING_SM)

        # Image
        img_wrap = QFrame()
        img_wrap.setStyleSheet(f"background: {BG_MEDIUM}; border-radius: {RADIUS_MD}px;")
        img_lay = QVBoxLayout(img_wrap)
        img_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label = QLabel()
        self.image_label.setFixedSize(120, 120)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_lay.addWidget(self.image_label)
        lay.addWidget(img_wrap)

        # Name & Info
        self.detail_name = QLabel("Select a card")
        self.detail_name.setFont(FONT_HEADER)
        self.detail_name.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self.detail_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_name.setWordWrap(True)
        lay.addWidget(self.detail_name)

        self.detail_info = QLabel("")
        self.detail_info.setFont(FONT_SMALL)
        self.detail_info.setStyleSheet(f"color: {TEXT_MUTED};")
        self.detail_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.detail_info)

        # Owned Checkbox
        self.owned_cb = QCheckBox("I Own This Card")
        self.owned_cb.setFont(FONT_BODY_BOLD)
        self.owned_cb.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self.owned_cb.toggled.connect(self.toggle_owned)
        lay.addWidget(self.owned_cb, alignment=Qt.AlignmentFlag.AlignCenter)

        # Level Selector
        lvl_hdr = QLabel("Card Level")
        lvl_hdr.setFont(FONT_TINY)
        lvl_hdr.setStyleSheet(f"color: {TEXT_MUTED};")
        lay.addWidget(lvl_hdr)

        self.level_btn_frame = QFrame()
        self.level_btn_lay = QHBoxLayout(self.level_btn_frame)
        self.level_btn_lay.setContentsMargins(0, 0, 0, 0)
        self.level_btn_lay.setSpacing(1)
        lay.addWidget(self.level_btn_frame)

        # Effects
        eff_hdr = QLabel("📊  Effects")
        eff_hdr.setFont(FONT_BODY_BOLD)
        eff_hdr.setStyleSheet(f"color: {ACCENT_PRIMARY};")
        lay.addWidget(eff_hdr)

        eff_scroll = QScrollArea()
        eff_scroll.setFixedHeight(220)
        eff_scroll.setWidgetResizable(True)
        eff_scroll.setStyleSheet(f"background: {BG_MEDIUM}; border-radius: {RADIUS_MD}px;")
        self.effects_container = QWidget()
        self.effects_container.setStyleSheet("background: transparent;")
        self.effects_lay = QVBoxLayout(self.effects_container)
        self.effects_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        self.effects_lay.setSpacing(2)
        self.effects_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        eff_scroll.setWidget(self.effects_container)
        lay.addWidget(eff_scroll)

        # Notes & Tags
        nt_hdr_row = QHBoxLayout()
        nt_lbl = QLabel("📝  Notes & Tags")
        nt_lbl.setFont(FONT_BODY_BOLD)
        nt_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY};")
        nt_hdr_row.addWidget(nt_lbl)
        nt_hdr_row.addStretch()
        nt_hdr_row.addWidget(create_styled_button(None, text="Save", width=50, height=24,
                                                  command=self._save_notes, style_type="success"))
        lay.addLayout(nt_hdr_row)

        tag_row = QHBoxLayout()
        tag_lbl = QLabel("Tags:")
        tag_lbl.setFont(FONT_TINY)
        tag_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        tag_row.addWidget(tag_lbl)
        self.tags_entry = create_styled_entry(None, placeholder="e.g. speed,stamina,top-tier")
        tag_row.addWidget(self.tags_entry, stretch=1)
        lay.addLayout(tag_row)

        self.tag_chips_frame = QFrame()
        self.tag_chips_lay = QHBoxLayout(self.tag_chips_frame)
        self.tag_chips_lay.setContentsMargins(0, 0, 0, 0)
        self.tag_chips_lay.setSpacing(SPACING_XS)
        self.tag_chips_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self.tag_chips_frame)

        self.note_text = QPlainTextEdit()
        self.note_text.setFixedHeight(60)
        self.note_text.setFont(FONT_SMALL)
        self.note_text.setStyleSheet(f"background: {BG_MEDIUM}; color: {TEXT_PRIMARY}; border-radius: {RADIUS_SM}px; padding: 4px;")
        lay.addWidget(self.note_text)

        scroll.setWidget(body)
        outer_lay.addWidget(scroll)

    # ─── DATA LOADING & FILTERING ─────────────────────────────────────────────

    def load_cards(self):
        self.cards = get_all_cards()
        self.filtered_cards = self.cards
        self.current_page = 0
        self.populate_tree()

    def reset_filters(self):
        self.search_entry.clear()
        self._rarity_var = "All"
        self.type_combo.setCurrentText("All")
        self.effect_combo.setCurrentText("All Effects")
        self.tag_combo.setCurrentText("All Tags")
        self.owned_only_cb.setChecked(False)
        self._sync_rarity_dock()
        self.filter_cards()

    def filter_cards(self):
        r = self._rarity_var if self._rarity_var != "All" else None
        t = self.type_combo.currentText() if self.type_combo.currentText() != "All" else None
        s = self.search_entry.text().strip() or None
        o = self.owned_only_cb.isChecked()
        e = self.effect_combo.currentText() if self.effect_combo.currentText() != "All Effects" else None
        tag = self.tag_combo.currentText() if self.tag_combo.currentText() != "All Tags" else None

        self.cards = get_all_cards(rarity_filter=r, type_filter=t, search_term=s, owned_only=o, effect_filter=e, tag_filter=tag)
        self.filtered_cards = self.cards
        self.current_page = 0
        self.selected_index = -1
        self.populate_tree()
        self.count_label.setText(f"{len(self.cards)} cards")

    def _sync_rarity_dock(self):
        for r, btn in self._rarity_btns.items():
            color = RARITY_COLORS.get(r, TEXT_MUTED) if r != "All" else TEXT_MUTED
            if r == self._rarity_var:
                btn.setStyleSheet(f"background-color: {ACCENT_PRIMARY}; color: {TEXT_PRIMARY}; border: none; border-radius: {RADIUS_SM}px;")
            else:
                btn.setStyleSheet(f"background-color: {BG_MEDIUM}; color: {color}; border: none; border-radius: {RADIUS_SM}px;")

    def _set_rarity(self, rarity):
        self._rarity_var = rarity
        self._sync_rarity_dock()
        self.filter_cards()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_index = -1
            self.populate_tree()

    def next_page(self):
        max_page = max(0, (len(self.filtered_cards) - 1) // self.items_per_page)
        if self.current_page < max_page:
            self.current_page += 1
            self.selected_index = -1
            self.populate_tree()

    def _get_list_icon(self, card_id, image_path):
        img = self.icon_cache.get(card_id)
        if img:
            self.icon_cache.move_to_end(card_id)
            return img
        rp = resolve_image_path(image_path)
        if rp and os.path.exists(rp):
            try:
                pix = QPixmap(rp).scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.icon_cache[card_id] = pix
                self.icon_cache.move_to_end(card_id)
                while len(self.icon_cache) > _ICON_CACHE_MAX:
                    self.icon_cache.popitem(last=False)
                return pix
            except Exception:
                pass
        return None

    def populate_tree(self):
        self._tree_gen += 1
        gen = self._tree_gen

        clear_layout(self.grid_layout)
        self.card_widgets.clear()
        self.card_checkboxes.clear()

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_cards = self.filtered_cards[start_idx:end_idx]

        max_page = max(1, (len(self.filtered_cards) + self.items_per_page - 1) // self.items_per_page)
        self.page_label.setText(f"{self.current_page + 1} / {max_page}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < max_page - 1)

        if not self.filtered_cards:
            lbl = QLabel("📭 No card data matching criteria")
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
            return

        self._queue_cards = list(page_cards)
        QTimer.singleShot(0, lambda: self._process_chunk(gen, 0, 0))

    def _process_chunk(self, gen, row, col):
        if gen != self._tree_gen or not self._queue_cards:
            return
        
        for _ in range(_POPULATE_CHUNK):
            if not self._queue_cards:
                break
            card = self._queue_cards.pop(0)
            self._add_card_widget(card, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
                
        if self._queue_cards:
            QTimer.singleShot(10, lambda: self._process_chunk(gen, row, col))

    def _add_card_widget(self, card, row, col):
        card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level = card

        disp = f"{name} (Lv{owned_level})" if is_owned and owned_level else name
        bc = ACCENT_SUCCESS if is_owned else BG_LIGHT
        bg = BG_ELEVATED if is_owned else BG_DARK

        f = ClickableFrame(card_id, self)
        f.setStyleSheet(f".QFrame {{ background-color: {bg}; border: 1px solid {bc}; border-radius: {RADIUS_MD}px; }}")
        f.setCursor(Qt.CursorShape.PointingHandCursor)
        self.card_widgets.append(f)
        self.grid_layout.addWidget(f, row, col)

        l = QHBoxLayout(f)
        l.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_XS, SPACING_XS)
        l.setSpacing(SPACING_SM)

        if self.bulk_mode:
            cb = QCheckBox()
            cb.setChecked(card_id in self.bulk_selected_ids)
            cb.toggled.connect(lambda _, cid=card_id: self._on_bulk_checkbox(cid))
            self.card_checkboxes[card_id] = cb
            l.addWidget(cb)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(44, 44)
        pix = self._get_list_icon(card_id, image_path)
        if pix:
            icon_lbl.setPixmap(pix)
        l.addWidget(icon_lbl)

        info_l = QVBoxLayout()
        info_l.setSpacing(2)
        n_lbl = QLabel(disp)
        n_lbl.setFont(FONT_SMALL)
        n_lbl.setStyleSheet("border: none;")
        n_lbl.setWordWrap(True)
        info_l.addWidget(n_lbl)

        meta_l = QHBoxLayout()
        meta_l.setSpacing(SPACING_XS)
        r_lbl = QLabel(rarity)
        r_lbl.setFont(FONT_TINY)
        r_lbl.setStyleSheet(f"color: {get_rarity_color(rarity)}; background: {BG_MEDIUM}; border-radius: 4px; padding: 2px 4px;")
        meta_l.addWidget(r_lbl)

        t_lbl = QLabel(f"{get_type_icon(card_type)} {card_type}")
        t_lbl.setFont(FONT_TINY)
        t_lbl.setStyleSheet(f"color: {get_type_color(card_type)}; border: none;")
        meta_l.addWidget(t_lbl)
        
        if is_owned:
            o_lbl = QLabel("✓")
            o_lbl.setFont(FONT_TINY)
            o_lbl.setStyleSheet(f"color: {ACCENT_SUCCESS}; border: none;")
            meta_l.addWidget(o_lbl)

        meta_l.addStretch()
        info_l.addLayout(meta_l)
        l.addLayout(info_l, stretch=1)

    # ─── SELECTION & DETAILS ──────────────────────────────────────────────────

    def on_select(self, card_id):
        if not card_id:
            return
        card = get_card_by_id(card_id)
        if not card:
            return

        card_id, name, rarity, card_type, max_level, url, image_path, is_owned, owned_level = card

        self.owned_cb.blockSignals(True)
        self.owned_cb.setChecked(bool(is_owned))
        self.owned_cb.blockSignals(False)

        rp = resolve_image_path(image_path)
        if rp and os.path.exists(rp):
            self.image_label.setPixmap(QPixmap(rp).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.image_label.setText("")
        else:
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("[No Image]")

        init_lvl = owned_level if is_owned and owned_level else max_level
        self.max_level = max_level
        self.update_level_buttons(rarity, max_level)
        if init_lvl not in getattr(self, 'valid_levels', []):
            init_lvl = max_level
        
        self.selected_level = init_lvl
        self._highlight_level_btn(init_lvl)

        self.detail_name.setText(f"{get_type_icon(card_type)}  {name}")
        self.detail_info.setText(f"{rarity}  ·  {card_type}  ·  Max Lv {max_level}")

        self.current_card_id = card_id
        self.update_effects_display()
        self._load_notes(card_id)
        self._add_to_recent(card_id)

        if self.on_card_selected:
            self.on_card_selected(card_id, name, self.selected_level)

    def update_level_buttons(self, rarity, max_level):
        if max_level == 50:
            self.valid_levels = [30, 35, 40, 45, 50]
        elif max_level == 45:
            self.valid_levels = [25, 30, 35, 40, 45]
        else:
            self.valid_levels = [20, 25, 30, 35, 40]

        clear_layout(self.level_btn_lay)
        self.level_buttons = {}

        for lvl in self.valid_levels:
            btn = QPushButton(f"Lv{lvl}")
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, l=lvl: self.set_level(l))
            self.level_btn_lay.addWidget(btn)
            self.level_buttons[lvl] = btn

    def _highlight_level_btn(self, level):
        for lvl, btn in self.level_buttons.items():
            if lvl == level:
                btn.setStyleSheet(f"background-color: {ACCENT_PRIMARY}; color: {TEXT_PRIMARY}; border: none; border-radius: {RADIUS_SM}px;")
            else:
                btn.setStyleSheet(f"background-color: {BG_MEDIUM}; color: {TEXT_MUTED}; border: none; border-radius: {RADIUS_SM}px;")

    def set_level(self, level):
        if not self.current_card_id: return
        self.selected_level = level
        self._highlight_level_btn(level)
        self.update_effects_display()
        if self.on_card_selected:
            card = get_card_by_id(self.current_card_id)
            if card: self.on_card_selected(self.current_card_id, card[1], level)
        if self.owned_cb.isChecked():
            update_owned_card_level(self.current_card_id, level)

    def toggle_owned(self):
        if self.current_card_id:
            set_card_owned(self.current_card_id, self.owned_cb.isChecked(), self.selected_level)
            self.filter_cards()
            if self.on_stats_updated:
                self.on_stats_updated()

    def update_effects_display(self):
        clear_layout(self.effects_lay)
        if not self.current_card_id: return

        effs = get_effects_at_level(self.current_card_id, self.selected_level)
        if not effs:
            l = QLabel(f"No effects data for Level {self.selected_level}")
            l.setStyleSheet(f"color: {TEXT_MUTED};")
            self.effects_lay.addWidget(l)
            return

        for en, ev in effs:
            v_str = str(ev)
            is_uniq = 'Unique' in en or 'unique' in en
            is_star = False
            col = ACCENT_PRIMARY

            if '%' in v_str:
                try:
                    num = int(v_str.replace('%', '').replace('+', ''))
                    if num >= 20:
                        is_star = True
                        col = ACCENT_WARNING
                except: pass
            elif v_str.lstrip('+-').isdigit():
                col = ACCENT_SECONDARY

            if is_uniq:
                uf = QFrame()
                uf.setStyleSheet("background: #2a2200; border: 1px solid #b8820a; border-radius: 4px;")
                ul = QVBoxLayout(uf)
                ul.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
                hdr = QLabel("⭐  Unique Effect")
                hdr.setStyleSheet("color: #f0c040; border: none; font-weight: bold;")
                ul.addWidget(hdr)
                bdy = QLabel(v_str)
                bdy.setStyleSheet("color: #f5e090; border: none;")
                bdy.setWordWrap(True)
                ul.addWidget(bdy)
                self.effects_lay.addWidget(uf)
            else:
                row = QHBoxLayout()
                row.setContentsMargins(2, 2, 2, 2)
                pref = "★ " if is_star else "   "
                nm = QLabel(f"{pref}{en}")
                nm.setStyleSheet(f"color: {TEXT_PRIMARY if is_star else TEXT_SECONDARY}; font-weight: {'bold' if is_star else 'normal'};")
                row.addWidget(nm, stretch=1)
                vl = QLabel(v_str)
                vl.setStyleSheet(f"color: {col}; font-weight: bold;")
                row.addWidget(vl)
                
                w = QWidget()
                w.setLayout(row)
                self.effects_lay.addWidget(w)

    def _load_notes(self, card_id):
        note, tags = get_card_notes(card_id)
        self.note_text.setPlainText(note or "")
        self.tags_entry.setText(tags or "")
        self._render_tag_chips(tags)

    def _save_notes(self):
        if not self.current_card_id: return
        note = self.note_text.toPlainText().strip()
        tags = self.tags_entry.text().strip()
        if tags:
            tags = ','.join(t.strip() for t in tags.split(',') if t.strip())
        set_card_notes(self.current_card_id, note, tags)
        self._render_tag_chips(tags)
        self._refresh_filter_dropdowns()

    def _render_tag_chips(self, tags_str):
        clear_layout(self.tag_chips_lay)
        if not tags_str: return
        cols = [ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_WARNING]
        for i, tag in enumerate(tags_str.split(',')):
            tag = tag.strip()
            if not tag: continue
            c = cols[i % len(cols)]
            btn = QPushButton(f"🏷 {tag}")
            btn.setStyleSheet(f"background: {BG_MEDIUM}; color: {c}; border-radius: 10px; padding: 2px 8px; font-size: 11px;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, t=tag: self._filter_by_tag(t))
            self.tag_chips_lay.addWidget(btn)

    def _filter_by_tag(self, tag):
        self.tag_combo.setCurrentText(tag)

    def _refresh_filter_dropdowns(self):
        try:
            self.effect_combo.blockSignals(True)
            self.effect_combo.clear()
            self.effect_combo.addItems(["All Effects"] + get_all_effect_names())
            self.effect_combo.blockSignals(False)
        except Exception: pass
        try:
            self.tag_combo.blockSignals(True)
            self.tag_combo.clear()
            self.tag_combo.addItems(["All Tags"] + get_all_tags())
            self.tag_combo.blockSignals(False)
        except Exception: pass

    # ─── RECENT & BULK & TOGGLE ───────────────────────────────────────────────

    def _build_recent_strip(self):
        clear_layout(self.recent_lay)
        if not _recent_cards:
            self.recent_frame.hide()
            return
        self.recent_frame.show()
        lbl = QLabel("🕒 Recent")
        lbl.setFont(FONT_TINY)
        lbl.setStyleSheet(f"color: {TEXT_DISABLED};")
        self.recent_lay.addWidget(lbl)

        for cid in _recent_cards:
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setStyleSheet(f"background: {BG_MEDIUM}; border-radius: {RADIUS_SM}px;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pix = self._get_list_icon(cid, get_card_by_id(cid)[6] if get_card_by_id(cid) else "")
            if pix:
                btn.setIcon(QIcon(pix))
                btn.setIconSize(pix.size())
            btn.clicked.connect(lambda _, id=cid: self.on_select(id))
            self.recent_lay.addWidget(btn)
        self.recent_lay.addStretch()

    def _add_to_recent(self, card_id):
        global _recent_cards
        if card_id in _recent_cards:
            _recent_cards.remove(card_id)
        _recent_cards.insert(0, card_id)
        _recent_cards = _recent_cards[:MAX_RECENT]
        self._build_recent_strip()

    def _toggle_bulk_mode(self):
        self.bulk_mode = not self.bulk_mode
        if self.bulk_mode:
            self.bulk_toggle_btn.setStyleSheet(f"background: {ACCENT_PRIMARY}; color: {TEXT_PRIMARY}; border-radius: {RADIUS_SM}px;")
            self.bulk_toggle_btn.setText("☑ Select")
            self.bulk_action_frame.show()
        else:
            self.bulk_toggle_btn.setStyleSheet(f"background: {BG_MEDIUM}; color: {TEXT_MUTED}; border-radius: {RADIUS_SM}px;")
            self.bulk_toggle_btn.setText("☐ Select")
            self.bulk_action_frame.hide()
            self.bulk_selected_ids.clear()
        self.populate_tree()

    def _select_all(self):
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        for c in self.filtered_cards[start:end]:
            self.bulk_selected_ids.add(c[0])
            if c[0] in self.card_checkboxes:
                self.card_checkboxes[c[0]].blockSignals(True)
                self.card_checkboxes[c[0]].setChecked(True)
                self.card_checkboxes[c[0]].blockSignals(False)
        self._update_bulk_count()

    def _deselect_all(self):
        self.bulk_selected_ids.clear()
        for cb in self.card_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self._update_bulk_count()

    def _on_bulk_checkbox(self, card_id):
        if card_id in self.card_checkboxes:
            if self.card_checkboxes[card_id].isChecked():
                self.bulk_selected_ids.add(card_id)
            else:
                self.bulk_selected_ids.discard(card_id)
        self._update_bulk_count()

    def _update_bulk_count(self):
        self.bulk_count_label.setText(f"{len(self.bulk_selected_ids)} selected")

    def _bulk_set_owned(self, owned):
        if not self.bulk_selected_ids: return
        set_cards_owned_bulk(list(self.bulk_selected_ids), owned=owned)
        self.bulk_selected_ids.clear()
        self.filter_cards()
        if self.on_stats_updated:
            self.on_stats_updated()

    def _toggle_detail_panel(self):
        self.details_visible = not self.details_visible
        if self.details_visible:
            self.details_frame.show()
            self.detail_toggle_btn.setText("◀")
        else:
            self.details_frame.hide()
            self.detail_toggle_btn.setText("▶")

    def navigate_to_card(self, card_id):
        self.reset_filters()
        for idx, card in enumerate(self.filtered_cards):
            if card[0] == card_id:
                self.current_page = idx // self.items_per_page
                self.selected_index = idx % self.items_per_page
                self.populate_tree()
                self.on_select(card_id)
                self._highlight_selected()
                return
