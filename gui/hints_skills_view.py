"""
Hints and Skills View - Display support hints and event skills
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_hints, get_events, get_all_event_skills, get_card_by_id


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
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.card_label = ttk.Label(header_frame, 
                                    text="💡 Select a card from the Card List tab",
                                    style='Header.TLabel')
        self.card_label.pack(side=tk.LEFT)
        
        # Main content with two columns
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left column: Hints
        hints_frame = ttk.LabelFrame(content_frame, text="🎯 Training Hints", padding=10)
        hints_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.hints_text = tk.Text(hints_frame, wrap=tk.WORD,
                                  bg='#16213e', fg='#eaeaea',
                                  font=('Segoe UI', 11),
                                  padx=15, pady=15, relief=tk.FLAT)
        self.hints_text.pack(fill=tk.BOTH, expand=True)
        self.hints_text.config(state=tk.DISABLED)
        
        # Add tag for styling
        self.hints_text.tag_configure('header', font=('Segoe UI', 12, 'bold'), foreground='#e94560')
        self.hints_text.tag_configure('skill', foreground='#4ecdc4')
        
        # Right column: Events and Skills
        events_frame = ttk.LabelFrame(content_frame, text="📅 Training Events & Skills", padding=10)
        events_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Treeview for events
        self.events_tree = ttk.Treeview(events_frame, columns=('event', 'skills'), show='tree headings')
        self.events_tree.heading('#0', text='Type')
        self.events_tree.heading('event', text='Event/Skill')
        self.events_tree.heading('skills', text='Details')
        
        self.events_tree.column('#0', width=30)
        self.events_tree.column('event', width=250)
        self.events_tree.column('skills', width=200)
        
        scrollbar = ttk.Scrollbar(events_frame, orient=tk.VERTICAL, command=self.events_tree.yview)
        self.events_tree.configure(yscrollcommand=scrollbar.set)
        
        self.events_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary section at bottom
        summary_frame = ttk.Frame(self)
        summary_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.summary_label = ttk.Label(summary_frame, text="", style='Subtitle.TLabel')
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
            self.hints_text.insert(tk.END, "No card selected\n")
            self.hints_text.config(state=tk.DISABLED)
            return
        
        hints = get_hints(self.current_card_id)
        
        self.hints_text.insert(tk.END, "Training Skills this card can teach:\n\n", 'header')
        
        if hints:
            for i, (hint_name, hint_desc) in enumerate(hints, 1):
                self.hints_text.insert(tk.END, f"  {i}. ", 'skill')
                self.hints_text.insert(tk.END, f"{hint_name}\n")
                if hint_desc:
                    self.hints_text.insert(tk.END, f"      {hint_desc}\n")
                self.hints_text.insert(tk.END, "\n")
        else:
            self.hints_text.insert(tk.END, "  No hints/skills data available.\n\n")
            self.hints_text.insert(tk.END, "  This may mean:\n")
            self.hints_text.insert(tk.END, "  • Card hasn't been scraped yet\n")
            self.hints_text.insert(tk.END, "  • Card has no trainable skills\n")
        
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
            text=f"📊 Summary: {hint_count} hints | {event_count} events"
        )
