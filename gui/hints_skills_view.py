"""
Hints and Skills View - Display support hints and event skills
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_hints, get_events, get_all_event_skills, get_card_by_id
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY, ACCENT_SUCCESS,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL,
    create_styled_text, create_card_frame
)


class HintsSkillsFrame(ttk.Frame):
    """Frame for viewing support hints and event skills"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.current_card_id = None
        self.current_card_name = None
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create the hints and skills interface"""
        # Header
        header_frame = tk.Frame(self, bg=BG_DARK)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        self.card_label = tk.Label(header_frame, 
                                   text="💡 Select a card from the Card List tab",
                                   font=FONT_HEADER, bg=BG_DARK, fg=ACCENT_PRIMARY)
        self.card_label.pack(side=tk.LEFT)
        
        # Main content with two columns
        content_frame = tk.Frame(self, bg=BG_DARK)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        # Left column: Hints
        left_container = tk.Frame(content_frame, bg=BG_DARK)
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        hints_header = tk.Frame(left_container, bg=BG_DARK)
        hints_header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(hints_header, text="🎯 Training Hints", font=FONT_SUBHEADER,
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        hints_frame = create_card_frame(left_container)
        hints_frame.pack(fill=tk.BOTH, expand=True)
        
        self.hints_text = create_styled_text(hints_frame, height=18)
        self.hints_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.hints_text.config(state=tk.DISABLED)
        
        # Configure tags for hints
        self.hints_text.tag_configure('header', font=FONT_SUBHEADER, foreground=ACCENT_PRIMARY)
        self.hints_text.tag_configure('skill', foreground=ACCENT_TERTIARY, font=FONT_BODY_BOLD)
        self.hints_text.tag_configure('desc', foreground=TEXT_MUTED)
        self.hints_text.tag_configure('number', foreground=ACCENT_SECONDARY)
        
        # Right column: Events and Skills
        right_container = tk.Frame(content_frame, bg=BG_DARK)
        right_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        events_header = tk.Frame(right_container, bg=BG_DARK)
        events_header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(events_header, text="📅 Training Events & Skills", font=FONT_SUBHEADER,
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        events_frame = create_card_frame(right_container)
        events_frame.pack(fill=tk.BOTH, expand=True)
        
        tree_container = tk.Frame(events_frame, bg=BG_MEDIUM)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Treeview for events
        self.events_tree = ttk.Treeview(tree_container, columns=('event', 'skills'), show='tree headings')
        self.events_tree.heading('#0', text='')
        self.events_tree.heading('event', text='Event/Skill')
        self.events_tree.heading('skills', text='Details')
        
        self.events_tree.column('#0', width=35)
        self.events_tree.column('event', width=240)
        self.events_tree.column('skills', width=180)
        
        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.events_tree.yview)
        self.events_tree.configure(yscrollcommand=scrollbar.set)
        
        self.events_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary section at bottom
        summary_frame = tk.Frame(self, bg=BG_MEDIUM, padx=15, pady=10)
        summary_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.summary_label = tk.Label(summary_frame, text="", font=FONT_SMALL,
                                      bg=BG_MEDIUM, fg=TEXT_SECONDARY)
        self.summary_label.pack()
    
    def set_card(self, card_id):
        """Load a card's hints and skills"""
        self.current_card_id = card_id
        
        # Get card info
        card = get_card_by_id(card_id)
        if card:
             self.current_card_name = card[1]
             self.card_label.config(text=f"💡 {self.current_card_name}")
        
        self.update_hints_display()
        self.update_events_display()
    
    def update_hints_display(self):
        """Update the hints display"""
        self.hints_text.config(state=tk.NORMAL)
        self.hints_text.delete('1.0', tk.END)
        
        if not self.current_card_id:
            self.hints_text.insert(tk.END, "No card selected\n\n", 'desc')
            self.hints_text.insert(tk.END, "Select a card from the Card List tab to view its hints.", 'desc')
            self.hints_text.config(state=tk.DISABLED)
            return
        
        hints = get_hints(self.current_card_id)
        
        self.hints_text.insert(tk.END, "Training Skills this card can teach:\n\n", 'header')
        
        if hints:
            for i, (hint_name, hint_desc) in enumerate(hints, 1):
                self.hints_text.insert(tk.END, f"  {i}. ", 'number')
                self.hints_text.insert(tk.END, f"{hint_name}\n", 'skill')
                if hint_desc:
                    self.hints_text.insert(tk.END, f"      {hint_desc}\n", 'desc')
                self.hints_text.insert(tk.END, "\n")
        else:
            self.hints_text.insert(tk.END, "  No hints/skills data available.\n\n", 'desc')
            self.hints_text.insert(tk.END, "  This may mean:\n", 'desc')
            self.hints_text.insert(tk.END, "  • Card hasn't been scraped yet\n", 'desc')
            self.hints_text.insert(tk.END, "  • Card has no trainable skills\n", 'desc')
        
        self.hints_text.config(state=tk.DISABLED)
    
    def update_events_display(self):
        """Update the events tree display"""
        self.events_tree.delete(*self.events_tree.get_children())
        
        if not self.current_card_id:
            return
        
        events = get_events(self.current_card_id)
        events_with_skills = get_all_event_skills(self.current_card_id)
        
        # Add events as parent nodes
        for event_id, event_name, event_type in events:
            skills = events_with_skills.get(event_name, [])
            skill_count = f"{len(skills)} skills" if skills else "No skills"
            
            event_node = self.events_tree.insert('', tk.END, text='📅',
                                                  values=(event_name, skill_count))
            
            # Add skills as children
            for skill in skills:
                self.events_tree.insert(event_node, tk.END, text='⭐',
                                        values=(skill, ''))
        
        # Update summary
        hint_count = len(get_hints(self.current_card_id))
        event_count = len(events)
        
        self.summary_label.config(
            text=f"📊 Summary: {hint_count} hints  │  {event_count} events"
        )
