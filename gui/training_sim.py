"""
Training Simulator View - Estimate training gains
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_decks, get_deck_combined_effects
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL,
    create_card_frame, create_styled_button
)

class TrainingSimFrame(ttk.Frame):
    """Frame for training simulation and calculus"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.current_deck_id = None
        self.deck_bonuses = {}
        
        self.create_widgets()
        self.refresh_decks()
        
    def create_widgets(self):
        """Create the simulation interface"""
        # Main layout: Top Controls, Bottom Results
        
        # === Controls Section ===
        controls_frame = tk.Frame(self, bg=BG_DARK)
        controls_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Deck Selection
        deck_group = tk.LabelFrame(controls_frame, text="1. Select Deck", 
                                   bg=BG_DARK, fg=ACCENT_PRIMARY, font=FONT_BODY_BOLD)
        deck_group.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        self.deck_combo = ttk.Combobox(deck_group, width=25, state='readonly')
        self.deck_combo.pack(padx=15, pady=15)
        self.deck_combo.bind('<<ComboboxSelected>>', self.on_deck_selected)
        
        # Motivation
        mood_group = tk.LabelFrame(controls_frame, text="2. Motivation", 
                                   bg=BG_DARK, fg=ACCENT_PRIMARY, font=FONT_BODY_BOLD)
        mood_group.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        self.mood_var = tk.StringVar(value="Perfect (x1.2)")
        moods = ["Perfect (x1.2)", "Good (x1.1)", "Normal (x1.0)", "Bad (x0.9)", "Terrible (x0.8)"]
        self.mood_combo = ttk.Combobox(mood_group, textvariable=self.mood_var, 
                                       values=moods, width=15, state='readonly')
        self.mood_combo.pack(padx=15, pady=15)
        self.mood_combo.bind('<<ComboboxSelected>>', self.recalculate)
        
        # Facility Levels
        fac_group = tk.LabelFrame(controls_frame, text="3. Facility Levels", 
                                  bg=BG_DARK, fg=ACCENT_PRIMARY, font=FONT_BODY_BOLD)
        fac_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        slider_frame = tk.Frame(fac_group, bg=BG_DARK)
        slider_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.fac_vars = {}
        types = ['Speed', 'Stamina', 'Power', 'Guts', 'Wisdom']
        colors = [ACCENT_SECONDARY, ACCENT_SUCCESS, '#eab308', '#ef4444', ACCENT_TERTIARY]
        
        for i, (t, color) in enumerate(zip(types, colors)):
            f = tk.Frame(slider_frame, bg=BG_DARK)
            f.pack(side=tk.LEFT, expand=True, fill=tk.X)
            
            tk.Label(f, text=t, fg=color, bg=BG_DARK, font=FONT_SMALL).pack()
            
            var = tk.IntVar(value=1)
            self.fac_vars[t] = var
            scale = tk.Scale(f, from_=1, to=5, orient=tk.HORIZONTAL, variable=var,
                             bg=BG_DARK, fg=TEXT_SECONDARY, highlightthickness=0,
                             command=lambda v: self.recalculate())
            scale.pack(fill=tk.X, padx=5)

        # === Results Section ===
        results_container = tk.Frame(self, bg=BG_DARK)
        results_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        tk.Label(results_container, text="📊 Estimated Gains per Turn", 
                 font=FONT_HEADER, bg=BG_DARK, fg=TEXT_PRIMARY).pack(anchor='w', pady=(0, 10))
        
        # Grid Frame
        self.grid_frame = create_card_frame(results_container)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize Grid
        self.create_results_grid()

    def create_results_grid(self):
        """Build the results table grid"""
        # Headers
        headers = ["Stat", "Speed", "Stamina", "Power", "Guts", "Wisdom"]
        self.grid_frame.columnconfigure(0, weight=1) # Labels
        for i in range(1, 6):
            self.grid_frame.columnconfigure(i, weight=1)
            
            # Header Label
            tk.Label(self.grid_frame, text=headers[i], font=FONT_SUBHEADER,
                     bg=BG_LIGHT, fg=TEXT_PRIMARY,
                     pady=10).grid(row=0, column=i, sticky='nsew', padx=1, pady=1)

        # Row Labels
        row_labels = ["Speed", "Stamina", "Power", "Guts", "Wisdom", "Skill Pt", "Energy"]
        self.result_cells = {} # Map (row_name, col_name) -> widget
        
        for r, label in enumerate(row_labels, 1):
            # Row Header
            tk.Label(self.grid_frame, text=label, font=FONT_BODY_BOLD,
                     bg=BG_MEDIUM, fg=TEXT_SECONDARY,
                     padx=10).grid(row=r, column=0, sticky='nsew', padx=1, pady=1)
            
            for c, col_type in enumerate(["Speed", "Stamina", "Power", "Guts", "Wisdom"], 1):
                # Cell
                lbl = tk.Label(self.grid_frame, text="-", font=FONT_BODY,
                               bg=BG_DARK, fg=TEXT_PRIMARY)
                lbl.grid(row=r, column=c, sticky='nsew', padx=1, pady=1)
                self.result_cells[(label, col_type)] = lbl

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
        if selection:
            deck_id = int(selection.split(':')[0])
            self.current_deck_id = deck_id
            
            # Get bonuses
            effects = get_deck_combined_effects(deck_id)
            self.deck_bonuses = {k: v['total'] for k, v in effects.items()}
            
            self.recalculate()

    def recalculate(self, *args):
        """Calculate and update stats"""
        if not self.current_deck_id:
            return

        # 1. Get Environment
        mood_multi = float(self.mood_var.get().split('x')[1].replace(')', ''))
        
        # 2. Base Gains (URA Scenario approx)
        # Structure: {TrainingType: {Stat: BaseVal}}
        # Scaling with Facility Level (1-5)
        
        def get_base(train_type, level):
            # Approximation of base gains
            # Level scaling: approx +1 or +2 per level
            lvl_mod = level - 1
            
            base = {}
            if train_type == 'Speed':
                base = {'Speed': 10 + (lvl_mod*2), 'Power': 0 + (lvl_mod if lvl_mod>2 else 0)}
            elif train_type == 'Stamina':
                base = {'Stamina': 9 + (lvl_mod*2), 'Guts': 4 + lvl_mod}
            elif train_type == 'Power':
                base = {'Power': 9 + (lvl_mod*2), 'Stamina': 4 + lvl_mod}
            elif train_type == 'Guts':
                base = {'Guts': 8 + (lvl_mod*2), 'Speed': 4 + lvl_mod, 'Power': 3}
            elif train_type == 'Wisdom':
                base = {'Wisdom': 9 + (lvl_mod*2), 'Speed': 2}
            
            # Common Skill Pt
            base['Skill Pt'] = 2
            
            # Energy cost
            if train_type == 'Wisdom':
                base['Energy'] = 5 # Gain
            else:
                base['Energy'] = -20 # Loss (simplified)
                
            return base

        # 3. Calculate for each column (Training Type)
        types = ['Speed', 'Stamina', 'Power', 'Guts', 'Wisdom']
        
        for t_type in types:
            fac_level = self.fac_vars[t_type].get()
            base_stats = get_base(t_type, fac_level)
            
            # Apply Bonuses
            # Formula: (Base + StatBonus) * (1 + TrainingEffect%) * Mood
            
            train_effect_bonus = self.deck_bonuses.get('Training Effectiveness', 0) / 100.0
            # Motivation bonus (from deck) is complex, let's ignore for MVP sim
            
            for stat_row in ["Speed", "Stamina", "Power", "Guts", "Wisdom", "Skill Pt", "Energy"]:
                cell = self.result_cells[(stat_row, t_type)]
                
                if stat_row == 'Energy':
                    # Energy calculation
                    val = base_stats.get('Energy', 0)
                    if val < 0: # Usage
                        # Apply Energy Discount
                        discount = self.deck_bonuses.get('Energy Discount', 0) / 100.0
                        val = val * (1 - discount)
                    cell.config(text=f"{int(val)}", fg=ACCENT_SUCCESS if val > 0 else TEXT_MUTED)
                    continue
                
                base_val = base_stats.get(stat_row, 0)
                
                if base_val > 0:
                    # Apply Bonuses
                    stat_bonus = self.deck_bonuses.get(f'{stat_row} Bonus', 0)
                    
                    # Core calc
                    final = (base_val + stat_bonus) * (1 + train_effect_bonus) * mood_multi
                    
                    # Highlight good values
                    color = TEXT_PRIMARY
                    if final > 20: color = ACCENT_SUCCESS
                    if final > 30: color = ACCENT_SECONDARY 
                    if final > 40: color = ACCENT_PRIMARY
                    
                    cell.config(text=f"+{int(final)}", fg=color)
                else:
                    cell.config(text="-", fg=TEXT_MUTED)
