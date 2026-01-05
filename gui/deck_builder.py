"""
Deck Builder Frame
Build decks with 6 cards and view combined effects with breakdown
Updated for CustomTkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
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


class CardSlot(ctk.CTkFrame):
    """Visual component for a single card slot"""
    def __init__(self, parent, index, remove_callback, level_callback):
        super().__init__(parent, fg_color="transparent", border_width=2, border_color=BG_LIGHT, corner_radius=8)
        self.index = index
        self.remove_callback = remove_callback
        self.level_callback = level_callback
        self.image_ref = None  # Keep reference to prevent GC
        
        self.setup_ui()
        
    def setup_ui(self):
        # Configure grid
        self.columnconfigure(0, weight=1)
        
        # Slot number indicator (Overlay)
        self.slot_label = ctk.CTkLabel(self, text=f"#{self.index + 1}", font=FONT_TINY,
                              fg_color="#000000", text_color="#ffffff", corner_radius=4, height=18, width=24)
        self.slot_label.place(x=4, y=4)
        
        # Image Area - Dominant
        # Initial placeholder
        self.image_label = ctk.CTkLabel(self, fg_color="transparent", text="📭", text_color=TEXT_MUTED,
                                    font=('Segoe UI', 32), width=90, height=90)
        self.image_label.grid(row=0, column=0, padx=5, pady=(5,0))
        
        # Mini Details Area (Below Image)
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=1, column=0, sticky='ew', padx=4, pady=4)
        self.info_frame.columnconfigure(0, weight=1)
        
        self.name_label = ctk.CTkLabel(self.info_frame, text="Empty", fg_color="transparent", text_color=TEXT_MUTED,
                                    font=FONT_TINY, anchor='center', height=16)
        self.name_label.grid(row=0, column=0, sticky='ew')
        
        # Controls Overlay (Bottom)
        self.ctrl_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.ctrl_frame.grid(row=1, column=0, sticky='ew', pady=(2,0))
        
        # Level Selector (Compact)
        self.level_var = tk.StringVar(value="50")
        self.level_combo = ctk.CTkComboBox(self.ctrl_frame, variable=self.level_var, 
                                        values=[], width=55, height=22, font=FONT_TINY, state='readonly', command=self._on_level_change)
        self.level_combo.pack(side=tk.LEFT, padx=2)
        
        # Remove Button (Compact)
        self.remove_btn = ctk.CTkButton(self.ctrl_frame, text="✕", fg_color=BG_LIGHT, text_color=ACCENT_ERROR,
                                    font=FONT_BODY_BOLD, width=22, height=22,
                                    hover_color=BG_HIGHLIGHT,
                                    command=lambda: self.remove_callback(self.index))
        # Pack later
        
        # Hide controls initially
        self.toggle_controls(False)

    def toggle_controls(self, visible):
        state = 'normal' if visible else 'disabled'
        self.level_combo.configure(state='readonly' if visible else 'disabled')
        if not visible:
            self.remove_btn.pack_forget()
        else:
            self.remove_btn.pack(side=tk.RIGHT, padx=2)

    def set_card(self, card_data):
        """Set card data"""
        if not card_data:
            self.reset()
            return
            
        card_id, name, rarity, card_type, image_path, level = card_data
        
        # Calculate valid levels
        if rarity == 'SSR':
            valid_levels = [50, 45, 40, 35, 30]
            max_lvl = 50
        elif rarity == 'SR':
            valid_levels = [45, 40, 35, 30, 25]
            max_lvl = 45
        else:
            valid_levels = [40, 35, 30, 25, 20]
            max_lvl = 40
            
        self.level_combo.configure(values=[str(l) for l in valid_levels])
        if level not in valid_levels: level = max_lvl
            
        color = get_type_color(card_type)
        
        # Truncate strictly
        display_name = name if len(name) < 15 else name[:12] + "..."
        self.name_label.configure(text=display_name, text_color=TEXT_PRIMARY)
        self.level_combo.set(str(level))
        
        rarity_borders = {'SSR': '#ffd700', 'SR': '#c0c0c0', 'R': '#cd853f'}
        self.configure(border_color=rarity_borders.get(rarity, BG_LIGHT))
        
        self._load_image(image_path)
        self.toggle_controls(True)
        
    def reset(self):
        self.name_label.configure(text="Empty", text_color=TEXT_MUTED)
        
        # Recreate label to avoid TclError with missing images
        if hasattr(self, 'image_label') and self.image_label:
            self.image_label.destroy()
            
        self.image_label = ctk.CTkLabel(self, fg_color="transparent", text="📭", text_color=TEXT_MUTED,
                                    font=('Segoe UI', 32), width=90, height=90)
        self.image_label.grid(row=0, column=0, padx=5, pady=(5,0))
        
        self.configure(border_color=BG_LIGHT)
        self.image_ref = None
        self.toggle_controls(False)
        
    def _load_image(self, path):
        resolved_path = resolve_image_path(path)
        
        # Prepare new image first
        new_image = None
        if resolved_path and os.path.exists(resolved_path):
            try:
                pil_img = Image.open(resolved_path)
                pil_img.thumbnail((90, 90), Image.Resampling.LANCZOS)
                new_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(90, 90))
            except Exception:
                pass

        # Recreate label
        if hasattr(self, 'image_label') and self.image_label:
            self.image_label.destroy()

        if new_image:
            self.image_ref = new_image # Keep ref
            self.image_label = ctk.CTkLabel(self, fg_color="transparent", text="", image=new_image)
        else:
            self.image_ref = None
            self.image_label = ctk.CTkLabel(self, fg_color="transparent", text="⚠️" if resolved_path else "🖼️", 
                                          text_color=TEXT_MUTED, font=('Segoe UI', 32), width=90, height=90)

        self.image_label.grid(row=0, column=0, padx=5, pady=(5,0))

    def _on_level_change(self, value):
        # CTkComboBox calls command with value
        self.level_callback(self.index, int(value))


class DeckBuilderFrame(ctk.CTkFrame):
    """Deck builder with combined effects breakdown"""
    
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.current_deck_id = None
        self.deck_slots = [None] * 6  # 6 card slots
        self.setup_ui()
        self.refresh_decks()
    
    def setup_ui(self):
        # Main container with split view (simulated with frames)
        
        # === Left Panel: Card Browser ===
        left_panel = ctk.CTkFrame(self, width=350, corner_radius=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10), pady=10)
        
        # Header
        header = ctk.CTkFrame(left_panel, fg_color="transparent")
        header.pack(fill=tk.X, pady=(15, 10), padx=10)
        ctk.CTkLabel(header, text="📋 Available Cards", font=FONT_SUBHEADER, 
                  text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # Filters
        filter_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        filter_frame.pack(fill=tk.X, pady=(0, 8), padx=10)
        
        # Filters - Initialize vars FIRST
        self.type_var = tk.StringVar(value="All")
        self.owned_only_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()
        
        # Search Entry
        self.search_entry = ctk.CTkEntry(filter_frame, textvariable=self.search_var, width=120, placeholder_text="Search...")
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Bind key release for search
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_cards())
        
        types = ["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"]
        type_combo = ctk.CTkComboBox(filter_frame, variable=self.type_var, 
                                  values=types, width=90, state='readonly', command=lambda e: self.filter_cards())
        type_combo.pack(side=tk.LEFT)
        
        ctk.CTkCheckBox(filter_frame, text="Owned", variable=self.owned_only_var, 
                        command=self.filter_cards, checkbox_width=24, checkbox_height=24, font=FONT_SMALL).pack(side=tk.LEFT, padx=5)
        
        # Add Button (Packed first to stick to bottom)
        add_btn = create_styled_button(left_panel, text="➕ Add to Deck", 
                                       command=self.add_selected_to_deck,
                                       style_type='accent')
        add_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        # Card List Treeview
        list_container = ctk.CTkFrame(left_panel, fg_color=BG_MEDIUM)
        list_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.card_tree = ttk.Treeview(list_container, columns=('name', 'rarity', 'type'), 
                                      show='tree headings', style="DeckList.Treeview")
        self.card_tree.heading('#0', text='')
        self.card_tree.column('#0', width=45, anchor='center')
        
        self.card_tree.heading('name', text='Name')
        self.card_tree.heading('rarity', text='Rarity')
        self.card_tree.heading('type', text='Type')
        self.card_tree.column('name', width=130)
        self.card_tree.column('rarity', width=45, anchor='center')
        self.card_tree.column('type', width=65, anchor='center')
        
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.card_tree.yview)
        self.card_tree.configure(yscrollcommand=scrollbar.set)
        
        self.card_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Double-click to add
        self.card_tree.bind('<Double-1>', lambda e: self.add_selected_to_deck())
        
        # === Right Panel: Deck & Stats ===
        right_panel = ctk.CTkFrame(self, fg_color="transparent")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)
        
        # Deck Controls
        deck_ctrl = ctk.CTkFrame(right_panel, fg_color="transparent")
        deck_ctrl.pack(fill=tk.X, pady=(0, 10)) # Reduced padding
        
        ctk.CTkLabel(deck_ctrl, text="🎴 Current Deck:", font=FONT_BODY, 
                  text_color=TEXT_SECONDARY).pack(side=tk.LEFT)
        
        self.deck_combo = ctk.CTkComboBox(deck_ctrl, width=200, state='readonly', command=self.on_deck_selected_val)
        self.deck_combo.pack(side=tk.LEFT, padx=10)
        
        create_styled_button(deck_ctrl, text="+ New", command=self.create_new_deck, width=60).pack(side=tk.LEFT, padx=5)
        
        # Delete button - danger style
        del_btn = ctk.CTkButton(deck_ctrl, text="🗑️ Delete", command=self.delete_current_deck, 
                             fg_color=BG_LIGHT, hover_color=ACCENT_ERROR, text_color=ACCENT_ERROR, width=80)
        del_btn.pack(side=tk.LEFT)
        
        # Card count indicator
        self.deck_count_label = ctk.CTkLabel(deck_ctrl, text="0/6 cards", 
                                          font=FONT_SMALL, text_color=ACCENT_PRIMARY)
        self.deck_count_label.pack(side=tk.LEFT, padx=15)
        
        # Deck Grid (3x2) - Scrollable if needed, but 6 cards fit fine.
        # We use a frame for the grid
        self.slots_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.slots_frame.pack(fill=tk.X)
        
        self.card_slots = []
        for i in range(6):
            slot = CardSlot(self.slots_frame, i, self.remove_from_slot, self.on_slot_level_changed)
            r, c = divmod(i, 3)
            slot.grid(row=r, column=c, padx=4, pady=4, sticky='nsew')
            self.slots_frame.columnconfigure(c, weight=1)
            self.card_slots.append(slot)
            
        # Stats / Effects Area
        effects_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        effects_header.pack(fill=tk.X, pady=(10, 5)) # Reduced padding
        ctk.CTkLabel(effects_header, text="📊 Combined Effects Breakdown", 
                  font=FONT_SUBHEADER, text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # Effects Tree Container
        effects_container = ctk.CTkFrame(right_panel, fg_color=BG_MEDIUM)
        effects_container.pack(fill=tk.BOTH, expand=True)
        
        self.effects_tree = ttk.Treeview(effects_container, 
                                          columns=('effect', 'total', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6'),
                                          show='headings', height=6) # Reduced Height
        
        self.effects_tree.heading('effect', text='Effect')
        self.effects_tree.heading('total', text='TOTAL')
        self.effects_tree.column('effect', width=140)
        self.effects_tree.column('total', width=60, anchor='center')
        
        for i in range(1, 7):
            self.effects_tree.heading(f'c{i}', text=f'#{i}')
            self.effects_tree.column(f'c{i}', width=45, anchor='center')
        
        vsb = ttk.Scrollbar(effects_container, orient=tk.VERTICAL, command=self.effects_tree.yview)
        self.effects_tree.configure(yscrollcommand=vsb.set)
        
        self.effects_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Unique Effects Area
        unique_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        unique_header.pack(fill=tk.X, pady=(10, 5))
        ctk.CTkLabel(unique_header, text="✨ Unique Effects", font=FONT_BODY_BOLD, 
                  text_color=ACCENT_SECONDARY).pack(side=tk.LEFT)
        
        unique_frame = ctk.CTkFrame(right_panel, fg_color=BG_MEDIUM)
        unique_frame.pack(fill=tk.X)
        
        self.unique_text = ctk.CTkTextbox(unique_frame, height=60, fg_color=BG_MEDIUM, text_color=TEXT_PRIMARY) # Reduced Height
        self.unique_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.unique_text.configure(state=tk.DISABLED)
        
        self.icon_cache = {}
        # Initial call to populate list if wanted, or wait for event loop
        self.after(100, self.filter_cards) # Delay slightly to ensure widget readiness


    # --- Logic Methods ---
    
    def filter_cards(self):
        for item in self.card_tree.get_children():
            self.card_tree.delete(item)
            
        type_filter = self.type_var.get() if self.type_var.get() != "All" else None
        
        # Search var comes from CTkEntry textvariable
        search_text = self.search_var.get()
        search = search_text if search_text else None
        
        owned_only = self.owned_only_var.get()
        
        cards = get_all_cards(type_filter=type_filter, search_term=search, owned_only=owned_only)
        
        # Limit to 100 cards to prevent UI lag if showing all
        # (Optimization)
        
        count = 0
        for card in cards:
            if count > 200: break # soft limit
            count += 1
            
            card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level = card
            
            # Load Icon
            img = self.icon_cache.get(card_id)
            resolved_path = resolve_image_path(image_path)
            
            if not img and resolved_path and os.path.exists(resolved_path):
                try:
                    pil_img = Image.open(resolved_path)
                    # Larger thumbnails in the list too (32x32 for list)
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
        values = [f"{d[0]}: {d[1]}" for d in decks]
        self.deck_combo.configure(values=values)
        if values and not self.current_deck_id:
            self.deck_combo.set(values[0])
            self.on_deck_selected_val(values[0])
        elif not values:
            self.deck_combo.set('')

    def on_deck_selected_val(self, value):
        if value:
            self.current_deck_id = int(value.split(':')[0])
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
        
        self.update_deck_count()
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
                # Clear slots
                for s in self.card_slots: s.reset()
                self.deck_slots = [None] * 6
                self.update_deck_count()
                self.update_effects_breakdown()

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
                # Get the last selected level for this card from main window
                level = 50
                parent = self.winfo_toplevel()
                # Try to access main window state (depends on how it's linked, usually via parent or global state)
                # We can't easily access MainWindow instance from here unless passed down.
                # Assuming default max level for now or 50.
                
                add_card_to_deck(self.current_deck_id, card_id, i, level)
                self.load_deck() # Reloads everything
                return
                
        messagebox.showinfo("Deck Full", "Remove a card first to add a new one.")

    def remove_from_slot(self, index):
        if self.current_deck_id and self.deck_slots[index]:
            remove_card_from_deck(self.current_deck_id, index)
            self.deck_slots[index] = None
            self.card_slots[index].reset()
            self.update_deck_count()
            self.update_effects_breakdown()
    
    def update_deck_count(self):
        """Update the X/6 cards display"""
        count = sum(1 for slot in self.deck_slots if slot is not None)
        self.deck_count_label.configure(text=f"{count}/6 cards")

    def on_slot_level_changed(self, index, new_level):
        if self.current_deck_id and self.deck_slots[index]:
            card_id = self.deck_slots[index]
            add_card_to_deck(self.current_deck_id, card_id, index, new_level)
            self.update_effects_breakdown()

    def update_effects_breakdown(self):
        for item in self.effects_tree.get_children():
            self.effects_tree.delete(item)
        
        # Clear Unique Text
        self.unique_text.configure(state=tk.NORMAL)
        self.unique_text.delete('1.0', tk.END)
        
        if not self.current_deck_id:
            self.unique_text.insert(tk.END, "No deck selected")
            self.unique_text.configure(state=tk.DISABLED)
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
                # Get name from slot label
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
            self.unique_text.insert(tk.END, "No unique effects in this deck")
        self.unique_text.configure(state=tk.DISABLED)

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
