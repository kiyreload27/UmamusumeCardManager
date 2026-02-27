"""
Race View - Browse races with filtering and detail panel
2-panel layout: Filterable Race List (Treeview) | Race Detail
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
    create_styled_entry, create_styled_button, create_card_frame
)

# Grade colors and icons
GRADE_COLORS = {
    'GI': '#FFD700', 'G1': '#FFD700',
    'GII': '#C0C0C0', 'G2': '#C0C0C0',
    'GIII': '#CD853F', 'G3': '#CD853F',
    'OP': '#54A0FF',
    'Pre-OP': '#5F27CD',
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
    """Race browser with filterable Treeview list and detail panel"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.races = []           # all races from DB
        self.filtered_races = []  # currently displayed subset
        self.current_race = None
        self.search_var = tk.StringVar()
        self._search_after_id = None  # for debounce

        self.create_widgets()
        self.load_races()

    # ──────────────────────────────────────────────
    # Widget creation
    # ──────────────────────────────────────────────

    def create_widgets(self):
        """Build the 2-panel layout"""
        self.columnconfigure(0, weight=3, minsize=600)
        self.columnconfigure(1, weight=2, minsize=350)
        self.rowconfigure(0, weight=1)

        # ─── LEFT PANEL: Race List ───
        left_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=12)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        left_frame.rowconfigure(3, weight=1)
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

        # Search bar (debounced)
        search_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        search_frame.columnconfigure(0, weight=1)

        search_entry = create_styled_entry(search_frame, textvariable=self.search_var,
                                            placeholder_text="🔍 Search races...")
        search_entry.grid(row=0, column=0, sticky="ew")
        search_entry.bind('<KeyRelease>', self._on_search_key)

        # Filter row using segmented buttons (no Toplevel popups)
        filter_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        filter_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        filter_frame.columnconfigure(0, weight=1)

        # Grade filter
        grade_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        grade_row.pack(fill=tk.X, pady=(0, 3))
        ctk.CTkLabel(grade_row, text="Grade:", font=FONT_TINY,
                     text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 5))
        self.grade_seg = ctk.CTkSegmentedButton(
            grade_row, values=["All", "GI", "GII", "GIII", "OP", "Pre-OP"],
            command=lambda _: self.apply_filters(),
            font=FONT_TINY, height=26
        )
        self.grade_seg.set("All")
        self.grade_seg.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Terrain + Distance row
        td_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        td_row.pack(fill=tk.X)

        ctk.CTkLabel(td_row, text="Terrain:", font=FONT_TINY,
                     text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 5))
        self.terrain_seg = ctk.CTkSegmentedButton(
            td_row, values=["All", "Turf", "Dirt"],
            command=lambda _: self.apply_filters(),
            font=FONT_TINY, height=26, width=120
        )
        self.terrain_seg.set("All")
        self.terrain_seg.pack(side=tk.LEFT, padx=(0, 10))

        ctk.CTkLabel(td_row, text="Dist:", font=FONT_TINY,
                     text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 5))
        self.distance_seg = ctk.CTkSegmentedButton(
            td_row, values=["All", "Short", "Mile", "Medium", "Long"],
            command=lambda _: self.apply_filters(),
            font=FONT_TINY, height=26
        )
        self.distance_seg.set("All")
        self.distance_seg.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Treeview for race list
        tree_container = ctk.CTkFrame(left_frame, fg_color="transparent")
        tree_container.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        self.tree = ttk.Treeview(
            tree_container,
            columns=('grade', 'name', 'track', 'terrain', 'distance'),
            show='headings',
            selectmode='browse',
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.tree.yview)

        self.tree.heading('grade', text='Grade', command=lambda: self._sort_column('grade'))
        self.tree.heading('name', text='Race', anchor='w', command=lambda: self._sort_column('name'))
        self.tree.heading('track', text='Track', anchor='w', command=lambda: self._sort_column('track'))
        self.tree.heading('terrain', text='Terrain', command=lambda: self._sort_column('terrain'))
        self.tree.heading('distance', text='Distance', command=lambda: self._sort_column('distance'))

        self.tree.column('grade', width=70, anchor='center')
        self.tree.column('name', width=220, minwidth=150)
        self.tree.column('track', width=130, minwidth=80)
        self.tree.column('terrain', width=70, anchor='center')
        self.tree.column('distance', width=80, anchor='center')

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # Tag colours for grades
        self.tree.tag_configure('GI', foreground='#FFD700')
        self.tree.tag_configure('G1', foreground='#FFD700')
        self.tree.tag_configure('GII', foreground='#C0C0C0')
        self.tree.tag_configure('G2', foreground='#C0C0C0')
        self.tree.tag_configure('GIII', foreground='#CD853F')
        self.tree.tag_configure('G3', foreground='#CD853F')
        self.tree.tag_configure('OP', foreground='#54A0FF')
        self.tree.tag_configure('Pre-OP', foreground='#5F27CD')

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

        # Sort state
        self._sort_col = None
        self._sort_reverse = False

    # ──────────────────────────────────────────────
    # Data loading and filtering
    # ──────────────────────────────────────────────

    def load_races(self):
        """Load all races from DB once"""
        self.races = get_all_races()
        self.filtered_races = list(self.races)
        self.count_label.configure(text=f"{len(self.races)} races")
        self._populate_tree(self.filtered_races)

    def _on_search_key(self, event=None):
        """Debounced search — waits 300ms after last keystroke"""
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, self.apply_filters)

    def apply_filters(self):
        """Filter the in-memory race list and repopulate Treeview"""
        self._search_after_id = None
        search = self.search_var.get().strip().lower()
        grade = self.grade_seg.get()
        terrain = self.terrain_seg.get()
        distance = self.distance_seg.get()

        filtered = []
        for r in self.races:
            # r: (race_id, name_en, name_jp, grade, racetrack, direction,
            #     participants, terrain, distance_type, distance_meters,
            #     season, time_of_day, race_date, race_class)
            if grade != "All" and (r[3] or "") != grade:
                continue
            if terrain != "All" and (r[7] or "") != terrain:
                continue
            if distance != "All" and (r[8] or "") != distance:
                continue
            if search:
                haystack = f"{r[1] or ''} {r[2] or ''} {r[4] or ''}".lower()
                if search not in haystack:
                    continue
            filtered.append(r)

        self.filtered_races = filtered
        self.count_label.configure(text=f"{len(filtered)} races")
        self._populate_tree(filtered)

    def _populate_tree(self, races):
        """Insert rows into the Treeview"""
        self.tree.delete(*self.tree.get_children())
        for race in races:
            race_id = race[0]
            name = race[1] or race[2] or ""
            grade = race[3] or ""
            track = race[4] or ""
            terrain = race[7] or ""
            dist_m = race[9]
            dist_text = f"{dist_m}m" if dist_m else (race[8] or "")

            tag = grade if grade in GRADE_COLORS else ''
            self.tree.insert('', tk.END, iid=str(race_id),
                             values=(grade, name, track, terrain, dist_text),
                             tags=(tag,))

    def _sort_column(self, col):
        """Sort Treeview by clicking a column header"""
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        col_map = {'grade': 3, 'name': 1, 'track': 4, 'terrain': 7, 'distance': 9}
        idx = col_map.get(col, 1)

        def sort_key(r):
            val = r[idx]
            if val is None:
                return ""
            if isinstance(val, int):
                return val
            return str(val).lower()

        self.filtered_races.sort(key=sort_key, reverse=self._sort_reverse)
        self._populate_tree(self.filtered_races)

    # ──────────────────────────────────────────────
    # Selection & detail
    # ──────────────────────────────────────────────

    def _on_tree_select(self, event=None):
        """Handle Treeview row selection"""
        sel = self.tree.selection()
        if not sel:
            return
        race_id = int(sel[0])
        # Find the race data
        for r in self.filtered_races:
            if r[0] == race_id:
                self.select_race(r)
                break

    def select_race(self, race_data):
        """Show full detail for a selected race"""
        self.current_race = race_data

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
        section = create_card_frame(self.detail_frame)
        section.pack(fill=tk.X, padx=10, pady=6)
        section.columnconfigure(1, weight=1)

        # Section title
        ctk.CTkLabel(section, text=title, font=FONT_SUBHEADER,
                     text_color=ACCENT_TERTIARY).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 5))

        for idx, (label, value) in enumerate(rows):
            row_num = idx + 1

            ctk.CTkLabel(section, text=label, font=FONT_BODY,
                         text_color=TEXT_MUTED).grid(
                row=row_num, column=0, sticky="w", padx=(12, 10), pady=4)

            ctk.CTkLabel(section, text=str(value), font=FONT_BODY_BOLD,
                         text_color=TEXT_PRIMARY).grid(
                row=row_num, column=1, sticky="e", padx=(10, 12), pady=4)

        # Bottom padding
        ctk.CTkFrame(section, height=8, fg_color="transparent").grid(
            row=len(rows) + 1, column=0, columnspan=2)
