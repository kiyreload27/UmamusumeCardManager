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

# Theme Colors (matching main_window.py)
BG_DARK = '#1a1a2e'
BG_MEDIUM = '#16213e'
BG_LIGHT = '#0f3460'
ACCENT = '#e94560'
TEXT_MAIN = '#eaeaea'

class CardSlot(tk.Frame):
    """Visual component for a single card slot"""
    def __init__(self, parent, index, remove_callback, level_callback):
        super().__init__(parent, bg=BG_MEDIUM, highlightthickness=1, highlightbackground=BG_LIGHT)
        self.index = index
        self.remove_callback = remove_callback
        self.level_callback = level_callback
        self.image_ref = None  # Keep reference to prevent GC
        
        self.setup_ui()
        
    def setup_ui(self):
        # Configure grid weight
        self.columnconfigure(1, weight=1)
        
        # Image Area (Left)
        self.image_label = tk.Label(self, bg=BG_MEDIUM, text="No Image", fg='gray',
                                    width=10, height=5) # Approximate size characters
        self.image_label.grid(row=0, column=0, rowspan=3, padx=5, pady=5)
        
        # Details Area (Right)
        self.name_label = tk.Label(self, text="Empty Slot", bg=BG_MEDIUM, fg=TEXT_MAIN,
                                   font=('Segoe UI', 10, 'bold'), anchor='w', wraplength=120)
        self.name_label.grid(row=0, column=1, sticky='w', padx=5, pady=(5,0))
        
        self.meta_label = tk.Label(self, text="", bg=BG_MEDIUM, fg='#aaaaaa',
                                   font=('Segoe UI', 9), anchor='w')
        self.meta_label.grid(row=1, column=1, sticky='w', padx=5)
        
        # Controls (Bottom Right)
        ctrl_frame = tk.Frame(self, bg=BG_MEDIUM)
        ctrl_frame.grid(row=2, column=1, sticky='ew', padx=5, pady=5)
        
        # Level Selector
        tk.Label(ctrl_frame, text="Lv:", bg=BG_MEDIUM, fg='#aaaaaa', font=('Segoe UI', 8)).pack(side=tk.LEFT)
        
        self.level_var = tk.StringVar(value="50")
        self.level_combo = ttk.Combobox(ctrl_frame, textvariable=self.level_var, 
                                        values=["50", "40", "25", "1"], width=3, state='readonly')
        self.level_combo.pack(side=tk.LEFT, padx=2)
        self.level_combo.bind('<<ComboboxSelected>>', self._on_level_change)
        
        # Remove Button
        self.remove_btn = tk.Button(ctrl_frame, text="✕", bg=BG_LIGHT, fg=TEXT_MAIN,
                                    bd=0, activebackground=ACCENT, cursor='hand2',
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
        type_colors = {
            'Speed': '#3498db', 'Stamina': '#e67e22', 'Power': '#f1c40f',
            'Guts': '#e74c3c', 'Wisdom': '#2ecc71', 'Friend': '#9b59b6', 'Group': '#f39c12'
        }
        color = type_colors.get(card_type, TEXT_MAIN)
        
        self.name_label.config(text=name, fg=TEXT_MAIN)
        self.meta_label.config(text=f"{rarity} | {card_type}", fg=color)
        self.level_var.set(str(level))
        
        # Load Image
        self._load_image(image_path)
        
        self.toggle_controls(True)
        
    def reset(self):
        self.name_label.config(text="Empty Slot", fg='gray')
        self.meta_label.config(text="")
        self.image_label.config(image='', text="Empty", width=10, height=5)
        self.image_ref = None
        self.toggle_controls(False)
        
    def _load_image(self, path):
        resolved_path = resolve_image_path(path)
        if resolved_path and os.path.exists(resolved_path):
            try:
                pil_img = Image.open(resolved_path)
                # Resize to thumbnail (maintain aspect ratio roughly, target height 80)
                # Original is usually ~120x160 or similar
                pil_img.thumbnail((70, 70), Image.Resampling.LANCZOS)
                self.image_ref = ImageTk.PhotoImage(pil_img)
                self.image_label.config(image=self.image_ref, width=0, height=0)
            except Exception as e:
                print(f"Failed to load image: {e}")
                self.image_label.config(image='', text="Error")
        else:
            self.image_label.config(image='', text="No Img")

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
        # Apply dark theme tweaks
        style = ttk.Style()
        # Create specific style for this treeview to allow larger rows (thumbnails)
        style.configure("DeckList.Treeview", background=BG_MEDIUM, fieldbackground=BG_MEDIUM, 
                        foreground=TEXT_MAIN, rowheight=40)
        style.map('DeckList.Treeview', background=[('selected', ACCENT)])
        
        # Main container with split view
        main_split = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_split.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === Left Panel: Card Browser ===
        left_panel = ttk.Frame(main_split)
        main_split.add(left_panel, weight=1)
        
        ttk.Label(left_panel, text="Available Cards", font=('Segoe UI', 12, 'bold')).pack(pady=(0,5))
        
        # Filters
        filter_frame = ttk.Frame(left_panel)
        filter_frame.pack(fill=tk.X, padx=2)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_cards())
        ttk.Entry(filter_frame, textvariable=self.search_var, width=20).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        
        self.type_var = tk.StringVar(value="All")
        types = ["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"]
        type_combo = ttk.Combobox(filter_frame, textvariable=self.type_var, values=types, width=8, state='readonly')
        type_combo.pack(side=tk.LEFT)
        type_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_cards())
        
        self.owned_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_frame, text="Owned", variable=self.owned_only_var, command=self.filter_cards).pack(side=tk.LEFT, padx=5)
        
        # Card List
        # show='tree headings' to show icon column (#0)
        self.card_tree = ttk.Treeview(left_panel, columns=('name', 'rarity', 'type'), 
                                      show='tree headings', style="DeckList.Treeview")
        self.card_tree.heading('#0', text='Art')
        self.card_tree.column('#0', width=50, anchor='center') # Icon column
        
        self.card_tree.heading('name', text='Name')
        self.card_tree.heading('rarity', text='Rarity')
        self.card_tree.heading('type', text='Type')
        self.card_tree.column('name', width=120)
        self.card_tree.column('rarity', width=40, anchor='center')
        self.card_tree.column('type', width=60, anchor='center')
        
        scrollbar = ttk.Scrollbar(left_panel, orient=tk.VERTICAL, command=self.card_tree.yview)
        self.card_tree.configure(yscrollcommand=scrollbar.set)
        
        self.card_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Add Button
        add_btn = tk.Button(left_panel, text="Add to Deck  >", bg=ACCENT, fg='white', 
                          font=('Segoe UI', 10, 'bold'), activebackground=BG_LIGHT,
                          command=self.add_selected_to_deck)
        add_btn.pack(fill=tk.X, pady=5)
        
        # === Right Panel: Deck & Stats ===
        right_panel = ttk.Frame(main_split)
        main_split.add(right_panel, weight=2)
        
        # Deck Controls
        deck_ctrl = ttk.Frame(right_panel)
        deck_ctrl.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(deck_ctrl, text="Current Deck:").pack(side=tk.LEFT)
        self.deck_combo = ttk.Combobox(deck_ctrl, width=25, state='readonly')
        self.deck_combo.pack(side=tk.LEFT, padx=5)
        self.deck_combo.bind('<<ComboboxSelected>>', self.on_deck_selected)
        
        ttk.Button(deck_ctrl, text="New", command=self.create_new_deck).pack(side=tk.LEFT, padx=5)
        ttk.Button(deck_ctrl, text="Delete", command=self.delete_current_deck).pack(side=tk.LEFT)
        
        # Deck Grid (3x2)
        self.slots_frame = ttk.Frame(right_panel)
        self.slots_frame.pack(fill=tk.X, padx=10)
        
        self.card_slots = []
        for i in range(6):
            slot = CardSlot(self.slots_frame, i, self.remove_from_slot, self.on_slot_level_changed)
            # Grid: 2 rows of 3 columns
            r, c = divmod(i, 3)
            slot.grid(row=r, column=c, padx=5, pady=5, sticky='nsew')
            self.slots_frame.columnconfigure(c, weight=1)
            self.card_slots.append(slot)
            
        # Stats / Effects Area
        ttk.Label(right_panel, text="Combined Effects Breakdown", font=('Segoe UI', 11, 'bold')).pack(anchor='w', padx=10, pady=(15, 5))
        
        effects_frame = ttk.Frame(right_panel)
        effects_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.effects_tree = ttk.Treeview(effects_frame, 
                                          columns=('effect', 'total', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6'),
                                          show='headings', height=10)
        
        self.effects_tree.heading('effect', text='Effect')
        self.effects_tree.heading('total', text='TOTAL')
        self.effects_tree.column('effect', width=150)
        self.effects_tree.column('total', width=60, anchor='center')
        
        for i in range(1, 7):
            self.effects_tree.heading(f'c{i}', text=f'#{i}')
            self.effects_tree.column(f'c{i}', width=40, anchor='center')
        
        vsb = ttk.Scrollbar(effects_frame, orient=tk.VERTICAL, command=self.effects_tree.yview)
        self.effects_tree.configure(yscrollcommand=vsb.set)
        
        self.effects_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Unique Effects Area
        ttk.Label(right_panel, text="Unique Effects Active:", font=('Segoe UI', 10, 'bold')).pack(anchor='w', padx=10, pady=(10, 0))
        
        unique_frame = ttk.Frame(right_panel)
        unique_frame.pack(fill=tk.X, padx=10, pady=(2, 10))
        
        self.unique_text = tk.Text(unique_frame, height=8, bg=BG_MEDIUM, fg=TEXT_MAIN,
                                   font=('Segoe UI', 9), wrap=tk.WORD, relief=tk.FLAT, padx=5, pady=5)
        
        unique_scroll = ttk.Scrollbar(unique_frame, orient=tk.VERTICAL, command=self.unique_text.yview)
        self.unique_text.configure(yscrollcommand=unique_scroll.set)
        
        self.unique_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        unique_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.unique_text.config(state=tk.DISABLED)
        
        self.icon_cache = {} # Cache for list icons
        self.filter_cards()
        


    # --- Logic Methods (Similar to original but adapted) ---
    
    def filter_cards(self):
        # Clear
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
            
            # Insert with image if available
            if img:
                self.card_tree.insert('', tk.END, text='', image=img, values=(name, rarity, card_type), iid=str(card_id))
            else:
                self.card_tree.insert('', tk.END, text='?', values=(name, rarity, card_type), iid=str(card_id))

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
        deck_cards = get_deck_cards(self.current_deck_id) # Returns (slot, level, id, name, rarity, type, img)
        
        for card in deck_cards:
            slot_pos, level, card_id, name, rarity, card_type, image_path = card
            if 0 <= slot_pos < 6:
                self.deck_slots[slot_pos] = card_id
                # Update Slot UI
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
            if messagebox.askyesno("Delete Deck", "Are you sure?"):
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
                # Add to DB (default level 50)
                add_card_to_deck(self.current_deck_id, card_id, i, 50)
                self.load_deck()
                return
                
        messagebox.showinfo("Deck Full", "Remove a card first.")

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
            self.unique_text.config(state=tk.DISABLED)
            return

        # Prepare data for calculation
        card_info = [] # [(card_id, level, valid_bool)]
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
                # Get card name for unique effect listing
                card_name = self.card_slots[i].name_label.cget("text")
                
                effects = get_effects_at_level(card_id, level)
                for name, value in effects:
                    if name == "Unique Effect":
                        unique_effects_list.append(f"• {card_name}: {value}")
                        continue
                        
                    if name not in all_effects:
                        all_effects[name] = [''] * 6
                    all_effects[name][i] = value
        
        # Fill Unique Effects
        if unique_effects_list:
            self.unique_text.insert(tk.END, "\n".join(unique_effects_list))
        else:
            self.unique_text.insert(tk.END, "None")
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
