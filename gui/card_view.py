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

# Rarity colors
RARITY_COLORS = {
    'SSR': '#FFD700',  # Gold
    'SR': '#C0C0C0',   # Silver  
    'R': '#CD7F32'     # Bronze
}

# Type emojis
TYPE_ICONS = {
    'Speed': '🏃',
    'Stamina': '💚',
    'Power': '💪',
    'Guts': '🔥',
    'Wisdom': '🧠',
    'Friend': '💜',
    'Group': '👥'
}


class CardListFrame(ttk.Frame):
    """Frame containing card list with search/filter, ownership, and details panel"""
    
    def __init__(self, parent, on_card_selected_callback=None):
        super().__init__(parent)
        self.on_card_selected = on_card_selected_callback
        self.cards = []
        self.current_card_id = None
        self.card_image = None  # Keep reference to prevent garbage collection
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
        left_frame = ttk.Frame(main_pane, width=400)
        main_pane.add(left_frame, weight=1)
        
        # Right panel - Card details
        self.details_frame = ttk.Frame(main_pane)
        main_pane.add(self.details_frame, weight=2)
        
        # === Left Panel Contents ===
        
        # Search bar
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_cards())
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Filter dropdowns
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Rarity filter
        ttk.Label(filter_frame, text="Rarity:").pack(side=tk.LEFT)
        self.rarity_var = tk.StringVar(value="All")
        rarity_combo = ttk.Combobox(filter_frame, textvariable=self.rarity_var,
                                    values=["All", "SSR", "SR", "R"], width=8, state='readonly')
        rarity_combo.pack(side=tk.LEFT, padx=5)
        rarity_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_cards())
        
        # Type filter
        ttk.Label(filter_frame, text="Type:").pack(side=tk.LEFT, padx=(10, 0))
        self.type_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(filter_frame, textvariable=self.type_var,
                                  values=["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"],
                                  width=10, state='readonly')
        type_combo.pack(side=tk.LEFT, padx=5)
        type_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_cards())
        
        # Owned only filter
        self.owned_only_var = tk.BooleanVar(value=False)
        owned_check = ttk.Checkbutton(filter_frame, text="Owned Only", 
                                       variable=self.owned_only_var, command=self.filter_cards)
        owned_check.pack(side=tk.LEFT, padx=10)
        
        # Reset Button
        ttk.Button(filter_frame, text="Reset", command=self.reset_filters, width=6).pack(side=tk.LEFT, padx=5)
        
        # Shortcuts
        self.bind_all('<Control-f>', lambda e: self.search_entry.focus_set())
        
        # Card count label
        self.count_label = ttk.Label(left_frame, text="0 cards", style='Subtitle.TLabel')
        self.count_label.pack(pady=5)
        
        # Card list (Treeview)
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview with scrollbar
        # Configure style for taller rows
        style = ttk.Style()
        style.configure("CardList.Treeview", rowheight=40)
        
        self.tree = ttk.Treeview(list_frame, columns=('owned', 'name', 'rarity', 'type'), 
                                  show='tree headings', selectmode='browse',
                                  style="CardList.Treeview")
                                  
        self.tree.heading('#0', text='Art')
        self.tree.column('#0', width=50, anchor='center')
        
        self.tree.heading('owned', text='★', command=lambda: self.sort_column('owned', False))
        self.tree.heading('name', text='Name', anchor='w', command=lambda: self.sort_column('name', False))
        self.tree.heading('rarity', text='Rarity', command=lambda: self.sort_column('rarity', False))
        self.tree.heading('type', text='Type', command=lambda: self.sort_column('type', False))
        
        self.tree.column('owned', width=30, anchor='center')
        self.tree.column('name', width=180, minwidth=150)
        self.tree.column('rarity', width=50, anchor='center')
        self.tree.column('type', width=80, anchor='center')
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        # Tag for owned cards
        self.tree.tag_configure('owned', background='#2d4a3e')
        
        # === Right Panel Contents (Details) ===
        self.create_details_panel()
    
    def create_details_panel(self):
        """Create the card details panel"""
        # Image placeholder
        self.image_label = ttk.Label(self.details_frame, text="")
        self.image_label.pack(pady=5)
        
        # Header
        self.detail_name = ttk.Label(self.details_frame, text="Select a card", style='Header.TLabel')
        self.detail_name.pack(pady=5)
        
        self.detail_info = ttk.Label(self.details_frame, text="", style='Subtitle.TLabel')
        self.detail_info.pack()
        
        # Owned checkbox
        owned_frame = ttk.Frame(self.details_frame)
        owned_frame.pack(pady=10)
        
        self.owned_var = tk.BooleanVar(value=False)
        self.owned_checkbox = ttk.Checkbutton(owned_frame, text="I Own This Card", 
                                               variable=self.owned_var, 
                                               command=self.toggle_owned,
                                               style='Large.TCheckbutton')
        self.owned_checkbox.pack(side=tk.LEFT)
        
        # Level selector
        level_frame = ttk.Frame(self.details_frame)
        level_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(level_frame, text="View Level:").pack(side=tk.LEFT)
        
        self.level_var = tk.IntVar(value=50)
        self.level_scale = ttk.Scale(level_frame, from_=1, to=50, orient=tk.HORIZONTAL,
                                     variable=self.level_var, command=self.on_level_change)
        self.level_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.level_label = ttk.Label(level_frame, text="50", width=4)
        self.level_label.pack(side=tk.LEFT)
        
        # Quick level buttons
        btn_frame = ttk.Frame(self.details_frame)
        btn_frame.pack(pady=5)
        for lvl in [1, 25, 40, 50]:
            ttk.Button(btn_frame, text=f"Lv{lvl}", width=6,
                       command=lambda l=lvl: self.set_level(l)).pack(side=tk.LEFT, padx=2)
        
        # Effects display
        effects_label = ttk.Label(self.details_frame, text="📊 Effects", style='Header.TLabel')
        effects_label.pack(pady=(15, 5))
        
        # Effects text area
        self.effects_text = tk.Text(self.details_frame, height=12, wrap=tk.WORD,
                                    bg='#16213e', fg='#eaeaea', font=('Consolas', 11),
                                    padx=10, pady=10, relief=tk.FLAT)
        self.effects_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
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
        self.filter_cards()

    def filter_cards(self):
        """Filter cards based on search and dropdown values"""
        rarity = self.rarity_var.get() if self.rarity_var.get() != "All" else None
        card_type = self.type_var.get() if self.type_var.get() != "All" else None
        search = self.search_var.get().strip() if self.search_var.get().strip() else None
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
            type_icon = TYPE_ICONS.get(card_type, '')
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
                        pil_img.thumbnail((32, 32), Image.Resampling.LANCZOS)
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
        
        self.count_label.config(text=f"{len(cards)} cards")
    
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
            
            # Update level slider max
            self.level_scale.config(to=max_level)
            self.level_var.set(initial_level)
            self.level_label.config(text=str(initial_level))
            
            # Update details display
            type_icon = TYPE_ICONS.get(card_type, '')
            self.detail_name.config(text=f"{type_icon} {name}")
            self.detail_info.config(text=f"{rarity} | {card_type} | Max Level: {max_level}")
            
            # Load effects
            self.current_card_id = card_id
            self.update_effects_display()
            
            # Notify parent window
            if self.on_card_selected:
                self.on_card_selected(card_id, name)
    
    def load_card_image(self, image_path):
        """Load and display card image"""
        resolved_path = resolve_image_path(image_path)
        
        if resolved_path and os.path.exists(resolved_path):
            try:
                img = Image.open(resolved_path)
                img.thumbnail((120, 120))  # Resize
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
    
    def set_level(self, level):
        """Set level from quick button"""
        self.level_var.set(level)
        self.level_label.config(text=str(level))
        self.update_effects_display()
        
        # Save level if owned
        if self.current_card_id and self.owned_var.get():
             update_owned_card_level(self.current_card_id, level)
             self.update_tree_item_level(self.current_card_id, level)

    def on_level_change(self, value):
        """Handle level slider change"""
        level = int(float(value))
        self.level_label.config(text=str(level))
        self.update_effects_display()
        
        # Save level if owned (debounce slightly in real app, but direct for now)
        if self.current_card_id and self.owned_var.get():
             update_owned_card_level(self.current_card_id, level)
             self.update_tree_item_level(self.current_card_id, level)

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
        
        if effects:
            self.effects_text.insert(tk.END, f"━━━ Level {level} Effects ━━━\n\n")
            for name, value in effects:
                self.effects_text.insert(tk.END, f"  • {name}: {value}\n")
        else:
            self.effects_text.insert(tk.END, f"No effects data for Level {level}\n\n")
            self.effects_text.insert(tk.END, "Available levels: 1, 25, 40, 50\n")
        
        self.effects_text.config(state=tk.DISABLED)
