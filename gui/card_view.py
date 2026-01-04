"""
Card List View - Browse and search support cards with ownership management
Updated for CustomTkinter
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import sys
import os
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_cards, get_card_by_id, get_effects_at_level, set_card_owned, is_card_owned, update_owned_card_level
from utils import resolve_image_path
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_MONO, FONT_FAMILY,
    RARITY_COLORS, TYPE_COLORS, TYPE_ICONS,
    create_styled_button, create_styled_text, create_card_frame,
    get_rarity_color, get_type_color, get_type_icon,
    EFFECT_DESCRIPTIONS, Tooltip, create_styled_entry
)


class CardListFrame(ctk.CTkFrame):
    """Frame containing card list with search/filter, ownership, and details panel"""
    
    def __init__(self, parent, on_card_selected_callback=None, on_stats_updated_callback=None):
        super().__init__(parent, fg_color="transparent") # Transparent to blend with tab
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
        # CTk doesn't have PanedWindow, so we'll use a grid or pack with frames
        # We can simulate split view with two frames
        
        # Left panel - Card list with filters
        left_frame = ctk.CTkFrame(self, width=420, corner_radius=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        
        # Right panel - Card details
        self.details_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # === Left Panel Contents ===
        
        # Initialize filter variables
        self.rarity_var = tk.StringVar(value="All")
        self.type_var = tk.StringVar(value="All")
        self.owned_only_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar(value="")
        
        # Search bar
        search_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        search_frame.pack(fill=tk.X, padx=15, pady=(20, 10))
        
        self.search_entry = ctk.CTkEntry(
            search_frame, 
            textvariable=self.search_var, 
            placeholder_text="🔍 Search cards...",
            width=200,
            height=36
        )
        self.search_entry.pack(fill=tk.X, expand=True)
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_cards()) # Trace didn't work smoothly with CTkVar sometimes
        
        # Filter dropdowns
        filter_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        filter_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        # Rarity filter
        # ctk.CTkLabel(filter_frame, text="Rarity:", font=FONT_TINY).pack(side=tk.LEFT)
        rarity_combo = ctk.CTkComboBox(
            filter_frame, 
            variable=self.rarity_var,
            values=["All", "SSR", "SR", "R"], 
            width=80,
            height=32,
            command=lambda e: self.filter_cards()
        )
        rarity_combo.pack(side=tk.LEFT, padx=(0, 10))
        rarity_combo.set("All")
        
        # Type filter
        # ctk.CTkLabel(filter_frame, text="Type:", font=FONT_TINY).pack(side=tk.LEFT)
        type_combo = ctk.CTkComboBox(
            filter_frame, 
            variable=self.type_var,
            values=["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"],
            width=100,
            height=32,
            command=lambda e: self.filter_cards()
        )
        type_combo.pack(side=tk.LEFT, padx=(0, 10))
        type_combo.set("All")
        
        # Reset Button (Icon only maybe? or small text)
        ctk.CTkButton(
            filter_frame, 
            text="✕", 
            width=32, 
            height=32,
            fg_color=BG_LIGHT, 
            hover_color=ACCENT_ERROR,
            command=self.reset_filters
        ).pack(side=tk.LEFT)

        # Owned Only Checkbox (Below filters for spacing)
        owned_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        owned_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        owned_check = ctk.CTkCheckBox(
            owned_frame, 
            text="Owned Only", 
            variable=self.owned_only_var, 
            command=self.filter_cards,
            font=FONT_SMALL
        )
        owned_check.pack(side=tk.LEFT)
        
        # Shortcuts
        # Shortcuts
        try:
            self.winfo_toplevel().bind('<Control-f>', lambda e: self.search_entry.focus_set())
        except AttributeError:
            pass # In case toplevel isn't ready or doesn't support bind yet
        
        # Card count label
        self.count_label = ctk.CTkLabel(
            left_frame, 
            text="0 cards", 
            font=FONT_SMALL, 
            text_color=TEXT_MUTED
        )
        self.count_label.pack(pady=(5, 5))
        
        # Card list (Treeview wrapped in Frame)
        # We use a standard Frame to hold the Treeview because Treeview is a tk widget
        tree_container = ctk.CTkFrame(left_frame, fg_color="transparent")
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        
        self.tree = ttk.Treeview(
            tree_container, 
            columns=('owned', 'name', 'rarity', 'type'), 
            show='tree headings', 
            selectmode='browse',
            style="CardList.Treeview",
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.tree.yview)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                                  
        self.tree.column('#0', width=100, anchor='center') # Thumbnail column
        
        self.tree.heading('owned', text='★', command=lambda: self.sort_column('owned', False))
        self.tree.heading('name', text='Name', anchor='w', command=lambda: self.sort_column('name', False))
        self.tree.heading('rarity', text='Rarity', command=lambda: self.sort_column('rarity', False))
        self.tree.heading('type', text='Type', command=lambda: self.sort_column('type', False))
        
        self.tree.column('owned', width=50, anchor='center')
        self.tree.column('name', width=350, minwidth=200)
        self.tree.column('rarity', width=80, anchor='center')
        self.tree.column('type', width=100, anchor='center')
        
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.tag_configure('owned', background='#1a3a2e') # Kept legacy tag, might need update if theme changes
        
        # === Right Panel Contents (Details) ===
        self.create_details_panel()
    
    def create_details_panel(self):
        """Create the card details panel"""
        # Container
        details_container = ctk.CTkFrame(self.details_frame, corner_radius=12)
        details_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0) # Flush with right panel
        
        # Content scrolling container (Optional, but good for small screens)
        # For now, static
        
        # Image area
        # We can't put ctk widgets inside standard frames easily for transparency, so we use ctk frame
        image_frame = ctk.CTkFrame(details_container, fg_color=BG_MEDIUM, corner_radius=12)
        image_frame.pack(pady=10)
        
        self.image_label = ctk.CTkLabel(image_frame, text="", height=180, width=180)
        self.image_label.pack(padx=10, pady=10)
        
        # Header with card name
        self.detail_name = ctk.CTkLabel(
            details_container, 
            text="Select a card", 
            font=(FONT_FAMILY, 24, 'bold'), 
            text_color=ACCENT_PRIMARY
        )
        self.detail_name.pack(pady=(0, 2))
        
        self.detail_info = ctk.CTkLabel(
            details_container, 
            text="", 
            font=FONT_SUBHEADER, 
            text_color=TEXT_MUTED
        )
        self.detail_info.pack()
        
        # Owned checkbox
        owned_frame = ctk.CTkFrame(details_container, fg_color="transparent")
        owned_frame.pack(pady=10)
        
        self.owned_var = tk.BooleanVar(value=False)
        self.owned_checkbox = ctk.CTkCheckBox(
            owned_frame, 
            text="✨ I Own This Card", 
            variable=self.owned_var, 
            command=self.toggle_owned,
            font=FONT_HEADER,
            checkbox_width=28, checkbox_height=28
        )
        self.owned_checkbox.pack(side=tk.LEFT)
        
        # Level selector
        level_frame = ctk.CTkFrame(details_container, fg_color="transparent")
        level_frame.pack(fill=tk.X, padx=40, pady=10)
        
        ctk.CTkLabel(level_frame, text="Card Level:", font=FONT_SUBHEADER, text_color=TEXT_SECONDARY).pack(side=tk.LEFT)
        
        # Level items
        level_ctrl = ctk.CTkFrame(level_frame, fg_color="transparent")
        level_ctrl.pack(side=tk.LEFT, padx=30)
        
        # Decrement button
        create_styled_button(
            level_ctrl, text="−", 
            width=36, height=36,
            command=self.decrement_level
        ).pack(side=tk.LEFT)
        
        self.level_var = tk.IntVar(value=50)
        self.max_level = 50
        self.valid_levels = [30, 35, 40, 45, 50]
        
        self.level_label = ctk.CTkLabel(
            level_ctrl, 
            text="50", width=60, 
            font=(FONT_FAMILY, 24, 'bold'), 
            text_color=ACCENT_PRIMARY
        )
        self.level_label.pack(side=tk.LEFT, padx=10)
        
        # Increment button
        create_styled_button(
            level_ctrl, text="+", 
            width=36, height=36,
            command=self.increment_level
        ).pack(side=tk.LEFT)
        
        # Quick level buttons
        self.level_btn_frame = ctk.CTkFrame(level_frame, fg_color="transparent")
        self.level_btn_frame.pack(side=tk.LEFT, padx=20)
        
        self.level_buttons = {}
        self.update_level_buttons('SSR', 50)
        
        # Effects display
        effects_header = ctk.CTkFrame(details_container, fg_color="transparent")
        effects_header.pack(fill=tk.X, padx=30, pady=(10, 5))
        
        ctk.CTkLabel(effects_header, text="📊 Effects at Current Level", font=FONT_SUBHEADER).pack(side=tk.LEFT)
        
        # Effects text area
        self.effects_text = create_styled_text(details_container, height=30)
        self.effects_text.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 30))
        self.effects_text.configure(state="disabled")
    
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
    
    def filter_cards(self, *args):
        """Filter cards based on search and dropdown values"""
        rarity = self.rarity_var.get() if self.rarity_var.get() != "All" else None
        card_type = self.type_var.get() if self.type_var.get() != "All" else None
        
        search_text = self.search_var.get().strip()
        search = search_text if search_text else None
        owned_only = self.owned_only_var.get()
        
        self.cards = get_all_cards(rarity_filter=rarity, type_filter=card_type, 
                                   search_term=search, owned_only=owned_only)
        self.populate_tree(self.cards)
        self.count_label.configure(text=f"{len(self.cards)} cards")
    
    def sort_column(self, col, reverse):
        """Sort treeview by column"""
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        if col == 'owned':
             l.sort(key=lambda t: t[0] if t[0] else "", reverse=reverse)
        elif col == 'rarity':
            rarity_map = {'SSR': 3, 'SR': 2, 'R': 1}
            l.sort(key=lambda t: rarity_map.get(t[0], 0), reverse=reverse)
        else:
            l.sort(reverse=reverse)
            
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
            
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
        
    def populate_tree(self, cards):
        """Populate treeview with cards"""
        self.tree.delete(*self.tree.get_children())
        
        for card in cards:
            card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level = card
            type_icon = get_type_icon(card_type)
            owned_mark = "★" if is_owned else ""
            tag = 'owned' if is_owned else ''
            
            display_name = name
            if is_owned and owned_level:
                display_name = f"{name} (Lv{owned_level})"
            
            # Load Icon (keeping simplistic for now)
            # Treeview images need to be tk.PhotoImage, PIL works
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(image_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        # Resize for treeview (Larger to fill row based on user request)
                        pil_img.thumbnail((78, 78), Image.Resampling.LANCZOS)
                        img = ImageTk.PhotoImage(pil_img)
                        self.icon_cache[card_id] = img
                    except:
                        pass
            
            # Only use image if cached/loaded
            kv = {'image': img} if img else {}
            
            self.tree.insert('', tk.END, iid=card_id, text='', 
                           values=(owned_mark, display_name, rarity, f"{type_icon} {card_type}"),
                           tags=(tag,), **kv)
        
        if hasattr(self, 'count_label'):
            self.count_label.configure(text=f"{len(cards)} cards")
    
    def on_select(self, event):
        """Handle card selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        card_id = int(selection[0])
        card = get_card_by_id(card_id)
        
        if card:
            card_id, name, rarity, card_type, max_level, url, image_path, is_owned, owned_level = card
            
            self.owned_var.set(bool(is_owned))
            
            # Load card image
            self.load_card_image(image_path)
            
            # Level logic
            initial_level = owned_level if is_owned and owned_level else max_level
            self.max_level = max_level
            self.update_level_buttons(rarity, max_level)
            
            if initial_level not in self.valid_levels:
                initial_level = max_level
            
            self.level_var.set(initial_level)
            self.level_label.configure(text=str(initial_level))
            self.selected_level = initial_level
            
            # Update details text
            type_icon = get_type_icon(card_type)
            
            self.detail_name.configure(text=f"{type_icon} {name}")
            self.detail_info.configure(text=f"{rarity} │ {card_type} │ Max Level: {max_level}")
            
            self.current_card_id = card_id
            self.update_effects_display()
            
            if self.on_card_selected:
                self.on_card_selected(card_id, name, self.selected_level)
    
    def load_card_image(self, image_path):
        """Load and display card image"""
        resolved_path = resolve_image_path(image_path)
        
        if resolved_path and os.path.exists(resolved_path):
            try:
                img = ctk.CTkImage(light_image=Image.open(resolved_path), 
                                   dark_image=Image.open(resolved_path),
                                   size=(180, 180))
                self.image_label.configure(image=img, text="")
            except Exception as e:
                self.image_label.configure(image=None, text="[Image Error]")
        else:
            self.image_label.configure(image=None, text="[No Image]")
    
    def toggle_owned(self):
        """Toggle owned status for current card"""
        if self.current_card_id:
            owned = self.owned_var.get()
            level = int(self.level_var.get())
            set_card_owned(self.current_card_id, owned, level)
            self.filter_cards() # Refresh status icons in tree
            
            if self.on_stats_updated:
                self.on_stats_updated()
    
    def update_level_buttons(self, rarity, max_level):
        """Update quick level buttons"""
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
            btn.configure(width=45, height=36, font=FONT_BODY_BOLD)
            btn.pack(side=tk.LEFT, padx=3)
            self.level_buttons[lvl] = btn

    def set_level(self, level):
        """Update selected level and notify callback"""
        if self.current_card_id:
            self.selected_level = level
            self.level_var.set(level)
            self.level_label.configure(text=str(level))
            self.update_effects_display()
            
            if self.on_card_selected:
                card = get_card_by_id(self.current_card_id)
                if card:
                    self.on_card_selected(self.current_card_id, card[1], self.selected_level)
        
        # Save level if owned
        if self.current_card_id and self.owned_var.get():
             update_owned_card_level(self.current_card_id, level)
             # Refresh just this item if possible, or full refresh
             # self.filter_cards() # Too heavy? logic needs to be robust
             pass # Tree update happens on next filter or refresh
    
    def increment_level(self):
        current = self.level_var.get()
        for lvl in self.valid_levels:
            if lvl > current:
                self.set_level(lvl)
                return
    
    def decrement_level(self):
        current = self.level_var.get()
        for lvl in reversed(self.valid_levels):
            if lvl < current:
                self.set_level(lvl)
                return

    def update_effects_display(self):
        """Update the effects display for current card and level"""
        if not self.current_card_id:
            return
        
        level = int(self.level_var.get())
        effects = get_effects_at_level(self.current_card_id, level)
        
        self.effects_text.configure(state="normal")
        self.effects_text.delete('1.0', tk.END)
        
        # Note: CTkTextbox tags are minimal (no foreground color support per tag as detailed as tk usually)
        # But we can try basic insert.
        # CTkTextbox does not support color tags in the same way `tag_configure` does for Text.
        # It's a limitation. We might have to stick to plain text or use the adapter to return a tk.Text if we strictly need color.
        # However, `create_styled_text` in theme.py is now returning a CTkTextbox.
        # If we need Rich Text, we might need to revert `create_styled_text` to use tk.Text but styled for Dark mode.
        # Let's check `theme.py` again. I defined `create_styled_text` as returning `CTkTextbox`.
        # CTkTextbox is good for uniform text. If we lost coloring, that's a trade-off for the UI look.
        # OR: We can use `tk.Text` inside a `ctkContainer` to keep coloring.
        # Let's assume for now we just want the text content.
        
        # For better UX, let's revert create_styled_text to use tk.Text because we really needed those highlights (+20% etc).
        # Actually, let's just format it nicely.
        
        if effects:
            self.effects_text.insert(tk.END, f"━━━ Level {level} ━━━\n\n")
            for name, value in effects:
                # Basic formatting
                prefix = ""
                # Logic for starring high values
                if '%' in str(value):
                    try:
                        num = int(str(value).replace('%', '').replace('+', ''))
                        if num >= 20:
                            prefix = "★ "
                    except:
                        pass
                
                self.effects_text.insert(tk.END, f"{prefix}{name}: {value}\n")
        else:
             self.effects_text.insert(tk.END, f"No effects data for Level {level}\n\nAvailable levels: {self.valid_levels}")
        
        self.effects_text.configure(state="disabled")

