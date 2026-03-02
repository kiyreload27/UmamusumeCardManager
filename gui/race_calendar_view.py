"""
Race Calendar View - Combined character selection and race suggestion calendar
Replaces the old Character and Race tabs.
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_characters, get_all_races
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY,
    create_styled_entry, create_styled_button, create_card_frame
)
from utils import resolve_image_path
from PIL import Image

# Define calendar structure
YEARS = ["Junior Year", "Classic Year", "Senior Year"]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
HALF_MONTHS = ["First Half", "Second Half"]

def format_half_month(month, half):
    """Format matching race_date in DB e.g. 'January, First Half'"""
    return f"{month}, {half}"


class RaceCalendarViewFrame(ctk.CTkFrame):
    """Race Calendar tab merging Characters and Races logic"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.characters = []
        self.races = []
        
        # State
        self.current_character = None
        self.aptitudes = {
            'Turf': tk.StringVar(value='C'),
            'Dirt': tk.StringVar(value='C'),
            'Sprint': tk.StringVar(value='C'),
            'Mile': tk.StringVar(value='C'),
            'Medium': tk.StringVar(value='C'),
            'Long': tk.StringVar(value='C')
        }
        
        # Store selected race overrides for slots
        # Key: (year, date_str), Value: race_data tuple
        self.selected_races = {}
        
        # Grid references
        self._image_refs = []
        self.calendar_tabs = None
        self.slot_frames = {} # To hold the UI references for each slot
        
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        """Build the main layout: Top (Character & Stats) + Bottom (Calendar)"""
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        
        # ─── TOP SECTION: Character & Stats ───
        top_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=12)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_frame.columnconfigure(1, weight=1)
        
        # Character selection
        char_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        char_frame.grid(row=0, column=0, sticky="nw", padx=15, pady=15)
        
        ctk.CTkLabel(char_frame, text="🐴 Select Character:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w")
        self.char_combo = ctk.CTkComboBox(
            char_frame, 
            values=["Loading..."], 
            command=self._on_character_select,
            width=200
        )
        self.char_combo.pack(anchor="w", pady=(5, 0))
        
        # Stats inputs
        stats_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        stats_frame.grid(row=0, column=1, sticky="w", padx=20, pady=15)
        
        ctk.CTkLabel(stats_frame, text="📊 Current Aptitudes (S-G):", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w")
        
        stats_input_row = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_input_row.pack(anchor="w", pady=(5, 0))
        
        for apt_name, var in self.aptitudes.items():
            if apt_name == 'Sprint':
                display_name = 'Sprint (Short)'
            else:
                display_name = apt_name

            col = ctk.CTkFrame(stats_input_row, fg_color="transparent")
            col.pack(side=tk.LEFT, padx=(0, 5))
            
            ctk.CTkLabel(col, text=display_name, font=FONT_TINY, text_color=TEXT_MUTED).pack()
            combo = ctk.CTkComboBox(
                col, 
                values=['S', 'A', 'B', 'C', 'D', 'E', 'F', 'G'],
                variable=var,
                width=55,
                command=self._on_stat_change
            )
            combo.pack()
        
        # ─── BOTTOM SECTION: Calendar ───
        cal_container = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=12)
        cal_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        cal_container.rowconfigure(1, weight=1)
        cal_container.columnconfigure(0, weight=1)
        
        header = ctk.CTkFrame(cal_container, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        ctk.CTkLabel(header, text="📅 Scheduled Races", font=FONT_HEADER, text_color=ACCENT_PRIMARY).pack(side=tk.LEFT)
        
        req_btn = create_styled_button(
            header, text="➕ Request New Race", 
            command=self._request_new_race,
            style_type="secondary"
        )
        req_btn.pack(side=tk.RIGHT)
        
        # Calendar Tabs
        self.calendar_tabs = ctk.CTkTabview(cal_container, fg_color=BG_MEDIUM)
        self.calendar_tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        for year in YEARS:
            tab = self.calendar_tabs.add(year)
            self._build_year_grid(tab, year)
            
    def _build_year_grid(self, parent_tab, year):
        """Build the 4x6 grid of half-months for a specific year"""
        # Outer scrollable frame just in case
        scroll = ctk.CTkScrollableFrame(parent_tab, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)
        
        # 4 columns (Width of screen usually fits 4 well, 24 items = 6 rows)
        # Let's use 4 columns, 6 rows
        for i in range(4):
            scroll.columnconfigure(i, weight=1, uniform="cal_col")
            
        row, col = 0, 0
        for month in MONTHS:
            for half in HALF_MONTHS:
                date_str = format_half_month(month, half)
                
                # Slot container
                slot = create_card_frame(scroll)
                slot.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
                slot.columnconfigure(0, weight=1)
                
                # Header showing the date (e.g. "Early Jan")
                # Format visually better for the UI
                ui_half = "Early" if half == "First Half" else "Late"
                ui_date = f"{ui_half} {month[:3]}"
                
                ctk.CTkLabel(slot, text=ui_date, font=FONT_BODY_BOLD, text_color=TEXT_MUTED).grid(row=0, column=0, pady=(5, 0))
                
                # Content frame (where the race button goes)
                content = ctk.CTkFrame(slot, fg_color="transparent")
                content.grid(row=1, column=0, sticky="nsew", pady=10, padx=5)
                
                # Default "Empty" button
                add_btn = create_styled_button(
                    content, text="➕", width=40,
                    command=lambda y=year, d=date_str: self._suggest_race_for_slot(y, d)
                )
                add_btn.pack()
                
                # Store reference for updating later
                self.slot_frames[(year, date_str)] = content
                
                col += 1
                if col > 3:
                    col = 0
                    row += 1

    def load_data(self):
        """Load characters and races from the database"""
        self.characters = get_all_characters()
        self.races = get_all_races()
        
        if self.characters:
            char_names = [c[1] for c in self.characters] # Assuming name is index 1
            self.char_combo.configure(values=char_names)
            self.char_combo.set(char_names[0])
            self._on_character_select(char_names[0])
        else:
            self.char_combo.set("No characters found")

    def _get_char_by_name(self, name):
        for c in self.characters:
            if c[1] == name:
                return c
        return None

    def _on_stat_change(self, _=None):
        self._refresh_calendar()

    def _on_character_select(self, name):
        self.current_character = self._get_char_by_name(name)
        
        # Load base aptitudes into UI
        if self.current_character:
            # char_data aptitudes: Turf=4, Dirt=5, Short=6, Mile=7, Medium=8, Long=9
            c = self.current_character
            self.aptitudes['Turf'].set(c[4] or 'G')
            self.aptitudes['Dirt'].set(c[5] or 'G')
            self.aptitudes['Sprint'].set(c[6] or 'G')
            self.aptitudes['Mile'].set(c[7] or 'G')
            self.aptitudes['Medium'].set(c[8] or 'G')
            self.aptitudes['Long'].set(c[9] or 'G')

        # Clear selected races on character change
        self.selected_races.clear()
        self._refresh_calendar()
        
    def _is_eligible(self, race_data):
        """
        Check if character is eligible for the race based on UI aptitudes.
        Rules:
        - Must have A, B, or C aptitude for the race's terrain
        - Must have A, B, or C aptitude for the race's distance
        """
        if not race_data: return False
        
        terrain = race_data[7] or ""
        dist_type = race_data[8] or ""
        
        # Map distance type from DB ("Short") to UI ("Sprint")
        if dist_type == "Short": dist_type = "Sprint"
        
        surf_grade = self.aptitudes.get(terrain, tk.StringVar(value='E')).get()
        if surf_grade not in ['S', 'A', 'B', 'C']:
            return False
            
        dist_grade = self.aptitudes.get(dist_type, tk.StringVar(value='E')).get()
        if dist_grade not in ['S', 'A', 'B', 'C']:
            return False
            
        return True

    def _get_eligible_races_for_date(self, year, date_str):
        """Get all races falling on this date that the character is eligible for"""
        if not self.current_character: return []
        
        eligible = []
        
        # Map year string to class
        class_map = {
            "Junior Year": "Junior Class",
            "Classic Year": "Classic Class",
            "Senior Year": "Senior Class"
        }
        race_class = class_map.get(year, "")
        
        for r in self.races:
            # Check date match
            if r[12] == date_str:
                # Class match (some races might not have class restrictions, but generally they do)
                # In gametora, a single race might be 'Classic Class' or 'Senior Class'.
                # We need to ensure we don't suggest a Junior race in Senior year.
                # If race class is empty (for OP/Pre-OP), we might allow it, but let's stick to matching classes.
                # Actually, Classic/Senior races sometimes overlap. For now let's just match strictly or if empty/broad.
                rc = r[13] or ""
                if rc == race_class or rc == "Classic/Senior Class" and race_class in ["Classic Class", "Senior Class"] or rc == "":
                    if self._is_eligible(r):
                        eligible.append(r)
                        
        return eligible

    def _suggest_race_for_slot(self, year, date_str):
        """Pick a race for the slot, or cycle to next if one is already selected"""
        eligible = self._get_eligible_races_for_date(year, date_str)
        if not eligible:
            print(f"No eligible races for {year} {date_str}")
            return
            
        current = self.selected_races.get((year, date_str))
        if current:
            # Find current index and get next
            try:
                # Try finding by race_id
                idx = next(i for i, r in enumerate(eligible) if r[0] == current[0])
                next_idx = (idx + 1) % len(eligible)
                self.selected_races[(year, date_str)] = eligible[next_idx]
            except StopIteration:
                self.selected_races[(year, date_str)] = eligible[0]
        else:
            self.selected_races[(year, date_str)] = eligible[0]
            
        self._refresh_slot(year, date_str)

    def _remove_race_from_slot(self, year, date_str):
        """Remove selected race from slot"""
        if (year, date_str) in self.selected_races:
            del self.selected_races[(year, date_str)]
        self._refresh_slot(year, date_str)

    def _refresh_calendar(self):
        """Update the entire calendar UI"""
        for year in YEARS:
            for month in MONTHS:
                for half in HALF_MONTHS:
                    date_str = format_half_month(month, half)
                    self._refresh_slot(year, date_str)
                    
    def _refresh_slot(self, year, date_str):
        """Update a specific UI slot"""
        content = self.slot_frames.get((year, date_str))
        if not content: return
        
        # Clear slot
        for w in content.winfo_children():
            w.destroy()
            
        race = self.selected_races.get((year, date_str))
        if race:
            # Show selected race
            name = race[1] or race[2] # EN then JP
            grade = race[3] or ""
            
            # Check warning
            warning = False
            if grade in ['GI', 'G1']:
                terrain = race[7] or ""
                dist_type = race[8] or ""
                if dist_type == "Short": dist_type = "Sprint"
                
                surf_grade = self.aptitudes.get(terrain, tk.StringVar(value='S')).get()
                dist_grade = self.aptitudes.get(dist_type, tk.StringVar(value='S')).get()
                
                val_map = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0, 'F': -1, 'G': -2}
                # Warning logic: If GI race, but relevant aptitudes are lower than A (value < 4)
                if val_map.get(surf_grade, 0) < 4 or val_map.get(dist_grade, 0) < 4:
                    warning = True
                
            color = ACCENT_WARNING if warning else ACCENT_PRIMARY
            bg = BG_LIGHT
            
            card = ctk.CTkFrame(content, fg_color=bg, corner_radius=6)
            card.pack(fill=tk.BOTH, expand=True)
            
            if warning:
                ctk.CTkLabel(card, text="⚠️ Hard", font=FONT_TINY, text_color=ACCENT_ERROR).pack(pady=(2, 0))
                
            ctk.CTkLabel(card, text=grade, font=FONT_BODY_BOLD, text_color=color).pack()
            # Truncate name if too long
            short_name = name[:12] + ".." if len(name) > 12 else name
            ctk.CTkLabel(card, text=short_name, font=FONT_TINY, text_color=TEXT_PRIMARY).pack(pady=(0, 2))
            
            # Reroll/Remove buttons
            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack()
            
            ctk.CTkButton(btns, text="🔄", width=25, height=20, font=FONT_TINY,
                         command=lambda y=year, d=date_str: self._suggest_race_for_slot(y, d)).pack(side=tk.LEFT, padx=2)
            ctk.CTkButton(btns, text="❌", width=25, height=20, font=FONT_TINY, fg_color=ACCENT_ERROR, hover_color="#b91c1c",
                         command=lambda y=year, d=date_str: self._remove_race_from_slot(y, d)).pack(side=tk.LEFT, padx=2)
            
        else:
            # Show empty Add button
            add_btn = create_styled_button(
                content, text="➕", width=40,
                command=lambda y=year, d=date_str: self._suggest_race_for_slot(y, d)
            )
            add_btn.pack(pady=5)
            
    def _request_new_race(self):
        """Handle request new race action"""
        # Given it's a request button, spawn a small dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Request New Race")
        dialog.geometry("400x200")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Request a Missing Race", font=FONT_HEADER).pack(pady=15)
        ctk.CTkLabel(dialog, text="If a race you need isn't supported yet,\nplease describe it below.", text_color=TEXT_MUTED).pack(pady=5)
        
        entry = ctk.CTkEntry(dialog, placeholder_text="e.g. Dirt GI in Classic December", width=300)
        entry.pack(pady=15)
        
        def on_submit():
            print("Race requested:", entry.get())
            dialog.destroy()
            
        ctk.CTkButton(dialog, text="Submit Request", command=on_submit).pack()

