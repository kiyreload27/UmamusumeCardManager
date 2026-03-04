"""
Race Calendar View - Combined character selection and race suggestion calendar
Premium redesign with grade-colored slots, aptitude badges, and visual calendar grid
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os
import math
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_characters, get_all_races
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    GRADE_COLORS,
    create_styled_entry, create_styled_button, create_card_frame
)
from utils import resolve_image_path
from PIL import Image

# Calendar structure
YEARS = ["Junior Year", "Classic Year", "Senior Year"]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
HALF_MONTHS = ["First Half", "Second Half"]

# Aptitude grade colors
GRADE_RANK_COLORS = {
    'S': '#fbbf24', 'A': '#34d399', 'B': '#60a5fa',
    'C': '#94a3b8', 'D': '#f97316', 'E': '#f87171',
    'F': '#ef4444', 'G': '#991b1b'
}


def format_half_month(month, half):
    return f"{month}, {half}"


class CharacterSelectionDialog(ctk.CTkToplevel):
    """Modal dialog for selecting a character via image grid"""
    def __init__(self, parent, characters, icon_cache, on_select_callback):
        super().__init__(parent)
        self.title("Select Character")
        self.geometry("660x520")
        self.transient(parent)
        self.grab_set()

        self.on_select_callback = on_select_callback
        self.characters = characters
        self.icon_cache = icon_cache

        self.configure(fg_color=BG_DARK)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_LG)

        ctk.CTkLabel(
            hdr, text="👤  Choose a Character",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        # Search
        self.search_var = tk.StringVar()
        search = ctk.CTkEntry(
            hdr, textvariable=self.search_var,
            placeholder_text="Search...", width=160, height=32,
            fg_color=BG_MEDIUM, border_color=BG_LIGHT,
            corner_radius=RADIUS_MD
        )
        search.pack(side=tk.RIGHT)
        self.search_var.trace_add('write', self._filter)

        # Grid
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=(0, SPACING_SM))

        for i in range(5):
            self.scroll.columnconfigure(i, weight=1)

        self._displayed = []
        self._render_chars(self.characters)

    def _filter(self, *args):
        term = self.search_var.get().lower()
        if term:
            filtered = [c for c in self.characters if term in c[1].lower()]
        else:
            filtered = self.characters
        self._render_chars(filtered)

    def _render_chars(self, chars):
        for w in self._displayed:
            w.destroy()
        self._displayed.clear()

        row, col = 0, 0
        for char in chars:
            char_id = char[0]
            name = char[1]
            img_path = char[3]

            card = ctk.CTkFrame(
                self.scroll, fg_color=BG_MEDIUM,
                corner_radius=RADIUS_MD, cursor="hand2"
            )
            card.grid(row=row, column=col, padx=SPACING_XS, pady=SPACING_XS, sticky="nsew")
            self._displayed.append(card)

            # Image
            img = self.icon_cache.get(char_id)
            if not img:
                resolved = resolve_image_path(img_path)
                if resolved and os.path.exists(resolved):
                    try:
                        pil_img = Image.open(resolved)
                        pil_img.thumbnail((65, 65), Image.Resampling.LANCZOS)
                        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(65, 65))
                        self.icon_cache[char_id] = img
                    except:
                        pass

            img_lbl = ctk.CTkLabel(
                card, text="" if img else "?",
                image=img if img else None,
                width=65, height=65, corner_radius=RADIUS_SM
            )
            img_lbl.pack(pady=(SPACING_SM, SPACING_XS), padx=SPACING_SM)

            disp_name = name[:11] + "…" if len(name) > 11 else name
            name_lbl = ctk.CTkLabel(
                card, text=disp_name,
                font=FONT_TINY, text_color=TEXT_PRIMARY
            )
            name_lbl.pack(pady=(0, SPACING_SM))

            def get_click_handler(cid=char_id):
                def handler(e):
                    self.on_select_callback(cid)
                    self.destroy()
                return handler

            on_click = get_click_handler()
            card.bind("<Button-1>", on_click)
            img_lbl.bind("<Button-1>", on_click)
            name_lbl.bind("<Button-1>", on_click)

            def on_enter(e, c=card):
                c.configure(border_color=ACCENT_PRIMARY, border_width=2)
            def on_leave(e, c=card):
                c.configure(border_width=0)

            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)

            col += 1
            if col > 4:
                col = 0
                row += 1


class RaceCalendarViewFrame(ctk.CTkFrame):
    """Race Calendar tab with grade-colored slots and aptitude badges"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.characters = []
        self.races = []

        self.current_character = None
        self.aptitudes = {
            'Turf': tk.StringVar(value='C'),
            'Dirt': tk.StringVar(value='C'),
            'Sprint': tk.StringVar(value='C'),
            'Mile': tk.StringVar(value='C'),
            'Medium': tk.StringVar(value='C'),
            'Long': tk.StringVar(value='C')
        }

        self.selected_races = {}
        self._image_refs = {}
        self._race_image_cache = {}  # track_image_path -> CTkImage
        self._stat_change_after_id = None
        self.calendar_tabs = None
        self.slot_frames = {}

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        """Build the main layout: Top (Character & Stats) + Bottom (Calendar)"""
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # ─── TOP SECTION: Character & Aptitudes ───
        top_frame = ctk.CTkFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        top_frame.grid(row=0, column=0, sticky="ew", padx=SPACING_SM, pady=(SPACING_SM, SPACING_XS))
        top_frame.columnconfigure(1, weight=1)

        # Character avatar + name
        char_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        char_frame.grid(row=0, column=0, sticky="nw", padx=SPACING_LG, pady=SPACING_LG)

        self.char_img_label = ctk.CTkLabel(
            char_frame, text="?",
            font=FONT_HEADER, width=75, height=75,
            corner_radius=RADIUS_MD, fg_color=BG_MEDIUM
        )
        self.char_img_label.pack(side=tk.LEFT, padx=(0, SPACING_MD))

        char_info = ctk.CTkFrame(char_frame, fg_color="transparent")
        char_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.char_name_label = ctk.CTkLabel(
            char_info, text="No Character Selected",
            font=FONT_SUBHEADER, text_color=TEXT_PRIMARY
        )
        self.char_name_label.pack(anchor="w", pady=(SPACING_XS, SPACING_XS))

        create_styled_button(
            char_info, text="👤  Choose Character...",
            command=self._open_character_selector,
            style_type="secondary", width=180, height=32
        ).pack(anchor="w")

        # Aptitude inputs as colored badge-style dropdowns
        stats_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        stats_frame.grid(row=0, column=1, sticky="w", padx=SPACING_LG, pady=SPACING_LG)

        ctk.CTkLabel(
            stats_frame, text="📊  Aptitudes",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, SPACING_XS))

        stats_input_row = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_input_row.pack(anchor="w")

        for apt_name, var in self.aptitudes.items():
            display_name = 'Short' if apt_name == 'Sprint' else apt_name

            col = ctk.CTkFrame(stats_input_row, fg_color="transparent")
            col.pack(side=tk.LEFT, padx=(0, SPACING_XS))

            ctk.CTkLabel(
                col, text=display_name,
                font=FONT_TINY, text_color=TEXT_MUTED
            ).pack()

            combo = ctk.CTkComboBox(
                col,
                values=['S', 'A', 'B', 'C', 'D', 'E', 'F', 'G'],
                variable=var, width=55, height=28,
                font=FONT_TINY,
                command=self._on_stat_change
            )
            combo.pack()

        # ─── CALENDAR SECTION ───
        cal_container = ctk.CTkFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        cal_container.grid(row=1, column=0, sticky="nsew", padx=SPACING_SM, pady=(SPACING_XS, SPACING_SM))
        cal_container.rowconfigure(1, weight=1)
        cal_container.columnconfigure(0, weight=1)

        header = ctk.CTkFrame(cal_container, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=SPACING_LG, pady=SPACING_MD)

        ctk.CTkLabel(
            header, text="📅  Scheduled Races",
            font=FONT_HEADER, text_color=ACCENT_PRIMARY
        ).pack(side=tk.LEFT)

        create_styled_button(
            header, text="➕  Request Race",
            command=self._request_new_race,
            style_type="ghost", height=32
        ).pack(side=tk.RIGHT)

        # Year tabs
        self.calendar_tabs = ctk.CTkTabview(
            cal_container, fg_color=BG_MEDIUM,
            segmented_button_selected_color=ACCENT_PRIMARY,
            segmented_button_unselected_color=BG_LIGHT
        )
        self.calendar_tabs.grid(row=1, column=0, sticky="nsew", padx=SPACING_SM, pady=(0, SPACING_SM))

        for year in YEARS:
            tab = self.calendar_tabs.add(year)
            self._build_year_grid(tab, year)

        # Refresh calendar when switching year tabs (lazy refresh)
        self.calendar_tabs.configure(command=self._on_year_tab_changed)

    def _build_year_grid(self, parent_tab, year):
        """Build the 4x6 grid of half-months for a specific year"""
        scroll = ctk.CTkScrollableFrame(parent_tab, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        for i in range(4):
            scroll.columnconfigure(i, weight=1, uniform="cal_col")

        row, col = 0, 0
        for month in MONTHS:
            for half in HALF_MONTHS:
                date_str = format_half_month(month, half)

                slot = ctk.CTkFrame(
                    scroll, fg_color=BG_DARK, corner_radius=RADIUS_MD,
                    border_width=1, border_color=BG_LIGHT
                )
                slot.grid(row=row, column=col, sticky="nsew", padx=SPACING_XS, pady=SPACING_XS)
                slot.columnconfigure(0, weight=1)

                # Date label
                ui_half = "Early" if half == "First Half" else "Late"
                ui_date = f"{ui_half} {month[:3]}"

                ctk.CTkLabel(
                    slot, text=ui_date,
                    font=FONT_TINY, text_color=TEXT_DISABLED,
                    height=18
                ).grid(row=0, column=0, pady=(SPACING_XS, 0), sticky='w', padx=SPACING_SM)

                content = ctk.CTkFrame(slot, fg_color="transparent")
                content.grid(row=1, column=0, sticky="nsew", pady=SPACING_XS, padx=SPACING_XS)

                # Default empty
                add_btn = ctk.CTkButton(
                    content, text="＋",
                    font=FONT_SMALL, width=36, height=28,
                    fg_color="transparent", hover_color=BG_HIGHLIGHT,
                    text_color=TEXT_DISABLED, corner_radius=RADIUS_SM,
                    command=lambda y=year, d=date_str: self._suggest_race_for_slot(y, d)
                )
                add_btn.pack(pady=SPACING_XS)

                self.slot_frames[(year, date_str)] = content

                col += 1
                if col > 3:
                    col = 0
                    row += 1

    def _open_character_selector(self):
        if not self.characters:
            return
        CharacterSelectionDialog(self, self.characters, self._image_refs, self._on_character_select_id)

    def load_data(self):
        self.characters = get_all_characters()
        self.races = get_all_races()

        if self.characters:
            self._on_character_select_id(self.characters[0][0])
        else:
            self.char_name_label.configure(text="No characters found")

    def _on_stat_change(self, _=None):
        """Debounced aptitude change — wait 150ms to avoid per-click full re-render"""
        if self._stat_change_after_id is not None:
            self.after_cancel(self._stat_change_after_id)
        self._stat_change_after_id = self.after(150, self._do_stat_refresh)

    def _do_stat_refresh(self):
        self._stat_change_after_id = None
        # Only refresh the currently visible tab to keep UI snappy;
        # other tabs will refresh when switched to via _on_year_tab_changed.
        if self.calendar_tabs:
            visible_year = self.calendar_tabs.get()
            for month in MONTHS:
                for half in HALF_MONTHS:
                    date_str = format_half_month(month, half)
                    self._refresh_slot(visible_year, date_str)

    def _on_character_select_id(self, char_id):
        char = next((c for c in self.characters if c[0] == char_id), None)
        if not char:
            return

        self.current_character = char
        self.char_name_label.configure(text=char[1])

        # Load character image
        img = self._image_refs.get(char_id)
        if img:
            self.char_img_label.configure(image=img, text="")
        else:
            img_path = char[3]
            resolved = resolve_image_path(img_path)
            if resolved and os.path.exists(resolved):
                try:
                    pil_img = Image.open(resolved)
                    pil_img.thumbnail((75, 75), Image.Resampling.LANCZOS)
                    img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(75, 75))
                    self._image_refs[char_id] = img
                    self.char_img_label.configure(image=img, text="")
                except (OSError, SyntaxError, ValueError) as e:
                    logging.debug(f"Failed to load character image: {e}")
                    self.char_img_label.configure(image=None, text="?")

        # Load aptitudes
        c = self.current_character
        self.aptitudes['Turf'].set(c[4] or 'G')
        self.aptitudes['Dirt'].set(c[5] or 'G')
        self.aptitudes['Sprint'].set(c[6] or 'G')
        self.aptitudes['Mile'].set(c[7] or 'G')
        self.aptitudes['Medium'].set(c[8] or 'G')
        self.aptitudes['Long'].set(c[9] or 'G')

        self.selected_races.clear()
        self._refresh_calendar()

    def _is_eligible(self, race_data):
        if not race_data:
            return False

        terrain = race_data[7] or ""
        dist_type = race_data[8] or ""
        if dist_type == "Short":
            dist_type = "Sprint"

        surf_grade = self.aptitudes.get(terrain, tk.StringVar(value='E')).get()
        if surf_grade not in ['S', 'A', 'B', 'C']:
            return False

        dist_grade = self.aptitudes.get(dist_type, tk.StringVar(value='E')).get()
        if dist_grade not in ['S', 'A', 'B', 'C']:
            return False

        return True

    def _get_eligible_races_for_date(self, year, date_str):
        if not self.current_character:
            return []

        eligible = []
        class_map = {
            "Junior Year": "Junior Class",
            "Classic Year": "Classic Class",
            "Senior Year": "Senior Class"
        }
        race_class = class_map.get(year, "")

        for r in self.races:
            if r[12] == date_str:
                rc = r[13] or ""
                if (rc == race_class) or \
                   (rc == "Classic/Senior Class" and race_class in ["Classic Class", "Senior Class"]) or \
                   (rc == ""):
                    if self._is_eligible(r):
                        eligible.append(r)

        return eligible

    def _suggest_race_for_slot(self, year, date_str):
        eligible = self._get_eligible_races_for_date(year, date_str)
        if not eligible:
            return

        current = self.selected_races.get((year, date_str))
        if current:
            try:
                idx = next(i for i, r in enumerate(eligible) if r[0] == current[0])
                next_idx = (idx + 1) % len(eligible)
                self.selected_races[(year, date_str)] = eligible[next_idx]
            except StopIteration:
                self.selected_races[(year, date_str)] = eligible[0]
        else:
            self.selected_races[(year, date_str)] = eligible[0]

        self._refresh_slot(year, date_str)

    def _remove_race_from_slot(self, year, date_str):
        if (year, date_str) in self.selected_races:
            del self.selected_races[(year, date_str)]
        self._refresh_slot(year, date_str)

    def _on_year_tab_changed(self, *_):
        """Refresh slots in the newly visible year tab"""
        if not self.calendar_tabs:
            return
        year = self.calendar_tabs.get()
        for month in MONTHS:
            for half in HALF_MONTHS:
                date_str = format_half_month(month, half)
                self._refresh_slot(year, date_str)

    def _refresh_calendar(self):
        for year in YEARS:
            for month in MONTHS:
                for half in HALF_MONTHS:
                    date_str = format_half_month(month, half)
                    self._refresh_slot(year, date_str)

    def _refresh_slot(self, year, date_str):
        content = self.slot_frames.get((year, date_str))
        if not content:
            return

        for w in content.winfo_children():
            w.destroy()

        race = self.selected_races.get((year, date_str))
        if race:
            name = race[1] or race[2]
            grade = race[3] or ""

            # Grade-colored background
            grade_color = GRADE_COLORS.get(grade, ACCENT_PRIMARY)

            # Warning check
            warning = False
            if grade in ['GI', 'G1']:
                terrain = race[7] or ""
                dist_type = race[8] or ""
                if dist_type == "Short":
                    dist_type = "Sprint"

                surf_grade = self.aptitudes.get(terrain, tk.StringVar(value='S')).get()
                dist_grade = self.aptitudes.get(dist_type, tk.StringVar(value='S')).get()

                val_map = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0, 'F': -1, 'G': -2}
                if val_map.get(surf_grade, 0) < 4 or val_map.get(dist_grade, 0) < 4:
                    warning = True

            # Card with grade-colored left accent
            border_color = ACCENT_ERROR if warning else grade_color
            card = ctk.CTkFrame(
                content, fg_color=BG_ELEVATED, corner_radius=RADIUS_SM,
                border_width=1, border_color=border_color
            )
            card.pack(fill=tk.BOTH, expand=True)

            if warning:
                ctk.CTkLabel(
                    card, text="⚠️ Hard",
                    font=FONT_TINY, text_color=ACCENT_ERROR,
                    height=16
                ).pack(pady=(SPACING_XS, 0))

            # Grade badge
            ctk.CTkLabel(
                card, text=grade,
                font=FONT_BODY_BOLD, text_color=grade_color
            ).pack()

            short_name = name[:14] + "…" if len(name) > 14 else name

            # Track image (small, beside race name)
            track_img_path = race[14] if len(race) > 14 else None
            if track_img_path:
                cached = self._race_image_cache.get(track_img_path)
                if not cached:
                    from utils import resolve_image_path
                    resolved = resolve_image_path(track_img_path)
                    if resolved and os.path.exists(resolved):
                        try:
                            pil_img = Image.open(resolved)
                            pil_img.thumbnail((40, 28), Image.Resampling.LANCZOS)
                            cached = ctk.CTkImage(
                                light_image=pil_img, dark_image=pil_img,
                                size=(40, 28)
                            )
                            self._race_image_cache[track_img_path] = cached
                        except Exception:
                            cached = None

                if cached:
                    img_row = ctk.CTkFrame(card, fg_color="transparent")
                    img_row.pack(pady=(SPACING_XS, 0))
                    ctk.CTkLabel(
                        img_row, text="", image=cached,
                        width=40, height=28
                    ).pack(side=tk.LEFT, padx=(0, SPACING_XS))
                    ctk.CTkLabel(
                        img_row, text=short_name,
                        font=FONT_TINY, text_color=TEXT_PRIMARY
                    ).pack(side=tk.LEFT)
                else:
                    ctk.CTkLabel(
                        card, text=short_name,
                        font=FONT_TINY, text_color=TEXT_PRIMARY
                    ).pack(pady=(0, SPACING_XS))
            else:
                ctk.CTkLabel(
                    card, text=short_name,
                    font=FONT_TINY, text_color=TEXT_PRIMARY
                ).pack(pady=(0, SPACING_XS))

            # Terrain + distance badges
            terrain_text = race[7] or ""
            dist_type_text = race[8] or ""
            if terrain_text or dist_type_text:
                badge_frame = ctk.CTkFrame(card, fg_color="transparent")
                badge_frame.pack(pady=(0, SPACING_XS))

                if terrain_text:
                    surf_icon = "🌿" if terrain_text == "Turf" else "🟤"
                    ctk.CTkLabel(
                        badge_frame, text=f"{surf_icon}{terrain_text}",
                        font=FONT_TINY, text_color=TEXT_MUTED
                    ).pack(side=tk.LEFT, padx=2)

                if dist_type_text:
                    ctk.CTkLabel(
                        badge_frame, text=dist_type_text,
                        font=FONT_TINY, text_color=TEXT_MUTED
                    ).pack(side=tk.LEFT, padx=2)

            # Action buttons
            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack(pady=(0, SPACING_XS))

            ctk.CTkButton(
                btns, text="🔄", width=26, height=22,
                font=FONT_TINY, fg_color="transparent",
                hover_color=BG_HIGHLIGHT, text_color=TEXT_MUTED,
                corner_radius=RADIUS_SM,
                command=lambda y=year, d=date_str: self._suggest_race_for_slot(y, d)
            ).pack(side=tk.LEFT, padx=1)

            ctk.CTkButton(
                btns, text="✕", width=26, height=22,
                font=FONT_TINY, fg_color="transparent",
                hover_color=ACCENT_ERROR, text_color=TEXT_MUTED,
                corner_radius=RADIUS_SM,
                command=lambda y=year, d=date_str: self._remove_race_from_slot(y, d)
            ).pack(side=tk.LEFT, padx=1)

        else:
            # Empty slot with subtle add button
            ctk.CTkButton(
                content, text="＋",
                font=FONT_SMALL, width=36, height=28,
                fg_color="transparent", hover_color=BG_HIGHLIGHT,
                text_color=TEXT_DISABLED, corner_radius=RADIUS_SM,
                command=lambda y=year, d=date_str: self._suggest_race_for_slot(y, d)
            ).pack(pady=SPACING_XS)

    def _request_new_race(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Request New Race")
        dialog.geometry("420x220")
        dialog.grab_set()
        dialog.configure(fg_color=BG_DARK)

        ctk.CTkLabel(
            dialog, text="Request a Missing Race",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(pady=SPACING_LG)

        ctk.CTkLabel(
            dialog, text="If a race you need isn't supported yet,\ndescribe it below.",
            text_color=TEXT_MUTED, font=FONT_SMALL
        ).pack(pady=SPACING_XS)

        entry = ctk.CTkEntry(
            dialog, placeholder_text="e.g. Dirt GI in Classic December",
            width=340, fg_color=BG_MEDIUM, border_color=BG_LIGHT,
            corner_radius=RADIUS_MD
        )
        entry.pack(pady=SPACING_MD)

        def on_submit():
            print("Race requested:", entry.get())
            dialog.destroy()

        create_styled_button(
            dialog, text="Submit Request",
            command=on_submit, style_type='accent'
        ).pack()
