"""
Training Event Timeline
View card events in a visual timeline showing choices and skill outcomes
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_cards, get_card_events
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_HEADER, FONT_SUBHEADER,
    FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    get_type_icon, get_type_color, get_rarity_color,
    create_styled_entry
)


class TrainingTimelineFrame(ctk.CTkFrame):
    """Event timeline view for a selected card"""

    def __init__(self, parent, navigate_to_card_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_to_card = navigate_to_card_callback
        self.selected_card_id = None
        self.all_cards = []
        self.event_widgets = []
        self._build_ui()
        self._load_cards()

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, SPACING_SM))

        ctk.CTkLabel(
            header, text="📅  Training Event Timeline",
            font=FONT_DISPLAY, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        # Card selector
        select_frame = ctk.CTkFrame(header, fg_color="transparent")
        select_frame.pack(side=tk.RIGHT)

        ctk.CTkLabel(
            select_frame, text="Card:",
            font=FONT_BODY_BOLD, text_color=TEXT_MUTED
        ).pack(side=tk.LEFT, padx=(0, SPACING_SM))

        self.card_search_var = tk.StringVar()
        self.card_search = create_styled_entry(
            select_frame, textvariable=self.card_search_var,
            placeholder_text="Search card..."
        )
        self.card_search.pack(side=tk.LEFT)
        self.card_search.configure(width=220, height=34)
        self.card_search.bind('<KeyRelease>', lambda e: self._filter_card_list())

        self.card_combo = ctk.CTkComboBox(
            select_frame, values=[], width=280, state='readonly',
            command=self._on_card_selected
        )
        self.card_combo.pack(side=tk.LEFT, padx=SPACING_SM)

        # Timeline content area
        self.timeline_scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        self.timeline_scroll.grid(row=1, column=0, sticky="nsew")

        # Default message
        self.empty_label = ctk.CTkLabel(
            self.timeline_scroll, text="Select a card to view its event timeline.",
            font=FONT_BODY, text_color=TEXT_MUTED
        )
        self.empty_label.pack(pady=SPACING_LG)

    def _load_cards(self):
        """Load all cards for the selector"""
        self.all_cards = get_all_cards()
        names = [f"{c[0]}: {c[1]}" for c in self.all_cards[:100]]
        self.card_combo.configure(values=names)

    def _filter_card_list(self):
        """Filter card combo based on search"""
        search = self.card_search_var.get().lower()
        if not search:
            names = [f"{c[0]}: {c[1]}" for c in self.all_cards[:100]]
        else:
            filtered = [c for c in self.all_cards if search in c[1].lower()]
            names = [f"{c[0]}: {c[1]}" for c in filtered[:50]]
        self.card_combo.configure(values=names)

    def _on_card_selected(self, value):
        """Handle card selection"""
        if not value:
            return
        card_id = int(value.split(':')[0])
        self.selected_card_id = card_id
        self._render_timeline(card_id)

    def _render_timeline(self, card_id):
        """Render the event timeline for a card"""
        for w in self.event_widgets:
            w.destroy()
        self.event_widgets.clear()

        if hasattr(self, 'empty_label') and self.empty_label:
            self.empty_label.pack_forget()

        try:
            events = get_card_events(card_id)
        except Exception:
            events = []

        if not events:
            lbl = ctk.CTkLabel(
                self.timeline_scroll,
                text="No events found for this card.\nEvent data may not have been scraped for this card.",
                font=FONT_BODY, text_color=TEXT_MUTED, justify="center"
            )
            lbl.pack(pady=SPACING_LG)
            self.event_widgets.append(lbl)
            return

        # Group events
        for idx, event in enumerate(events):
            event_name = event.get('name', f'Event {idx + 1}')
            choices = event.get('choices', [])

            # Event card
            card = ctk.CTkFrame(
                self.timeline_scroll, fg_color=BG_ELEVATED,
                corner_radius=RADIUS_MD, border_width=1, border_color=BG_LIGHT
            )
            card.pack(fill=tk.X, padx=SPACING_MD, pady=SPACING_XS)
            self.event_widgets.append(card)

            # Timeline dot + connector
            dot_frame = ctk.CTkFrame(card, fg_color="transparent", width=40)
            dot_frame.pack(side=tk.LEFT, fill=tk.Y, padx=SPACING_XS)

            dot = ctk.CTkFrame(
                dot_frame, fg_color=ACCENT_PRIMARY,
                width=12, height=12, corner_radius=6
            )
            dot.place(x=14, y=14)

            # Event content
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                        padx=SPACING_SM, pady=SPACING_SM)

            ctk.CTkLabel(
                content, text=event_name,
                font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, anchor="w"
            ).pack(fill=tk.X)

            if not choices:
                ctk.CTkLabel(
                    content, text="(No choice data)",
                    font=FONT_SMALL, text_color=TEXT_DISABLED, anchor="w"
                ).pack(fill=tk.X)
            else:
                for ci, choice in enumerate(choices):
                    choice_label = choice.get('label', f'Choice {ci + 1}')
                    effects = choice.get('effects', '')

                    choice_row = ctk.CTkFrame(content, fg_color=BG_MEDIUM, corner_radius=RADIUS_SM)
                    choice_row.pack(fill=tk.X, pady=2)

                    ctk.CTkLabel(
                        choice_row, text=f"  ➤ {choice_label}",
                        font=FONT_SMALL, text_color=ACCENT_INFO, anchor="w"
                    ).pack(side=tk.LEFT, padx=SPACING_XS, pady=SPACING_XS)

                    if effects:
                        ctk.CTkLabel(
                            choice_row, text=effects,
                            font=FONT_TINY, text_color=TEXT_MUTED, anchor="e"
                        ).pack(side=tk.RIGHT, padx=SPACING_SM, pady=SPACING_XS)

    def set_card(self, card_id):
        """Set card from external navigation"""
        self.selected_card_id = card_id
        self._render_timeline(card_id)
