"""
Card Upgrade Planner
Compare card effects at different levels to find optimal upgrade breakpoints
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_cards, get_effects_at_level
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_HEADER, FONT_SUBHEADER,
    FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
    get_type_icon, get_rarity_color,
    create_styled_button, create_styled_entry
)


class UpgradePlannerFrame(ctk.CTkFrame):
    """Compare card effects across levels to plan optimal upgrades"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.all_cards = []
        self.selected_card_id = None
        self.comparison_widgets = []
        self._build_ui()
        self._load_cards()

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, SPACING_SM))

        ctk.CTkLabel(
            header, text="📈  Upgrade Planner",
            font=FONT_DISPLAY, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        # Card selector
        select_frame = ctk.CTkFrame(header, fg_color="transparent")
        select_frame.pack(side=tk.RIGHT)

        self.card_search_var = tk.StringVar()
        self.card_search = create_styled_entry(
            select_frame, textvariable=self.card_search_var,
            placeholder_text="Search card..."
        )
        self.card_search.pack(side=tk.LEFT)
        self.card_search.configure(width=200, height=34)
        self.card_search.bind('<KeyRelease>', lambda e: self._filter_card_list())

        self.card_combo = ctk.CTkComboBox(
            select_frame, values=[], width=260, state='readonly',
            command=self._on_card_selected
        )
        self.card_combo.pack(side=tk.LEFT, padx=SPACING_SM)

        # Level selectors
        level_frame = ctk.CTkFrame(header, fg_color="transparent")
        level_frame.pack(side=tk.RIGHT, padx=SPACING_LG)

        ctk.CTkLabel(
            level_frame, text="Compare:",
            font=FONT_SMALL, text_color=TEXT_MUTED
        ).pack(side=tk.LEFT, padx=(0, SPACING_XS))

        all_levels = [str(l) for l in [20, 25, 30, 35, 40, 45, 50]]

        self.level_a_combo = ctk.CTkComboBox(
            level_frame, values=all_levels, width=70, state='readonly'
        )
        self.level_a_combo.pack(side=tk.LEFT, padx=2)
        self.level_a_combo.set("30")

        ctk.CTkLabel(
            level_frame, text="→",
            font=FONT_BODY_BOLD, text_color=TEXT_MUTED
        ).pack(side=tk.LEFT, padx=SPACING_XS)

        self.level_b_combo = ctk.CTkComboBox(
            level_frame, values=all_levels, width=70, state='readonly'
        )
        self.level_b_combo.pack(side=tk.LEFT, padx=2)
        self.level_b_combo.set("50")

        create_styled_button(
            level_frame, text="Compare",
            command=self._compare_levels,
            style_type='accent', width=90, height=34
        ).pack(side=tk.LEFT, padx=SPACING_SM)

        # Results area
        self.results_scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        self.results_scroll.grid(row=1, column=0, sticky="nsew")
        self.results_scroll.columnconfigure(0, weight=2)
        self.results_scroll.columnconfigure(1, weight=1)
        self.results_scroll.columnconfigure(2, weight=1)
        self.results_scroll.columnconfigure(3, weight=1)

        # Default message
        self.empty_label = ctk.CTkLabel(
            self.results_scroll,
            text="Select a card and click Compare to see effect differences between levels.",
            font=FONT_BODY, text_color=TEXT_MUTED
        )
        self.empty_label.pack(pady=SPACING_LG)

    def _load_cards(self):
        self.all_cards = get_all_cards()
        names = [f"{c[0]}: {c[1]} ({c[2]})" for c in self.all_cards[:100]]
        self.card_combo.configure(values=names)

    def _filter_card_list(self):
        search = self.card_search_var.get().lower()
        if not search:
            names = [f"{c[0]}: {c[1]} ({c[2]})" for c in self.all_cards[:100]]
        else:
            filtered = [c for c in self.all_cards if search in c[1].lower()]
            names = [f"{c[0]}: {c[1]} ({c[2]})" for c in filtered[:50]]
        self.card_combo.configure(values=names)

    def _on_card_selected(self, value):
        if not value:
            return
        self.selected_card_id = int(value.split(':')[0])

    def _parse_value(self, v):
        """Parse an effect value string to a float"""
        try:
            return float(str(v).replace('%', '').replace('+', ''))
        except (ValueError, AttributeError):
            return 0.0

    def _compare_levels(self):
        """Compare effects at two levels"""
        if not self.selected_card_id:
            return

        for w in self.comparison_widgets:
            w.destroy()
        self.comparison_widgets.clear()

        if hasattr(self, 'empty_label') and self.empty_label:
            self.empty_label.pack_forget()

        level_a = int(self.level_a_combo.get())
        level_b = int(self.level_b_combo.get())

        effects_a = get_effects_at_level(self.selected_card_id, level_a)
        effects_b = get_effects_at_level(self.selected_card_id, level_b)

        # Build effect maps
        map_a = {name: value for name, value in effects_a}
        map_b = {name: value for name, value in effects_b}

        all_names = sorted(set(list(map_a.keys()) + list(map_b.keys())))

        # Title
        title = ctk.CTkLabel(
            self.results_scroll,
            text=f"Comparing Lv{level_a} → Lv{level_b}",
            font=FONT_SUBHEADER, text_color=ACCENT_PRIMARY
        )
        title.pack(pady=(SPACING_MD, SPACING_SM))
        self.comparison_widgets.append(title)

        # Headers
        hdr_frame = ctk.CTkFrame(self.results_scroll, fg_color=BG_MEDIUM, corner_radius=RADIUS_SM)
        hdr_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_XS))
        self.comparison_widgets.append(hdr_frame)

        for text, w in [("Effect", 200), (f"Lv{level_a}", 100), (f"Lv{level_b}", 100), ("Change", 100)]:
            ctk.CTkLabel(
                hdr_frame, text=text, font=FONT_BODY_BOLD,
                text_color=TEXT_PRIMARY, width=w, anchor="w"
            ).pack(side=tk.LEFT, padx=SPACING_SM, pady=SPACING_XS)

        # Rows
        changes_found = 0
        for effect_name in all_names:
            if effect_name == "Unique Effect":
                continue

            val_a_str = map_a.get(effect_name, '-')
            val_b_str = map_b.get(effect_name, '-')
            val_a = self._parse_value(val_a_str)
            val_b = self._parse_value(val_b_str)
            diff = val_b - val_a

            is_pct = '%' in str(val_a_str) or '%' in str(val_b_str)

            if diff > 0:
                diff_color = ACCENT_SUCCESS
                diff_text = f"+{diff:.0f}{'%' if is_pct else ''}"
                changes_found += 1
            elif diff < 0:
                diff_color = ACCENT_ERROR
                diff_text = f"{diff:.0f}{'%' if is_pct else ''}"
                changes_found += 1
            else:
                diff_color = TEXT_DISABLED
                diff_text = "—"

            row = ctk.CTkFrame(self.results_scroll, fg_color="transparent")
            row.pack(fill=tk.X, padx=SPACING_MD, pady=1)
            self.comparison_widgets.append(row)

            ctk.CTkLabel(
                row, text=effect_name, font=FONT_BODY,
                text_color=TEXT_SECONDARY, width=200, anchor="w"
            ).pack(side=tk.LEFT, padx=SPACING_SM)

            ctk.CTkLabel(
                row, text=str(val_a_str), font=FONT_BODY,
                text_color=TEXT_MUTED, width=100, anchor="w"
            ).pack(side=tk.LEFT, padx=SPACING_SM)

            ctk.CTkLabel(
                row, text=str(val_b_str), font=FONT_BODY_BOLD,
                text_color=TEXT_PRIMARY, width=100, anchor="w"
            ).pack(side=tk.LEFT, padx=SPACING_SM)

            ctk.CTkLabel(
                row, text=diff_text, font=FONT_BODY_BOLD,
                text_color=diff_color, width=100, anchor="w"
            ).pack(side=tk.LEFT, padx=SPACING_SM)

        # Summary
        summary = ctk.CTkFrame(
            self.results_scroll, fg_color=BG_ELEVATED,
            corner_radius=RADIUS_MD, border_width=1, border_color=BG_LIGHT
        )
        summary.pack(fill=tk.X, padx=SPACING_MD, pady=SPACING_MD)
        self.comparison_widgets.append(summary)

        if changes_found > 0:
            ctk.CTkLabel(
                summary,
                text=f"✨ {changes_found} effect{'s' if changes_found != 1 else ''} change between Lv{level_a} and Lv{level_b}",
                font=FONT_BODY_BOLD, text_color=ACCENT_SUCCESS
            ).pack(padx=SPACING_LG, pady=SPACING_MD)
        else:
            ctk.CTkLabel(
                summary,
                text=f"No effect changes between Lv{level_a} and Lv{level_b}",
                font=FONT_BODY, text_color=TEXT_MUTED
            ).pack(padx=SPACING_LG, pady=SPACING_MD)

        # Unique effects
        for effects_list, lvl in [(effects_a, level_a), (effects_b, level_b)]:
            for name, value in effects_list:
                if name == "Unique Effect":
                    ue_frame = ctk.CTkFrame(
                        self.results_scroll, fg_color=BG_ELEVATED,
                        corner_radius=RADIUS_MD
                    )
                    ue_frame.pack(fill=tk.X, padx=SPACING_MD, pady=SPACING_XS)
                    self.comparison_widgets.append(ue_frame)
                    ctk.CTkLabel(
                        ue_frame, text=f"✨ Unique Effect (Lv{lvl}):",
                        font=FONT_BODY_BOLD, text_color=ACCENT_WARNING
                    ).pack(anchor="w", padx=SPACING_MD, pady=(SPACING_SM, 0))
                    ctk.CTkLabel(
                        ue_frame, text=str(value),
                        font=FONT_SMALL, text_color=TEXT_SECONDARY, wraplength=500
                    ).pack(anchor="w", padx=SPACING_MD, pady=(0, SPACING_SM))
                    break  # Only need one unique effect display per level
