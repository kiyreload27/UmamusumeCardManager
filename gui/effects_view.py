"""
Effects Search View - Search for effects across all owned cards
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import search_owned_effects
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL,
    create_styled_button, create_styled_entry
)
from utils import resolve_image_path

class EffectsFrame(ttk.Frame):
    """Frame for searching effects across owned cards"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()
        
    def create_widgets(self):
        """Create the effects search interface"""
        # Header / Search Bar
        header_frame = tk.Frame(self, bg=BG_DARK)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        # Search container
        search_container = tk.Frame(header_frame, bg=BG_DARK)
        search_container.pack(fill=tk.X)
        
        tk.Label(search_container, text="🔍 Search Effect:", 
                 font=FONT_HEADER, bg=BG_DARK, fg=TEXT_PRIMARY).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_entry = create_styled_entry(search_container, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self.perform_search())
        
        search_btn = create_styled_button(search_container, text="Search", 
                                          command=self.perform_search, style_type='primary')
        search_btn.pack(side=tk.LEFT)
        
        # Example/Help text
        help_frame = tk.Frame(header_frame, bg=BG_DARK)
        help_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Label(help_frame, text="Examples: Friendship, Motivation, Race Bonus, Skill Pt", 
                 font=FONT_SMALL, bg=BG_DARK, fg=TEXT_MUTED).pack(side=tk.LEFT)

        # Results Area
        results_frame = ttk.LabelFrame(self, text="  Search Results (Owned Cards)  ", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Treeview
        columns = ('card', 'level', 'current_value', 'effect_name')
        self.tree = ttk.Treeview(results_frame, columns=columns, show='headings', selectmode='browse')
        
        self.tree.heading('card', text='Card Name', anchor='w')
        self.tree.heading('level', text='Level', anchor='center')
        self.tree.heading('current_value', text='Value', anchor='center')
        self.tree.heading('effect_name', text='Effect Name', anchor='w')
        
        self.tree.column('card', width=250)
        self.tree.column('level', width=60, anchor='center')
        self.tree.column('current_value', width=80, anchor='center')
        self.tree.column('effect_name', width=150)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status Label
        self.status_label = tk.Label(results_frame, text="", bg=BG_MEDIUM, fg=TEXT_SECONDARY, font=FONT_SMALL)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

    def parse_value(self, value_str):
        """Parse effect value string to float for sorting"""
        try:
            # Extract number from string (e.g. "20%" -> 20, "+15" -> 15)
            # Remove non-numeric characters except . and -
            clean = re.sub(r'[^\d.-]', '', str(value_str))
            return float(clean)
        except:
            return -999999.0 # Sort to bottom if invalid

    def perform_search(self):
        """Execute search and update results"""
        term = self.search_var.get().strip()
        if not term:
            messagebox.showwarning("Search", "Please enter a search term")
            return
            
        # clear current
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Query DB
        results = search_owned_effects(term)
        
        if not results:
            self.status_label.config(text="No matching effects found among owned cards.")
            return
            
        # Process and Sort
        # Row: (card_id, card_name, image_path, effect_name, effect_value, level)
        processed_results = []
        for r in results:
            val_num = self.parse_value(r[4])
            processed_results.append({
                'data': r,
                'sort_val': val_num
            })
            
        # Sort by value descending
        processed_results.sort(key=lambda x: x['sort_val'], reverse=True)
        
        # Populate Tree
        for item in processed_results:
            r = item['data']
            #Columns: card, level, current_value, effect_name
            values = (r[1], f"Lv {r[5]}", r[4], r[3])
            self.tree.insert('', tk.END, values=values)
            
        self.status_label.config(text=f"Found {len(processed_results)} owned cards with matching effects.")
    
    # Compatibility methods for main_window integration (empty as we don't need them anymore)
    def set_card(self, card_id):
        pass

