"""
Character View - Browse characters and their aptitude data
2-panel layout: Scrollable Character Grid | Character Detail
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_characters, get_character_count
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY,
    create_styled_entry, create_styled_button
)
from utils import resolve_image_path
from PIL import Image

# Aptitude grade colors (S is best, G is worst)
APTITUDE_COLORS = {
    'S': '#FFD700',    # Gold
    'A': '#FF6B6B',    # Red
    'B': '#FF9F43',    # Orange
    'C': '#FECA57',    # Yellow
    'D': '#54A0FF',    # Blue
    'E': '#5F27CD',    # Purple
    'F': '#576574',    # Gray
    'G': '#2C3A47',    # Dark gray
}

APTITUDE_BG_COLORS = {
    'S': '#3D3200',
    'A': '#3D1A1A',
    'B': '#3D2810',
    'C': '#3D3015',
    'D': '#152940',
    'E': '#1A0F30',
    'F': '#1A1D20',
    'G': '#0F1215',
}


def resolve_character_image(image_path):
    """Resolve path for character images"""
    if not image_path:
        return None
    
    if os.path.isabs(image_path) and os.path.exists(image_path):
        return image_path
    
    # Try relative to exe/project root
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    full_path = os.path.join(base, image_path)
    if os.path.exists(full_path):
        return full_path
    
    # Try assets/characters/ prefix
    if not image_path.startswith('assets'):
        full_path = os.path.join(base, 'assets', 'characters', os.path.basename(image_path))
        if os.path.exists(full_path):
            return full_path
    
    return None


class CharacterViewFrame(ctk.CTkFrame):
    """Character browser with 2-panel layout"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.characters = []
        self.current_character = None
        self._image_refs = []  # Keep references to prevent GC
        self._detail_image_ref = None
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self.filter_characters())
        
        self.create_widgets()
        self.load_characters()

    def create_widgets(self):
        """Build the 2-panel layout"""
        # Main horizontal split
        self.columnconfigure(0, weight=3, minsize=600)
        self.columnconfigure(1, weight=2, minsize=350)
        self.rowconfigure(0, weight=1)

        # ─── LEFT PANEL: Character Grid ───
        left_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=12)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        left_frame.rowconfigure(1, weight=1)
        left_frame.columnconfigure(0, weight=1)

        # Search bar
        search_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        search_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(search_frame, text="🐴 Characters", font=FONT_HEADER,
                     text_color=ACCENT_PRIMARY).grid(row=0, column=0, sticky="w")

        self.count_label = ctk.CTkLabel(search_frame, text="0 characters", font=FONT_SMALL,
                                         text_color=TEXT_MUTED)
        self.count_label.grid(row=0, column=1, sticky="e", padx=(10, 0))

        search_entry = create_styled_entry(search_frame, textvariable=self.search_var,
                                            placeholder_text="🔍 Search characters...")
        search_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        # Scrollable character grid
        self.char_scroll = ctk.CTkScrollableFrame(left_frame, fg_color=BG_DARK,
                                                    corner_radius=0)
        self.char_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure the grid columns
        self.char_scroll.grid_columnconfigure(0, weight=1)
        self.char_scroll.grid_columnconfigure(1, weight=1)
        self.char_scroll.grid_columnconfigure(2, weight=1)

        # ─── RIGHT PANEL: Character Detail ───
        self.detail_frame = ctk.CTkScrollableFrame(self, fg_color=BG_MEDIUM, corner_radius=12)
        self.detail_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        self.detail_frame.columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.detail_frame,
            text="← Select a character\nto see their aptitude data",
            font=FONT_BODY,
            text_color=TEXT_MUTED,
            justify="center"
        )
        self.empty_label.pack(expand=True, pady=100)

    def _propagate_scroll(self, event, scroll_frame):
        """Manually propagate mouse wheel events to a specific scrollable canvas"""
        try:
            scroll_frame._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass

    def _bind_scroll_recursive(self, widget, scroll_frame, depth=0):
        """Recursively bind mouse wheel, limiting depth to avoid event explosion"""
        if depth > 2:
            return
        widget.bind("<MouseWheel>", lambda e: self._propagate_scroll(e, scroll_frame), add="+")
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child, scroll_frame, depth + 1)

    def load_characters(self):
        """Load all characters from DB"""
        self.characters = get_all_characters()
        self.count_label.configure(text=f"{len(self.characters)} characters")
        self.render_character_grid(self.characters)

    def filter_characters(self):
        """Filter characters by search term"""
        search = self.search_var.get().strip()
        if search:
            filtered = get_all_characters(search_term=search)
        else:
            filtered = self.characters
        self.count_label.configure(text=f"{len(filtered)} characters")
        self.render_character_grid(filtered)

    def render_character_grid(self, characters):
        """Render character cards in a grid layout"""
        # Clear existing
        for widget in self.char_scroll.winfo_children():
            widget.destroy()
        self._image_refs.clear()

        if not characters:
            ctk.CTkLabel(
                self.char_scroll,
                text="No characters found.\n\nRun the character scraper:\npython main.py --scrape-characters",
                font=FONT_BODY,
                text_color=TEXT_MUTED,
                justify="center"
            ).grid(row=0, column=0, columnspan=3, pady=50)
            return

        for idx, char in enumerate(characters):
            row = idx // 3
            col = idx % 3
            # Ensure row has weight so they don't squash each other
            self.char_scroll.grid_rowconfigure(row, weight=1, uniform="row")
            self._create_character_card(char, row, col)

    def _create_character_card(self, char_data, row, col):
        """Create a single character card in the grid"""
        # char_data: (character_id, name, gametora_id, image_path,
        #             turf, dirt, short, mile, medium, long,
        #             runner, leader, betweener, chaser)
        char_id = char_data[0]
        name = char_data[1]
        image_path = char_data[3]

        # Aptitude data
        aptitudes = {
            'Turf': char_data[4], 'Dirt': char_data[5],
            'Short': char_data[6], 'Mile': char_data[7],
            'Medium': char_data[8], 'Long': char_data[9],
            'Runner': char_data[10], 'Leader': char_data[11],
            'Betweener': char_data[12], 'Chaser': char_data[13]
        }

        # Card frame
        card = ctk.CTkFrame(self.char_scroll, fg_color=BG_MEDIUM, corner_radius=10,
                            cursor="hand2")
        card.grid(row=row, column=col, sticky="new", padx=8, pady=8)
        
        # Make inner content center aligned
        card.grid_columnconfigure(0, weight=1)

        # Character image
        resolved = resolve_character_image(image_path)
        if resolved:
            try:
                img = Image.open(resolved)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
                self._image_refs.append(ctk_img)
                img_label = ctk.CTkLabel(card, image=ctk_img, text="")
                img_label.grid(row=0, column=0, padx=5, pady=(8, 2))
            except Exception:
                ctk.CTkLabel(card, text="🐴", font=("Segoe UI", 30)).grid(
                    row=0, column=0, padx=5, pady=(8, 2))
        else:
            ctk.CTkLabel(card, text="🐴", font=("Segoe UI", 30)).grid(
                row=0, column=0, padx=5, pady=(8, 2))

        # Character name
        name_label = ctk.CTkLabel(card, text=name, font=FONT_SMALL,
                                   text_color=TEXT_PRIMARY, wraplength=150)
        name_label.grid(row=1, column=0, padx=5, pady=(2, 2))

        # Mini aptitude badges (top 3)
        badge_frame = ctk.CTkFrame(card, fg_color="transparent")
        badge_frame.grid(row=2, column=0, padx=5, pady=(0, 6))

        # Show surface aptitudes as compact badges
        for i, (key, short_key) in enumerate([('Turf', '🌿'), ('Dirt', '🟤')]):
            grade = aptitudes.get(key, '?')
            color = APTITUDE_COLORS.get(grade, TEXT_MUTED)
            badge = ctk.CTkLabel(badge_frame, text=f"{short_key}{grade}",
                                  font=FONT_TINY, text_color=color)
            badge.pack(side=tk.LEFT, padx=2)

        # Click handler
        def on_click(e, cid=char_id, data=char_data):
            self.select_character(cid, data)

        card.bind("<Button-1>", on_click)
        for child in card.winfo_children():
            child.bind("<Button-1>", on_click)
            for grandchild in child.winfo_children():
                grandchild.bind("<Button-1>", on_click)

        # Hover effects
        def on_enter(e):
            card.configure(fg_color=BG_LIGHT)

        def on_leave(e):
            if self.current_character != char_id:
                card.configure(fg_color=BG_MEDIUM)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        card._char_id = char_id

        # Bind scroll events to ensure smooth scrolling over the cards
        self._bind_scroll_recursive(card, self.char_scroll)

    def select_character(self, char_id, char_data):
        """Show full detail for a selected character"""
        self.current_character = char_id
        
        # Highlight card
        for child in self.char_scroll.winfo_children():
            if hasattr(child, '_char_id'):
                if child._char_id == char_id:
                    child.configure(fg_color=BG_LIGHT)
                else:
                    child.configure(fg_color=BG_MEDIUM)

        # Clear detail panel
        for widget in self.detail_frame.winfo_children():
            widget.destroy()

        name = char_data[1]
        image_path = char_data[3]
        aptitudes = {
            'Turf': char_data[4], 'Dirt': char_data[5],
            'Short': char_data[6], 'Mile': char_data[7],
            'Medium': char_data[8], 'Long': char_data[9],
            'Runner': char_data[10], 'Leader': char_data[11],
            'Betweener': char_data[12], 'Chaser': char_data[13]
        }

        # ── Header with image and name ──
        header_frame = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        resolved = resolve_character_image(image_path)
        if resolved:
            try:
                img = Image.open(resolved)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 120))
                self._detail_image_ref = ctk_img
                ctk.CTkLabel(header_frame, image=ctk_img, text="").pack(pady=(0, 5))
            except Exception:
                ctk.CTkLabel(header_frame, text="🐴", font=("Segoe UI", 40)).pack(pady=(0, 5))
        else:
            ctk.CTkLabel(header_frame, text="🐴", font=("Segoe UI", 40)).pack(pady=(0, 5))

        ctk.CTkLabel(header_frame, text=name, font=FONT_HEADER,
                     text_color=TEXT_PRIMARY).pack()

        # ── Divider ──
        ctk.CTkFrame(self.detail_frame, height=2, fg_color=BG_LIGHT).pack(
            fill=tk.X, padx=15, pady=10)

        # ── Aptitude Section: Surface ──
        self._add_aptitude_section("🌍 Surface", [
            ('Turf', '🌿', aptitudes.get('Turf')),
            ('Dirt', '🟤', aptitudes.get('Dirt')),
        ])

        # ── Aptitude Section: Distance ──
        self._add_aptitude_section("📏 Distance", [
            ('Short', '🏃', aptitudes.get('Short')),
            ('Mile', '🏇', aptitudes.get('Mile')),
            ('Medium', '📐', aptitudes.get('Medium')),
            ('Long', '🏔️', aptitudes.get('Long')),
        ])

        # ── Aptitude Section: Strategy ──
        self._add_aptitude_section("🎯 Strategy", [
            ('Runner', '🥇', aptitudes.get('Runner')),
            ('Leader', '🏅', aptitudes.get('Leader')),
            ('Betweener', '⚖️', aptitudes.get('Betweener')),
            ('Chaser', '🔥', aptitudes.get('Chaser')),
        ])

    def _add_aptitude_section(self, title, items):
        """Add an aptitude section with grade bars"""
        section = ctk.CTkFrame(self.detail_frame, fg_color=BG_DARK, corner_radius=10)
        section.pack(fill=tk.X, padx=10, pady=5)
        section.columnconfigure(1, weight=1)

        # Section title
        ctk.CTkLabel(section, text=title, font=FONT_SUBHEADER,
                     text_color=ACCENT_TERTIARY).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 5))

        for idx, (label, icon, grade) in enumerate(items):
            row_num = idx + 1
            grade = grade or '?'
            color = APTITUDE_COLORS.get(grade, TEXT_MUTED)
            bg_color = APTITUDE_BG_COLORS.get(grade, BG_MEDIUM)

            # Label
            ctk.CTkLabel(section, text=f"{icon} {label}", font=FONT_BODY,
                         text_color=TEXT_SECONDARY).grid(
                row=row_num, column=0, sticky="w", padx=(12, 5), pady=3)

            # Grade badge
            grade_badge = ctk.CTkLabel(
                section, text=f"  {grade}  ", font=FONT_BODY_BOLD,
                text_color=color, fg_color=bg_color, corner_radius=6,
                height=28, width=40
            )
            grade_badge.grid(row=row_num, column=1, sticky="e", padx=(5, 12), pady=3)

        # Bottom padding
        ctk.CTkFrame(section, height=8, fg_color="transparent").grid(
            row=len(items) + 1, column=0, columnspan=3)
