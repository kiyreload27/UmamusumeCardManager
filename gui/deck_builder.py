"""
Deck Builder Frame
Build decks with 6 cards and view combined effects with breakdown
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import (
    get_all_cards, get_all_decks, create_deck, delete_deck,
    add_card_to_deck, remove_card_from_deck, get_deck_cards,
    get_effects_at_level
)
from utils import resolve_image_path
from gui.theme import (
    BG_DARK, BG_DARKEST, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    TYPE_COLORS, get_type_color, get_type_icon,
    create_styled_button, create_styled_text, create_card_frame
)


class CardSlot(tk.Frame):
    """Visual component for a single card slot"""
    def __init__(self, parent, index, remove_callback, level_callback):
        super().__init__(parent, bg=BG_MEDIUM, highlightthickness=2, highlightbackground=BG_LIGHT)
        self.index = index
        self.remove_callback = remove_callback
        self.level_callback = level_callback
        self.image_ref = None  # Keep reference to prevent GC
        
        self.setup_ui()
        
    def setup_ui(self):
        # Configure grid weight
        self.columnconfigure(1, weight=1)
        
        # Slot number indicator
        slot_label = tk.Label(self, text=f"#{self.index + 1}", font=FONT_TINY,
                              bg=BG_LIGHT, fg=TEXT_MUTED, padx=4, pady=2)
        slot_label.place(x=2, y=2)
        
        # Image Area (Left)
        self.image_label = tk.Label(self, bg=BG_MEDIUM, text="📭", fg=TEXT_MUTED,
                                    font=('Segoe UI', 20))
        self.image_label.grid(row=0, column=0, rowspan=3, padx=8, pady=8)
        
        # Details Area (Right)
        self.name_label = tk.Label(self, text="Empty Slot", bg=BG_MEDIUM, fg=TEXT_MUTED,
                                   font=FONT_BODY_BOLD, anchor='w', wraplength=130)
        self.name_label.grid(row=0, column=1, sticky='w', padx=8, pady=(10, 0))
        
        self.meta_label = tk.Label(self, text="", bg=BG_MEDIUM, fg=TEXT_MUTED,
                                   font=FONT_SMALL, anchor='w')
        self.meta_label.grid(row=1, column=1, sticky='w', padx=8)
        
        # Controls (Bottom Right)
        ctrl_frame = tk.Frame(self, bg=BG_MEDIUM)
        ctrl_frame.grid(row=2, column=1, sticky='ew', padx=8, pady=8)
        
        # Level Selector
        tk.Label(ctrl_frame, text="Lv:", bg=BG_MEDIUM, fg=TEXT_MUTED, 
                 font=FONT_SMALL).pack(side=tk.LEFT)
        
        self.level_var = tk.StringVar(value="50")
        self.level_combo = ttk.Combobox(ctrl_frame, textvariable=self.level_var, 
                                        values=["50", "40", "25", "1"], width=4, state='readonly')
        self.level_combo.pack(side=tk.LEFT, padx=4)
        self.level_combo.bind('<<ComboboxSelected>>', self._on_level_change)
        
        # Remove Button
        self.remove_btn = tk.Button(ctrl_frame, text="✕", bg=BG_LIGHT, fg=ACCENT_ERROR,
                                    bd=0, font=FONT_BODY_BOLD, width=2,
                                    activebackground=ACCENT_ERROR, activeforeground=TEXT_PRIMARY,
                                    cursor='hand2',
                                    command=lambda: self.remove_callback(self.index))
        self.remove_btn.pack(side=tk.RIGHT)
        
        # Hide controls initially
        self.toggle_controls(False)

    def toggle_controls(self, visible):
        state = 'normal' if visible else 'disabled'
        self.level_combo.config(state='readonly' if visible else 'disabled')
        if not visible:
            self.remove_btn.pack_forget()
        else:
            self.remove_btn.pack(side=tk.RIGHT)

    def set_card(self, card_data):
        """Set card data: (id, name, rarity, type, image_path, level)"""
        if not card_data:
            self.reset()
            return
            
        card_id, name, rarity, card_type, image_path, level = card_data
        
        # Update styling based on type
        color = get_type_color(card_type)
        type_icon = get_type_icon(card_type)
        
        self.name_label.config(text=name, fg=TEXT_PRIMARY)
        self.meta_label.config(text=f"{type_icon} {rarity} │ {card_type}", fg=color)
        self.level_var.set(str(level))
        
        # Update border color based on rarity
        rarity_borders = {'SSR': '#ffd700', 'SR': '#c0c0c0', 'R': '#cd853f'}
        self.config(highlightbackground=rarity_borders.get(rarity, BG_LIGHT))
        
        # Load Image
        self._load_image(image_path)
        
        self.toggle_controls(True)
        
    def reset(self):
        self.name_label.config(text="Empty Slot", fg=TEXT_MUTED)
        self.meta_label.config(text="Click a card to add")
        self.image_label.config(image='', text="📭", font=('Segoe UI', 20))
        self.config(highlightbackground=BG_LIGHT)
        self.image_ref = None
        self.toggle_controls(False)
        
    def _load_image(self, path):
        resolved_path = resolve_image_path(path)
        if resolved_path and os.path.exists(resolved_path):
            try:
                pil_img = Image.open(resolved_path)
                pil_img.thumbnail((65, 65), Image.Resampling.LANCZOS)
                self.image_ref = ImageTk.PhotoImage(pil_img)
                self.image_label.config(image=self.image_ref, text='')
            except Exception as e:
                print(f"Failed to load image: {e}")
                self.image_label.config(image='', text="⚠️")
        else:
            self.image_label.config(image='', text="🖼️")

    def _on_level_change(self, event):
        self.level_callback(self.index, int(self.level_var.get()))


class DeckBuilderFrame(ttk.Frame):
    """Deck builder with combined effects breakdown"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.current_deck_id = None
        self.deck_slots = [None] * 6  # 6 card slots
        self.setup_ui()
        self.refresh_decks()
    
    def setup_ui(self):
        # Main container with split view
        main_split = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_split.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === Left Panel: Card Browser ===
        left_panel = ttk.Frame(main_split)
        main_split.add(left_panel, weight=1)
        
        # Header
        header = tk.Frame(left_panel, bg=BG_DARK)
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text="📋 Available Cards", font=FONT_SUBHEADER, 
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # Filters
        filter_frame = tk.Frame(left_panel, bg=BG_DARK)
        filter_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_cards())
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=18)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        self.type_var = tk.StringVar(value="All")
        types = ["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"]
        type_combo = ttk.Combobox(filter_frame, textvariable=self.type_var, 
                                  values=types, width=9, state='readonly')
        type_combo.pack(side=tk.LEFT)
        type_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_cards())
        
        self.owned_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_frame, text="Owned", variable=self.owned_only_var, 
                        command=self.filter_cards).pack(side=tk.LEFT, padx=8)
        
        # Card List
        list_frame = tk.Frame(left_panel, bg=BG_DARK)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.card_tree = ttk.Treeview(list_frame, columns=('name', 'rarity', 'type'), 
                                      show='tree headings', style="DeckList.Treeview")
        self.card_tree.heading('#0', text='')
        self.card_tree.column('#0', width=45, anchor='center')
        
        self.card_tree.heading('name', text='Name')
        self.card_tree.heading('rarity', text='Rarity')
        self.card_tree.heading('type', text='Type')
        self.card_tree.column('name', width=130)
        self.card_tree.column('rarity', width=45, anchor='center')
        self.card_tree.column('type', width=65, anchor='center')
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.card_tree.yview)
        self.card_tree.configure(yscrollcommand=scrollbar.set)
        
        self.card_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add Button
        add_btn = create_styled_button(left_panel, text="➕ Add to Deck", 
                                       command=self.add_selected_to_deck,
                                       style_type='accent')
        add_btn.pack(fill=tk.X, pady=10)
        
        # === Right Panel: Deck & Stats ===
        right_panel = ttk.Frame(main_split)
        main_split.add(right_panel, weight=2)
        
        # Deck Controls
        deck_ctrl = tk.Frame(right_panel, bg=BG_DARK)
        deck_ctrl.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(deck_ctrl, text="🎴 Current Deck:", font=FONT_BODY, 
                 bg=BG_DARK, fg=TEXT_SECONDARY).pack(side=tk.LEFT)
        self.deck_combo = ttk.Combobox(deck_ctrl, width=25, state='readonly')
        self.deck_combo.pack(side=tk.LEFT, padx=10)
        self.deck_combo.bind('<<ComboboxSelected>>', self.on_deck_selected)
        
        ttk.Button(deck_ctrl, text="+ New", command=self.create_new_deck, 
                   style='Small.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(deck_ctrl, text="🗑️ Delete", command=self.delete_current_deck,
                   style='Small.TButton').pack(side=tk.LEFT)
        
        # Deck Grid (3x2)
        self.slots_frame = tk.Frame(right_panel, bg=BG_DARK)
        self.slots_frame.pack(fill=tk.X)
        
        self.card_slots = []
        for i in range(6):
            slot = CardSlot(self.slots_frame, i, self.remove_from_slot, self.on_slot_level_changed)
            r, c = divmod(i, 3)
            slot.grid(row=r, column=c, padx=6, pady=6, sticky='nsew')
            self.slots_frame.columnconfigure(c, weight=1)
            self.card_slots.append(slot)
            
        # Stats / Effects Area
        effects_header = tk.Frame(right_panel, bg=BG_DARK)
        effects_header.pack(fill=tk.X, pady=(20, 10))
        tk.Label(effects_header, text="📊 Combined Effects Breakdown", 
                 font=FONT_SUBHEADER, bg=BG_DARK, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        effects_frame = create_card_frame(right_panel)
        effects_frame.pack(fill=tk.BOTH, expand=True)
        
        self.effects_tree = ttk.Treeview(effects_frame, 
                                          columns=('effect', 'total', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6'),
                                          show='headings', height=8)
        
        self.effects_tree.heading('effect', text='Effect')
        self.effects_tree.heading('total', text='TOTAL')
        self.effects_tree.column('effect', width=140)
        self.effects_tree.column('total', width=60, anchor='center')
        
        for i in range(1, 7):
            self.effects_tree.heading(f'c{i}', text=f'#{i}')
            self.effects_tree.column(f'c{i}', width=45, anchor='center')
        
        vsb = ttk.Scrollbar(effects_frame, orient=tk.VERTICAL, command=self.effects_tree.yview)
        self.effects_tree.configure(yscrollcommand=vsb.set)
        
        self.effects_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
        
        # Unique Effects Area
        unique_header = tk.Frame(right_panel, bg=BG_DARK)
        unique_header.pack(fill=tk.X, pady=(15, 8))
        tk.Label(unique_header, text="✨ Unique Effects", font=FONT_BODY_BOLD, 
                 bg=BG_DARK, fg=ACCENT_SECONDARY).pack(side=tk.LEFT)
        
        unique_frame = create_card_frame(right_panel)
        unique_frame.pack(fill=tk.X)
        
        self.unique_text = create_styled_text(unique_frame, height=5)
        self.unique_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.unique_text.config(state=tk.DISABLED)
        
        self.icon_cache = {}
        self.filter_cards()


    # --- Logic Methods ---
    
    def filter_cards(self):
        for item in self.card_tree.get_children():
            self.card_tree.delete(item)
            
        type_filter = self.type_var.get() if self.type_var.get() != "All" else None
        search = self.search_var.get() if self.search_var.get() else None
        owned_only = self.owned_only_var.get()
        
        cards = get_all_cards(type_filter=type_filter, search_term=search, owned_only=owned_only)
        
        for card in cards:
            card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level = card
            
            # Load Icon
            img = self.icon_cache.get(card_id)
            resolved_path = resolve_image_path(image_path)
            
            if not img and resolved_path and os.path.exists(resolved_path):
                try:
                    pil_img = Image.open(resolved_path)
                    pil_img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                    img = ImageTk.PhotoImage(pil_img)
                    self.icon_cache[card_id] = img
                except:
                    pass
            
            type_icon = get_type_icon(card_type)
            if img:
                self.card_tree.insert('', tk.END, text='', image=img, 
                                      values=(name, rarity, f"{type_icon}"), iid=str(card_id))
            else:
                self.card_tree.insert('', tk.END, text='?', 
                                      values=(name, rarity, f"{type_icon}"), iid=str(card_id))

    def refresh_decks(self):
        decks = get_all_decks()
        self.deck_combo['values'] = [f"{d[0]}: {d[1]}" for d in decks]
        if decks and not self.current_deck_id:
            self.deck_combo.current(0)
            self.on_deck_selected(None)

    def on_deck_selected(self, event):
        selection = self.deck_combo.get()
        if selection:
            self.current_deck_id = int(selection.split(':')[0])
            self.load_deck()

    def load_deck(self):
        if not self.current_deck_id:
            return
            
        # Reset visual slots
        for s in self.card_slots:
            s.reset()
        self.deck_slots = [None] * 6
        
        # Load from DB
        deck_cards = get_deck_cards(self.current_deck_id)
        
        for card in deck_cards:
            slot_pos, level, card_id, name, rarity, card_type, image_path = card
            if 0 <= slot_pos < 6:
                self.deck_slots[slot_pos] = card_id
                self.card_slots[slot_pos].set_card((card_id, name, rarity, card_type, image_path, level))
        
        self.update_effects_breakdown()

    def create_new_deck(self):
        name = tk.simpledialog.askstring("New Deck", "Enter deck name:")
        if name:
            deck_id = create_deck(name)
            self.current_deck_id = deck_id
            self.refresh_decks()
            self.deck_combo.set(f"{deck_id}: {name}")
            self.load_deck()

    def delete_current_deck(self):
        if self.current_deck_id:
            if messagebox.askyesno("Delete Deck", "Are you sure you want to delete this deck?"):
                delete_deck(self.current_deck_id)
                self.current_deck_id = None
                self.deck_combo.set('')
                self.refresh_decks()
                self.load_deck()

    def add_selected_to_deck(self):
        if not self.current_deck_id:
            messagebox.showwarning("No Deck", "Select or create a deck first.")
            return
            
        selection = self.card_tree.selection()
        if not selection:
            return
        card_id = int(selection[0])
        
        # Check for duplicates
        if card_id in self.deck_slots:
             messagebox.showinfo("Duplicate Card", "This card is already in the deck.")
             return

        # Find empty slot
        for i in range(6):
            if self.deck_slots[i] is None:
                add_card_to_deck(self.current_deck_id, card_id, i, 50)
                self.load_deck()
                return
                
        messagebox.showinfo("Deck Full", "Remove a card first to add a new one.")

    def remove_from_slot(self, index):
        if self.current_deck_id and self.deck_slots[index]:
            remove_card_from_deck(self.current_deck_id, index)
            self.deck_slots[index] = None
            self.card_slots[index].reset()
            self.update_effects_breakdown()

    def on_slot_level_changed(self, index, new_level):
        if self.current_deck_id and self.deck_slots[index]:
            card_id = self.deck_slots[index]
            add_card_to_deck(self.current_deck_id, card_id, index, new_level)
            self.update_effects_breakdown()

    def update_effects_breakdown(self):
        for item in self.effects_tree.get_children():
            self.effects_tree.delete(item)
        
        # Clear Unique Text
        self.unique_text.config(state=tk.NORMAL)
        self.unique_text.delete('1.0', tk.END)
        
        if not self.current_deck_id:
            self.unique_text.insert(tk.END, "No deck selected")
            self.unique_text.config(state=tk.DISABLED)
            return

        # Prepare data for calculation
        card_info = []
        for i in range(6):
            if self.deck_slots[i]:
                level = int(self.card_slots[i].level_var.get())
                card_info.append((self.deck_slots[i], level))
            else:
                card_info.append(None)
        
        # Gather effects
        all_effects = {}
        unique_effects_list = []
        
        for i, info in enumerate(card_info):
            if info:
                card_id, level = info
                card_name = self.card_slots[i].name_label.cget("text")
                
                effects = get_effects_at_level(card_id, level)
                for name, value in effects:
                    if name == "Unique Effect":
                        unique_effects_list.append(f"• {card_name}: {value}")
                        continue
                        
                    if name not in all_effects:
                        all_effects[name] = [''] * 6
                    all_effects[name][i] = value
        
        # Configure tags
        self.unique_text.tag_configure('card_name', foreground=ACCENT_PRIMARY)
        
        # Fill Unique Effects
        if unique_effects_list:
            self.unique_text.insert(tk.END, "\n".join(unique_effects_list))
        else:
            self.unique_text.insert(tk.END, "No unique effects in this deck", 'card_name')
        self.unique_text.config(state=tk.DISABLED)

        # Sum totals
        for effect_name, values in sorted(all_effects.items()):
            total = 0
            is_percent = False
            for v in values:
                if v:
                    if '%' in str(v): is_percent = True
                    try:
                        total += float(str(v).replace('%','').replace('+',''))
                    except: pass
            
            total_str = f"{total:.0f}%" if is_percent else (f"+{total:.0f}" if total > 0 else str(int(total)))
            row_vals = [effect_name, total_str] + values
            self.effects_tree.insert('', tk.END, values=row_vals)

import tkinter.simpledialog
