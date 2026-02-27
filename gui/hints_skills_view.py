"""
Skill Search View - Find cards by the skills they teach
Updated for CustomTkinter
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import sys
import os
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_unique_skills, get_cards_with_skill, get_card_by_id, get_hints, get_all_event_skills
from utils import resolve_image_path
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL,
    create_card_frame, get_type_icon, create_styled_button, create_styled_entry
)


class SkillSearchFrame(ctk.CTkFrame):
    """Frame for searching skills and finding cards that have them"""
    
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.all_skills = []
        self.icon_cache = {}
        self.current_skill = None
        
        self.create_widgets()
        self.load_skills()
    
    def create_widgets(self):
        """Create the skill search interface"""
        # Main split container
        # Use two frames instead of PanedWindow
        
        # === Left Panel: Skill List ===
        left_frame = create_card_frame(self, width=390)
        left_frame.pack_propagate(False) # Force width to stay 600
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        
        # Search Header
        header = ctk.CTkFrame(left_frame, fg_color="transparent")
        header.pack(fill=tk.X, pady=(15, 10), padx=10)
        ctk.CTkLabel(header, text="🔍 Search Skills", font=FONT_HEADER, 
                  text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # Search Entry
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_skills)
        
        # Use styled entry
        search_entry = ctk.CTkEntry(left_frame, textvariable=self.search_var, placeholder_text="Type to filter...")
        search_entry.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Skill Listbox Container (Styled)
        list_container = ctk.CTkFrame(left_frame, fg_color="transparent")
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Using tk.Listbox because CTk doesn't have one and ScrollableFrame is harder to manage for simple selection list
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.skill_listbox = tk.Listbox(list_container, 
                                        bg=BG_MEDIUM, fg=TEXT_SECONDARY,
                                        selectbackground=ACCENT_PRIMARY,
                                        selectforeground=TEXT_PRIMARY,
                                        highlightthickness=0, bd=0,
                                        font=FONT_BODY,
                                        yscrollcommand=scrollbar.set)
        
        scrollbar.config(command=self.skill_listbox.yview)
        
        self.skill_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.skill_listbox.bind('<<ListboxSelect>>', self.on_skill_selected)
        
        # === Right Panel: Results ===
        right_frame = create_card_frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Search Row (Search + Filter)
        search_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        search_frame.pack(fill=tk.X, padx=10, pady=15)
        
        self.result_header = ctk.CTkLabel(search_frame, text="Select a skill to see cards", 
                                       font=FONT_SUBHEADER, text_color=ACCENT_PRIMARY)
        self.result_header.pack(side=tk.LEFT)
        
        # Owned Filter
        self.owned_only_var = tk.BooleanVar(value=False)
        self.owned_check = ctk.CTkCheckBox(search_frame, text="Show Owned Only", 
                                           variable=self.owned_only_var, 
                                           command=self.on_filter_changed,
                                           font=FONT_SMALL)
        self.owned_check.pack(side=tk.RIGHT, padx=10)
        
        # Results Treeview Container
        tree_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        cols = ('owned', 'name', 'rarity', 'type', 'source', 'details')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='tree headings',
                                 style="Treeview")
        
        self.tree.heading('#0', text='')
        self.tree.heading('owned', text='★')
        self.tree.heading('name', text='Card Name')
        self.tree.heading('rarity', text='Rarity')
        self.tree.heading('type', text='Type')
        self.tree.heading('source', text='Source')
        self.tree.heading('details', text='Details')
        
        self.tree.column('#0', width=50, anchor='center')
        self.tree.column('owned', width=30, anchor='center')
        self.tree.column('name', width=180)
        self.tree.column('rarity', width=50, anchor='center')
        self.tree.column('type', width=80, anchor='center')
        self.tree.column('source', width=100)
        self.tree.column('details', width=250)
        
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Stats footer
        self.stats_label = ctk.CTkLabel(right_frame, text="", font=FONT_SMALL,
                                   text_color=TEXT_MUTED)
        self.stats_label.pack(anchor='e', pady=5, padx=10)

    def load_skills(self):
        """Load all unique skills into listbox"""
        skills_data = get_all_unique_skills()
        # Store as list of (skill_name, is_golden) tuples
        self.all_skills = skills_data
        self.update_listbox(skills_data)
        
    def update_listbox(self, items):
        """Update listbox content"""
        self.skill_listbox.delete(0, tk.END)
        for item in items:
            if isinstance(item, tuple):
                skill_name, is_golden = item
                # Display with golden indicator
                display_name = f"✨ GOLDEN {skill_name}" if is_golden else skill_name
                self.skill_listbox.insert(tk.END, display_name)
            else:
                # Backward compatibility
                self.skill_listbox.insert(tk.END, item)
            
    def filter_skills(self, *args):
        """Filter skills based on search text"""
        search = self.search_var.get().lower()
        if not search:
            self.update_listbox(self.all_skills)
            return
        
        # Filter skills - handle both tuple format and string format
        filtered = []
        for item in self.all_skills:
            if isinstance(item, tuple):
                skill_name, is_golden = item
                if search in skill_name.lower() or (search == "golden" and is_golden):
                    filtered.append(item)
            else:
                if search in item.lower():
                    filtered.append(item)
        
        self.update_listbox(filtered)
        
    def on_filter_changed(self):
        """Handle filter checkbox change"""
        if self.current_skill:
            self.show_cards_for_skill(self.current_skill)

    def on_skill_selected(self, event):
        """Handle skill selection from listbox"""
        selection = self.skill_listbox.curselection()
        if not selection:
            return
            
        display_name = self.skill_listbox.get(selection[0])
        # Extract actual skill name (remove "✨ GOLDEN " prefix if present)
        if display_name.startswith("✨ GOLDEN "):
            skill_name = display_name.replace("✨ GOLDEN ", "", 1)
        else:
            skill_name = display_name
        
        self.current_skill = skill_name
        self.show_cards_for_skill(skill_name)
    
    def show_cards_for_skill(self, skill_name):
        """Fetch and display cards with the selected skill"""
        self.current_skill = skill_name
        self.result_header.configure(text=f"Cards with skill: {skill_name}")
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        cards = get_cards_with_skill(skill_name)
        
        owned_only = self.owned_only_var.get()
        
        display_count = 0
        for card in cards:
            if owned_only and not card.get('is_owned'):
                continue
                
            display_count += 1
            # Load Icon
            card_id = card['card_id']
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(card['image_path'])
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                        img = ImageTk.PhotoImage(pil_img)
                        self.icon_cache[card_id] = img
                    except:
                        pass
            
            # Handle both 'type' and 'card_type' keys for compatibility
            card_type = card.get('type') or card.get('card_type') or 'Unknown'
            type_display = f"{get_type_icon(card_type)} {card_type}"
            owned_mark = "★" if card.get('is_owned') else ""
            
            # Highlight golden skills in source column
            source = card.get('source', 'Event')
            if card.get('is_gold', False):
                source = f"✨ GOLDEN {source.replace('✨ GOLDEN ', '')}"  # Ensure no double prefix
            
            # Handle potential None values
            card_name = card.get('name') or 'Unknown'
            card_rarity = card.get('rarity') or 'Unknown'
            card_details = card.get('details') or 'No details available'
            
            values = (
                owned_mark,
                card_name,
                card_rarity,
                type_display,
                source,
                card_details
            )
            
            kv = {'image': img} if img else {}
            self.tree.insert('', tk.END, text='', values=values, **kv)
                
        self.stats_label.configure(text=f"Found {display_count} cards")

    def set_card(self, card_id):
        """No longer responsive to card selection in this tab"""
        pass
