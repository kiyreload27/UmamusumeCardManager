"""
Collection Progress Dashboard
Visual overview of card collection with progress bars, stats, and quick actions
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_database_stats, get_owned_count, get_collection_stats
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER,
    FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    RARITY_COLORS, TYPE_COLORS, get_type_icon,
    create_styled_button
)


class CollectionDashboard(ctk.CTkFrame):
    """Collection progress dashboard with visual stats and progress bars"""

    def __init__(self, parent, navigate_to_cards_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_to_cards = navigate_to_cards_callback
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Scrollable content
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill=tk.BOTH, expand=True)

        # Header
        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.pack(fill=tk.X, pady=(0, SPACING_LG), padx=SPACING_MD)

        ctk.CTkLabel(
            header, text="📊  Collection Dashboard",
            font=FONT_DISPLAY, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        if self.navigate_to_cards:
            create_styled_button(
                header, text="📋 Browse Cards",
                command=self.navigate_to_cards,
                style_type='accent', height=36, width=140
            ).pack(side=tk.RIGHT)

        # === Top Stats Row ===
        self.top_stats_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.top_stats_frame.pack(fill=tk.X, pady=(0, SPACING_XL), padx=SPACING_MD)

        # === Two Column Layout below top stats ===
        self.columns_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.columns_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING_MD)
        self.columns_frame.columnconfigure(0, weight=1)
        self.columns_frame.columnconfigure(1, weight=1)

        # Left Column: Rarity Breakdown
        self.rarity_section = ctk.CTkFrame(
            self.columns_frame, fg_color=BG_DARK,
            corner_radius=RADIUS_LG, border_width=1, border_color=BG_LIGHT
        )
        self.rarity_section.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING_MD))

        # Right Column: Type Breakdown
        self.type_section = ctk.CTkFrame(
            self.columns_frame, fg_color=BG_DARK,
            corner_radius=RADIUS_LG, border_width=1, border_color=BG_LIGHT
        )
        self.type_section.grid(row=0, column=1, sticky="nsew")

    def refresh(self):
        """Refresh all dashboard data"""
        try:
            stats = get_collection_stats()
        except Exception:
            stats = self._fallback_stats()

        self._render_top_stats(stats)
        self._render_rarity_bars(stats)
        self._render_type_bars(stats)

    def _fallback_stats(self):
        """Build stats from basic queries when get_collection_stats isn't available"""
        db_stats = get_database_stats()
        owned = get_owned_count()
        total = db_stats.get('total_cards', 0)
        by_rarity = db_stats.get('by_rarity', {})

        return {
            'total': total,
            'owned': owned,
            'by_rarity': {r: {'total': c, 'owned': 0} for r, c in by_rarity.items()},
            'by_type': {}
        }

    def _render_top_stats(self, stats):
        """Render the top stats cards using large metrics"""
        for w in self.top_stats_frame.winfo_children():
            w.destroy()

        self.top_stats_frame.columnconfigure((0,1,2,3), weight=1)

        total = stats.get('total', 0)
        owned = stats.get('owned', 0)
        pct = (owned / total * 100) if total > 0 else 0

        stat_data = [
            ("📋", "Total Cards", str(total), TEXT_PRIMARY),
            ("✅", "Owned", str(owned), ACCENT_SUCCESS),
            ("📈", "Completion", f"{pct:.1f}%", ACCENT_PRIMARY),
            ("❌", "Missing", str(total - owned), ACCENT_ERROR),
        ]

        for i, (icon, label, value, color) in enumerate(stat_data):
            card = ctk.CTkFrame(
                self.top_stats_frame, fg_color=BG_DARK,
                corner_radius=RADIUS_LG, border_width=1, border_color=BG_LIGHT
            )
            card.grid(row=0, column=i, sticky="nsew", padx=SPACING_SM)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(padx=SPACING_LG, pady=SPACING_LG, expand=True)

            ctk.CTkLabel(
                inner, text=icon, font=FONT_DISPLAY, text_color=color
            ).pack(anchor="center", pady=(0, SPACING_XS))

            ctk.CTkLabel(
                inner, text=value, font=FONT_DISPLAY, text_color=TEXT_PRIMARY
            ).pack(anchor="center")

            ctk.CTkLabel(
                inner, text=label, font=FONT_SMALL, text_color=TEXT_MUTED
            ).pack(anchor="center", pady=(SPACING_XS, 0))

    def _render_rarity_bars(self, stats):
        """Render rarity breakdown using circular progress rings"""
        for w in self.rarity_section.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.rarity_section, text="  ⭐  By Rarity",
            font=FONT_SUBHEADER, text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=SPACING_LG, pady=(SPACING_LG, SPACING_SM))

        rings_container = ctk.CTkFrame(self.rarity_section, fg_color="transparent")
        rings_container.pack(fill=tk.BOTH, expand=True, pady=SPACING_MD)
        rings_container.columnconfigure((0,1,2), weight=1)

        by_rarity = stats.get('by_rarity', {})
        for i, rarity in enumerate(['SSR', 'SR', 'R']):
            data = by_rarity.get(rarity, {'total': 0, 'owned': 0})
            total = data.get('total', 0)
            owned = data.get('owned', 0)
            pct = (owned / total * 100) if total > 0 else 0
            color = RARITY_COLORS.get(rarity, TEXT_MUTED)

            ring_frame = ctk.CTkFrame(rings_container, fg_color="transparent")
            ring_frame.grid(row=0, column=i, sticky="nsew")

            canvas_size = 120
            thickness = 12
            canvas = tk.Canvas(
                ring_frame, width=canvas_size, height=canvas_size,
                bg=BG_DARK, highlightthickness=0
            )
            canvas.pack()

            # Background ring
            canvas.create_oval(
                thickness, thickness, canvas_size-thickness, canvas_size-thickness,
                outline=BG_MEDIUM, width=thickness
            )

            # Foreground ring
            extent = -(pct / 100) * 360
            if extent != 0:
                canvas.create_arc(
                    thickness, thickness, canvas_size-thickness, canvas_size-thickness,
                    start=90, extent=extent, outline=color, style=tk.ARC, width=thickness
                )

            # Center text
            ctk.CTkLabel(ring_frame, text=rarity, font=FONT_TITLE, text_color=color).place(relx=0.5, rely=0.42, anchor="center")
            ctk.CTkLabel(ring_frame, text=f"{pct:.0f}%", font=FONT_TINY, text_color=TEXT_MUTED).place(relx=0.5, rely=0.6, anchor="center")

            # Footnote
            ctk.CTkLabel(
                ring_frame, text=f"{owned} / {total}",
                font=FONT_SMALL, text_color=TEXT_SECONDARY
            ).pack(pady=(SPACING_SM, 0))

        # Bottom padding
        ctk.CTkFrame(self.rarity_section, fg_color="transparent", height=SPACING_MD).pack()

    def _render_type_bars(self, stats):
        """Render type breakdown progress bars"""
        for w in self.type_section.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.type_section, text="  🎯  By Type",
            font=FONT_SUBHEADER, text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=SPACING_LG, pady=(SPACING_LG, SPACING_SM))

        by_type = stats.get('by_type', {})
        for card_type in ['Speed', 'Stamina', 'Power', 'Guts', 'Wisdom', 'Friend', 'Group']:
            data = by_type.get(card_type, {'total': 0, 'owned': 0})
            total = data.get('total', 0)
            owned = data.get('owned', 0)
            if total == 0:
                continue
            pct = (owned / total * 100) if total > 0 else 0
            color = TYPE_COLORS.get(card_type, TEXT_MUTED)
            icon = get_type_icon(card_type)

            row = ctk.CTkFrame(self.type_section, fg_color="transparent")
            row.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_XS)

            ctk.CTkLabel(
                row, text=f"{icon} {card_type}", font=FONT_BODY,
                text_color=TEXT_SECONDARY, width=90, anchor="w"
            ).pack(side=tk.LEFT)

            ctk.CTkLabel(
                row, text=f"{owned}/{total}",
                font=FONT_SMALL, text_color=TEXT_MUTED, width=60
            ).pack(side=tk.RIGHT)

            ctk.CTkLabel(
                row, text=f"{pct:.0f}%",
                font=FONT_TINY, text_color=TEXT_DISABLED, width=40
            ).pack(side=tk.RIGHT)

            track = ctk.CTkFrame(row, fg_color=BG_MEDIUM, corner_radius=4, height=10)
            track.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=SPACING_SM)
            track.pack_propagate(False)

            fill_w = max(1, int(pct)) if total > 0 else 0
            if fill_w > 0:
                fill = ctk.CTkFrame(track, fg_color=color, corner_radius=4)
                fill.place(relwidth=fill_w / 100, relheight=1.0)

        ctk.CTkFrame(self.type_section, fg_color="transparent", height=SPACING_MD).pack()
