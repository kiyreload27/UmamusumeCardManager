"""
Deck Comparison Dialog
Compare the combined effects of two decks side by side
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_decks, get_deck_cards, get_effects_at_level, get_deck_combined_effects
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
    create_styled_button
)


class DeckComparisonDialog(ctk.CTkToplevel):
    """Compare two decks side by side with effect diffs"""

    def __init__(self, parent, current_deck_id=None):
        super().__init__(parent)
        self.title("Deck Comparison")
        self.geometry("750x600")
        self.resizable(True, True)
        self.minsize(650, 500)

        self.transient(parent)
        self.grab_set()

        self.decks = get_all_decks()
        self.current_deck_id = current_deck_id
        self.comparison_widgets = []

        self._build_ui()
        self.after(100, self.lift)

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        header.pack(fill=tk.X)

        ctk.CTkLabel(
            header, text="⚖️  Deck Comparison",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(padx=SPACING_LG, pady=SPACING_LG)

        # Deck selectors
        selector = ctk.CTkFrame(self, fg_color="transparent")
        selector.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_MD)

        values = [f"{d[0]}: {d[1]}" for d in self.decks]

        # Deck A
        ctk.CTkLabel(selector, text="Deck A:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        self.deck_a_combo = ctk.CTkComboBox(selector, width=220, state='readonly', values=values)
        self.deck_a_combo.pack(side=tk.LEFT, padx=(SPACING_SM, SPACING_LG))

        ctk.CTkLabel(selector, text="vs", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=SPACING_SM)

        # Deck B
        ctk.CTkLabel(selector, text="Deck B:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(side=tk.LEFT, padx=(SPACING_LG, 0))
        self.deck_b_combo = ctk.CTkComboBox(selector, width=220, state='readonly', values=values)
        self.deck_b_combo.pack(side=tk.LEFT, padx=SPACING_SM)

        # Compare button
        create_styled_button(
            selector, text="Compare", command=self._compare,
            style_type='accent', width=90
        ).pack(side=tk.RIGHT)

        # Pre-select current deck
        if self.current_deck_id and values:
            for v in values:
                if v.startswith(f"{self.current_deck_id}:"):
                    self.deck_a_combo.set(v)
                    break
            if len(values) > 1:
                self.deck_b_combo.set(values[1] if values[0].startswith(f"{self.current_deck_id}:") else values[0])

        # Results scroll
        self.results_scroll = ctk.CTkScrollableFrame(self, fg_color=BG_DARK, corner_radius=RADIUS_LG)
        self.results_scroll.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))
        self.results_scroll.columnconfigure(0, weight=2)
        self.results_scroll.columnconfigure(1, weight=1)
        self.results_scroll.columnconfigure(2, weight=1)
        self.results_scroll.columnconfigure(3, weight=1)

    def _parse_effect_value(self, value_str):
        """Parse effect value string to float"""
        try:
            return float(str(value_str).replace('%', '').replace('+', ''))
        except (ValueError, AttributeError):
            return 0.0

    def _compare(self):
        """Perform the comparison"""
        for w in self.comparison_widgets:
            w.destroy()
        self.comparison_widgets.clear()

        val_a = self.deck_a_combo.get()
        val_b = self.deck_b_combo.get()

        if not val_a or not val_b:
            return

        deck_a_id = int(val_a.split(':')[0])
        deck_b_id = int(val_b.split(':')[0])

        effects_a = get_deck_combined_effects(deck_a_id)
        effects_b = get_deck_combined_effects(deck_b_id)

        # Merge all effect names
        all_effects = sorted(set(list(effects_a.keys()) + list(effects_b.keys())))

        # Table headers
        hdrs = ["Effect", "Deck A", "Deck B", "Diff"]
        for col, text in enumerate(hdrs):
            lbl = ctk.CTkLabel(
                self.results_scroll, text=text,
                font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY,
                fg_color=BG_MEDIUM, corner_radius=RADIUS_SM
            )
            lbl.grid(row=0, column=col, sticky="nsew", padx=1, pady=1, ipadx=SPACING_SM, ipady=SPACING_XS)
            self.comparison_widgets.append(lbl)

        for row_idx, effect_name in enumerate(all_effects, start=1):
            total_a = effects_a.get(effect_name, {}).get('total', 0)
            total_b = effects_b.get(effect_name, {}).get('total', 0)
            diff = total_b - total_a

            # Determine format
            is_pct = any('%' in str(v) for bd in [effects_a.get(effect_name, {}).get('breakdown', []),
                                                   effects_b.get(effect_name, {}).get('breakdown', [])]
                         for _, v in bd)

            fmt = lambda v: f"{v:.0f}%" if is_pct else f"{v:+.0f}" if v != 0 else "0"

            # Diff color
            if diff > 0:
                diff_color = ACCENT_SUCCESS
                diff_text = f"+{diff:.0f}{'%' if is_pct else ''}"
            elif diff < 0:
                diff_color = ACCENT_ERROR
                diff_text = f"{diff:.0f}{'%' if is_pct else ''}"
            else:
                diff_color = TEXT_DISABLED
                diff_text = "—"

            row_bg = BG_DARK if row_idx % 2 == 0 else "transparent"

            # Name
            lbl_name = ctk.CTkLabel(
                self.results_scroll, text=effect_name,
                font=FONT_BODY, text_color=TEXT_SECONDARY, anchor="w"
            )
            lbl_name.grid(row=row_idx, column=0, sticky="nsew", padx=SPACING_SM, pady=1)
            self.comparison_widgets.append(lbl_name)

            # Deck A value
            lbl_a = ctk.CTkLabel(
                self.results_scroll, text=fmt(total_a),
                font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY
            )
            lbl_a.grid(row=row_idx, column=1, sticky="nsew", padx=SPACING_SM, pady=1)
            self.comparison_widgets.append(lbl_a)

            # Deck B value
            lbl_b = ctk.CTkLabel(
                self.results_scroll, text=fmt(total_b),
                font=FONT_BODY_BOLD, text_color=ACCENT_SECONDARY
            )
            lbl_b.grid(row=row_idx, column=2, sticky="nsew", padx=SPACING_SM, pady=1)
            self.comparison_widgets.append(lbl_b)

            # Diff
            lbl_diff = ctk.CTkLabel(
                self.results_scroll, text=diff_text,
                font=FONT_BODY_BOLD, text_color=diff_color
            )
            lbl_diff.grid(row=row_idx, column=3, sticky="nsew", padx=SPACING_SM, pady=1)
            self.comparison_widgets.append(lbl_diff)


def show_deck_comparison(parent, current_deck_id=None):
    """Open the deck comparison dialog"""
    DeckComparisonDialog(parent, current_deck_id)
