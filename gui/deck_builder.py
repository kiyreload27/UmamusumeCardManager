"""
Deck Builder Frame
Build decks with 6 cards and view combined effects with breakdown
Premium redesign with visual slot cards, drag-and-drop, export/import, and comparison
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import json
import sys
import os
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import (
    get_all_cards, get_all_decks, create_deck, delete_deck,
    add_card_to_deck, remove_card_from_deck, get_deck_cards,
    get_effects_at_level, export_single_deck, import_single_deck
)
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    get_type_color, get_type_icon, get_rarity_color,
    create_styled_button, create_styled_entry, create_card_frame
)
from gui.deck_comparison import show_deck_comparison
import tkinter.simpledialog


class CardSlot(ctk.CTkFrame):
    """Visual component for a single card slot with premium styling"""
    def __init__(self, parent, index, remove_callback, level_callback, on_drop_callback=None):
        super().__init__(
            parent, fg_color=BG_DARK, border_width=1,
            border_color=BG_LIGHT, corner_radius=RADIUS_MD
        )
        self.index = index
        self.remove_callback = remove_callback
        self.level_callback = level_callback
        self.on_drop = on_drop_callback
        self.image_ref = None
        self._is_occupied = False
        self.setup_ui()

        # Drop target – accept drags
        self.bind("<Enter>", self._on_drag_enter)
        self.bind("<Leave>", self._on_drag_leave)

    def setup_ui(self):
        self.columnconfigure(0, weight=1)

        # Slot number badge
        self.slot_label = ctk.CTkLabel(
            self, text=f"#{self.index + 1}",
            font=FONT_TINY, fg_color=BG_LIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM,
            height=18, width=24
        )
        self.slot_label.place(x=6, y=6)

        # Image placeholder
        self.image_label = ctk.CTkLabel(
            self, fg_color="transparent", text="＋",
            text_color=TEXT_DISABLED, font=('Segoe UI', 28),
            width=80, height=80, corner_radius=RADIUS_SM
        )
        self.image_label.grid(row=0, column=0, padx=SPACING_SM, pady=(SPACING_SM, 0))

        # Info text
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=1, column=0, sticky='ew', padx=SPACING_XS, pady=SPACING_XS)
        self.info_frame.columnconfigure(0, weight=1)

        self.name_label = ctk.CTkLabel(
            self.info_frame, text="Empty",
            fg_color="transparent", text_color=TEXT_DISABLED,
            font=FONT_TINY, anchor='center', height=16
        )
        self.name_label.grid(row=0, column=0, sticky='ew')

        # Controls (hidden by default)
        self.ctrl_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.ctrl_frame.grid(row=1, column=0, sticky='ew', pady=(SPACING_XS, 0))

        self.level_var = tk.StringVar(value="50")
        self.level_combo = ctk.CTkComboBox(
            self.ctrl_frame, variable=self.level_var,
            values=[], width=55, height=24, font=FONT_TINY,
            state='readonly', command=self._on_level_change
        )

        self.remove_btn = ctk.CTkButton(
            self.ctrl_frame, text="✕",
            fg_color="transparent", text_color=ACCENT_ERROR,
            font=FONT_BODY_BOLD, width=24, height=24,
            corner_radius=RADIUS_SM, hover_color=BG_HIGHLIGHT,
            command=lambda: self.remove_callback(self.index)
        )

        self.toggle_controls(False)

    def _on_drag_enter(self, event):
        """Visual feedback when a card is dragged over this slot"""
        if not self._is_occupied:
            self.configure(border_color=ACCENT_PRIMARY, border_width=2)

    def _on_drag_leave(self, event):
        """Remove visual feedback"""
        if not self._is_occupied:
            self.configure(border_color=BG_LIGHT, border_width=1)

    def accept_drop(self, card_id):
        """Called when a card is dropped on this slot"""
        if self.on_drop:
            self.on_drop(self.index, card_id)

    def toggle_controls(self, visible):
        # Level combo is always disabled — level is set by the Card Library
        self.level_combo.configure(state='disabled')
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
        self._is_occupied = True

        if rarity == 'SSR':
            valid_levels = [50, 45, 40, 35, 30]
            max_lvl = 50
        elif rarity == 'SR':
            valid_levels = [45, 40, 35, 30, 25]
            max_lvl = 45
        else:
            valid_levels = [40, 35, 30, 25, 20]
            max_lvl = 40

        # Force level into a valid value for this rarity BEFORE touching the widget
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = max_lvl
        if level not in valid_levels:
            level = max_lvl

        level_str = str(level)

        # Set the StringVar FIRST so configure(values=...) and configure(state=...) never
        # have a chance to re-render with the stale default "50"
        self.level_var.set(level_str)

        display_name = name if len(name) < 14 else name[:11] + "…"
        self.name_label.configure(text=display_name, text_color=TEXT_PRIMARY)

        # Rarity-colored top border
        rarity_border = {
            'SSR': ACCENT_WARNING, 'SR': TEXT_SECONDARY, 'R': BG_HIGHLIGHT
        }
        self.configure(
            border_color=rarity_border.get(rarity, BG_LIGHT),
            fg_color=BG_ELEVATED
        )

        self._load_image(image_path)

        # Now configure the combobox values and show controls
        self.level_combo.configure(values=[str(l) for l in valid_levels])
        self.toggle_controls(True)

        # Set AGAIN after toggle_controls (which calls configure(state=disabled)) to
        # ensure the widget cannot have reverted to its previous StringVar state
        self.level_var.set(level_str)
        self.level_combo.set(level_str)


    def reset(self):
        self._is_occupied = False
        self.name_label.configure(text="Empty", text_color=TEXT_DISABLED)

        if hasattr(self, 'image_label') and self.image_label:
            self.image_label.destroy()

        self.image_label = ctk.CTkLabel(
            self, fg_color="transparent", text="＋",
            text_color=TEXT_DISABLED, font=('Segoe UI', 28),
            width=80, height=80, corner_radius=RADIUS_SM
        )
        self.image_label.grid(row=0, column=0, padx=SPACING_SM, pady=(SPACING_SM, 0))

        self.configure(border_color=BG_LIGHT, fg_color=BG_DARK)
        self.image_ref = None
        self.toggle_controls(False)

    def _load_image(self, path):
        resolved_path = resolve_image_path(path)
        new_image = None
        if resolved_path and os.path.exists(resolved_path):
            try:
                pil_img = Image.open(resolved_path)
                pil_img.thumbnail((76, 76), Image.Resampling.LANCZOS)
                new_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(76, 76))
            except Exception:
                pass

        if hasattr(self, 'image_label') and self.image_label:
            self.image_label.destroy()

        if new_image:
            self.image_ref = new_image
            self.image_label = ctk.CTkLabel(
                self, fg_color="transparent", text="",
                image=new_image, width=80, height=80, corner_radius=RADIUS_SM
            )
        else:
            self.image_ref = None
            self.image_label = ctk.CTkLabel(
                self, fg_color="transparent",
                text="⚠️" if resolved_path else "🖼️",
                text_color=TEXT_MUTED, font=('Segoe UI', 28), width=80, height=80
            )

        self.image_label.grid(row=0, column=0, padx=SPACING_SM, pady=(SPACING_SM, 0))

    def _on_level_change(self, value):
        self.level_callback(self.index, int(value))


class DeckBuilderFrame(ctk.CTkFrame):
    """Deck builder with combined effects breakdown, drag-and-drop, export/import, and comparison"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.current_deck_id = None
        self.deck_slots = [None] * 6
        self.icon_cache = {}
        self.av_card_widgets = []
        self.selected_av_card_id = None

        # Drag state
        self._drag_card_id = None
        self._drag_indicator = None

        self._card_render_gen = 0
        self._card_render_queue = []
        # Persistent card data keyed by card_id so we can look up level even
        # after the render queue has been consumed chunk-by-chunk.
        self._all_rendered_cards = {}
        self._search_after_id = None

        self.setup_ui()
        self.refresh_decks()

    def setup_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=2)  # Main panel (Slots + Browser)
        self.grid_columnconfigure(1, weight=1)  # Sidebar (Effects)

        # === Left Main Panel (Deck + Browser) ===
        main_panel = ctk.CTkFrame(self, fg_color="transparent")
        main_panel.grid(row=0, column=0, sticky="nsew", padx=(SPACING_MD, SPACING_XS), pady=SPACING_MD)
        main_panel.grid_rowconfigure(0, weight=0)  # Deck area
        main_panel.grid_rowconfigure(1, weight=1)  # Browser area

        # Move the deck controls and slots to the top of main_panel
        # Deck controls bar
        deck_ctrl = ctk.CTkFrame(
            main_panel, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        deck_ctrl.grid(row=0, column=0, sticky="ew", pady=(0, SPACING_MD))

        deck_inner = ctk.CTkFrame(deck_ctrl, fg_color="transparent")
        deck_inner.pack(fill=tk.BOTH, padx=SPACING_LG, pady=SPACING_MD)

        ctk.CTkLabel(
            deck_inner, text="🎴  Deck",
            font=FONT_SUBHEADER, text_color=TEXT_SECONDARY
        ).pack(side=tk.LEFT, padx=(0, SPACING_SM))

        self.deck_combo = ctk.CTkComboBox(
            deck_inner, width=220, state='readonly',
            command=self.on_deck_selected_val
        )
        self.deck_combo.pack(side=tk.LEFT)

        create_styled_button(
            deck_inner, text="➕ New",
            command=self.create_new_deck, width=80
        ).pack(side=tk.LEFT, padx=SPACING_SM)

        ctk.CTkButton(
            deck_inner, text="🗑️",
            command=self.delete_current_deck,
            fg_color="transparent", hover_color=ACCENT_ERROR,
            text_color=TEXT_MUTED, width=36,
            font=FONT_BODY_BOLD, corner_radius=RADIUS_SM
        ).pack(side=tk.LEFT)

        self.deck_count_label = ctk.CTkLabel(
            deck_inner, text="0 / 6",
            font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY
        )
        self.deck_count_label.pack(side=tk.RIGHT)

        # Action buttons row (Compare, Export, Import)
        action_row = ctk.CTkFrame(deck_ctrl, fg_color="transparent")
        action_row.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_MD))

        ctk.CTkButton(
            action_row, text="⚖️ Compare",
            command=self._show_comparison,
            font=FONT_TINY, width=90, height=28,
            fg_color=BG_MEDIUM, hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM
        ).pack(side=tk.LEFT, padx=(0, SPACING_XS))

        ctk.CTkButton(
            action_row, text="📤 Export",
            command=self._export_deck,
            font=FONT_TINY, width=80, height=28,
            fg_color=BG_MEDIUM, hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM
        ).pack(side=tk.LEFT, padx=(0, SPACING_XS))

        ctk.CTkButton(
            action_row, text="📥 Import",
            command=self._import_deck,
            font=FONT_TINY, width=80, height=28,
            fg_color=BG_MEDIUM, hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM
        ).pack(side=tk.LEFT)

        # Card Slots Row (2x3 grid)
        self.slots_frame = ctk.CTkFrame(deck_ctrl, fg_color="transparent")
        self.slots_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_MD))

        self.card_slots = []
        for i in range(6):
            r = i // 3
            c = i % 3
            slot = CardSlot(
                self.slots_frame, i,
                self.remove_from_slot, self.on_slot_level_changed,
                on_drop_callback=self._on_card_dropped
            )
            slot.grid(row=r, column=c, padx=SPACING_XS, pady=SPACING_XS, sticky='nsew')
            self.slots_frame.columnconfigure(c, weight=1)
            self.card_slots.append(slot)

        # Card Browser (Bottom of Main Panel)
        browser_panel = ctk.CTkFrame(
            main_panel, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        browser_panel.grid(row=1, column=0, sticky="nsew")

        header = ctk.CTkFrame(browser_panel, fg_color="transparent")
        header.pack(fill=tk.X, pady=(SPACING_LG, SPACING_SM), padx=SPACING_LG)
        ctk.CTkLabel(
            header, text="📋  Available Cards",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        ctk.CTkLabel(
            header, text="drag → slot",
            font=FONT_TINY, text_color=TEXT_DISABLED
        ).pack(side=tk.RIGHT)

        filter_frame = ctk.CTkFrame(browser_panel, fg_color="transparent")
        filter_frame.pack(fill=tk.X, pady=(0, SPACING_SM), padx=SPACING_LG)

        self.type_var = tk.StringVar(value="All")
        self.owned_only_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()

        self.search_entry = create_styled_entry(
            filter_frame, textvariable=self.search_var,
            placeholder_text="Search..."
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, SPACING_SM))
        self.search_entry.bind('<KeyRelease>', self._schedule_filter)

        types = ["All", "Speed", "Stamina", "Power", "Guts", "Wisdom", "Friend", "Group"]
        type_combo = ctk.CTkComboBox(
            filter_frame, variable=self.type_var,
            values=types, width=100, state='readonly',
            command=lambda e: self.filter_cards()
        )
        type_combo.pack(side=tk.LEFT)

        rarity_frame = ctk.CTkFrame(browser_panel, fg_color="transparent")
        rarity_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))

        ctk.CTkLabel(
            rarity_frame, text="Rarity:",
            font=FONT_TINY, text_color=TEXT_MUTED
        ).pack(side=tk.LEFT, padx=(0, SPACING_XS))

        self.rarity_seg = ctk.CTkSegmentedButton(
            rarity_frame,
            values=["All", "SSR", "SR", "R"],
            command=lambda _: self.filter_cards(),
            font=FONT_TINY, height=26
        )
        self.rarity_seg.set("All")
        self.rarity_seg.pack(side=tk.LEFT, fill=tk.X, expand=True)

        owned_frame = ctk.CTkFrame(browser_panel, fg_color="transparent")
        owned_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))
        ctk.CTkCheckBox(
            owned_frame, text="Owned Only",
            variable=self.owned_only_var, command=self.filter_cards,
            font=FONT_TINY, checkbox_width=16, checkbox_height=16
        ).pack(side=tk.LEFT)

        add_btn = create_styled_button(
            browser_panel, text="➕  Add to Deck",
            command=self.add_selected_to_deck, style_type='accent'
        )
        add_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=SPACING_LG, padx=SPACING_LG)

        self.card_scroll = ctk.CTkScrollableFrame(browser_panel, fg_color="transparent")
        self.card_scroll.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=(0, SPACING_SM))
        self.card_scroll.columnconfigure(0, weight=1)

        # === Right Panel: Effects Summary Sidebar ===
        right_panel = ctk.CTkFrame(self, fg_color="transparent")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(SPACING_XS, SPACING_MD), pady=SPACING_MD)



        # Effects Breakdown
        effects_container = ctk.CTkFrame(
            right_panel, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        effects_container.pack(fill=tk.BOTH, expand=True)

        stats_header = ctk.CTkFrame(effects_container, fg_color="transparent")
        stats_header.pack(fill=tk.X, padx=SPACING_LG, pady=(SPACING_LG, SPACING_SM))
        ctk.CTkLabel(
            stats_header, text="📊  Combined Effects",
            font=FONT_SUBHEADER, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        # Deck Score badge
        self.score_badge = ctk.CTkLabel(
            stats_header, text="Score: —",
            font=FONT_BODY_BOLD, text_color=ACCENT_WARNING,
            fg_color=BG_MEDIUM, corner_radius=RADIUS_FULL,
            height=28, width=110
        )
        self.score_badge.pack(side=tk.LEFT, padx=(SPACING_SM, 0))

        ctk.CTkLabel(
            stats_header, text="✨ Unique Effects",
            font=FONT_SMALL, text_color=ACCENT_SECONDARY
        ).pack(side=tk.RIGHT)

        stats_body = ctk.CTkFrame(effects_container, fg_color="transparent")
        stats_body.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))

        # Effects table (top)
        self.table_scroll = ctk.CTkScrollableFrame(
            stats_body, fg_color=BG_DARKEST, corner_radius=RADIUS_SM,
            border_width=1, border_color=BG_LIGHT
        )
        self.table_scroll.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, SPACING_SM))
        self.table_scroll.columnconfigure(0, weight=3)
        self.table_scroll.columnconfigure(1, weight=1)

        # Unique effects (bottom)
        self.unique_text = ctk.CTkTextbox(
            stats_body, fg_color=BG_DARKEST, height=120,
            border_width=1, border_color=BG_LIGHT,
            text_color=TEXT_PRIMARY, corner_radius=RADIUS_SM,
            font=FONT_SMALL
        )
        self.unique_text.pack(side=tk.BOTTOM, fill=tk.X)
        self.unique_text.configure(state=tk.DISABLED)

        self.after(200, self.filter_cards)

    # --- Drag and Drop ---

    def _start_drag(self, card_id, event):
        """Start dragging a card from the browser"""
        self._drag_card_id = card_id
        # Bind global mouse events for drag
        self.winfo_toplevel().bind("<B1-Motion>", self._on_drag_motion)
        self.winfo_toplevel().bind("<ButtonRelease-1>", self._on_drag_release)

    def _on_drag_motion(self, event):
        """Update drag indicator position"""
        if not self._drag_card_id:
            return
        # Change cursor to indicate dragging
        try:
            self.winfo_toplevel().configure(cursor="hand2")
        except tk.TclError:
            pass

    def _on_drag_release(self, event):
        """End drag — check if dropped on a slot"""
        if not self._drag_card_id:
            return

        card_id = self._drag_card_id
        self._drag_card_id = None

        try:
            self.winfo_toplevel().configure(cursor="")
            self.winfo_toplevel().unbind("<B1-Motion>")
            self.winfo_toplevel().unbind("<ButtonRelease-1>")
        except tk.TclError:
            pass

        # Check which slot the mouse is over
        x, y = event.x_root, event.y_root
        for slot in self.card_slots:
            try:
                sx = slot.winfo_rootx()
                sy = slot.winfo_rooty()
                sw = slot.winfo_width()
                sh = slot.winfo_height()
                if sx <= x <= sx + sw and sy <= y <= sy + sh:
                    slot.accept_drop(card_id)
                    return
            except tk.TclError:
                pass

    def _on_card_dropped(self, slot_index, card_id):
        """Handle a card being dropped on a slot"""
        if not self.current_deck_id:
            messagebox.showwarning("No Deck", "Select or create a deck first.")
            return

        if card_id in self.deck_slots:
            messagebox.showinfo("Duplicate", "This card is already in the deck.")
            return

        if self.deck_slots[slot_index] is not None:
            # Replace existing card
            remove_card_from_deck(self.current_deck_id, slot_index)

        # Use the card's owned level from the persistent card dict
        level = self._get_card_level(card_id)

        add_card_to_deck(self.current_deck_id, card_id, slot_index, level)
        self.load_deck()

    # --- Deck Export/Import ---

    def _export_deck(self):
        """Export current deck to JSON"""
        if not self.current_deck_id:
            messagebox.showwarning("No Deck", "Select a deck to export.")
            return

        deck_data = export_single_deck(self.current_deck_id)
        if not deck_data:
            return

        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Export Deck",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"deck_{deck_data['name'].replace(' ', '_')}.json"
        )
        if not filepath:
            return

        deck_data['_format'] = 'uma_deck_v1'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(deck_data, f, indent=2, ensure_ascii=False)

        messagebox.showinfo("Exported", f"Deck '{deck_data['name']}' exported with {len(deck_data['slots'])} cards.")

    def _import_deck(self):
        """Import a deck from JSON"""
        filepath = filedialog.askopenfilename(
            parent=self,
            title="Import Deck",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            messagebox.showerror("Error", f"Invalid file: {e}")
            return

        deck_id, matched, total = import_single_deck(deck_data)
        self.current_deck_id = deck_id
        self.refresh_decks()
        self.deck_combo.set(f"{deck_id}: {deck_data.get('name', 'Imported')}")
        self.load_deck()

        messagebox.showinfo(
            "Imported",
            f"Deck '{deck_data.get('name')}' imported.\n"
            f"Matched {matched}/{total} cards."
        )

    # --- Comparison ---

    def _show_comparison(self):
        """Open deck comparison dialog"""
        show_deck_comparison(self.winfo_toplevel(), current_deck_id=self.current_deck_id)

    # --- Card Selection & Rendering ---

    def _select_av_card(self, card_id):
        self.selected_av_card_id = card_id
        for c in self.av_card_widgets:
            is_sel = getattr(c, '_data_id', None) == card_id
            c.configure(
                border_color=ACCENT_PRIMARY if is_sel else BG_LIGHT,
                fg_color=BG_ELEVATED if is_sel else BG_DARK
            )

    def _schedule_filter(self, _=None):
        """Debounce filter so we don't query the DB on every keystroke"""
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, self.filter_cards)

    def filter_cards(self):
        self._search_after_id = None
        self._card_render_gen += 1
        my_gen = self._card_render_gen

        for widget in self.av_card_widgets:
            widget.destroy()
        self.av_card_widgets.clear()
        # Clear persistent lookup so stale cards from old filters are gone
        self._all_rendered_cards.clear()

        type_filter = self.type_var.get() if self.type_var.get() != "All" else None
        # Read directly from the segmented button widget (CTkSegmentedButton does NOT
        # write back to a StringVar, so we must call .get() on the widget itself)
        rarity_sel = self.rarity_seg.get()
        rarity_filter = rarity_sel if rarity_sel != "All" else None
        search_text = self.search_var.get()
        search = search_text if search_text else None
        owned_only = self.owned_only_var.get()

        cards = get_all_cards(rarity_filter=rarity_filter, type_filter=type_filter, search_term=search, owned_only=owned_only)
        self._card_render_queue = list(cards[:40])
        self._process_card_queue(my_gen)

    def _process_card_queue(self, gen):
        if gen != self._card_render_gen or not self._card_render_queue:
            return

        chunk = self._card_render_queue[:10]
        self._card_render_queue = self._card_render_queue[10:]

        for card in chunk:
            card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level = card
            # Store in persistent dict so level lookup always works later
            self._all_rendered_cards[card_id] = card

            row_frame = ctk.CTkFrame(
                self.card_scroll, fg_color=BG_DARK,
                corner_radius=RADIUS_SM, border_width=1, border_color=BG_LIGHT
            )
            row_frame.pack(fill=tk.X, pady=3, padx=SPACING_XS)
            row_frame._data_id = card_id
            self.av_card_widgets.append(row_frame)

            def make_clickable(w, id=card_id):
                w.bind("<Button-1>", lambda e, c=id: self._select_av_card(c))
                w.bind("<Double-Button-1>", lambda e, c=id: self.add_selected_to_deck())
                for child in w.winfo_children():
                    make_clickable(child, id)

            def make_draggable(w, id=card_id):
                """Enable drag from card browser items"""
                w.bind("<B1-Motion>", lambda e, c=id: self._start_drag(c, e))
                for child in w.winfo_children():
                    make_draggable(child, id)

            # Image
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(image_path)
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((36, 36), Image.Resampling.LANCZOS)
                        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(36, 36))
                        self.icon_cache[card_id] = img
                    except (OSError, SyntaxError, ValueError):
                        pass

            ctk.CTkLabel(
                row_frame, text="", image=img if img else None,
                width=36, height=36, corner_radius=RADIUS_SM
            ).pack(side=tk.LEFT, padx=SPACING_XS, pady=SPACING_XS)

            info = ctk.CTkFrame(row_frame, fg_color="transparent")
            info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=SPACING_XS, pady=SPACING_XS)

            ctk.CTkLabel(
                info, text=name,
                font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, anchor="w"
            ).pack(fill=tk.X)

            ctk.CTkLabel(
                info, text=f"{get_type_icon(card_type)} {card_type} · {rarity}",
                font=FONT_TINY, text_color=get_rarity_color(rarity), anchor="w"
            ).pack(fill=tk.X)

            make_clickable(row_frame)
            make_draggable(row_frame)

        if self._card_render_queue and gen == self._card_render_gen:
            self.after(20, lambda: self._process_card_queue(gen))

    # --- Deck CRUD ---

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

        for s in self.card_slots:
            s.reset()
        self.deck_slots = [None] * 6

        deck_cards = get_deck_cards(self.current_deck_id)

        for card in deck_cards:
            slot_pos, level, card_id, name, rarity, card_type, image_path = card
            if 0 <= slot_pos < 6:
                # Repair legacy bad levels (e.g. R card stored at level 50)
                corrected_level = min(level, self._rarity_max_level(rarity))
                if corrected_level != level:
                    add_card_to_deck(self.current_deck_id, card_id, slot_pos, corrected_level)
                    level = corrected_level
                self.deck_slots[slot_pos] = card_id
                self.card_slots[slot_pos].set_card(
                    (card_id, name, rarity, card_type, image_path, level)
                )

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
                for s in self.card_slots:
                    s.reset()
                self.deck_slots = [None] * 6
                self.update_deck_count()
                self.update_effects_breakdown()

    @staticmethod
    def _rarity_max_level(rarity):
        """Return the maximum valid level for a given rarity"""
        if rarity == 'SSR':
            return 50
        elif rarity == 'SR':
            return 45
        return 40  # R and fallback

    def _get_card_level(self, card_id_or_data):
        """Get the appropriate level for a card when adding to deck.
        Accepts either a card_id (int) or a card data tuple.
        Uses owned level from Card Library; falls back to rarity-based max.
        ALWAYS caps the result by the rarity-based maximum."""
        # Resolve card_data from persistent dict if given an id
        if isinstance(card_id_or_data, int):
            card_data = self._all_rendered_cards.get(card_id_or_data)
        else:
            card_data = card_id_or_data
            if card_data:
                self._all_rendered_cards[card_data[0]] = card_data

        if card_data:
            # card_data: (card_id, name, rarity, card_type, max_level, image_path, is_owned, owned_level)
            rarity = card_data[2]
            max_level = self._rarity_max_level(rarity)
            owned_level = card_data[7]
            if owned_level:
                # Cap: a card physically can't exceed its rarity max regardless of what's
                # stored in the library (user may have typed 50 for an SR/R by mistake)
                return min(int(owned_level), max_level)
            return max_level
        return 50  # ultimate fallback (unknown card)

    def add_selected_to_deck(self):
        if not self.current_deck_id:
            messagebox.showwarning("No Deck", "Select or create a deck first.")
            return

        if not self.selected_av_card_id:
            return

        card_id = self.selected_av_card_id

        if card_id in self.deck_slots:
            messagebox.showinfo("Duplicate", "This card is already in the deck.")
            return

        # Look up owned level from the persistent card dict (never wiped during render)
        level = self._get_card_level(card_id)

        for i in range(6):
            if self.deck_slots[i] is None:
                add_card_to_deck(self.current_deck_id, card_id, i, level)
                self.load_deck()
                return

        messagebox.showinfo("Full", "Remove a card first to add a new one.")

    def remove_from_slot(self, index):
        if self.current_deck_id and self.deck_slots[index]:
            remove_card_from_deck(self.current_deck_id, index)
            self.deck_slots[index] = None
            self.card_slots[index].reset()
            self.update_deck_count()
            self.update_effects_breakdown()

    def update_deck_count(self):
        count = sum(1 for slot in self.deck_slots if slot is not None)
        self.deck_count_label.configure(text=f"{count} / 6")

    def on_slot_level_changed(self, index, new_level):
        if self.current_deck_id and self.deck_slots[index]:
            card_id = self.deck_slots[index]
            add_card_to_deck(self.current_deck_id, card_id, index, new_level)
            self.update_effects_breakdown()

    def update_effects_breakdown(self):
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
                # Cap level to the card's rarity max before DB lookup
                # (guards against old deck_slots rows with level=50 for SR/R cards)
                rarity = None
                for row in self._all_rendered_cards.values():
                    if row[0] == card_id:
                        rarity = row[2]
                        break
                if rarity:
                    level = min(level, self._rarity_max_level(rarity))
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

        # Table headers
        hdr_bg = BG_MEDIUM
        headers = ["Effect", "Total"] + [f"#{i+1}" for i in range(6)]
        for col_idx, text in enumerate(headers):
            ctk.CTkLabel(
                self.table_scroll, text=text, font=FONT_BODY_BOLD,
                fg_color=hdr_bg, text_color=TEXT_PRIMARY,
                corner_radius=RADIUS_SM
            ).grid(
                row=0, column=col_idx, sticky="nsew",
                padx=1, pady=1, ipadx=SPACING_XS, ipady=SPACING_XS
            )

        # Table rows
        row_idx = 1
        for effect_name, values in sorted(all_effects.items()):
            total = 0
            is_percent = False
            for v in values:
                if v and v != '-':
                    if '%' in str(v):
                        is_percent = True
                    try:
                        total += float(str(v).replace('%', '').replace('+', ''))
                    except:
                        pass

            total_str = (
                f"{total:.0f}%" if is_percent
                else (f"+{total:.0f}" if total > 0 else str(int(total)))
            )

            ctk.CTkLabel(
                self.table_scroll, text=effect_name,
                font=FONT_BODY, anchor="w",
                text_color=TEXT_SECONDARY
            ).grid(row=row_idx, column=0, sticky="nsew", padx=SPACING_XS, pady=1)

            ctk.CTkLabel(
                self.table_scroll, text=total_str,
                font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY
            ).grid(row=row_idx, column=1, sticky="nsew", padx=SPACING_XS, pady=1)

            for i, v in enumerate(values):
                ctk.CTkLabel(
                    self.table_scroll, text=str(v),
                    font=FONT_TINY,
                    text_color=TEXT_DISABLED if v == '-' else TEXT_PRIMARY
                ).grid(row=row_idx, column=2+i, sticky="nsew", padx=SPACING_XS, pady=1)

            row_idx += 1

        # Compute Deck Score = Friendship Bonus ×2 + Training Bonus + Hint Rate + Race Bonus
        def _parse_num(v):
            try:
                return float(str(v).replace('%', '').replace('+', ''))
            except:
                return 0.0

        def _get_total(effect_key):
            for name, vals in all_effects.items():
                if effect_key.lower() in name.lower():
                    return sum(_parse_num(v) for v in vals if v and v != '-')
            return 0.0

        friendship = _get_total('Friendship')
        training   = _get_total('Training')
        hint_rate   = _get_total('Hint Rate')
        race_bonus  = _get_total('Race Bonus')
        score = int(friendship * 2 + training + hint_rate + race_bonus)

        if score > 0:
            color = ACCENT_SUCCESS if score >= 300 else (ACCENT_WARNING if score >= 150 else TEXT_MUTED)
            self.score_badge.configure(text=f"⭐ Score: {score}", text_color=color)
        else:
            self.score_badge.configure(text="Score: —", text_color=TEXT_MUTED)
