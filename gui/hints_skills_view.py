"""
Skill Search View - Find cards by the skills they teach
"""

import tkinter as tk
from tkinter import ttk
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
    create_card_frame, get_type_icon, create_styled_button
)


class SkillSearchFrame(ttk.Frame):
    """Frame for searching skills and finding cards that have them"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.all_skills = []
        self.icon_cache = {}
        
        self.create_widgets()
        self.load_skills()
    
    def create_widgets(self):
        """Create the skill search interface"""
        # Main split container
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === Left Panel: Skill List ===
        left_frame = tk.Frame(main_pane, bg=BG_DARK, width=300)
        main_pane.add(left_frame, weight=1)
        
        # Search Header
        header = tk.Frame(left_frame, bg=BG_DARK)
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text="🔍 Search Skills", font=FONT_HEADER, 
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # Search Entry
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_skills)
        
        search_entry = ttk.Entry(left_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, padx=(0, 5), pady=(0, 10))
        
        # Skill Listbox
        list_container = create_card_frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
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
        right_frame = tk.Frame(main_pane, bg=BG_DARK)
        main_pane.add(right_frame, weight=3)
        
        # Result Header
        self.result_header = tk.Label(right_frame, text="Select a skill to see who has it", 
                                      font=FONT_HEADER, bg=BG_DARK, fg=ACCENT_TERTIARY)
        self.result_header.pack(anchor='w', pady=(0, 15), padx=10)
        
        # Results Treeview
        tree_frame = create_card_frame(right_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
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
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
        
        # Stats footer
        self.stats_label = tk.Label(right_frame, text="", font=FONT_SMALL,
                                   bg=BG_DARK, fg=TEXT_MUTED)
        self.stats_label.pack(anchor='e', pady=5, padx=10)

    def load_skills(self):
        """Load all unique skills into listbox"""
        self.all_skills = get_all_unique_skills()
        self.update_listbox(self.all_skills)
        
    def update_listbox(self, items):
        """Update listbox content"""
        self.skill_listbox.delete(0, tk.END)
        for item in items:
            self.skill_listbox.insert(tk.END, item)
            
    def filter_skills(self, *args):
        """Filter skills based on search text"""
        search = self.search_var.get().lower()
        if not search:
            self.update_listbox(self.all_skills)
            return
            
        filtered = [s for s in self.all_skills if search in s.lower()]
        self.update_listbox(filtered)
        
    def on_skill_selected(self, event):
        """Handle skill selection"""
        selection = self.skill_listbox.curselection()
        if not selection:
            return
            
        skill_name = self.skill_listbox.get(selection[0])
        self.show_cards_for_skill(skill_name)
        
    def show_cards_for_skill(self, skill_name):
        """Fetch and display cards with the selected skill"""
        self.result_header.config(text=f"Cards with skill: {skill_name}")
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        cards = get_cards_with_skill(skill_name)
        
        for card in cards:
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
            
            type_display = f"{get_type_icon(card['type'])} {card['type']}"
            owned_mark = "★" if card.get('is_owned') else ""
            
            values = (
                owned_mark,
                card['name'],
                card['rarity'],
                type_display,
                card['source'],
                card['details']
            )
            
            if img:
                self.tree.insert('', tk.END, text='', image=img, values=values)
            else:
                self.tree.insert('', tk.END, text='?', values=values)
                
        self.stats_label.config(text=f"Found {len(cards)} cards")

    def set_card(self, card_id):
        """
        Show all skills (Hints and Events) for a specific card.
        Called by main window when a card is selected in the list.
        """
        card = get_card_by_id(card_id)
        if not card: return
        
        card_name = card[1]
        self.result_header.config(text=f"Skills for: {card_name}")
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        all_skills = []
        
        # 1. Get Hints
        hints = get_hints(card_id)
        for h_name, h_desc in hints:
            all_skills.append({
                'card_id': card_id,
                'name': card_name,
                'rarity': card[2],
                'type': card[3],
                'image_path': card[6],
                'source': 'Training Hint',
                'details': f"{h_name}: {h_desc}",
                'is_owned': bool(card[7])
            })
            
        # 2. Get Event Skills
        event_dict = get_all_event_skills(card_id)
        for ev_name, skills in event_dict.items():
            all_skills.append({
                'card_id': card_id,
                'name': card_name,
                'rarity': card[2],
                'type': card[3],
                'image_path': card[6],
                'source': 'Event',
                'details': f"{ev_name} ({', '.join(skills)})",
                'is_owned': bool(card[7])
            })
            
        # Display them
        for skill in all_skills:
            img = self.icon_cache.get(skill['card_id'])
            if not img:
                resolved_path = resolve_image_path(skill['image_path'])
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                        img = ImageTk.PhotoImage(pil_img)
                        self.icon_cache[skill['card_id']] = img
                    except: pass
            
            type_display = f"{get_type_icon(skill['type'])} {skill['type']}"
            owned_mark = "★" if skill.get('is_owned') else ""
            
            values = (
                owned_mark,
                skill['name'],
                skill['rarity'],
                type_display,
                skill['source'],
                skill['details']
            )
            
            if img:
                self.tree.insert('', tk.END, text='', image=img, values=values)
            else:
                self.tree.insert('', tk.END, text='?', values=values)
                
        self.stats_label.config(text=f"Showing {len(all_skills)} skill sources for {card_name}")
