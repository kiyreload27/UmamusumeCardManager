"""
Effects Search View - Search for effects across all owned cards
Premium redesign with quick-filter chips and visual result cards
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import sys
import os
import re
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import search_owned_effects
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_TERTIARY, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_button, create_styled_entry, create_card_frame
)
from utils import resolve_image_path


# Quick filter presets
QUICK_FILTERS = [
    "Friendship", "Motivation", "Race Bonus", "Skill Pt",
    "Training", "Specialty", "Hint", "Fan Count"
]


class EffectsFrame(ctk.CTkFrame):
    """Frame for searching effects across owned cards"""

    def __init__(self, parent, navigate_to_card_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_to_card = navigate_to_card_callback
        self.icon_cache = {}
        self.result_widgets = []
        self.create_widgets()

    def create_widgets(self):
        """Create the effects search interface"""
        # Header / Search Bar
        header_frame = ctk.CTkFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        header_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(SPACING_LG, SPACING_SM))

        # Title row
        title_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_row.pack(fill=tk.X, padx=SPACING_LG, pady=(SPACING_LG, SPACING_SM))

        ctk.CTkLabel(
            title_row, text="📊  Search Effects",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        ctk.CTkLabel(
            title_row, text="Search across all owned cards",
            font=FONT_SMALL, text_color=TEXT_MUTED
        ).pack(side=tk.RIGHT)

        # Search input row
        search_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        search_container.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))

        self.search_var = tk.StringVar()
        self.search_entry = create_styled_entry(
            search_container, textvariable=self.search_var,
            placeholder_text="Type an effect name..."
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, SPACING_SM))
        self.search_entry.bind('<Return>', lambda e: self.perform_search())

        search_btn = create_styled_button(
            search_container, text="Search",
            command=self.perform_search, style_type='accent',
            width=100
        )
        search_btn.pack(side=tk.LEFT)

        # Quick filter chips
        chips_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        chips_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_LG))

        for term in QUICK_FILTERS:
            chip = ctk.CTkButton(
                chips_frame, text=term,
                font=FONT_TINY, width=70, height=26,
                fg_color=BG_MEDIUM, hover_color=BG_HIGHLIGHT,
                text_color=TEXT_MUTED, corner_radius=RADIUS_FULL,
                command=lambda t=term: self._quick_search(t)
            )
            chip.pack(side=tk.LEFT, padx=2)

        # Results Area
        results_frame = ctk.CTkFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        results_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))

        result_header = ctk.CTkFrame(results_frame, fg_color="transparent")
        result_header.pack(fill=tk.X, padx=SPACING_LG, pady=(SPACING_MD, SPACING_XS))

        ctk.CTkLabel(
            result_header, text="Results",
            font=FONT_SUBHEADER, text_color=ACCENT_PRIMARY
        ).pack(side=tk.LEFT)

        self.status_label = ctk.CTkLabel(
            result_header, text="",
            font=FONT_TINY, text_color=TEXT_DISABLED
        )
        self.status_label.pack(side=tk.RIGHT)

        # Scrollable result grid
        self.scroll_area = ctk.CTkScrollableFrame(results_frame, fg_color="transparent")
        self.scroll_area.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=(0, SPACING_SM))
        self.scroll_area.columnconfigure(0, weight=1)
        self.scroll_area.columnconfigure(1, weight=1)
        self.scroll_area.columnconfigure(2, weight=1)

    def _quick_search(self, term):
        """Fill search and execute"""
        self.search_var.set(term)
        self.perform_search()

    def parse_value(self, value_str):
        """Parse effect value string to float for sorting"""
        try:
            clean = re.sub(r'[^\d.-]', '', str(value_str))
            return float(clean)
        except:
            return -999999.0

    def perform_search(self):
        """Execute search and update results"""
        term = self.search_var.get().strip()
        if not term:
            messagebox.showwarning("Search", "Please enter a search term")
            return

        for widget in self.result_widgets:
            widget.destroy()
        self.result_widgets.clear()

        results = search_owned_effects(term)

        if not results:
            self.status_label.configure(text="No matching effects found among owned cards.")
            return

        # Process and sort
        processed = []
        for r in results:
            val_num = self.parse_value(r[4])
            processed.append({'data': r, 'sort_val': val_num})
        processed.sort(key=lambda x: x['sort_val'], reverse=True)

        # Populate grid
        row, col = 0, 0
        count = 0
        for item in processed:
            if count >= 100:
                self.status_label.configure(
                    text=f"Showing top 100 of {len(processed)} results"
                )
                break
            count += 1

            r = item['data']
            card_id, card_name, image_path, effect_name, effect_value, level = r

            card_frame = ctk.CTkFrame(
                self.scroll_area, fg_color=BG_DARK,
                corner_radius=RADIUS_MD, border_width=1, border_color=BG_LIGHT
            )
            card_frame.grid(row=row, column=col, sticky="nsew", padx=SPACING_SM, pady=SPACING_SM)
            self.result_widgets.append(card_frame)

            # Image
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(image_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(60, 60))
                        self.icon_cache[card_id] = img
                    except:
                        pass

            img_label = ctk.CTkLabel(
                card_frame, text="", image=img if img else None,
                width=60, height=60, corner_radius=RADIUS_SM
            )
            img_label.pack(side=tk.LEFT, padx=SPACING_SM, pady=SPACING_SM)

            info_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=SPACING_SM, padx=(0, SPACING_SM))

            # Card name + level badge — clickable for cross-view linking
            header_box = ctk.CTkFrame(info_frame, fg_color="transparent")
            header_box.pack(fill=tk.X)

            name_label = ctk.CTkLabel(
                header_box, text=card_name,
                font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY, anchor="w",
                cursor="hand2"
            )
            name_label.pack(side=tk.LEFT)
            if self.navigate_to_card:
                name_label.bind("<Button-1>", lambda e, cid=card_id: self.navigate_to_card(cid))

            ctk.CTkLabel(
                header_box, text=f"Lv{level}",
                font=FONT_TINY, text_color=TEXT_MUTED,
                fg_color=BG_MEDIUM, corner_radius=4,
                height=18, width=35
            ).pack(side=tk.RIGHT)

            # Effect name + value
            effect_box = ctk.CTkFrame(info_frame, fg_color="transparent")
            effect_box.pack(fill=tk.X, pady=(SPACING_XS, 0))

            ctk.CTkLabel(
                effect_box, text=effect_name,
                font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w"
            ).pack(side=tk.LEFT)

            ctk.CTkLabel(
                effect_box, text=str(effect_value),
                font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY
            ).pack(side=tk.RIGHT)

            col += 1
            if col > 2:
                col = 0
                row += 1

        self.status_label.configure(text=f"Found {len(processed)} matches")

    def set_card(self, card_id):
        pass
