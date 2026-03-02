"""
Effects Search View - Search for effects across all owned cards
Redesigned with modern grids and cards
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import sys
import os
import re
from PIL import Image

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
        self.result_widgets = []
        self.create_widgets()
        
    def create_widgets(self):
        """Create the effects search interface"""
        # Header / Search Bar area
        header_frame = create_card_frame(self)
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        # Search container
        search_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        search_container.pack(fill=tk.X, padx=20, pady=20)
        
        ctk.CTkLabel(search_container, text="🔍 Search Effect:", 
                  font=FONT_HEADER, text_color=TEXT_PRIMARY).pack(side=tk.LEFT, padx=(0, 15))
        
        self.search_var = tk.StringVar()
        self.search_entry = create_styled_entry(search_container, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))
        self.search_entry.bind('<Return>', lambda e: self.perform_search())
        
        search_btn = create_styled_button(search_container, text="Search", 
                                          command=self.perform_search, style_type='accent')
        search_btn.pack(side=tk.LEFT)
        
        # Example/Help text
        help_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        help_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        ctk.CTkLabel(help_frame, text="Examples: Friendship, Motivation, Race Bonus, Skill Pt", 
                  font=FONT_SMALL, text_color=TEXT_MUTED).pack(side=tk.LEFT)

        # Results Area
        self.results_container = create_card_frame(self)
        self.results_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        header_label_frame = ctk.CTkFrame(self.results_container, fg_color="transparent")
        header_label_frame.pack(fill=tk.X, padx=20, pady=(15, 5))
        
        ctk.CTkLabel(header_label_frame, text="Search Results", 
                     font=FONT_SUBHEADER, text_color=ACCENT_PRIMARY).pack(side=tk.LEFT)
        
        self.status_label = ctk.CTkLabel(header_label_frame, text="", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.status_label.pack(side=tk.RIGHT)
        
        # Scrollable Grid Replacing Treeview
        self.scroll_area = ctk.CTkScrollableFrame(self.results_container, fg_color="transparent")
        self.scroll_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 15))
        
        # Set up grid column weights
        self.scroll_area.columnconfigure(0, weight=1)
        self.scroll_area.columnconfigure(1, weight=1)
        self.scroll_area.columnconfigure(2, weight=1)

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
        for widget in self.result_widgets:
            widget.destroy()
        self.result_widgets.clear()
            
        # Query DB
        results = search_owned_effects(term)
        
        if not results:
            self.status_label.configure(text="No matching effects found among owned cards.")
            return
            
        # Process and Sort
        processed_results = []
        for r in results:
            val_num = self.parse_value(r[4])
            processed_results.append({'data': r, 'sort_val': val_num})
            
        processed_results.sort(key=lambda x: x['sort_val'], reverse=True)
        
        # Populate Grid
        row, col = 0, 0
        for item in processed_results:
            r = item['data']
            
            card_id, card_name, image_path, effect_name, effect_value, level = r
            
            # Result Card Widget
            card_frame = ctk.CTkFrame(self.scroll_area, fg_color=BG_DARK, corner_radius=10, border_width=1, border_color=BG_HIGHLIGHT)
            card_frame.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
            self.result_widgets.append(card_frame)
            
            # Load Image
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(image_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((70, 70), Image.Resampling.LANCZOS)
                        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(70, 70))
                        self.icon_cache[card_id] = img
                    except:
                        pass
            
            img_label = ctk.CTkLabel(card_frame, text="", image=img if img else None, width=70, height=70, corner_radius=8)
            img_label.pack(side=tk.LEFT, padx=10, pady=10)
            
            info_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=10, padx=(0, 10))
            
            # Build text content
            header_box = ctk.CTkFrame(info_frame, fg_color="transparent")
            header_box.pack(fill=tk.X)
            
            ctk.CTkLabel(header_box, text=card_name, font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, anchor="w").pack(side=tk.LEFT)
            ctk.CTkLabel(header_box, text=f"Lv {level}", font=FONT_SMALL, text_color=TEXT_MUTED).pack(side=tk.RIGHT)
            
            effect_box = ctk.CTkFrame(info_frame, fg_color="transparent", corner_radius=6)
            effect_box.pack(fill=tk.X, pady=(8, 0))
            
            ctk.CTkLabel(effect_box, text=effect_name, font=FONT_BODY, text_color=TEXT_SECONDARY, anchor="w").pack(side=tk.LEFT)
            
            # Highlight value
            val_lbl = ctk.CTkLabel(effect_box, text=str(effect_value), font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY)
            val_lbl.pack(side=tk.RIGHT)
            
            col += 1
            if col > 2:
                col = 0
                row += 1
            
        self.status_label.configure(text=f"Found {len(processed_results)} matches.")
    
    # Compatibility methods for main_window integration
    def set_card(self, card_id):
        pass
