"""
Effects Search View - Search for effects across all owned cards
Updated for CustomTkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import sys
import os
import re
from PIL import Image, ImageTk  # Added missing import

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import search_owned_effects
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL,
    create_styled_button, create_styled_entry, create_card_frame
)
from utils import resolve_image_path

class EffectsFrame(ctk.CTkFrame):
    """Frame for searching effects across owned cards"""
    
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.icon_cache = {}
        self.create_widgets()
        
    def create_widgets(self):
        """Create the effects search interface"""
        # Header / Search Bar
        header_frame = create_card_frame(self)
        header_frame.pack(fill=tk.X, padx=18, pady=(18, 10))
        
        # Search container
        search_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        search_container.pack(fill=tk.X)
        
        ctk.CTkLabel(search_container, text="🔍 Search Effect:", 
                  font=FONT_HEADER, text_color=TEXT_PRIMARY).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(search_container, textvariable=self.search_var, width=300)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self.perform_search())
        
        search_btn = create_styled_button(search_container, text="Search", 
                                          command=self.perform_search, style_type='accent')
        search_btn.pack(side=tk.LEFT)
        
        # Example/Help text
        help_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        help_frame.pack(fill=tk.X, pady=(5, 0))
        ctk.CTkLabel(help_frame, text="Examples: Friendship, Motivation, Race Bonus, Skill Pt", 
                  font=FONT_SMALL, text_color=TEXT_MUTED).pack(side=tk.LEFT)

        # Results Area
        results_container = create_card_frame(self)
        results_container.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
        
        # Label for the frame
        ctk.CTkLabel(results_container, text="Search Results (Owned Cards)", 
                     font=FONT_SUBHEADER, text_color=ACCENT_PRIMARY).pack(pady=(10, 5))
        
        # Treeview Container
        tree_frame = ctk.CTkFrame(results_container, fg_color="transparent")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Treeview - ADDING IMAGE COLUMN
        # Note: Treeview column #0 is the tree column where icons live.
        # We will put the image in #0 and text in #0 if possible, or name in #1
        # Treeview - ADDING IMAGE COLUMN
        # Use #0 for Icon only, like Card View
        columns = ('card_name', 'level', 'current_value', 'effect_name')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', selectmode='browse', style="CardList.Treeview")
        
        self.tree.heading('#0', text='Image')
        self.tree.column('#0', width=100, anchor='center')
        
        self.tree.heading('card_name', text='Card Name', anchor='w')
        self.tree.heading('level', text='Level', anchor='center')
        self.tree.heading('current_value', text='Value', anchor='center')
        self.tree.heading('effect_name', text='Effect Name', anchor='w')
        
        self.tree.column('card_name', width=200)
        self.tree.column('level', width=60, anchor='center')
        self.tree.column('current_value', width=80, anchor='center')
        self.tree.column('effect_name', width=200)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        # ... (rest of scrollbar setup) ...
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status Label
        self.status_label = ctk.CTkLabel(results_container, text="", font=FONT_SMALL, text_color=TEXT_SECONDARY)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 10))

    def parse_value(self, value_str):
        """Parse effect value string to float for sorting"""
        try:
            clean = re.sub(r'[^\d.-]', '', str(value_str))
            return float(clean)
        except:
            return -999999.0

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
            self.status_label.configure(text="No matching effects found among owned cards.")
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
            
            card_id = r[0]
            image_path = r[2]
            
            # Load Image
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(image_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        # Match CardList size
                        pil_img.thumbnail((78, 78), Image.Resampling.LANCZOS)
                        img = ImageTk.PhotoImage(pil_img)
                        self.icon_cache[card_id] = img
                    except:
                        pass
            
            kv = {'image': img} if img else {}
            
            # Insert into tree
            # #0 = Image (Text '')
            # Cols = Name, Level, Value, Effect
            values = (r[1], f"Lv {r[5]}", r[4], r[3])
            
            self.tree.insert('', tk.END, text='', values=values, **kv)
            
        self.status_label.configure(text=f"Found {len(processed_results)} owned cards with matching effects.")
    
    # Compatibility methods for main_window integration
    def set_card(self, card_id):
        pass

