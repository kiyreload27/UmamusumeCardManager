"""
Effects View - Display support effects at all levels with interactive slider
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_effects, get_effects_at_level, get_unique_effect_names, get_card_by_id


class EffectsFrame(ttk.Frame):
    """Frame for viewing support effects at different levels"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.current_card_id = None
        self.current_card_name = None
        self.max_level = 50
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create the effects view interface"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.card_label = ttk.Label(header_frame, text="📊 Select a card from the Card List tab", 
                                    style='Header.TLabel')
        self.card_label.pack(side=tk.LEFT)
        
        # Legend Button
        ttk.Button(header_frame, text="?", width=3, command=self.show_legend).pack(side=tk.RIGHT)
        
        # Level control frame
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Level slider
        ttk.Label(control_frame, text="Level:").pack(side=tk.LEFT)
        
        self.level_var = tk.IntVar(value=50)
        self.level_scale = ttk.Scale(control_frame, from_=1, to=50, orient=tk.HORIZONTAL,
                                     variable=self.level_var, length=400,
                                     command=self.on_level_change)
        self.level_scale.pack(side=tk.LEFT, padx=10)
        
        self.level_display = ttk.Label(control_frame, text="50", width=4, style='Header.TLabel')
        self.level_display.pack(side=tk.LEFT)
        
        # Quick level buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.LEFT, padx=20)
        
        quick_levels = [1, 25, 40, 50]
        for lvl in quick_levels:
            btn = ttk.Button(button_frame, text=str(lvl), width=4,
                           command=lambda l=lvl: self.set_level(l))
            btn.pack(side=tk.LEFT, padx=2)
        
        # Main content area
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left: Current level effects
        left_frame = ttk.LabelFrame(content_frame, text="Current Level Effects", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.current_effects = tk.Text(left_frame, wrap=tk.WORD, 
                                       bg='#16213e', fg='#eaeaea', 
                                       font=('Consolas', 12),
                                       padx=15, pady=15, relief=tk.FLAT)
        self.current_effects.pack(fill=tk.BOTH, expand=True)
        self.current_effects.config(state=tk.DISABLED)
        
        # Right: Effect progression table
        right_frame = ttk.LabelFrame(content_frame, text="Effect Progression", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Treeview for effect table
        columns = ('effect', 'lv1', 'lv25', 'lv40', 'lv50')
        self.effects_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=15)
        
        self.effects_tree.heading('effect', text='Effect', anchor='w')
        self.effects_tree.column('effect', width=150, minwidth=120)
        
        for col in columns[1:]:
            level = col.replace('lv', 'Lv ')
            self.effects_tree.heading(col, text=level)
            self.effects_tree.column(col, width=60, anchor='center')
        
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.effects_tree.yview)
        self.effects_tree.configure(yscrollcommand=scrollbar.set)
        
        self.effects_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def show_legend(self):
        """Show effect explanations"""
        legend = {
            "Friendship Bonus": "Increases stats gained when training with this support card during Friendship Training (orange aura).",
            "Motivation Bonus": "Increases stats gained based on your Uma's motivation level.",
            "Specialty Rate": "Increases the chance of this card appearing in its specialty training (e.g., Speed card in Speed training).",
            "Training Bonus": "Flat percentage increase to stats gained in training where this card is present.",
            "Initial Bond": "Starting gauge value for this card.",
            "Race Bonus": "Increases stats gained from racing.",
            "Fan Count Bonus": "Increases fans gained from racing.",
            "Skill Pt Bonus": "Bonus skill points gained when training with this card.",
            "Hint Lv": "Starting level of skills taught by this card's hints.",
            "Hint Rate": "Increases chance of getting a hint event."
        }
        
        text = "Effect Explanations:\n\n"
        for name, desc in legend.items():
            text += f"• {name}:\n  {desc}\n\n"
            
        messagebox.showinfo("Effect Legend", text)

    def set_card(self, card_id):
        """Load a card's effects"""
        self.current_card_id = card_id
        
        # Get card info for max level
        card = get_card_by_id(card_id)
        if card:
            # card structure likely: id, name, rarity, type, max_level, ...
            self.current_card_name = card[1]
            self.max_level = card[4]
            self.level_scale.config(to=self.max_level)
            if self.level_var.get() > self.max_level:
                self.level_var.set(self.max_level)
            
            self.card_label.config(text=f"📊 {self.current_card_name}")
        
        # Update displays
        self.update_current_effects()
        self.update_progression_table()
    
    def set_level(self, level):
        """Set level from quick button"""
        if level <= self.max_level:
            self.level_var.set(level)
            self.level_display.config(text=str(level))
            self.update_current_effects()
    
    def on_level_change(self, value):
        """Handle level slider change"""
        level = int(float(value))
        self.level_display.config(text=str(level))
        self.update_current_effects()
    
    def update_current_effects(self):
        """Update the current level effects display"""
        self.current_effects.config(state=tk.NORMAL)
        self.current_effects.delete('1.0', tk.END)
        
        if not self.current_card_id:
            self.current_effects.insert(tk.END, "No card selected\n")
            self.current_effects.config(state=tk.DISABLED)
            return
        
        level = self.level_var.get()
        effects = get_effects_at_level(self.current_card_id, level)
        
        self.current_effects.insert(tk.END, f"━━━ Level {level} ━━━\n\n")
        
        if effects:
            for name, value in effects:
                # Highlight high values
                if '%' in str(value):
                    try:
                        num = int(str(value).replace('%', '').replace('+', ''))
                        if num >= 20:
                            self.current_effects.insert(tk.END, f"★ ")
                    except:
                        pass
                self.current_effects.insert(tk.END, f"{name}: {value}\n")
        else:
            self.current_effects.insert(tk.END, "No effect data available\n")
        
        self.current_effects.config(state=tk.DISABLED)
    
    def update_progression_table(self):
        """Update the effect progression table"""
        self.effects_tree.delete(*self.effects_tree.get_children())
        
        if not self.current_card_id:
            return
        
        # Get all effects
        all_effects = get_all_effects(self.current_card_id)
        
        # Organize by effect name
        effect_by_level = {}
        for level, effect_name, effect_value in all_effects:
            if effect_name not in effect_by_level:
                effect_by_level[effect_name] = {}
            effect_by_level[effect_name][level] = effect_value
        
        # Key levels for the table
        key_levels = [1, 25, 40, 50]
        
        # Add rows
        for effect_name, levels in sorted(effect_by_level.items()):
            row = [effect_name]
            for lvl in key_levels:
                # Find closest level we have data for
                value = levels.get(lvl, '')
                if not value:
                    # Try to find nearest
                    for l in sorted(levels.keys()):
                        if l <= lvl:
                            value = levels[l]
                row.append(value)
            
            self.effects_tree.insert('', tk.END, values=row)
