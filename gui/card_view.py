"""
Card List View - Browse and search support cards with ownership management
"""

import tkinter as tk
from tkinter import ttk
import sys
import os
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_cards, get_card_by_id, get_effects_at_level, set_card_owned, is_card_owned, update_owned_card_level
from utils import resolve_image_path
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_MONO,
    RARITY_COLORS, TYPE_COLORS, TYPE_ICONS,
    create_styled_button, create_styled_text, create_card_frame,
    get_rarity_color, get_type_color, get_type_icon,
    EFFECT_DESCRIPTIONS, Tooltip
)


class CardListFrame(ttk.Frame):
    """Frame containing card list with search/filter, ownership, and details panel"""
    
    def __init__(self, parent, on_card_selected_callback=None, on_stats_updated_callback=None):
        super().__init__(parent)
        self.on_card_selected = on_card_selected_callback
        self.on_stats_updated = on_stats_updated_callback
        self.cards = []
        self.current_card_id = None
        self.selected_level = 50
        self.card_image = None
        self.icon_cache = {}  # Cache for list icons
        
        # Create main layout
        self.create_widgets()
        self.load_cards()


    
    def create_widgets(self):
        """Create the card list interface"""
        # Main horizontal layout
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Card list with filters
        left_frame = ttk.Frame(main_pane, width=420)
        main_pane.add(left_frame, weight=1)
        
        # Right panel - Card details
        self.details_frame = ttk.Frame(main_pane)
        main_pane.add(self.details_frame, weight=2)
        
        # === Left Panel Contents ===
        
        # Initialize filter variables FIRST (before search trace can trigger filter_cards)
        self.rarity_var = tk.StringVar(value="All")
        self.type_var = tk.StringVar(value="All")
        self.owned_only_var = tk.BooleanVar(value=False)
        
        # Search bar with modern styling
        search_frame = tk.Frame(left_frame, bg=BG_DARK)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        search_icon = tk.Label(search_frame, text="🔍", font=FONT_BODY, bg=BG_DARK, fg=TEXT_MUTED)
        search_icon.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=35)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Set placeholder BEFORE adding the trace (so it doesn't trigger filter)
        self.search_entry.insert(0, "Search cards...")
        self.search_entry.config(foreground=TEXT_MUTED)
        self.search_entry.bind('<FocusIn>', self._on_search_focus_in)
        self.search_entry.bind('<FocusOut>', self._on_search_focus_out)
        
        # NOW add the trace (after placeholder is set)
        self.search_var.trace('w', lambda *args: self.filter_cards())
        
        # Filter dropdowns
        filter_frame = tk.Frame(left_frame, bg=BG_DARK)
        filter_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Rarity filter
        tk.Label(filter_frame, text="Rarity:", font=FONT_SMALL, bg=BG_DARK, fg=TEXT_MUTED).pack(side=tk.LEFT)
        rarity_combo = ttk.Combobox(filter_frame, textvariable=self.rarity_var,
                                    values=["All", "SSR", "SR", "R"], width=7, state='readonly')
        rarity_combo.pack(side=tk.LEFT, padx=(5, 15))
        rarity_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_cards())
        
        # Type filter
        tk.Label(filter_frame, text="Type:", font=FONT_SMALL, bg=BG_DARK, fg=TEXT_MUTED).pack(side=tk.LEFT)
        type_combo = ttk.Combobox(filter_frame, textvariable=self.type_var,
                                  values=["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"],
                                  width=10, state='readonly')
        type_combo.pack(side=tk.LEFT, padx=5)
        type_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_cards())
        
        # Owned only filter
        owned_check = ttk.Checkbutton(filter_frame, text="Owned Only", 
                                       variable=self.owned_only_var, command=self.filter_cards)
        owned_check.pack(side=tk.LEFT, padx=15)
        
        # Reset Button
        ttk.Button(filter_frame, text="Reset", command=self.reset_filters, 
                   style='Small.TButton', width=7).pack(side=tk.LEFT, padx=5)
        
        # Shortcuts
        self.bind_all('<Control-f>', lambda e: self.search_entry.focus_set())
        
        # Card count label
        self.count_label = tk.Label(left_frame, text="0 cards", font=FONT_SMALL, 
                                    bg=BG_DARK, fg=ACCENT_PRIMARY)
        self.count_label.pack(pady=5)
        
        # Card list (Treeview)
        list_frame = tk.Frame(left_frame, bg=BG_DARK)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.tree = ttk.Treeview(list_frame, columns=('owned', 'name', 'rarity', 'type'), 
                                  show='tree headings', selectmode='browse',
                                  style="CardList.Treeview")
                                  
        self.tree.heading('#0', text='')
        self.tree.column('#0', width=45, anchor='center')
        
        self.tree.heading('owned', text='★', command=lambda: self.sort_column('owned', False))
        self.tree.heading('name', text='Name', anchor='w', command=lambda: self.sort_column('name', False))
        self.tree.heading('rarity', text='Rarity', command=lambda: self.sort_column('rarity', False))
        self.tree.heading('type', text='Type', command=lambda: self.sort_column('type', False))
        
        self.tree.column('owned', width=30, anchor='center')
        self.tree.column('name', width=180, minwidth=150)
        self.tree.column('rarity', width=55, anchor='center')
        self.tree.column('type', width=90, anchor='center')
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        # Tag for owned cards
        self.tree.tag_configure('owned', background='#1a3a2e')
        
        # === Right Panel Contents (Details) ===
        self.create_details_panel()
    
    def create_details_panel(self):
        """Create the card details panel"""
        # Container with card-like appearance
        details_container = tk.Frame(self.details_frame, bg=BG_DARK)
        details_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Image area with card frame
        image_frame = create_card_frame(details_container, padx=10, pady=10)
        image_frame.pack(pady=10)
        
        self.image_label = tk.Label(image_frame, text="", bg=BG_MEDIUM)
        self.image_label.pack(padx=5, pady=5)
        
        # Header with card name
        self.detail_name = tk.Label(details_container, text="Select a card", 
                                    font=FONT_HEADER, bg=BG_DARK, fg=ACCENT_PRIMARY)
        self.detail_name.pack(pady=(10, 5))
        
        self.detail_info = tk.Label(details_container, text="", 
                                    font=FONT_SMALL, bg=BG_DARK, fg=TEXT_MUTED)
        self.detail_info.pack()
        
        # Owned checkbox with emphasis
        owned_frame = tk.Frame(details_container, bg=BG_DARK)
        owned_frame.pack(pady=15)
        
        self.owned_var = tk.BooleanVar(value=False)
        self.owned_checkbox = ttk.Checkbutton(owned_frame, text="✨ I Own This Card", 
                                               variable=self.owned_var, 
                                               command=self.toggle_owned,
                                               style='Large.TCheckbutton')
        self.owned_checkbox.pack(side=tk.LEFT)
        
        # Level selector with button-based control (no slider)
        level_frame = tk.Frame(details_container, bg=BG_DARK)
        level_frame.pack(fill=tk.X, padx=30, pady=10)
        
        tk.Label(level_frame, text="Card Level:", font=FONT_BODY, 
                 bg=BG_DARK, fg=TEXT_SECONDARY).pack(side=tk.LEFT)
        
        # Level display with increment/decrement
        level_ctrl = tk.Frame(level_frame, bg=BG_DARK)
        level_ctrl.pack(side=tk.LEFT, padx=15)
        
        self.level_var = tk.IntVar(value=50)
        self.max_level = 50
        self.valid_levels = [30, 35, 40, 45, 50] # Default SSR
        
        # Decrement button
        dec_btn = tk.Button(level_ctrl, text="−", font=FONT_HEADER,
                           bg=BG_LIGHT, fg=TEXT_PRIMARY, bd=0, width=2,
                           activebackground=BG_HIGHLIGHT, cursor='hand2',
                           command=self.decrement_level)
        dec_btn.pack(side=tk.LEFT)
        
        self.level_label = tk.Label(level_ctrl, text="50", width=4, font=FONT_HEADER,
                                    bg=BG_MEDIUM, fg=ACCENT_PRIMARY, padx=10)
        self.level_label.pack(side=tk.LEFT, padx=2)
        
        # Increment button
        inc_btn = tk.Button(level_ctrl, text="+", font=FONT_HEADER,
                           bg=BG_LIGHT, fg=TEXT_PRIMARY, bd=0, width=2,
                           activebackground=BG_HIGHLIGHT, cursor='hand2',
                           command=self.increment_level)
        inc_btn.pack(side=tk.LEFT)
        
        # Quick level buttons container
        self.level_btn_frame = tk.Frame(level_frame, bg=BG_DARK)
        self.level_btn_frame.pack(side=tk.LEFT, padx=20)
        
        self.level_buttons = {}
        # Initial population
        self.update_level_buttons('SSR', 50)
        
        # Effects display header
        effects_header = tk.Frame(details_container, bg=BG_DARK)
        effects_header.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        tk.Label(effects_header, text="📊 Effects at Current Level", 
                 font=FONT_SUBHEADER, bg=BG_DARK, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # Effects text area with modern styling
        effects_frame = create_card_frame(details_container)
        effects_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        self.effects_text = create_styled_text(effects_frame, height=10)
        self.effects_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.effects_text.config(state=tk.DISABLED)
    
    def load_cards(self):
        """Load all cards from database"""
        self.cards = get_all_cards()
        self.populate_tree(self.cards)
    
    def reset_filters(self):
        """Reset all filters to default"""
        self.search_var.set("")
        self.rarity_var.set("All")
        self.type_var.set("All")
        self.owned_only_var.set(False)
        # Reset placeholder
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, "Search cards...")
        self.search_entry.config(foreground=TEXT_MUTED)
        self.filter_cards()
    
    def _on_search_focus_in(self, event):
        """Clear placeholder on focus"""
        if self.search_entry.get() == "Search cards...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(foreground=TEXT_PRIMARY)
    
    def _on_search_focus_out(self, event):
        """Show placeholder if empty"""
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search cards...")
            self.search_entry.config(foreground=TEXT_MUTED)

    def filter_cards(self):
        """Filter cards based on search and dropdown values"""
        rarity = self.rarity_var.get() if self.rarity_var.get() != "All" else None
        card_type = self.type_var.get() if self.type_var.get() != "All" else None
        # Ignore placeholder text
        search_text = self.search_var.get().strip()
        search = search_text if search_text and search_text != "Search cards..." else None
        owned_only = self.owned_only_var.get()
        
        self.cards = get_all_cards(rarity_filter=rarity, type_filter=card_type, 
                                   search_term=search, owned_only=owned_only)
        self.populate_tree(self.cards)
    
    def sort_column(self, col, reverse):
        """Sort treeview by column"""
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        # Custom sort logic
        if col == 'owned':
             # Sort by star/empty
             l.sort(key=lambda t: t[0] if t[0] else "", reverse=reverse)
        elif col == 'rarity':
            # Sort by rarity rank (SSR > SR > R)
            rarity_map = {'SSR': 3, 'SR': 2, 'R': 1}
            l.sort(key=lambda t: rarity_map.get(t[0], 0), reverse=reverse)
        else:
            # Default string sort
            l.sort(reverse=reverse)
            
        # Rearrange items
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
            
        # Reverse sort next time
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
        
    def populate_tree(self, cards):
        """Populate treeview with cards"""
        self.tree.delete(*self.tree.get_children())
        
        for card in cards:
            card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level = card
            type_icon = get_type_icon(card_type)
            owned_mark = "★" if is_owned else ""
            tag = 'owned' if is_owned else ''
            
            # Show level for owned cards
            display_name = name
            if is_owned and owned_level:
                display_name = f"{name} (Lv{owned_level})"
            
            # Load Icon
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(image_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((48, 48), Image.Resampling.LANCZOS)
                        img = ImageTk.PhotoImage(pil_img)
                        self.icon_cache[card_id] = img
                    except:
                        pass
            
            if img:
                self.tree.insert('', tk.END, iid=card_id, text='', image=img,
                               values=(owned_mark, display_name, rarity, f"{type_icon} {card_type}"),
                               tags=(tag,))
            else:
                self.tree.insert('', tk.END, iid=card_id, text='', 
                               values=(owned_mark, display_name, rarity, f"{type_icon} {card_type}"),
                               tags=(tag,))
        
        self.count_label.config(text=f"✨ {len(cards)} cards")
    
    def on_select(self, event):
        """Handle card selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        card_id = int(selection[0])
        card = get_card_by_id(card_id)
        
        if card:
            card_id, name, rarity, card_type, max_level, url, image_path, is_owned, owned_level = card
            
            # Update owned checkbox
            self.owned_var.set(bool(is_owned))
            
            # Load card image if available
            self.load_card_image(image_path)
            
            # Use owned level if owned, otherwise max level or default 50
            initial_level = owned_level if is_owned and owned_level else max_level
            
            # Update level controls
            self.max_level = max_level
            self.update_level_buttons(rarity, max_level)
            
            # Snap initial level to valid levels
            if initial_level not in self.valid_levels:
                # Find closest or default to max
                initial_level = max_level
            
            self.level_var.set(initial_level)
            self.level_label.config(text=str(initial_level))
            self.selected_level = initial_level
            
            # Update details display with colors
            type_icon = get_type_icon(card_type)
            type_color = get_type_color(card_type)
            rarity_color = get_rarity_color(rarity)
            
            self.detail_name.config(text=f"{type_icon} {name}", fg=ACCENT_PRIMARY)
            self.detail_info.config(text=f"{rarity} │ {card_type} │ Max Level: {max_level}")
            
            # Load effects
            self.current_card_id = card_id
            self.update_effects_display()
            
            # Notify parent window
            if self.on_card_selected:
                self.on_card_selected(card_id, name, self.selected_level)
    
    def load_card_image(self, image_path):
        """Load and display card image"""
        resolved_path = resolve_image_path(image_path)
        
        if resolved_path and os.path.exists(resolved_path):
            try:
                img = Image.open(resolved_path)
                img.thumbnail((130, 130))  # Slightly larger
                self.card_image = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.card_image)
            except Exception as e:
                self.image_label.config(image='', text="[Image not found]")
        else:
            self.image_label.config(image='', text="")
    
    def toggle_owned(self):
        """Toggle owned status for current card"""
        if self.current_card_id:
            owned = self.owned_var.get()
            level = int(self.level_var.get())
            set_card_owned(self.current_card_id, owned, level)
            self.filter_cards()  # Refresh list to update owned markers
            
            # Notify parent to refresh stats
            if self.on_stats_updated:
                self.on_stats_updated()
    
    def update_level_buttons(self, rarity, max_level):
        """Update quick level buttons based on rarity/max level"""
        # Determine valid levels
        if max_level == 50: # SSR
            self.valid_levels = [30, 35, 40, 45, 50]
        elif max_level == 45: # SR
            self.valid_levels = [25, 30, 35, 40, 45]
        else: # R (max 40)
            self.valid_levels = [20, 25, 30, 35, 40]
            
        # Clear existing buttons
        for widget in self.level_btn_frame.winfo_children():
            widget.destroy()
        self.level_buttons = {}
        
        # Create new buttons
        for lvl in self.valid_levels:
            btn = create_styled_button(self.level_btn_frame, text=f"Lv{lvl}", 
                                       command=lambda l=lvl: self.set_level(l),
                                       style_type='default')
            btn.config(width=5, padx=6, pady=3, font=FONT_SMALL)
            btn.pack(side=tk.LEFT, padx=2)
            self.level_buttons[lvl] = btn

    def set_level(self, level):
        """Update selected level and notify callback"""
        if self.current_card_id:
            self.selected_level = level
            self.level_var.set(level)
            self.level_label.config(text=str(level))
            self.update_effects_display()
            
            # Notify parent window about level change
            if self.on_card_selected:
                card = get_card_by_id(self.current_card_id)
                if card:
                    self.on_card_selected(self.current_card_id, card[1], self.selected_level)
        
        # Save level if owned
        if self.current_card_id and self.owned_var.get():
             update_owned_card_level(self.current_card_id, level)
             self.update_tree_item_level(self.current_card_id, level)

    def increment_level(self):
        """Increase level to next valid step"""
        current = self.level_var.get()
        # Find next level in valid_levels
        for lvl in self.valid_levels:
            if lvl > current:
                self.set_level(lvl)
                return
    
    def decrement_level(self):
        """Decrease level to previous valid step"""
        current = self.level_var.get()
        # Find previous level in valid_levels
        for lvl in reversed(self.valid_levels):
            if lvl < current:
                self.set_level(lvl)
                return

    def update_tree_item_level(self, card_id, level):
        """Update visible name in tree without full reload"""
        if self.tree.exists(card_id):
            current_values = self.tree.item(card_id, 'values')
            if current_values:
                # current_values is a tuple: (owned_mark, name, rarity, type)
                # We need to strip existing " (LvXX)" from name if present
                name = current_values[1]
                base_name = name.split(" (Lv")[0]
                new_name = f"{base_name} (Lv{level})"
                
                # Make new values tuple preserving other columns
                new_values = (current_values[0], new_name, current_values[2], current_values[3])
                self.tree.item(card_id, values=new_values)
                
    def update_effects_display(self):
        """Update the effects display for current card and level"""
        if not self.current_card_id:
            return
        
        level = int(self.level_var.get())
        effects = get_effects_at_level(self.current_card_id, level)
        
        self.effects_text.config(state=tk.NORMAL)
        self.effects_text.delete('1.0', tk.END)
        
        # Configure tags for styling
        self.effects_text.tag_configure('header', font=FONT_SUBHEADER, foreground=ACCENT_PRIMARY)
        self.effects_text.tag_configure('highlight', foreground=ACCENT_SUCCESS)
        self.effects_text.tag_configure('effect_name', foreground=TEXT_SECONDARY)
        self.effects_text.tag_configure('effect_value', foreground=TEXT_PRIMARY)
        self.effects_text.tag_configure('effect_tooltip', underline=False) 
        
        if effects:
            self.effects_text.insert(tk.END, f"━━━ Level {level} ━━━\n\n", 'header')
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
                    self.effects_text.insert(tk.END, prefix, 'highlight')
                
                # Insert effect name with tooltip tag
                tag_name = f"tooltip_{name.replace(' ', '_')}"
                self.effects_text.insert(tk.END, f"{name}: ", ('effect_name', tag_name))
                
                # Bind tooltip events
                self.effects_text.tag_bind(tag_name, "<Enter>", lambda e, n=name: self.show_effect_tooltip(e, n))
                self.effects_text.tag_bind(tag_name, "<Leave>", self.hide_effect_tooltip)
                
                self.effects_text.insert(tk.END, f"{value}\n", 'effect_value')
        else:
            self.effects_text.insert(tk.END, f"No effects data for Level {level}\n\n")
            self.effects_text.insert(tk.END, "Available levels: 1, 25, 40, 50\n", 'effect_name')
        
        self.effects_text.config(state=tk.DISABLED)

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
