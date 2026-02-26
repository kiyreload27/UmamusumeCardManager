"""
Race View - Browse races with filtering and detail panel
2-panel layout: Filterable Race List | Race Detail
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_races, get_race_count
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY,
    create_styled_entry, create_styled_button
)

# Grade colors and icons
GRADE_COLORS = {
    'GI': '#FFD700',      # Gold
    'G1': '#FFD700',
    'GII': '#C0C0C0',     # Silver
    'G2': '#C0C0C0',
    'GIII': '#CD853F',    # Bronze
    'G3': '#CD853F',
    'OP': '#54A0FF',      # Blue
    'Pre-OP': '#5F27CD',  # Purple
}

GRADE_BADGES = {
    'GI': '🥇', 'G1': '🥇',
    'GII': '🥈', 'G2': '🥈',
    'GIII': '🥉', 'G3': '🥉',
    'OP': '🔵', 'Pre-OP': '🟣',
}

TERRAIN_COLORS = {
    'Turf': '#22c55e',
    'Dirt': '#d97706',
}

TERRAIN_ICONS = {
    'Turf': '🌿',
    'Dirt': '🟤',
}

DISTANCE_COLORS = {
    'Short': '#ef4444',
    'Mile': '#f97316',
    'Medium': '#eab308',
    'Long': '#3b82f6',
}


class RaceViewFrame(ctk.CTkFrame):
    """Race browser with filterable list and detail panel"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.races = []
        self.current_race = None
        self.search_var = tk.StringVar()
        self.grade_var = tk.StringVar(value="All")
        self.terrain_var = tk.StringVar(value="All")
        self.distance_var = tk.StringVar(value="All")

        self.search_var.trace_add('write', lambda *a: self.filter_races())

        self.create_widgets()
        self.load_races()

    def create_widgets(self):
        """Build the 2-panel layout"""
        self.columnconfigure(0, weight=3, minsize=600)
        self.columnconfigure(1, weight=2, minsize=350)
        self.rowconfigure(0, weight=1)

        # ─── LEFT PANEL: Race List ───
        left_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=12)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        left_frame.rowconfigure(2, weight=1)
        left_frame.columnconfigure(0, weight=1)

        # Header
        header_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="🏁 Races", font=FONT_HEADER,
                     text_color=ACCENT_PRIMARY).grid(row=0, column=0, sticky="w")

        self.count_label = ctk.CTkLabel(header_frame, text="0 races", font=FONT_SMALL,
                                         text_color=TEXT_MUTED)
        self.count_label.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # Search and filters row
        filter_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        filter_frame.columnconfigure(0, weight=1)

        search_entry = create_styled_entry(filter_frame, textvariable=self.search_var,
                                            placeholder_text="🔍 Search races...")
        search_entry.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Filter buttons row
        btn_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew")

        # Grade filter
        ctk.CTkLabel(btn_frame, text="Grade:", font=FONT_TINY,
                     text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 3))
        grade_menu = ctk.CTkOptionMenu(
            btn_frame, values=["All", "GI", "GII", "GIII", "OP", "Pre-OP"],
            variable=self.grade_var, command=lambda _: self.filter_races(),
            width=80, height=26, font=FONT_TINY
        )
        grade_menu.pack(side=tk.LEFT, padx=(0, 8))

        # Terrain filter
        ctk.CTkLabel(btn_frame, text="Terrain:", font=FONT_TINY,
                     text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 3))
        terrain_menu = ctk.CTkOptionMenu(
            btn_frame, values=["All", "Turf", "Dirt"],
            variable=self.terrain_var, command=lambda _: self.filter_races(),
            width=70, height=26, font=FONT_TINY
        )
        terrain_menu.pack(side=tk.LEFT, padx=(0, 8))

        # Distance filter
        ctk.CTkLabel(btn_frame, text="Distance:", font=FONT_TINY,
                     text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 3))
        distance_menu = ctk.CTkOptionMenu(
            btn_frame, values=["All", "Short", "Mile", "Medium", "Long"],
            variable=self.distance_var, command=lambda _: self.filter_races(),
            width=80, height=26, font=FONT_TINY
        )
        distance_menu.pack(side=tk.LEFT)

        # Scrollable race list
        self.race_scroll = ctk.CTkScrollableFrame(left_frame, fg_color=BG_DARK,
                                                    corner_radius=0)
        self.race_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.race_scroll.columnconfigure(0, weight=1)

        # ─── RIGHT PANEL: Race Detail ───
        self.detail_frame = ctk.CTkScrollableFrame(self, fg_color=BG_MEDIUM, corner_radius=12)
        self.detail_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        self.detail_frame.columnconfigure(0, weight=1)

        # Empty state
        self.empty_label = ctk.CTkLabel(
            self.detail_frame,
            text="← Select a race\nto see full details",
            font=FONT_BODY,
            text_color=TEXT_MUTED,
            justify="center"
        )
        self.empty_label.pack(expand=True, pady=100)

    def load_races(self):
        """Load all races from DB"""
        self.races = get_all_races()
        self.count_label.configure(text=f"{len(self.races)} races")
        self.render_race_list(self.races)

    def filter_races(self):
        """Filter races by search/grade/terrain/distance"""
        search = self.search_var.get().strip() or None
        grade = self.grade_var.get()
        terrain = self.terrain_var.get()
        distance = self.distance_var.get()

        filtered = get_all_races(
            search_term=search,
            grade_filter=grade if grade != "All" else None,
            terrain_filter=terrain if terrain != "All" else None,
            distance_filter=distance if distance != "All" else None,
        )
        self.count_label.configure(text=f"{len(filtered)} races")
        self.render_race_list(filtered)

    def render_race_list(self, races):
        """Render race cards in the list"""
        for widget in self.race_scroll.winfo_children():
            widget.destroy()

        if not races:
            ctk.CTkLabel(
                self.race_scroll,
                text="No races found.\n\nRun the race scraper:\npython main.py --scrape-races",
                font=FONT_BODY,
                text_color=TEXT_MUTED,
                justify="center"
            ).pack(pady=50)
            return

        for idx, race in enumerate(races):
            self._create_race_card(race, idx)

    def _create_race_card(self, race_data, idx):
        """Create a single race card in the list"""
        # race_data: (race_id, name_en, name_jp, grade, racetrack, direction,
        #             participants, terrain, distance_type, distance_meters,
        #             season, time_of_day, race_date, race_class)
        race_id = race_data[0]
        name_en = race_data[1] or ""
        name_jp = race_data[2] or ""
        grade = race_data[3] or ""
        racetrack = race_data[4] or ""
        terrain = race_data[7] or ""
        distance_type = race_data[8] or ""
        distance_meters = race_data[9]

        # Card frame
        card = ctk.CTkFrame(self.race_scroll, fg_color=BG_MEDIUM, corner_radius=8,
                            cursor="hand2", height=65)
        card.pack(fill=tk.X, padx=4, pady=2)
        card.pack_propagate(False)

        # Content layout: [Grade Badge] [Name + Track] [Distance badge] [Terrain badge]
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        inner.columnconfigure(1, weight=1)

        # Grade badge
        grade_color = GRADE_COLORS.get(grade, TEXT_MUTED)
        grade_icon = GRADE_BADGES.get(grade, '🏁')
        grade_label = ctk.CTkLabel(inner, text=f"{grade_icon}", font=("Segoe UI", 18))
        grade_label.grid(row=0, column=0, rowspan=2, padx=(0, 8), sticky="w")

        # Name
        display_name = name_en if name_en else name_jp
        ctk.CTkLabel(inner, text=display_name, font=FONT_BODY_BOLD,
                     text_color=TEXT_PRIMARY, anchor="w").grid(
            row=0, column=1, sticky="ew")

        # Subtitle: Racetrack + Class info
        subtitle_parts = []
        if racetrack:
            subtitle_parts.append(racetrack)
        if race_data[13]:  # race_class
            subtitle_parts.append(race_data[13])
        subtitle = " • ".join(subtitle_parts) if subtitle_parts else ""
        ctk.CTkLabel(inner, text=subtitle, font=FONT_TINY,
                     text_color=TEXT_MUTED, anchor="w").grid(
            row=1, column=1, sticky="ew")

        # Right side badges
        badge_frame = ctk.CTkFrame(inner, fg_color="transparent")
        badge_frame.grid(row=0, column=2, rowspan=2, padx=(5, 0), sticky="e")

        # Terrain badge
        terrain_icon = TERRAIN_ICONS.get(terrain, '')
        terrain_color = TERRAIN_COLORS.get(terrain, TEXT_MUTED)
        if terrain:
            ctk.CTkLabel(badge_frame, text=f"{terrain_icon}{terrain}",
                         font=FONT_TINY, text_color=terrain_color).pack(
                side=tk.LEFT, padx=3)

        # Distance badge
        dist_color = DISTANCE_COLORS.get(distance_type, TEXT_SECONDARY)
        dist_text = f"{distance_meters}m" if distance_meters else distance_type
        if dist_text:
            ctk.CTkLabel(badge_frame, text=dist_text, font=FONT_TINY,
                         text_color=dist_color, fg_color=BG_DARK,
                         corner_radius=4, height=20, width=55).pack(
                side=tk.LEFT, padx=3)

        # Grade text
        if grade:
            ctk.CTkLabel(badge_frame, text=grade, font=FONT_TINY,
                         text_color=grade_color, fg_color=BG_DARK,
                         corner_radius=4, height=20, width=45).pack(
                side=tk.LEFT, padx=3)

        # Click handler
        def on_click(e, data=race_data):
            self.select_race(data)

        card.bind("<Button-1>", on_click)
        for child in card.winfo_children():
            child.bind("<Button-1>", on_click)
            for gc in child.winfo_children():
                gc.bind("<Button-1>", on_click)
                for ggc in gc.winfo_children():
                    ggc.bind("<Button-1>", on_click)

        # Hover effects
        def on_enter(e):
            card.configure(fg_color=BG_LIGHT)
        def on_leave(e):
            card.configure(fg_color=BG_MEDIUM)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def select_race(self, race_data):
        """Show full detail for a selected race"""
        # Clear detail panel
        for widget in self.detail_frame.winfo_children():
            widget.destroy()

        name_en = race_data[1] or ""
        name_jp = race_data[2] or ""
        grade = race_data[3] or ""
        racetrack = race_data[4] or ""
        direction = race_data[5] or ""
        participants = race_data[6]
        terrain = race_data[7] or ""
        distance_type = race_data[8] or ""
        distance_meters = race_data[9]
        season = race_data[10] or ""
        time_of_day = race_data[11] or ""
        race_date = race_data[12] or ""
        race_class = race_data[13] or ""

        # ── Header ──
        header = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        header.pack(fill=tk.X, padx=15, pady=(15, 5))

        grade_icon = GRADE_BADGES.get(grade, '🏁')
        grade_color = GRADE_COLORS.get(grade, TEXT_PRIMARY)

        ctk.CTkLabel(header, text=f"{grade_icon} {grade}", font=FONT_TITLE,
                     text_color=grade_color).pack(anchor="w")

        display_name = name_en if name_en else name_jp
        ctk.CTkLabel(header, text=display_name, font=FONT_HEADER,
                     text_color=TEXT_PRIMARY).pack(anchor="w", pady=(2, 0))

        if name_jp and name_en:
            ctk.CTkLabel(header, text=name_jp, font=FONT_SMALL,
                         text_color=TEXT_MUTED).pack(anchor="w")

        # ── Divider ──
        ctk.CTkFrame(self.detail_frame, height=2, fg_color=BG_LIGHT).pack(
            fill=tk.X, padx=15, pady=10)

        # ── Race Info Section ──
        detail_rows = []
        if racetrack:
            detail_rows.append(('🏟️ Racetrack', racetrack))
        if race_class:
            detail_rows.append(('📋 Class', race_class))
        if race_date:
            detail_rows.append(('📅 Date', race_date))
        if terrain:
            terrain_icon = TERRAIN_ICONS.get(terrain, '')
            detail_rows.append((f'{terrain_icon} Terrain', terrain))
        if distance_type:
            detail_rows.append(('📏 Distance Type', distance_type))
        if distance_meters:
            detail_rows.append(('📐 Distance', f'{distance_meters} m'))
        if direction:
            dir_icons = {'Left': '↰', 'Right': '↱', 'Straight': '↑'}
            dir_icon = dir_icons.get(direction, '↔')
            detail_rows.append((f'{dir_icon} Direction', direction))
        if participants:
            detail_rows.append(('👥 Participants', str(participants)))
        if season:
            season_icons = {'Spring': '🌸', 'Summer': '☀️', 'Autumn': '🍂', 'Winter': '❄️'}
            s_icon = season_icons.get(season, '🗓️')
            detail_rows.append((f'{s_icon} Season', season))
        if time_of_day:
            tod_icons = {'Day': '☀️', 'Evening': '🌅', 'Night': '🌙'}
            t_icon = tod_icons.get(time_of_day, '⏰')
            detail_rows.append((f'{t_icon} Time', time_of_day))

        self._add_detail_section("Race Details", detail_rows)

    def _add_detail_section(self, title, rows):
        """Add a styled section card to the detail panel"""
        section = ctk.CTkFrame(self.detail_frame, fg_color=BG_DARK, corner_radius=10)
        section.pack(fill=tk.X, padx=10, pady=5)
        section.columnconfigure(1, weight=1)

        # Section title
        ctk.CTkLabel(section, text=title, font=FONT_SUBHEADER,
                     text_color=ACCENT_TERTIARY).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 5))

        for idx, (label, value) in enumerate(rows):
            row_num = idx + 1

            # Label
            ctk.CTkLabel(section, text=label, font=FONT_BODY,
                         text_color=TEXT_MUTED).grid(
                row=row_num, column=0, sticky="w", padx=(12, 10), pady=4)

            # Value
            ctk.CTkLabel(section, text=str(value), font=FONT_BODY_BOLD,
                         text_color=TEXT_PRIMARY).grid(
                row=row_num, column=1, sticky="e", padx=(10, 12), pady=4)

        # Bottom padding
        ctk.CTkFrame(section, height=8, fg_color="transparent").grid(
            row=len(rows) + 1, column=0, columnspan=2)
