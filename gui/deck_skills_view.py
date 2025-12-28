"""
Deck Skills View - Detailed breakdown of all skills in a deck or for a single card
"""

import tkinter as tk
from tkinter import ttk
import sys
import os
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import (
    get_all_decks, get_deck_cards, get_card_by_id, 
    get_hints, get_all_event_skills
)
from utils import resolve_image_path
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL,
    create_card_frame, get_type_icon
)


class DeckSkillsFrame(ttk.Frame):
    """Frame for viewing combined skills of a deck or individual cards"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.icon_cache = {}
        self.current_mode = "Deck" # or "Single"
        
        self.create_widgets()
        self.refresh_decks()
    
    def create_widgets(self):
        """Create the deck skills interface"""
        # Header / Controls
        ctrl_frame = tk.Frame(self, bg=BG_DARK)
        ctrl_frame.pack(fill=tk.X, padx=20, pady=15)
        
        # Left side: Mode/Deck selection
        selection_frame = tk.Frame(ctrl_frame, bg=BG_DARK)
        selection_frame.pack(side=tk.LEFT)
        
        tk.Label(selection_frame, text="🎴 Select Deck:", font=FONT_BODY, 
                 bg=BG_DARK, fg=TEXT_SECONDARY).pack(side=tk.LEFT)
        
        self.deck_combo = ttk.Combobox(selection_frame, width=30, state='readonly')
        self.deck_combo.pack(side=tk.LEFT, padx=10)
        self.deck_combo.bind('<<ComboboxSelected>>', self.on_deck_selected)
        
        # Mode indicator/Description
        self.mode_label = tk.Label(ctrl_frame, text="Showing skills for selected deck", 
                                   font=FONT_HEADER, bg=BG_DARK, fg=ACCENT_PRIMARY)
        self.mode_label.pack(side=tk.RIGHT)
        
        # Main Results Tree
        tree_container = create_card_frame(self)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        cols = ('skill', 'rarity', 'source', 'details')
        self.tree = ttk.Treeview(tree_container, columns=cols, show='tree headings',
                                 style="Treeview")
        
        self.tree.heading('#0', text='★  Card / Skill')
        self.tree.heading('skill', text='Skill Name')
        self.tree.heading('rarity', text='Rarity')
        self.tree.heading('source', text='Source')
        self.tree.heading('details', text='Details / Other Event Skills')
        
        self.tree.column('#0', width=250, anchor='w')
        self.tree.column('skill', width=150)
        self.tree.column('rarity', width=50, anchor='center')
        self.tree.column('source', width=100)
        self.tree.column('details', width=450)
        
        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
        
        # Footer
        self.stats_label = tk.Label(self, text="", font=FONT_SMALL,
                                   bg=BG_DARK, fg=TEXT_MUTED)
        self.stats_label.pack(anchor='e', pady=5, padx=20)

    def refresh_decks(self):
        """Load decks into combobox"""
        decks = get_all_decks()
        self.deck_combo['values'] = [f"{d[0]}: {d[1]}" for d in decks]
        if decks:
            self.deck_combo.current(0)
            self.on_deck_selected(None)

    def on_deck_selected(self, event):
        """Handle deck selection"""
        selection = self.deck_combo.get()
        if not selection: return
        
        deck_id = int(selection.split(':')[0])
        deck_name = selection.split(': ')[1]
        
        self.current_mode = "Deck"
        self.mode_label.config(text=f"Deck: {deck_name}", fg=ACCENT_PRIMARY)
        self.show_deck_skills(deck_id)

    def show_deck_skills(self, deck_id):
        """Fetch and display all skills from a deck"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        deck_cards = get_deck_cards(deck_id)
        if not deck_cards:
            self.stats_label.config(text="Deck is empty")
            return
            
        total_skills = 0
        for card_row in deck_cards:
            slot_pos, level, card_id, name, rarity, card_type, image_path = card_row
            
            card_full = get_card_by_id(card_id)
            is_owned = bool(card_full[7]) if card_full else False
            
            # Create Parent Node for Card
            owned_mark = "★ " if is_owned else "   "
            parent_id = self.add_card_node(card_id, owned_mark, name, rarity, card_type, image_path)
            
            # 1. Hints
            hints = get_hints(card_id)
            for h_name, h_desc in hints:
                self.add_skill_row(parent_id, h_name, "Training Hint", h_desc)
                total_skills += 1
                
            # 2. Event Skills
            events = get_all_event_skills(card_id)
            for event in events:
                self.add_skill_row(parent_id, event['skill_name'], "Event", event['details'])
                total_skills += 1
                    
        self.stats_label.config(text=f"Found {total_skills} total skill sources in deck")

    def add_card_node(self, card_id, owned_mark, name, rarity, card_type, image_path):
        """Add a parent node for a card"""
        img = self.icon_cache.get(card_id)
        if not img:
            resolved_path = resolve_image_path(image_path)
            if resolved_path and os.path.exists(resolved_path):
                try:
                    pil_img = Image.open(resolved_path)
                    pil_img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                    img = ImageTk.PhotoImage(pil_img)
                    self.icon_cache[card_id] = img
                except: pass
        
        type_icon = get_type_icon(card_type)
        display_text = f"{owned_mark}{name}"
        
        # Parent row only needs display text and rarity (optional)
        iid = self.tree.insert('', tk.END, text=display_text, image=img, open=True,
                               values=("", rarity, f"{type_icon} {card_type}", ""))
        return iid

    def add_skill_row(self, parent_id, skill_name, source, details):
        """Add a child skill row to a card node"""
        values = (
            skill_name,
            "", # Rarity column empty for skills
            source,
            details
        )
        self.tree.insert(parent_id, tk.END, values=values)

    def set_card(self, card_id):
        """Show skills for a single card selection"""
        card = get_card_by_id(card_id)
        if not card: return
        
        card_id, name, rarity, card_type, max_level, url, image_path, is_owned, owned_level = card
        
        self.current_mode = "Single"
        self.mode_label.config(text=f"Card: {name}", fg=ACCENT_SECONDARY)
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        total_skills = 0
        
        # Create Parent Node
        owned_mark = "★ " if is_owned else "   "
        parent_id = self.add_card_node(card_id, owned_mark, name, rarity, card_type, image_path)
        
        # 1. Hints
        hints = get_hints(card_id)
        for h_name, h_desc in hints:
            self.add_skill_row(parent_id, h_name, "Training Hint", h_desc)
            total_skills += 1
            
        # 2. Event Skills
        events = get_all_event_skills(card_id)
        for event in events:
            self.add_skill_row(parent_id, event['skill_name'], "Event", event['details'])
            total_skills += 1
                
        self.stats_label.config(text=f"Showing {total_skills} skill sources for {name}")
