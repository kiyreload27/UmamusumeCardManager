"""
Card List View - Browse and search support cards with ownership management
Premium redesign with card grid, inline detail panel, and modern filter bar
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os
import logging
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_cards, get_card_by_id, get_effects_at_level, set_card_owned, is_card_owned, update_owned_card_level
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


class CardListFrame(ctk.CTkFrame):
    """Frame containing card list with search/filter, ownership, and details panel"""

    def __init__(self, parent, on_card_selected_callback=None, on_stats_updated_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.on_card_selected = on_card_selected_callback
        self.on_stats_updated = on_stats_updated_callback
        self.cards = []
        self.current_card_id = None
        self.selected_level = 50
        self.card_image = None
        self.icon_cache = {}
        
        # Pagination state
        self.current_page = 0
        self.items_per_page = 40
        self.filtered_cards = []

        # Create main layout
        self.create_widgets()
        self.load_cards()

    def create_widgets(self):
        """Create the card list interface"""
        # Left panel - Card list with filters
        left_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=RADIUS_LG, 
                                   border_width=1, border_color=BG_LIGHT, width=440)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, SPACING_SM))

        # Right panel - Card details
        self.details_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # === Filter Variables ===
        self.rarity_var = tk.StringVar(value="All")
        self.type_var = tk.StringVar(value="All")
        self.owned_only_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar(value="")

        # === Search Bar ===
        search_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        search_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(SPACING_LG, SPACING_SM))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="🔍  Search cards...",
            width=200, height=38,
            fg_color=BG_MEDIUM, border_color=BG_LIGHT,
            corner_radius=RADIUS_MD
        )
        self.search_entry.pack(fill=tk.X, expand=True)
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_cards())

        # === Filter Chips Row ===
        filter_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
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

        # Owned checkbox + count label row
        meta_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        meta_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_SM))

        ctk.CTkCheckBox(
            meta_frame, text="Owned Only",
            variable=self.owned_only_var,
            command=self.filter_cards,
            font=FONT_TINY, checkbox_width=18, checkbox_height=18,
            corner_radius=4
        ).pack(side=tk.LEFT)

        self.count_label = ctk.CTkLabel(
            meta_frame, text="0 cards",
            font=FONT_TINY, text_color=TEXT_DISABLED
        )
        self.count_label.pack(side=tk.RIGHT)

        # Keyboard shortcut
        try:
            self.winfo_toplevel().bind('<Control-f>', lambda e: self.search_entry.focus_set())
        except AttributeError:
            pass

        # === Pagination ===
        self.pagination_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
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
        self.scroll_container = ctk.CTkScrollableFrame(left_frame, fg_color="transparent")
        self.scroll_container.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=(0, SPACING_SM))
        self.scroll_container.columnconfigure(0, weight=1)
        self.scroll_container.columnconfigure(1, weight=1)

        self.card_widgets = []

        # === Details Panel ===
        self.create_details_panel()

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
        image_wrapper = ctk.CTkFrame(detail_scroll, fg_color=BG_MEDIUM, corner_radius=RADIUS_LG)
        image_wrapper.pack(pady=SPACING_LG, padx=SPACING_XL)

        self.image_label = ctk.CTkLabel(image_wrapper, text="", height=180, width=180)
        self.image_label.pack(padx=SPACING_MD, pady=SPACING_MD)

        # Card name - display size
        self.detail_name = ctk.CTkLabel(
            detail_scroll, text="Select a card",
            font=FONT_DISPLAY, text_color=TEXT_PRIMARY
        )
        self.detail_name.pack(pady=(0, SPACING_XS))

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
        owned_frame.pack(pady=SPACING_SM)

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
        level_section.pack(fill=tk.X, padx=SPACING_XL, pady=SPACING_MD)

        ctk.CTkLabel(
            level_section, text="Card Level",
            font=FONT_SMALL, text_color=TEXT_MUTED
        ).pack(anchor="w", pady=(0, SPACING_XS))

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
        effects_header.pack(fill=tk.X, padx=SPACING_XL, pady=(SPACING_MD, SPACING_XS))

        self.effects_level_label = ctk.CTkLabel(
            effects_header, text="📊  Effects at Level 50",
            font=FONT_SUBHEADER, text_color=ACCENT_PRIMARY
        )
        self.effects_level_label.pack(side=tk.LEFT)

        # Effects text area
        self.effects_text = create_styled_text(detail_scroll, height=20)
        self.effects_text.pack(fill=tk.BOTH, expand=True, padx=SPACING_XL, pady=(0, SPACING_XL))
        self.effects_text.configure(state="disabled")

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
        self.owned_only_var.set(False)
        self.filter_cards()

    def filter_cards(self, *args):
        """Filter cards based on search and dropdown values"""
        rarity = self.rarity_var.get() if self.rarity_var.get() != "All" else None
        card_type = self.type_var.get() if self.type_var.get() != "All" else None
        search_text = self.search_var.get().strip()
        search = search_text if search_text else None
        owned_only = self.owned_only_var.get()

        self.cards = get_all_cards(
            rarity_filter=rarity, type_filter=card_type,
            search_term=search, owned_only=owned_only
        )
        self.filtered_cards = self.cards
        self.current_page = 0
        self.populate_tree()
        self.count_label.configure(text=f"{len(self.cards)} cards")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.populate_tree()

    def next_page(self):
        max_page = max(0, (len(self.filtered_cards) - 1) // self.items_per_page)
        if self.current_page < max_page:
            self.current_page += 1
            self.populate_tree()

    def populate_tree(self):
        """Populate scrollable frame with modern card widgets using pagination"""
        for widget in self.card_widgets:
            widget.destroy()
        self.card_widgets.clear()

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

            # Image
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(image_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((72, 72), Image.Resampling.LANCZOS)
                        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(72, 72))
                        self.icon_cache[card_id] = img
                    except (OSError, SyntaxError, ValueError) as e:
                        logging.debug(f"Failed to load card icon {image_path}: {e}")

            img_label = ctk.CTkLabel(
                card_frame, text="", image=img if img else None,
                width=72, height=72, corner_radius=RADIUS_SM
            )
            img_label.pack(side=tk.LEFT, padx=SPACING_SM, pady=SPACING_SM)

            # Info container
            info_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=SPACING_SM, padx=(0, SPACING_SM))

            ctk.CTkLabel(
                info_frame, text=display_name,
                font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY,
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
                    size=(180, 180)
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
