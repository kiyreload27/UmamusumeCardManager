"""
Skill Search View - Find cards by the skills they teach
Redesigned with modern grids and styled cards
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import sys
import os
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_unique_skills, get_cards_with_skill, get_card_by_id, get_hints, get_all_event_skills
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY, ACCENT_SUCCESS, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    create_card_frame, get_type_icon, get_rarity_color, create_styled_button, create_styled_entry
)


class SkillSearchFrame(ctk.CTkFrame):
    """Frame for searching skills and finding cards that have them"""
    
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.all_skills = []
        self.icon_cache = {}
        self.current_skill = None
        self.skill_widgets = []
        self.result_widgets = []
        
        self._rendering_skills = False
        self._rendering_cards = False
        self._skill_render_queue = []
        self._card_render_queue = []
        
        self.create_widgets()
        self.load_skills()
    
    def create_widgets(self):
        """Create the skill search interface"""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        
        # === Left Panel: Skill List ===
        left_frame = create_card_frame(self)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        header = ctk.CTkFrame(left_frame, fg_color="transparent")
        header.pack(fill=tk.X, pady=(20, 10), padx=20)
        ctk.CTkLabel(header, text="🔍 Search Skills", font=FONT_HEADER, text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # Search Entry
        self.search_var = tk.StringVar()
        search_entry = create_styled_entry(left_frame, textvariable=self.search_var, placeholder_text="Type to filter skills...")
        search_entry.pack(fill=tk.X, padx=20, pady=(0, 15))
        self.search_var.trace_add('write', self.filter_skills)
        
        # Skill List Container (Scrollable)
        self.skill_list_scroll = ctk.CTkScrollableFrame(left_frame, fg_color="transparent", corner_radius=8)
        self.skill_list_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 15))
        self.skill_list_scroll.columnconfigure(0, weight=1)
        
        # === Right Panel: Results ===
        right_frame = create_card_frame(self)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        # Search Row (Search + Filter)
        search_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        search_frame.pack(fill=tk.X, padx=20, pady=20)
        
        self.result_header = ctk.CTkLabel(search_frame, text="Select a skill to see cards", 
                                       font=FONT_SUBHEADER, text_color=ACCENT_PRIMARY)
        self.result_header.pack(side=tk.LEFT)
        
        # Owned Filter
        self.owned_only_var = tk.BooleanVar(value=False)
        self.owned_check = ctk.CTkCheckBox(search_frame, text="Show Owned Only", 
                                           variable=self.owned_only_var, 
                                           command=self.on_filter_changed,
                                           font=FONT_SMALL)
        self.owned_check.pack(side=tk.RIGHT)
        
        # Results Scroll Container
        self.results_scroll = ctk.CTkScrollableFrame(right_frame, fg_color="transparent")
        self.results_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.results_scroll.columnconfigure(0, weight=1)
        self.results_scroll.columnconfigure(1, weight=1)
        
        # Stats footer
        self.stats_label = ctk.CTkLabel(right_frame, text="", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.stats_label.pack(anchor='e', pady=10, padx=20)

    def load_skills(self):
        """Load all unique skills"""
        self.all_skills = get_all_unique_skills()
        self.update_skill_list(self.all_skills)
        
    def _select_skill_widget(self, skill_name, widget):
        for w in self.skill_widgets:
            w.configure(fg_color="transparent")
        widget.configure(fg_color=BG_HIGHLIGHT)
        self.on_skill_selected(skill_name)
        
    def update_skill_list(self, items):
        """Update skill list UI sequentially to avoid blocking"""
        self._rendering_skills = False # Cancel any ongoing render
        
        for w in self.skill_widgets:
            w.destroy()
        self.skill_widgets.clear()
        
        display_items = items[:60]
        self._skill_render_queue = display_items
        self._rendering_skills = True
        
        self._process_skill_queue()
        
    def _process_skill_queue(self):
        if not self._rendering_skills or not self._skill_render_queue:
            self._rendering_skills = False
            return
            
        # Process up to 10 at a time
        chunk = self._skill_render_queue[:10]
        self._skill_render_queue = self._skill_render_queue[10:]
        
        for item in chunk:
            if isinstance(item, tuple):
                skill_name, is_golden = item
            else:
                skill_name, is_golden = item, False
                
            color = ACCENT_WARNING if is_golden else TEXT_PRIMARY
            prefix = "✨ " if is_golden else "• "
            
            btn = ctk.CTkButton(
                self.skill_list_scroll, 
                text=f"{prefix}{skill_name}", 
                font=FONT_BODY_BOLD if is_golden else FONT_BODY,
                text_color=color,
                fg_color="transparent",
                hover_color=BG_LIGHT,
                anchor="w",
                corner_radius=6,
                height=36
            )
            btn.pack(fill=tk.X, pady=1, padx=4)
            btn.configure(command=lambda n=skill_name, b=btn: self._select_skill_widget(n, b))
            self.skill_widgets.append(btn)
            
        if self._skill_render_queue:
            self.after(20, self._process_skill_queue)
            
    def filter_skills(self, *args):
        search = self.search_var.get().lower()
        if not search:
            self.update_skill_list(self.all_skills)
            return
            
        filtered = []
        for item in self.all_skills:
            if isinstance(item, tuple):
                skill_name, is_golden = item
                if search in skill_name.lower() or (search == "golden" and is_golden):
                    filtered.append(item)
            else:
                if search in item.lower():
                    filtered.append(item)
                    
        self.update_skill_list(filtered)
        
    def on_filter_changed(self):
        if self.current_skill:
            self.show_cards_for_skill(self.current_skill)

    def on_skill_selected(self, skill_name):
        self.current_skill = skill_name
        self.show_cards_for_skill(skill_name)
    
    def show_cards_for_skill(self, skill_name):
        self.current_skill = skill_name
        self._rendering_cards = False # Cancel any ongoing render
        self.result_header.configure(text=f"Cards with ✨ {skill_name}")
        
        for w in self.result_widgets:
            w.destroy()
        self.result_widgets.clear()
            
        cards = get_cards_with_skill(skill_name)
        owned_only = self.owned_only_var.get()
        
        filtered_cards = []
        for card in cards:
            if owned_only and not card.get('is_owned'):
                continue
            filtered_cards.append(card)
            
        self.stats_label.configure(text=f"Loading cards...")
        
        self._card_render_queue = filtered_cards
        self._card_render_row = 0
        self._card_render_col = 0
        self._card_render_count = 0
        self._rendering_cards = True
        
        self._process_card_queue()
        
    def _process_card_queue(self):
        if not self._rendering_cards or not self._card_render_queue:
            self._rendering_cards = False
            self.stats_label.configure(text=f"Found {self._card_render_count} cards teaching ✨ {self.current_skill}")
            return
            
        # Process up to 5 cards per frame to maintain 60fps interaction
        chunk = self._card_render_queue[:5]
        self._card_render_queue = self._card_render_queue[5:]
        
        for card in chunk:
            self._card_render_count += 1
            card_id = card['card_id']
            card_type = card.get('type') or card.get('card_type') or 'Unknown'
            rarity = card.get('rarity') or 'Unknown'
            is_owned = card.get('is_owned')
            
            bg_color = BG_MEDIUM if is_owned else BG_DARK
            border_color = ACCENT_SUCCESS if is_owned else BG_HIGHLIGHT
            
            card_frame = ctk.CTkFrame(self.results_scroll, fg_color=bg_color, corner_radius=10, border_width=1, border_color=border_color)
            card_frame.grid(row=self._card_render_row, column=self._card_render_col, sticky="nsew", padx=6, pady=6)
            self.result_widgets.append(card_frame)
            
            # Load Image
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(card['image_path'])
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((70, 70), Image.Resampling.LANCZOS)
                        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(70, 70))
                        self.icon_cache[card_id] = img
                    except: pass
            
            img_label = ctk.CTkLabel(card_frame, text="", image=img if img else None, width=70, height=70, corner_radius=8)
            img_label.pack(side=tk.LEFT, padx=10, pady=10)
            
            # Info container
            info = ctk.CTkFrame(card_frame, fg_color="transparent")
            info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=10, padx=(0, 10))
            
            # Name & Meta
            hdr = ctk.CTkFrame(info, fg_color="transparent")
            hdr.pack(fill=tk.X)
            ctk.CTkLabel(hdr, text=card.get('name', 'Unknown'), font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, anchor="w").pack(side=tk.LEFT)
            ctk.CTkLabel(hdr, text=f"{get_type_icon(card_type)} {card_type} • {rarity}", font=FONT_SMALL, text_color=get_rarity_color(rarity)).pack(side=tk.RIGHT)
            
            # Details Box
            det = ctk.CTkFrame(info, fg_color=BG_DARKEST if is_owned else BG_MEDIUM, corner_radius=6)
            det.pack(fill=tk.X, pady=(5,0), ipady=4)
            
            source = card.get('source', 'Event')
            if card.get('is_gold', False):
                source = f"✨ GOLDEN {source.replace('✨ GOLDEN ', '')}"
                
            ctk.CTkLabel(det, text=source, font=FONT_SMALL, text_color=ACCENT_WARNING if 'GOLDEN' in source else ACCENT_SECONDARY, anchor="w").pack(fill=tk.X, padx=8)
            ctk.CTkLabel(det, text=card.get('details', ''), font=FONT_TINY, text_color=TEXT_MUTED, anchor="w", justify="left", wraplength=200).pack(fill=tk.X, padx=8)
            
            self._card_render_col += 1
            if self._card_render_col > 1:
                self._card_render_col = 0
                self._card_render_row += 1
                
        if self._card_render_queue:
            self.after(10, self._process_card_queue)

    def set_card(self, card_id):
        pass
