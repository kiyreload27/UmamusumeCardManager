"""
Card List View - Browse and search support cards with ownership management
Premium redesign with card grid, inline detail panel, modern filter bar,
recently viewed strip, bulk ownership toggle, and keyboard navigation
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os
import logging
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import (
    get_all_cards, get_card_by_id, get_effects_at_level,
    set_card_owned, is_card_owned, update_owned_card_level,
    set_cards_owned_bulk, get_card_notes, set_card_notes,
    get_all_tags, get_all_effect_names
)
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY, FONT_MONO, FONT_FAMILY,
    RARITY_COLORS, TYPE_COLORS, TYPE_ICONS,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_button, create_styled_text, create_card_frame,
    create_badge, create_section_header, create_glass_frame,
    get_rarity_color, get_type_color, get_type_icon,
    EFFECT_DESCRIPTIONS, Tooltip, create_styled_entry
)

# Module-level recently viewed list shared across instances
_recent_cards = []  # list of card_id, max 10
MAX_RECENT = 10


class CardListFrame(ctk.CTkFrame):
    """Frame containing card list with search/filter, ownership, and details panel"""

    def __init__(self, parent, on_card_selected_callback=None, on_stats_updated_callback=None,
                 navigate_to_card_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.on_card_selected = on_card_selected_callback
        self.on_stats_updated = on_stats_updated_callback
        self.navigate_to_card_callback = navigate_to_card_callback
        self.cards = []
        self.current_card_id = None
        self.selected_level = 50
        self.card_image = None
        self.icon_cache = {}
        
        # Pagination state
        self.current_page = 0
        self.items_per_page = 40
        self.filtered_cards = []

        # Keyboard navigation state
        self.selected_index = -1  # index within current page

        # Bulk selection state
        self.bulk_mode = False
        self.bulk_selected_ids = set()
        self.card_checkboxes = {}  # card_id -> checkbox var

        # Create main layout
        self.create_widgets()
        self.load_cards()

        # Bind keyboard events
        self._bind_keyboard()

    def _bind_keyboard(self):
        """Bind keyboard shortcuts for navigation"""
        try:
            top = self.winfo_toplevel()
            top.bind('<Control-f>', lambda e: self.search_entry.focus_set())
            top.bind('<Escape>', lambda e: self._handle_escape())
        except (AttributeError, tk.TclError):
            pass

    def _handle_escape(self):
        """Handle Escape key — clear search, exit bulk mode, or reset filters"""
        if self.bulk_mode:
            self._toggle_bulk_mode()
            return
        if self.search_var.get():
            self.search_var.set("")
            self.filter_cards()
            return
        self.reset_filters()

    def _handle_arrow_key(self, direction):
        """Handle Up/Down arrow key navigation in the card list"""
        if not self.filtered_cards:
            return

        page_size = self.items_per_page
        page_cards_count = min(page_size, len(self.filtered_cards) - self.current_page * page_size)

        if direction == 'down':
            # Two columns, so down moves by 2 (next row)
            self.selected_index += 2
            if self.selected_index >= page_cards_count:
                # Go to next page
                max_page = max(0, (len(self.filtered_cards) - 1) // self.items_per_page)
                if self.current_page < max_page:
                    self.current_page += 1
                    self.selected_index = 0
                    self.populate_tree()
                else:
                    self.selected_index = page_cards_count - 1
                return
        elif direction == 'up':
            self.selected_index -= 2
            if self.selected_index < 0:
                if self.current_page > 0:
                    self.current_page -= 1
                    new_count = min(page_size, len(self.filtered_cards) - self.current_page * page_size)
                    self.selected_index = new_count - 1
                    self.populate_tree()
                else:
                    self.selected_index = 0
                return
        elif direction == 'left':
            self.selected_index = max(0, self.selected_index - 1)
        elif direction == 'right':
            self.selected_index = min(page_cards_count - 1, self.selected_index + 1)

        self._highlight_selected()

    def _highlight_selected(self):
        """Highlight the selected card widget"""
        for i, widget in enumerate(self.card_widgets):
            if i == self.selected_index:
                widget.configure(border_color=ACCENT_PRIMARY, border_width=2)
            else:
                # Restore original border
                card_idx = self.current_page * self.items_per_page + i
                if card_idx < len(self.filtered_cards):
                    card = self.filtered_cards[card_idx]
                    is_owned = card[6]
                    widget.configure(
                        border_color=ACCENT_SUCCESS if is_owned else BG_LIGHT,
                        border_width=1
                    )

    def _handle_enter(self):
        """Handle Enter key — select the highlighted card"""
        if self.selected_index >= 0 and self.selected_index < len(self.card_widgets):
            card_idx = self.current_page * self.items_per_page + self.selected_index
            if card_idx < len(self.filtered_cards):
                card_id = self.filtered_cards[card_idx][0]
                self.on_select(card_id)

    def create_widgets(self):
        """Create the card list interface"""
        # Use grid for responsive two-column layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  # left: card list
        self.grid_columnconfigure(1, weight=2)  # right: details

        # Left panel - Card list with filters (no fixed width)
        self.left_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
                                   border_width=1, border_color=BG_LIGHT)
        self.left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, SPACING_XS))

        # Right panel - Card details (collapsible)
        self.details_visible = True
        self.details_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.details_frame.grid(row=0, column=1, sticky='nsew')

        # === Recently Viewed Strip ===
        self.recent_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.recent_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(SPACING_SM, 0))
        self._build_recent_strip()

        # === Filter Variables ===
        self.rarity_var = tk.StringVar(value="All")
        self.type_var = tk.StringVar(value="All")
        self.owned_only_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar(value="")

        # === Search Bar ===
        search_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        search_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(SPACING_SM, SPACING_SM))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="🔍  Search cards...",
            height=38,
            fg_color=BG_MEDIUM, border_color=BG_LIGHT,
            corner_radius=RADIUS_MD
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Detail panel toggle button
        self.detail_toggle_btn = ctk.CTkButton(
            search_frame, text="◀", width=32, height=38,
            font=FONT_BODY, fg_color=BG_MEDIUM,
            hover_color=BG_HIGHLIGHT, text_color=TEXT_MUTED,
            corner_radius=RADIUS_MD,
            command=self._toggle_detail_panel
        )
        self.detail_toggle_btn.pack(side=tk.RIGHT, padx=(SPACING_XS, 0))
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_cards())
        # Arrow keys in search field navigate the card list
        self.search_entry.bind('<Down>', lambda e: self._handle_arrow_key('down'))
        self.search_entry.bind('<Up>', lambda e: self._handle_arrow_key('up'))
        self.search_entry.bind('<Return>', lambda e: self._handle_enter())

        # === Filter Chips Row ===
        filter_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        filter_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_SM))

        # Rarity pills
        rarity_group = ctk.CTkFrame(filter_frame, fg_color="transparent")
        rarity_group.pack(side=tk.LEFT)

        for rarity in ["All", "SSR", "SR", "R"]:
            color = RARITY_COLORS.get(rarity, TEXT_MUTED) if rarity != "All" else TEXT_MUTED
            btn = ctk.CTkButton(
                rarity_group, text=rarity,
                width=45, height=28,
                font=FONT_TINY,
                fg_color=BG_MEDIUM, hover_color=BG_HIGHLIGHT,
                text_color=color,
                corner_radius=RADIUS_FULL,
                command=lambda r=rarity: self._set_rarity(r)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Type filter
        type_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.type_var,
            values=["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"],
            width=100, height=28,
            font=FONT_TINY,
            command=lambda e: self.filter_cards()
        )
        type_combo.pack(side=tk.LEFT, padx=(SPACING_SM, 0))
        type_combo.set("All")

        # Reset button
        ctk.CTkButton(
            filter_frame, text="✕", width=28, height=28,
            fg_color="transparent", hover_color=ACCENT_ERROR,
            text_color=TEXT_MUTED, font=FONT_BODY_BOLD,
            corner_radius=RADIUS_SM,
            command=self.reset_filters
        ).pack(side=tk.RIGHT)

        # === Advanced Filter Row (Effect + Tag) ===
        adv_filter_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        adv_filter_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_SM))

        # Effect filter
        self.effect_var = tk.StringVar(value="All Effects")
        self.effect_combo = ctk.CTkComboBox(
            adv_filter_frame,
            variable=self.effect_var,
            values=["All Effects"],
            width=150, height=28,
            font=FONT_TINY,
            command=lambda e: self.filter_cards()
        )
        self.effect_combo.pack(side=tk.LEFT, padx=(0, SPACING_SM))

        # Tag filter
        self.tag_var = tk.StringVar(value="All Tags")
        self.tag_combo = ctk.CTkComboBox(
            adv_filter_frame,
            variable=self.tag_var,
            values=["All Tags"],
            width=130, height=28,
            font=FONT_TINY,
            command=lambda e: self.filter_cards()
        )
        self.tag_combo.pack(side=tk.LEFT)

        # Load effect names and tags into dropdowns
        self._refresh_filter_dropdowns()

        # Owned checkbox + count label + bulk mode toggle
        meta_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        meta_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_SM))

        ctk.CTkCheckBox(
            meta_frame, text="Owned Only",
            variable=self.owned_only_var,
            command=self.filter_cards,
            font=FONT_TINY, checkbox_width=18, checkbox_height=18,
            corner_radius=4
        ).pack(side=tk.LEFT)

        # Bulk mode toggle button
        self.bulk_toggle_btn = ctk.CTkButton(
            meta_frame, text="☐ Select",
            width=70, height=24, font=FONT_TINY,
            fg_color=BG_MEDIUM, hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM,
            command=self._toggle_bulk_mode
        )
        self.bulk_toggle_btn.pack(side=tk.LEFT, padx=(SPACING_SM, 0))

        self.count_label = ctk.CTkLabel(
            meta_frame, text="0 cards",
            font=FONT_TINY, text_color=TEXT_DISABLED
        )
        self.count_label.pack(side=tk.RIGHT)

        # === Bulk Action Bar (hidden by default) ===
        self.bulk_action_frame = ctk.CTkFrame(self.left_frame, fg_color=BG_MEDIUM, corner_radius=RADIUS_SM)
        # Not packed initially — shown only in bulk mode

        self.bulk_count_label = ctk.CTkLabel(
            self.bulk_action_frame, text="0 selected",
            font=FONT_SMALL, text_color=TEXT_PRIMARY
        )
        self.bulk_count_label.pack(side=tk.LEFT, padx=SPACING_SM)

        ctk.CTkButton(
            self.bulk_action_frame, text="All",
            width=40, height=26, font=FONT_TINY,
            fg_color=BG_LIGHT, hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM,
            command=self._select_all
        ).pack(side=tk.LEFT, padx=2)

        ctk.CTkButton(
            self.bulk_action_frame, text="None",
            width=40, height=26, font=FONT_TINY,
            fg_color=BG_LIGHT, hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM,
            command=self._deselect_all
        ).pack(side=tk.LEFT, padx=2)

        ctk.CTkButton(
            self.bulk_action_frame, text="✓ Mark Owned",
            width=90, height=26, font=FONT_TINY,
            fg_color=ACCENT_SUCCESS, hover_color="#2dd36f",
            text_color="#ffffff", corner_radius=RADIUS_SM,
            command=lambda: self._bulk_set_owned(True)
        ).pack(side=tk.RIGHT, padx=(2, SPACING_SM))

        ctk.CTkButton(
            self.bulk_action_frame, text="✗ Unown",
            width=70, height=26, font=FONT_TINY,
            fg_color=ACCENT_ERROR, hover_color="#ff4961",
            text_color="#ffffff", corner_radius=RADIUS_SM,
            command=lambda: self._bulk_set_owned(False)
        ).pack(side=tk.RIGHT, padx=2)

        # === Pagination ===
        self.pagination_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.pagination_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_XS))

        self.btn_prev = ctk.CTkButton(
            self.pagination_frame, text="◀",
            width=36, height=28, font=FONT_SMALL,
            fg_color=BG_MEDIUM, hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM,
            command=self.prev_page
        )
        self.btn_prev.pack(side=tk.LEFT)

        self.page_label = ctk.CTkLabel(
            self.pagination_frame, text="Page 1 / 1",
            font=FONT_TINY, text_color=TEXT_MUTED
        )
        self.page_label.pack(side=tk.LEFT, expand=True)

        self.btn_next = ctk.CTkButton(
            self.pagination_frame, text="▶",
            width=36, height=28, font=FONT_SMALL,
            fg_color=BG_MEDIUM, hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM,
            command=self.next_page
        )
        self.btn_next.pack(side=tk.RIGHT)

        # === Card Grid (scrollable) ===
        self.scroll_container = ctk.CTkScrollableFrame(self.left_frame, fg_color="transparent")
        self.scroll_container.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=(0, SPACING_SM))
        self.scroll_container.columnconfigure(0, weight=1)
        self.scroll_container.columnconfigure(1, weight=1)

        self.card_widgets = []

        # === Details Panel ===
        self.create_details_panel()

    # ------- Recently Viewed Strip -------

    def _build_recent_strip(self):
        """Build or rebuild the recently viewed cards strip"""
        for child in self.recent_frame.winfo_children():
            child.destroy()

        if not _recent_cards:
            self.recent_frame.pack_forget()
            return

        self.recent_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(SPACING_SM, 0))

        # Section label
        ctk.CTkLabel(
            self.recent_frame, text="🕒 Recent",
            font=FONT_TINY, text_color=TEXT_DISABLED
        ).pack(side=tk.LEFT, padx=(0, SPACING_XS))

        for card_id in _recent_cards:
            img = self.icon_cache.get(card_id)
            if not img:
                # Try to load a small thumb from cache
                card = get_card_by_id(card_id)
                if card:
                    resolved = resolve_image_path(card[6])  # image_path
                    if resolved and os.path.exists(resolved):
                        try:
                            pil_img = Image.open(resolved)
                            pil_img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                            img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                            self.icon_cache[card_id] = img
                        except (OSError, SyntaxError, ValueError):
                            pass

            btn = ctk.CTkButton(
                self.recent_frame, text="", image=img if img else None,
                width=36, height=36, fg_color=BG_MEDIUM,
                hover_color=BG_HIGHLIGHT, corner_radius=RADIUS_SM,
                command=lambda cid=card_id: self.on_select(cid)
            )
            btn.pack(side=tk.LEFT, padx=1)

            # Tooltip with card name 
            card_data = get_card_by_id(card_id)
            if card_data:
                Tooltip(btn, card_data[1])

    def _add_to_recent(self, card_id):
        """Add a card to the recently viewed list"""
        global _recent_cards
        if card_id in _recent_cards:
            _recent_cards.remove(card_id)
        _recent_cards.insert(0, card_id)
        _recent_cards = _recent_cards[:MAX_RECENT]
        self._build_recent_strip()

    # ------- Bulk Selection -------

    def _toggle_bulk_mode(self):
        """Toggle bulk selection mode"""
        self.bulk_mode = not self.bulk_mode
        if self.bulk_mode:
            self.bulk_toggle_btn.configure(
                text="☑ Select", fg_color=ACCENT_PRIMARY, text_color=TEXT_PRIMARY
            )
            self.bulk_action_frame.pack(
                fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_SM),
                before=self.pagination_frame
            )
        else:
            self.bulk_toggle_btn.configure(
                text="☐ Select", fg_color=BG_MEDIUM, text_color=TEXT_MUTED
            )
            self.bulk_action_frame.pack_forget()
            self.bulk_selected_ids.clear()
            self.card_checkboxes.clear()

        self.populate_tree()

    def _select_all(self):
        """Select all cards on current page"""
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_cards = self.filtered_cards[start_idx:end_idx]
        for card in page_cards:
            card_id = card[0]
            self.bulk_selected_ids.add(card_id)
            if card_id in self.card_checkboxes:
                self.card_checkboxes[card_id].set(True)
        self._update_bulk_count()

    def _deselect_all(self):
        """Deselect all cards"""
        self.bulk_selected_ids.clear()
        for var in self.card_checkboxes.values():
            var.set(False)
        self._update_bulk_count()

    def _on_bulk_checkbox(self, card_id):
        """Handle individual checkbox toggle"""
        if card_id in self.card_checkboxes:
            if self.card_checkboxes[card_id].get():
                self.bulk_selected_ids.add(card_id)
            else:
                self.bulk_selected_ids.discard(card_id)
        self._update_bulk_count()

    def _update_bulk_count(self):
        """Update the bulk selection count label"""
        self.bulk_count_label.configure(text=f"{len(self.bulk_selected_ids)} selected")

    def _bulk_set_owned(self, owned):
        """Bulk set owned status"""
        if not self.bulk_selected_ids:
            return
        card_ids = list(self.bulk_selected_ids)
        set_cards_owned_bulk(card_ids, owned=owned)
        self.bulk_selected_ids.clear()
        self.card_checkboxes.clear()
        self.filter_cards()
        if self.on_stats_updated:
            self.on_stats_updated()

    # ------- Navigation to specific card -------

    def navigate_to_card(self, card_id):
        """Navigate to and select a specific card by ID, adjusting page if needed"""
        # Find the card in the full unfiltered list
        self.reset_filters()
        # Find position of card_id in filtered_cards
        for idx, card in enumerate(self.filtered_cards):
            if card[0] == card_id:
                self.current_page = idx // self.items_per_page
                self.selected_index = idx % self.items_per_page
                self.populate_tree()
                self.on_select(card_id)
                self._highlight_selected()
                return

    def _set_rarity(self, rarity):
        self.rarity_var.set(rarity)
        self.filter_cards()

    def create_details_panel(self):
        """Create the card details panel"""
        details_container = ctk.CTkFrame(
            self.details_frame, fg_color=BG_DARK,
            corner_radius=RADIUS_LG, border_width=1, border_color=BG_LIGHT
        )
        details_container.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        # Scrollable detail content for small screens
        detail_scroll = ctk.CTkScrollableFrame(details_container, fg_color="transparent")
        detail_scroll.pack(fill=tk.BOTH, expand=True)

        # Image area with elevated background
        image_wrapper = ctk.CTkFrame(detail_scroll, fg_color=BG_MEDIUM, corner_radius=RADIUS_MD)
        image_wrapper.pack(pady=(SPACING_SM, SPACING_XS), padx=SPACING_LG)

        self.image_label = ctk.CTkLabel(image_wrapper, text="", height=120, width=120)
        self.image_label.pack(padx=SPACING_SM, pady=SPACING_SM)

        # Card name
        self.detail_name = ctk.CTkLabel(
            detail_scroll, text="Select a card",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        )
        self.detail_name.pack(pady=(0, 2))

        # Info badges row
        self.detail_info_frame = ctk.CTkFrame(detail_scroll, fg_color="transparent")
        self.detail_info_frame.pack(pady=(0, SPACING_MD))

        self.detail_info = ctk.CTkLabel(
            self.detail_info_frame, text="",
            font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self.detail_info.pack()

        # Ownership toggle
        owned_frame = ctk.CTkFrame(detail_scroll, fg_color="transparent")
        owned_frame.pack(pady=SPACING_XS)

        self.owned_var = tk.BooleanVar(value=False)
        self.owned_checkbox = ctk.CTkSwitch(
            owned_frame, text="  I Own This Card",
            variable=self.owned_var,
            command=self.toggle_owned,
            font=FONT_BODY_BOLD,
            progress_color=ACCENT_SUCCESS,
            button_color=TEXT_PRIMARY,
            button_hover_color=TEXT_SECONDARY,
            switch_width=46, switch_height=24
        )
        self.owned_checkbox.pack()

        # Level selector section
        level_section = ctk.CTkFrame(detail_scroll, fg_color="transparent")
        level_section.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_XS)

        ctk.CTkLabel(
            level_section, text="Card Level",
            font=FONT_TINY, text_color=TEXT_MUTED
        ).pack(anchor="w", pady=(0, 2))

        # Segmented level control
        self.level_btn_frame = ctk.CTkFrame(level_section, fg_color="transparent")
        self.level_btn_frame.pack(fill=tk.X)

        self.level_var = tk.IntVar(value=50)
        self.max_level = 50
        self.valid_levels = [30, 35, 40, 45, 50]
        self.level_buttons = {}
        self.update_level_buttons('SSR', 50)

        # Effects section
        effects_header = ctk.CTkFrame(detail_scroll, fg_color="transparent")
        effects_header.pack(fill=tk.X, padx=SPACING_LG, pady=(SPACING_SM, SPACING_XS))

        self.effects_level_label = ctk.CTkLabel(
            effects_header, text="📊  Effects at Level 50",
            font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY
        )
        self.effects_level_label.pack(side=tk.LEFT)

        # Effects text area
        self.effects_text = create_styled_text(detail_scroll, height=14)
        self.effects_text.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))
        self.effects_text.configure(state="disabled")

        # === Notes & Tags Section ===
        notes_header = ctk.CTkFrame(detail_scroll, fg_color="transparent")
        notes_header.pack(fill=tk.X, padx=SPACING_LG, pady=(SPACING_SM, SPACING_XS))

        ctk.CTkLabel(
            notes_header, text="📝  Notes & Tags",
            font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY
        ).pack(side=tk.LEFT)

        save_note_btn = ctk.CTkButton(
            notes_header, text="Save", width=50, height=24,
            font=FONT_TINY, fg_color=ACCENT_SUCCESS, hover_color="#2dd36f",
            text_color="#ffffff", corner_radius=RADIUS_SM,
            command=self._save_notes
        )
        save_note_btn.pack(side=tk.RIGHT)

        # Tags entry
        tags_row = ctk.CTkFrame(detail_scroll, fg_color="transparent")
        tags_row.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_XS))

        ctk.CTkLabel(
            tags_row, text="Tags:",
            font=FONT_TINY, text_color=TEXT_MUTED, width=35
        ).pack(side=tk.LEFT)

        self.tags_entry = ctk.CTkEntry(
            tags_row, placeholder_text="e.g. speed,stamina,top-tier",
            height=28, font=FONT_TINY,
            fg_color=BG_MEDIUM, border_color=BG_LIGHT,
            corner_radius=RADIUS_SM
        )
        self.tags_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=SPACING_XS)

        # Tag chips display
        self.tag_chips_frame = ctk.CTkFrame(detail_scroll, fg_color="transparent")
        self.tag_chips_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_XS))

        # Note text
        self.note_text = ctk.CTkTextbox(
            detail_scroll, height=60, font=FONT_SMALL,
            fg_color=BG_MEDIUM, border_color=BG_LIGHT,
            border_width=1, corner_radius=RADIUS_SM
        )
        self.note_text.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_LG))

    def load_cards(self):
        """Load all cards from database"""
        self.cards = get_all_cards()
        self.filtered_cards = self.cards
        self.current_page = 0
        self.populate_tree()

    def reset_filters(self):
        """Reset all filters to default"""
        self.search_var.set("")
        self.rarity_var.set("All")
        self.type_var.set("All")
        self.effect_var.set("All Effects")
        self.tag_var.set("All Tags")
        self.owned_only_var.set(False)
        self.filter_cards()

    def filter_cards(self, *args):
        """Filter cards based on search and dropdown values"""
        rarity = self.rarity_var.get() if self.rarity_var.get() != "All" else None
        card_type = self.type_var.get() if self.type_var.get() != "All" else None
        search_text = self.search_var.get().strip()
        search = search_text if search_text else None
        owned_only = self.owned_only_var.get()

        effect = self.effect_var.get() if self.effect_var.get() != "All Effects" else None
        tag = self.tag_var.get() if self.tag_var.get() != "All Tags" else None

        self.cards = get_all_cards(
            rarity_filter=rarity, type_filter=card_type,
            search_term=search, owned_only=owned_only,
            effect_filter=effect, tag_filter=tag
        )
        self.filtered_cards = self.cards
        self.current_page = 0
        self.selected_index = -1
        self.populate_tree()
        self.count_label.configure(text=f"{len(self.cards)} cards")

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

    def populate_tree(self):
        """Populate scrollable frame with modern card widgets using pagination"""
        for widget in self.card_widgets:
            widget.destroy()
        self.card_widgets.clear()
        self.card_checkboxes.clear()

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_cards = self.filtered_cards[start_idx:end_idx]

        max_page = max(1, (len(self.filtered_cards) + self.items_per_page - 1) // self.items_per_page)
        self.page_label.configure(text=f"{self.current_page + 1} / {max_page}")

        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < max_page - 1 else "disabled")

        row, col = 0, 0
        for card in page_cards:
            card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level = card
            type_icon = get_type_icon(card_type)

            display_name = name
            if is_owned and owned_level:
                display_name = f"{name} (Lv{owned_level})"

            # Card styling
            border_color = ACCENT_SUCCESS if is_owned else BG_LIGHT
            bg_color = BG_ELEVATED if is_owned else BG_DARK

            card_frame = ctk.CTkFrame(
                self.scroll_container, fg_color=bg_color,
                corner_radius=RADIUS_MD, border_width=1,
                border_color=border_color
            )
            card_frame.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            self.card_widgets.append(card_frame)

            def make_clickable(widget, cid=card_id):
                widget.bind("<Button-1>", lambda e, id=cid: self.on_select(id))
                for child in widget.winfo_children():
                    make_clickable(child, cid)

            # Bulk checkbox (if in bulk mode)
            if self.bulk_mode:
                cb_var = tk.BooleanVar(value=(card_id in self.bulk_selected_ids))
                self.card_checkboxes[card_id] = cb_var
                cb = ctk.CTkCheckBox(
                    card_frame, text="", variable=cb_var,
                    command=lambda cid=card_id: self._on_bulk_checkbox(cid),
                    checkbox_width=18, checkbox_height=18,
                    corner_radius=4, width=20
                )
                cb.pack(side=tk.LEFT, padx=(SPACING_XS, 0), pady=SPACING_XS)

            # Image
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(image_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((44, 44), Image.Resampling.LANCZOS)
                        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(44, 44))
                        self.icon_cache[card_id] = img
                    except (OSError, SyntaxError, ValueError) as e:
                        logging.debug(f"Failed to load card icon {image_path}: {e}")

            img_label = ctk.CTkLabel(
                card_frame, text="", image=img if img else None,
                width=44, height=44, corner_radius=RADIUS_SM
            )
            img_label.pack(side=tk.LEFT, padx=SPACING_XS, pady=SPACING_XS)

            # Info container
            info_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=SPACING_XS, padx=(0, SPACING_XS))

            ctk.CTkLabel(
                info_frame, text=display_name,
                font=FONT_SMALL, text_color=TEXT_PRIMARY,
                anchor="w", justify="left"
            ).pack(fill=tk.X)

            # Meta badges
            meta_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
            meta_frame.pack(fill=tk.X, pady=(SPACING_XS, 0))

            rarity_color = get_rarity_color(rarity)
            type_color = get_type_color(card_type)

            ctk.CTkLabel(
                meta_frame, text=rarity,
                font=FONT_TINY, text_color=rarity_color,
                fg_color=BG_MEDIUM, corner_radius=4,
                height=18, width=30
            ).pack(side=tk.LEFT, padx=(0, SPACING_XS))

            ctk.CTkLabel(
                meta_frame, text=f"{type_icon} {card_type}",
                font=FONT_TINY, text_color=type_color
            ).pack(side=tk.LEFT)

            if is_owned:
                ctk.CTkLabel(
                    meta_frame, text="✓",
                    font=FONT_TINY, text_color=ACCENT_SUCCESS
                ).pack(side=tk.RIGHT)

            if not self.bulk_mode:
                make_clickable(card_frame)

            col += 1
            if col > 1:
                col = 0
                row += 1

    def on_select(self, override_id=None):
        """Handle card selection"""
        card_id = override_id
        if not card_id:
            return
        card = get_card_by_id(card_id)

        if card:
            card_id, name, rarity, card_type, max_level, url, image_path, is_owned, owned_level = card

            self.owned_var.set(bool(is_owned))

            # Load card image
            self.load_card_image(image_path)

            # Level logic
            initial_level = owned_level if is_owned and owned_level else max_level
            self.max_level = max_level
            self.update_level_buttons(rarity, max_level)

            if initial_level not in self.valid_levels:
                initial_level = max_level

            self.level_var.set(initial_level)
            self.selected_level = initial_level

            # Update details
            type_icon = get_type_icon(card_type)
            self.detail_name.configure(text=f"{type_icon}  {name}")

            # Info with badges
            self.detail_info.configure(
                text=f"{rarity}  ·  {card_type}  ·  Max Lv {max_level}"
            )

            self.current_card_id = card_id
            self.update_effects_display()

            # Load notes & tags for this card
            self._load_notes(card_id)

            # Add to recently viewed
            self._add_to_recent(card_id)

            if self.on_card_selected:
                self.on_card_selected(card_id, name, self.selected_level)

    def load_card_image(self, image_path):
        """Load and display card image"""
        resolved_path = resolve_image_path(image_path)

        if resolved_path and os.path.exists(resolved_path):
            try:
                img = ctk.CTkImage(
                    light_image=Image.open(resolved_path),
                    dark_image=Image.open(resolved_path),
                    size=(120, 120)
                )
                self.image_label.configure(image=img, text="")
            except Exception:
                self.image_label.configure(image=None, text="[Image Error]")
        else:
            self.image_label.configure(image=None, text="[No Image]")

    def toggle_owned(self):
        """Toggle owned status for current card"""
        if self.current_card_id:
            owned = self.owned_var.get()
            level = int(self.level_var.get())
            set_card_owned(self.current_card_id, owned, level)
            self.filter_cards()

            if self.on_stats_updated:
                self.on_stats_updated()

    def update_level_buttons(self, rarity, max_level):
        """Update segmented level control"""
        if max_level == 50:
            self.valid_levels = [30, 35, 40, 45, 50]
        elif max_level == 45:
            self.valid_levels = [25, 30, 35, 40, 45]
        else:
            self.valid_levels = [20, 25, 30, 35, 40]

        for widget in self.level_btn_frame.winfo_children():
            widget.destroy()
        self.level_buttons = {}

        for idx, lvl in enumerate(self.valid_levels):
            is_active = (lvl == self.level_var.get())
            btn = ctk.CTkButton(
                self.level_btn_frame, text=f"Lv{lvl}",
                command=lambda l=lvl: self.set_level(l),
                width=55, height=34, font=FONT_BODY_BOLD,
                fg_color=ACCENT_PRIMARY if is_active else BG_MEDIUM,
                hover_color=BG_HIGHLIGHT,
                text_color=TEXT_PRIMARY if is_active else TEXT_MUTED,
                corner_radius=RADIUS_SM if idx > 0 and idx < len(self.valid_levels) - 1 else RADIUS_MD,
            )
            btn.pack(side=tk.LEFT, padx=1)
            self.level_buttons[lvl] = btn

    def set_level(self, level):
        """Update selected level and notify callback"""
        if self.current_card_id:
            self.selected_level = level
            self.level_var.set(level)
            self.update_effects_display()

            # Refresh level button states
            for lvl, btn in self.level_buttons.items():
                if lvl == level:
                    btn.configure(fg_color=ACCENT_PRIMARY, text_color=TEXT_PRIMARY)
                else:
                    btn.configure(fg_color=BG_MEDIUM, text_color=TEXT_MUTED)

            if self.on_card_selected:
                card = get_card_by_id(self.current_card_id)
                if card:
                    self.on_card_selected(self.current_card_id, card[1], self.selected_level)

        if self.current_card_id and self.owned_var.get():
            update_owned_card_level(self.current_card_id, level)

    def increment_level(self):
        current = self.level_var.get()
        for lvl in self.valid_levels:
            if lvl > current:
                self.set_level(lvl)
                return

    def decrement_level(self):
        current = self.level_var.get()
        for lvl in reversed(self.valid_levels):
            if lvl < current:
                self.set_level(lvl)
                return

    def update_effects_display(self):
        """Update the effects display for current card and level"""
        if not self.current_card_id:
            return

        level = int(self.level_var.get())
        effects = get_effects_at_level(self.current_card_id, level)

        self.effects_level_label.configure(text=f"📊  Effects at Level {level}")

        self.effects_text.configure(state="normal")
        self.effects_text.delete('1.0', tk.END)

        if effects:
            self.effects_text.insert(tk.END, f"{'─' * 40}\n")
            self.effects_text.insert(tk.END, f"  LEVEL {level} EFFECTS\n")
            self.effects_text.insert(tk.END, f"{'─' * 40}\n\n")
            for name, value in effects:
                prefix = ""
                if '%' in str(value):
                    try:
                        num = int(str(value).replace('%', '').replace('+', ''))
                        if num >= 20:
                            prefix = "★ "
                    except:
                        pass
                self.effects_text.insert(tk.END, f"  {prefix}{name:.<32} {value}\n")
        else:
            self.effects_text.insert(tk.END, f"  No effects data for Level {level}\n\n")
            self.effects_text.insert(tk.END, f"  Available levels: {self.valid_levels}")

        self.effects_text.configure(state="disabled")

    # ------- Notes & Tags -------

    def _load_notes(self, card_id):
        """Load notes and tags for a card into the UI"""
        note, tags = get_card_notes(card_id)

        # Update note text
        self.note_text.delete('1.0', tk.END)
        if note:
            self.note_text.insert(tk.END, note)

        # Update tags entry
        self.tags_entry.delete(0, tk.END)
        if tags:
            self.tags_entry.insert(0, tags)

        # Render tag chips
        self._render_tag_chips(tags)

    def _save_notes(self):
        """Save notes and tags for the current card"""
        if not self.current_card_id:
            return
        note = self.note_text.get('1.0', tk.END).strip()
        tags = self.tags_entry.get().strip()

        # Normalize tags: strip whitespace around commas
        if tags:
            tags = ','.join(t.strip() for t in tags.split(',') if t.strip())

        set_card_notes(self.current_card_id, note, tags)
        self._render_tag_chips(tags)
        self._refresh_filter_dropdowns()

    def _render_tag_chips(self, tags_str):
        """Render tag chips from a comma-separated string"""
        for child in self.tag_chips_frame.winfo_children():
            child.destroy()

        if not tags_str:
            return

        tag_colors = [ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_WARNING]
        for i, tag in enumerate(tags_str.split(',')):
            tag = tag.strip()
            if not tag:
                continue
            color = tag_colors[i % len(tag_colors)]
            chip = ctk.CTkButton(
                self.tag_chips_frame, text=f"🏷 {tag}",
                font=FONT_TINY, width=0, height=22,
                fg_color=BG_MEDIUM, hover_color=BG_HIGHLIGHT,
                text_color=color, corner_radius=RADIUS_FULL,
                command=lambda t=tag: self._filter_by_tag(t)
            )
            chip.pack(side=tk.LEFT, padx=2)

    def _filter_by_tag(self, tag):
        """Filter cards by clicking on a tag chip"""
        self.tag_var.set(tag)
        self.filter_cards()

    def _refresh_filter_dropdowns(self):
        """Refresh effect and tag filter dropdown values"""
        try:
            effects = get_all_effect_names()
            self.effect_combo.configure(values=["All Effects"] + effects)
        except Exception:
            pass

        try:
            tags = get_all_tags()
            self.tag_combo.configure(values=["All Tags"] + tags)
        except Exception:
            pass

    def _toggle_detail_panel(self):
        """Toggle the visibility of the right detail panel"""
        self.details_visible = not self.details_visible
        if self.details_visible:
            self.details_frame.grid(row=0, column=1, sticky='nsew')
            self.grid_columnconfigure(1, weight=2)
            self.detail_toggle_btn.configure(text="◀")
        else:
            self.details_frame.grid_remove()
            self.grid_columnconfigure(1, weight=0)
            self.detail_toggle_btn.configure(text="▶")
