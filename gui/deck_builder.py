"""
Deck Builder Frame
Build decks with 6 cards and view combined effects with breakdown
Refactored to match modern Tailwind UI Grid layout
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import sys
import os
from PIL import Image

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
    get_type_color, get_type_icon, get_rarity_color,
    create_styled_button, create_styled_entry, create_card_frame
)
import tkinter.simpledialog


class CardSlot(ctk.CTkFrame):
    """Visual component for a single card slot"""
    def __init__(self, parent, index, remove_callback, level_callback):
        super().__init__(parent, fg_color=BG_DARK, border_width=1, border_color=BG_HIGHLIGHT, corner_radius=10)
        self.index = index
        self.remove_callback = remove_callback
        self.level_callback = level_callback
        self.image_ref = None  # Keep reference to prevent GC
        self.setup_ui()
        
    def setup_ui(self):
        self.columnconfigure(0, weight=1)
        
        # Slot Indicator
        self.slot_label = ctk.CTkLabel(self, text=f"#{self.index + 1}", font=FONT_TINY,
                                      fg_color=BG_LIGHT, text_color=TEXT_PRIMARY, corner_radius=4, height=20, width=28)
        self.slot_label.place(x=6, y=6)
        
        # Image Box
        self.image_label = ctk.CTkLabel(self, fg_color="transparent", text="📭", text_color=TEXT_MUTED,
                                        font=('Segoe UI', 32), width=90, height=90, corner_radius=8)
        self.image_label.grid(row=0, column=0, padx=8, pady=(8, 0))
        
        # Info Text
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=1, column=0, sticky='ew', padx=6, pady=6)
        self.info_frame.columnconfigure(0, weight=1)
        
        self.name_label = ctk.CTkLabel(self.info_frame, text="Empty", fg_color="transparent", text_color=TEXT_MUTED,
                                       font=FONT_TINY, anchor='center', height=16)
        self.name_label.grid(row=0, column=0, sticky='ew')
        
        # Controls
        self.ctrl_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.ctrl_frame.grid(row=1, column=0, sticky='ew', pady=(4, 0))
        
        self.level_var = tk.StringVar(value="50")
        self.level_combo = ctk.CTkComboBox(self.ctrl_frame, variable=self.level_var, 
                                           values=[], width=55, height=24, font=FONT_TINY, state='readonly', command=self._on_level_change)
        
        self.remove_btn = ctk.CTkButton(self.ctrl_frame, text="✕", fg_color=BG_LIGHT, text_color=ACCENT_ERROR,
                                        font=FONT_BODY_BOLD, width=24, height=24, corner_radius=6,
                                        hover_color=BG_HIGHLIGHT, command=lambda: self.remove_callback(self.index))
        
        self.toggle_controls(False)

    def toggle_controls(self, visible):
        state = 'readonly' if visible else 'disabled'
        self.level_combo.configure(state=state)
        if not visible:
            self.remove_btn.pack_forget()
            self.level_combo.pack_forget()
        else:
            self.level_combo.pack(side=tk.LEFT)
            self.remove_btn.pack(side=tk.RIGHT)

    def set_card(self, card_data):
        if not card_data:
            self.reset()
            return
            
        card_id, name, rarity, card_type, image_path, level = card_data
        
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
            
        display_name = name if len(name) < 14 else name[:11] + "..."
        self.name_label.configure(text=display_name, text_color=TEXT_PRIMARY)
        self.level_combo.set(str(level))
        
        self.configure(border_color=ACCENT_SUCCESS if rarity == 'SSR' else (TEXT_SECONDARY if rarity == 'SR' else BG_LIGHT))
        self.configure(fg_color=BG_MEDIUM)
        
        self._load_image(image_path)
        self.toggle_controls(True)
        
    def reset(self):
        self.name_label.configure(text="Empty", text_color=TEXT_MUTED)
        
        if hasattr(self, 'image_label') and self.image_label:
            self.image_label.destroy()
            
        self.image_label = ctk.CTkLabel(self, fg_color="transparent", text="📭", text_color=TEXT_MUTED,
                                        font=('Segoe UI', 32), width=90, height=90, corner_radius=8)
        self.image_label.grid(row=0, column=0, padx=8, pady=(8, 0))
        
        self.configure(border_color=BG_HIGHLIGHT, fg_color=BG_DARK)
        self.image_ref = None
        self.toggle_controls(False)
        
    def _load_image(self, path):
        resolved_path = resolve_image_path(path)
        new_image = None
        if resolved_path and os.path.exists(resolved_path):
            try:
                pil_img = Image.open(resolved_path)
                pil_img.thumbnail((86, 86), Image.Resampling.LANCZOS)
                new_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(86, 86))
            except Exception:
                pass

        if hasattr(self, 'image_label') and self.image_label:
            self.image_label.destroy()

        if new_image:
            self.image_ref = new_image
            self.image_label = ctk.CTkLabel(self, fg_color="transparent", text="", image=new_image, width=90, height=90, corner_radius=8)
        else:
            self.image_ref = None
            self.image_label = ctk.CTkLabel(self, fg_color="transparent", text="⚠️" if resolved_path else "🖼️", 
                                            text_color=TEXT_MUTED, font=('Segoe UI', 32), width=90, height=90)

        self.image_label.grid(row=0, column=0, padx=8, pady=(8, 0))

    def _on_level_change(self, value):
        self.level_callback(self.index, int(value))


class DeckBuilderFrame(ctk.CTkFrame):
    """Deck builder with combined effects breakdown"""
    
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.current_deck_id = None
        self.deck_slots = [None] * 6
        self.icon_cache = {}
        self.av_card_widgets = []
        self.selected_av_card_id = None
        
        self._rendering_cards = False
        self._card_render_queue = []
        
        self.setup_ui()
        self.refresh_decks()
    
    def setup_ui(self):
        # Overall Left/Right Split Container
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1) # Panel Left
        self.grid_columnconfigure(1, weight=3) # Panel Right (Deck + Stats)
        
        # === Left Panel: Card Browser ===
        left_panel = create_card_frame(self)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        header = ctk.CTkFrame(left_panel, fg_color="transparent")
        header.pack(fill=tk.X, pady=(20, 10), padx=20)
        ctk.CTkLabel(header, text="📋 Available Cards", font=FONT_HEADER, text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # Filters
        filter_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        filter_frame.pack(fill=tk.X, pady=(0, 10), padx=20)
        
        self.type_var = tk.StringVar(value="All")
        self.owned_only_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()
        
        self.search_entry = create_styled_entry(filter_frame, textvariable=self.search_var, placeholder_text="Search...")
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_cards())
        
        types = ["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"]
        type_combo = ctk.CTkComboBox(filter_frame, variable=self.type_var, values=types, width=100, state='readonly', command=lambda e: self.filter_cards())
        type_combo.pack(side=tk.LEFT)
        
        owned_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        owned_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        ctk.CTkCheckBox(owned_frame, text="Owned Only", variable=self.owned_only_var, command=self.filter_cards, font=FONT_SMALL).pack(side=tk.LEFT)
        
        # Add Button (Locked to bottom)
        add_btn = create_styled_button(left_panel, text="➕ Add to Deck", command=self.add_selected_to_deck, style_type='accent')
        add_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=20, padx=20)

        # Card Scroll List
        self.card_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.card_scroll.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.card_scroll.columnconfigure(0, weight=1)
        
        # === Right Panel: Deck & Stats ===
        right_panel = ctk.CTkFrame(self, fg_color="transparent")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        # Deck Controls
        deck_ctrl = create_card_frame(right_panel)
        deck_ctrl.pack(fill=tk.X, pady=(0, 15))
        deck_ctrl_inner = ctk.CTkFrame(deck_ctrl, fg_color="transparent")
        deck_ctrl_inner.pack(fill=tk.BOTH, padx=20, pady=15)
        
        ctk.CTkLabel(deck_ctrl_inner, text="🎴 Target Deck", font=FONT_SUBHEADER, text_color=TEXT_SECONDARY).pack(side=tk.LEFT, padx=(0, 15))
        
        self.deck_combo = ctk.CTkComboBox(deck_ctrl_inner, width=220, state='readonly', command=self.on_deck_selected_val)
        self.deck_combo.pack(side=tk.LEFT)
        
        create_styled_button(deck_ctrl_inner, text="➕ Build New Template", command=self.create_new_deck, width=160).pack(side=tk.LEFT, padx=15)
        ctk.CTkButton(deck_ctrl_inner, text="🗑️ Trash", command=self.delete_current_deck, fg_color=BG_LIGHT, hover_color=ACCENT_ERROR, text_color=ACCENT_ERROR, width=100, font=FONT_BODY_BOLD).pack(side=tk.LEFT)
        
        self.deck_count_label = ctk.CTkLabel(deck_ctrl_inner, text="0 / 6 Cards", font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY)
        self.deck_count_label.pack(side=tk.RIGHT)
        
        # Slots Grid
        self.slots_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.slots_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.card_slots = []
        for i in range(6):
            slot = CardSlot(self.slots_frame, i, self.remove_from_slot, self.on_slot_level_changed)
            # Use 6 columns horizontal or wrap depending on space. 6 fits nice laterally.
            slot.grid(row=0, column=i, padx=5, pady=5, sticky='nsew')
            self.slots_frame.columnconfigure(i, weight=1)
            self.card_slots.append(slot)
            
        # Stats Area (Scrolling Grid for Modernization)
        effects_container = create_card_frame(right_panel)
        effects_container.pack(fill=tk.BOTH, expand=True)
        
        stats_header = ctk.CTkFrame(effects_container, fg_color="transparent")
        stats_header.pack(fill=tk.X, padx=20, pady=(20, 10))
        ctk.CTkLabel(stats_header, text="📊 Combined Effects Breakdown", font=FONT_SUBHEADER, text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        ctk.CTkLabel(stats_header, text="✨ Unique Active Effects", font=FONT_SUBHEADER, text_color=ACCENT_SECONDARY).pack(side=tk.RIGHT)
        
        stats_body = ctk.CTkFrame(effects_container, fg_color="transparent")
        stats_body.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Table Scroll (Left)
        # Using a Scrollable Frame to build a custom flex table instead of Treeview
        self.table_scroll = ctk.CTkScrollableFrame(stats_body, fg_color=BG_DARK, corner_radius=8, border_width=1, border_color=BG_HIGHLIGHT)
        self.table_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.table_scroll.columnconfigure(0, weight=3) # Name
        self.table_scroll.columnconfigure(1, weight=1) # Total
        
        # Unique text (Right)
        self.unique_text = ctk.CTkTextbox(stats_body, width=280, fg_color=BG_DARK, border_width=1, border_color=BG_HIGHLIGHT, text_color=TEXT_PRIMARY, corner_radius=8)
        self.unique_text.pack(side=tk.RIGHT, fill=tk.Y)
        self.unique_text.configure(state=tk.DISABLED)
        
        self.after(200, self.filter_cards) 

    # --- Logic Methods ---
    
    def _select_av_card(self, card_id):
        self.selected_av_card_id = card_id
        for c in self.av_card_widgets:
            c.configure(border_color=ACCENT_PRIMARY if getattr(c, '_data_id', None) == card_id else BG_HIGHLIGHT)
            c.configure(fg_color=BG_MEDIUM if getattr(c, '_data_id', None) == card_id else BG_DARK)
    
    def filter_cards(self):
        self._rendering_cards = False # Cancel ongoing
        for widget in self.av_card_widgets:
            widget.destroy()
        self.av_card_widgets.clear()
            
        type_filter = self.type_var.get() if self.type_var.get() != "All" else None
        search_text = self.search_var.get()
        search = search_text if search_text else None
        owned_only = self.owned_only_var.get()
        
        cards = get_all_cards(type_filter=type_filter, search_term=search, owned_only=owned_only)
        self._card_render_queue = cards[:40] # soft limit
        self._rendering_cards = True
        
        self._process_card_queue()
        
    def _process_card_queue(self):
        if not self._rendering_cards or not self._card_render_queue:
            self._rendering_cards = False
            return
            
        # Process 5 cards per frame to stay at 60fps interaction
        chunk = self._card_render_queue[:5]
        self._card_render_queue = self._card_render_queue[5:]
        
        for card in chunk:
            card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level = card
            
            row_frame = ctk.CTkFrame(self.card_scroll, fg_color=BG_DARK, corner_radius=8, border_width=1, border_color=BG_HIGHLIGHT)
            row_frame.pack(fill=tk.X, pady=4, padx=4)
            row_frame._data_id = card_id
            self.av_card_widgets.append(row_frame)
            
            def make_clickable(w, id=card_id):
                w.bind("<Button-1>", lambda e, c=id: self._select_av_card(c))
                w.bind("<Double-Button-1>", lambda e, c=id: self.add_selected_to_deck())
                for child in w.winfo_children():
                    make_clickable(child, id)
                    
            # Use small Image
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(image_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((40, 40), Image.Resampling.LANCZOS)
                        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(40, 40))
                        self.icon_cache[card_id] = img
                    except: pass
            
            ctk.CTkLabel(row_frame, text="", image=img if img else None, width=40, height=40, corner_radius=4).pack(side=tk.LEFT, padx=5, pady=5)
            
            info = ctk.CTkFrame(row_frame, fg_color="transparent")
            info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            ctk.CTkLabel(info, text=name, font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, anchor="w").pack(fill=tk.X)
            ctk.CTkLabel(info, text=f"{get_type_icon(card_type)} {card_type} • {rarity}", font=FONT_SMALL, text_color=get_rarity_color(rarity), anchor="w").pack(fill=tk.X)
            
            make_clickable(row_frame)
            
        if self._card_render_queue:
            self.after(15, self._process_card_queue)

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
        if not self.current_deck_id: return
            
        for s in self.card_slots: s.reset()
        self.deck_slots = [None] * 6
        
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
                for s in self.card_slots: s.reset()
                self.deck_slots = [None] * 6
                self.update_deck_count()
                self.update_effects_breakdown()

    def add_selected_to_deck(self):
        if not self.current_deck_id:
            messagebox.showwarning("No Deck", "Select or create a deck first.")
            return
            
        if not self.selected_av_card_id:
            return
            
        card_id = self.selected_av_card_id
        
        if card_id in self.deck_slots:
             messagebox.showinfo("Duplicate Card", "This card is already in the deck.")
             return

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
            self.update_deck_count()
            self.update_effects_breakdown()
    
    def update_deck_count(self):
        count = sum(1 for slot in self.deck_slots if slot is not None)
        self.deck_count_label.configure(text=f"{count} / 6 Cards")

    def on_slot_level_changed(self, index, new_level):
        if self.current_deck_id and self.deck_slots[index]:
            card_id = self.deck_slots[index]
            add_card_to_deck(self.current_deck_id, card_id, index, new_level)
            self.update_effects_breakdown()

    def update_effects_breakdown(self):
        # Clear Table
        for widget in self.table_scroll.winfo_children():
            widget.destroy()
        
        self.unique_text.configure(state=tk.NORMAL)
        self.unique_text.delete('1.0', tk.END)
        
        if not self.current_deck_id:
            self.unique_text.insert(tk.END, "No deck selected")
            self.unique_text.configure(state=tk.DISABLED)
            return

        card_info = []
        for i in range(6):
            if self.deck_slots[i]:
                level = int(self.card_slots[i].level_var.get())
                card_info.append((self.deck_slots[i], level))
            else:
                card_info.append(None)
        
        all_effects = {}
        unique_effects_list = []
        
        for i, info in enumerate(card_info):
            if info:
                card_id, level = info
                card_name = self.card_slots[i].name_label.cget("text")
                effects = get_effects_at_level(card_id, level)
                for name, value in effects:
                    if name == "Unique Effect":
                        unique_effects_list.append(f"• {card_name}:\n  {value}\n")
                        continue
                        
                    if name not in all_effects:
                        all_effects[name] = ['-'] * 6
                    all_effects[name][i] = value
        
        if unique_effects_list:
            self.unique_text.insert(tk.END, "\n".join(unique_effects_list))
        else:
            self.unique_text.insert(tk.END, "\nNo unique effects in this deck.")
        self.unique_text.configure(state=tk.DISABLED)

        # Build custom table headers
        hdr_bg = BG_MEDIUM
        headers = ["Effect Name", "Total"] + [f"Card {i+1}" for i in range(6)]
        for col_idx, text in enumerate(headers):
            ctk.CTkLabel(self.table_scroll, text=text, font=FONT_BODY_BOLD, fg_color=hdr_bg, text_color=TEXT_PRIMARY, corner_radius=4).grid(row=0, column=col_idx, sticky="nsew", padx=2, pady=2, ipadx=5, ipady=5)
        
        # Build Table rows
        row_idx = 1
        for effect_name, values in sorted(all_effects.items()):
            total = 0
            is_percent = False
            for v in values:
                if v and v != '-':
                    if '%' in str(v): is_percent = True
                    try: total += float(str(v).replace('%','').replace('+',''))
                    except: pass
            
            total_str = f"{total:.0f}%" if is_percent else (f"+{total:.0f}" if total > 0 else str(int(total)))
            
            # Row Widgets
            ctk.CTkLabel(self.table_scroll, text=effect_name, font=FONT_BODY, anchor="w", text_color=TEXT_SECONDARY).grid(row=row_idx, column=0, sticky="nsew", padx=5, pady=2)
            ctk.CTkLabel(self.table_scroll, text=total_str, font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY).grid(row=row_idx, column=1, sticky="nsew", padx=5, pady=2)
            
            for i, v in enumerate(values):
                ctk.CTkLabel(self.table_scroll, text=str(v), font=FONT_SMALL, text_color=TEXT_MUTED if v == '-' else TEXT_PRIMARY).grid(row=row_idx, column=2+i, sticky="nsew", padx=5, pady=2)
                
            row_idx += 1
