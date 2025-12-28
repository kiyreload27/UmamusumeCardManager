"""
Effects View - Display support effects at all levels with interactive slider
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_effects, get_effects_at_level, get_unique_effect_names, get_card_by_id
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_MONO,
    create_styled_button, create_styled_text, create_card_frame,
    EFFECT_DESCRIPTIONS
)


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
        header_frame = tk.Frame(self, bg=BG_DARK)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        self.card_label = tk.Label(header_frame, text="📊 Select a card from the Card List tab",
                                   font=FONT_HEADER, bg=BG_DARK, fg=ACCENT_PRIMARY)
        self.card_label.pack(side=tk.LEFT)
        
        # Legend Button
        legend_btn = create_styled_button(header_frame, text="❓ Legend", 
                                          command=self.show_legend, style_type='default')
        legend_btn.config(font=FONT_SMALL, padx=10, pady=4)
        legend_btn.pack(side=tk.RIGHT)
        
        # Level control frame
        control_frame = tk.Frame(self, bg=BG_MEDIUM, padx=15, pady=12)
        control_frame.pack(fill=tk.X, padx=20)
        
        # Level label
        tk.Label(control_frame, text="Level:", font=FONT_BODY, 
                 bg=BG_MEDIUM, fg=TEXT_SECONDARY).pack(side=tk.LEFT)
        
        # Level display with increment/decrement buttons
        level_ctrl = tk.Frame(control_frame, bg=BG_MEDIUM)
        level_ctrl.pack(side=tk.LEFT, padx=15)
        
        # Decrement button
        dec_btn = tk.Button(level_ctrl, text="−", font=FONT_HEADER,
                           bg=BG_LIGHT, fg=TEXT_PRIMARY, bd=0, width=2,
                           activebackground=BG_HIGHLIGHT, cursor='hand2',
                           command=self.decrement_level)
        dec_btn.pack(side=tk.LEFT)
        
        self.level_var = tk.IntVar(value=50)
        self.level_display = tk.Label(level_ctrl, text="50", width=4, font=FONT_HEADER,
                                      bg=BG_LIGHT, fg=ACCENT_PRIMARY, padx=10)
        self.level_display.pack(side=tk.LEFT, padx=2)
        
        # Increment button
        inc_btn = tk.Button(level_ctrl, text="+", font=FONT_HEADER,
                           bg=BG_LIGHT, fg=TEXT_PRIMARY, bd=0, width=2,
                           activebackground=BG_HIGHLIGHT, cursor='hand2',
                           command=self.increment_level)
        inc_btn.pack(side=tk.LEFT)
        
        # Quick level buttons
        button_frame = tk.Frame(control_frame, bg=BG_MEDIUM)
        button_frame.pack(side=tk.LEFT, padx=25)
        
        quick_levels = [1, 25, 40, 50]
        for lvl in quick_levels:
            btn = create_styled_button(button_frame, text=f"Lv{lvl}",
                                       command=lambda l=lvl: self.set_level(l),
                                       style_type='default')
            btn.config(width=5, font=FONT_SMALL, padx=6, pady=3)
            btn.pack(side=tk.LEFT, padx=3)
        
        # Main content area
        content_frame = tk.Frame(self, bg=BG_DARK)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Left: Current level effects
        left_frame = ttk.LabelFrame(content_frame, text="  Current Level Effects  ", padding=12)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.current_effects = create_styled_text(left_frame, height=15)
        self.current_effects.pack(fill=tk.BOTH, expand=True)
        self.current_effects.config(state=tk.DISABLED)
        
        # Right: Effect progression table
        right_frame = ttk.LabelFrame(content_frame, text="  Effect Progression  ", padding=12)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Treeview for effect table
        columns = ('effect', 'lv1', 'lv25', 'lv40', 'lv50')
        self.effects_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=12)
        
        self.effects_tree.heading('effect', text='Effect', anchor='w')
        self.effects_tree.column('effect', width=140, minwidth=120)
        
        for col in columns[1:]:
            level = col.replace('lv', 'Lv ')
            self.effects_tree.heading(col, text=level)
            self.effects_tree.column(col, width=65, anchor='center')
        
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.effects_tree.yview)
        self.effects_tree.configure(yscrollcommand=scrollbar.set)
        
        self.effects_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def show_legend(self):
        """Show effect explanations"""
        legend = {
            "Friendship Bonus": "Increases stats gained when training with this support card during Friendship Training (orange aura).",
            "Motivation Bonus": "Increases stats gained based on your Uma's motivation level.",
            "Specialty Rate": "Increases the chance of this card appearing in its specialty training.",
            "Training Bonus": "Flat percentage increase to stats gained in training where this card is present.",
            "Initial Bond": "Starting gauge value for this card.",
            "Race Bonus": "Increases stats gained from racing.",
            "Fan Count Bonus": "Increases fans gained from racing.",
            "Skill Pt Bonus": "Bonus skill points gained when training with this card.",
            "Hint Lv": "Starting level of skills taught by this card's hints.",
            "Hint Rate": "Increases chance of getting a hint event."
        }
        
        text = "📖 Effect Explanations:\n\n"
        for name, desc in legend.items():
            text += f"• {name}:\n  {desc}\n\n"
            
        messagebox.showinfo("Effect Legend", text)

    def set_card(self, card_id):
        """Load a card's effects"""
        self.current_card_id = card_id
        
        # Get card info for max level
        card = get_card_by_id(card_id)
        if card:
            self.current_card_name = card[1]
            self.max_level = card[4]
            if self.level_var.get() > self.max_level:
                self.level_var.set(self.max_level)
                self.level_display.config(text=str(self.max_level))
            
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
    
    def increment_level(self):
        """Increase level by 1"""
        current = self.level_var.get()
        if current < self.max_level:
            self.set_level(current + 1)
    
    def decrement_level(self):
        """Decrease level by 1"""
        current = self.level_var.get()
        if current > 1:
            self.set_level(current - 1)
    
    def update_current_effects(self):
        """Update the current level effects display"""
        self.current_effects.config(state=tk.NORMAL)
        self.current_effects.delete('1.0', tk.END)
        
        # Configure tags
        self.current_effects.tag_configure('header', font=FONT_SUBHEADER, foreground=ACCENT_PRIMARY)
        self.current_effects.tag_configure('highlight', foreground=ACCENT_SUCCESS)
        self.current_effects.tag_configure('effect_name', foreground=TEXT_SECONDARY)
        self.current_effects.tag_configure('effect_value', foreground=TEXT_PRIMARY, font=FONT_BODY_BOLD)
        self.current_effects.tag_configure('effect_tooltip', underline=False)
        
        if not self.current_card_id:
            self.current_effects.insert(tk.END, "No card selected\n\n", 'effect_name')
            self.current_effects.insert(tk.END, "Select a card from the Card List tab to view its effects.", 'effect_name')
            self.current_effects.config(state=tk.DISABLED)
            return
        
        level = self.level_var.get()
        effects = get_effects_at_level(self.current_card_id, level)
        
        self.current_effects.insert(tk.END, f"━━━ Level {level} ━━━\n\n", 'header')
        
        if effects:
            for name, value in effects:
                # Highlight high values
                prefix = ""
                if '%' in str(value):
                    try:
                        num = int(str(value).replace('%', '').replace('+', ''))
                        if num >= 20:
                            prefix = "★ "
                    except:
                        pass
                
                if prefix:
                    self.current_effects.insert(tk.END, prefix, 'highlight')
                
                # Insert effect name with tooltip tag
                tag_name = f"tooltip_{name.replace(' ', '_')}"
                self.current_effects.insert(tk.END, f"{name}: ", ('effect_name', tag_name))
                
                # Bind tooltip events
                self.current_effects.tag_bind(tag_name, "<Enter>", lambda e, n=name: self.show_effect_tooltip(e, n))
                self.current_effects.tag_bind(tag_name, "<Leave>", self.hide_effect_tooltip)
                
                self.current_effects.insert(tk.END, f"{value}\n", 'effect_value')
        else:
            self.current_effects.insert(tk.END, "No effect data available for this level.\n\n", 'effect_name')
            self.current_effects.insert(tk.END, "Try selecting: Lv 1, 25, 40, or 50", 'effect_name')
        
        self.current_effects.config(state=tk.DISABLED)

    def show_effect_tooltip(self, event, effect_name):
        """Show tooltip for effect"""
        if effect_name in EFFECT_DESCRIPTIONS:
            text = EFFECT_DESCRIPTIONS[effect_name]
            x = event.x_root + 15
            y = event.y_root + 10
            
            # Close existing if any
            self.hide_effect_tooltip(None)
            
            self.tooltip_window = tk.Toplevel(self)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tooltip_window, text=text, justify=tk.LEFT,
                             background=BG_LIGHT, foreground=TEXT_PRIMARY,
                             relief=tk.SOLID, borderwidth=1, font=FONT_SMALL,
                             padx=10, pady=5, wraplength=250)
            label.pack()

    def hide_effect_tooltip(self, event):
        """Hide tooltip"""
        if hasattr(self, 'tooltip_window') and self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
    
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
