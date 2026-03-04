"""
Deck Skills View - Detailed breakdown of all skills in a deck or for a single card
Premium redesign with card blocks and skill source badges
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os
import logging
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import (
    get_all_decks, get_deck_cards, get_card_by_id,
    get_hints, get_all_event_skills
)
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_WARNING, ACCENT_SUCCESS, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_card_frame, get_type_icon, get_rarity_color
)


class DeckSkillsFrame(ctk.CTkFrame):
    """Frame for viewing combined skills of a deck or individual cards"""

    def __init__(self, parent, navigate_to_card_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_to_card = navigate_to_card_callback
        self.icon_cache = {}
        self.current_mode = "Deck"
        self.card_blocks = []

        self._block_render_gen = 0
        self._block_render_queue = []

        self.create_widgets()
        self.refresh_decks()

    def create_widgets(self):
        """Create the deck skills interface"""
        # Controls bar
        ctrl_frame = ctk.CTkFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        ctrl_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(SPACING_LG, SPACING_SM))

        selection_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        selection_frame.pack(side=tk.LEFT, padx=SPACING_LG, pady=SPACING_LG)

        ctk.CTkLabel(
            selection_frame, text="📜  Select Deck:",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT, padx=(0, SPACING_SM))

        self.deck_combo = ctk.CTkComboBox(
            selection_frame, width=250, state='readonly',
            command=self.on_deck_selected_val
        )
        self.deck_combo.pack(side=tk.LEFT)

        self.mode_label = ctk.CTkLabel(
            ctrl_frame, text="Showing skills for selected deck",
            font=FONT_SMALL, text_color=ACCENT_PRIMARY
        )
        self.mode_label.pack(side=tk.RIGHT, padx=SPACING_LG)

        # Results scroll
        self.results_container = ctk.CTkFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        self.results_container.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))

        self.scroll_area = ctk.CTkScrollableFrame(self.results_container, fg_color="transparent")
        self.scroll_area.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=SPACING_SM)

        # Stats footer
        self.stats_label = ctk.CTkLabel(
            self.results_container, text="",
            font=FONT_TINY, text_color=TEXT_DISABLED
        )
        self.stats_label.pack(side=tk.BOTTOM, anchor='e', pady=SPACING_SM, padx=SPACING_LG)

    def refresh_decks(self):
        decks = get_all_decks()
        values = [f"{d[0]}: {d[1]}" for d in decks]
        self.deck_combo.configure(values=values)
        if values:
            self.deck_combo.set(values[0])
            self.on_deck_selected_val(values[0])

    def on_deck_selected_val(self, value):
        if not value:
            return
        deck_id = int(value.split(':')[0])
        deck_name = value.split(': ')[1]

        self.current_mode = "Deck"
        self.mode_label.configure(text=f"Deck: {deck_name}", text_color=ACCENT_PRIMARY)
        self.show_deck_skills(deck_id)

    def _clear_blocks(self):
        for block in self.card_blocks:
            block.destroy()
        self.card_blocks.clear()

    def show_deck_skills(self, deck_id):
        self._clear_blocks()
        self._block_render_gen += 1
        my_gen = self._block_render_gen

        deck_cards = get_deck_cards(deck_id)
        if not deck_cards:
            self.stats_label.configure(text="Deck is empty")
            return

        card_data_list = []
        total_skills = 0
        hint_count = 0
        event_count = 0
        golden_count = 0

        for card_row in deck_cards:
            slot_pos, level, card_id, name, rarity, card_type, image_path = card_row
            card_full = get_card_by_id(card_id)
            is_owned = bool(card_full[7]) if card_full else False

            skills = []
            hints = get_hints(card_id)
            for h_name, h_desc in hints:
                skills.append({"name": h_name, "source": "Training Hint", "desc": h_desc, "golden": False})
                total_skills += 1
                hint_count += 1

            events = get_all_event_skills(card_id)
            for event in events:
                src = "Event"
                golden = False
                if event.get('is_gold', False):
                    src = "Event (Golden)"
                    golden = True
                    golden_count += 1
                else:
                    event_count += 1
                skills.append({"name": event['skill_name'], "source": src, "desc": event['details'], "golden": golden})
                total_skills += 1

            card_data_list.append((card_id, name, rarity, card_type, image_path, is_owned, skills))

        self.stats_label.configure(
            text=f"{total_skills} skills  ·  Hints: {hint_count}  ·  Events: {event_count}  ·  Golden: {golden_count}"
        )
        self._block_render_queue = card_data_list[:]
        self._process_block_queue(my_gen)

    def _process_block_queue(self, gen):
        if gen != self._block_render_gen or not self._block_render_queue:
            return

        card_id, name, rarity, card_type, image_path, is_owned, skills = self._block_render_queue.pop(0)
        self._render_card_block(card_id, name, rarity, card_type, image_path, is_owned, skills)

        if self._block_render_queue and gen == self._block_render_gen:
            self.after(25, lambda: self._process_block_queue(gen))

    def _render_card_block(self, card_id, name, rarity, card_type, image_path, is_owned, skills):
        """Render a card block with its skills"""
        block_frame = ctk.CTkFrame(
            self.scroll_area, fg_color=BG_DARK,
            corner_radius=RADIUS_MD, border_width=1,
            border_color=ACCENT_SUCCESS if is_owned else BG_LIGHT
        )
        block_frame.pack(fill=tk.X, pady=SPACING_SM, padx=SPACING_XS)
        self.card_blocks.append(block_frame)

        # Header
        header = ctk.CTkFrame(block_frame, fg_color="transparent")
        header.pack(fill=tk.X, padx=SPACING_MD, pady=SPACING_SM)

        # Image
        img = self.icon_cache.get(card_id)
        if not img:
            resolved = resolve_image_path(image_path)
            if resolved and os.path.exists(resolved):
                try:
                    pil_img = Image.open(resolved)
                    pil_img.thumbnail((44, 44), Image.Resampling.LANCZOS)
                    img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(44, 44))
                    self.icon_cache[card_id] = img
                except (OSError, SyntaxError, ValueError) as e:
                    logging.debug(f"Failed to load deck skill card icon: {e}")

        ctk.CTkLabel(
            header, text="", image=img if img else None,
            width=44, height=44, corner_radius=RADIUS_SM
        ).pack(side=tk.LEFT, padx=(0, SPACING_SM))

        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Card name — clickable for cross-view linking
        name_label = ctk.CTkLabel(
            info, text=name,
            font=FONT_SUBHEADER, text_color=ACCENT_PRIMARY, anchor="w",
            cursor="hand2"
        )
        name_label.pack(fill=tk.X)
        if self.navigate_to_card:
            name_label.bind("<Button-1>", lambda e, cid=card_id: self.navigate_to_card(cid))

        owned_text = " · Owned ✓" if is_owned else ""
        ctk.CTkLabel(
            info, text=f"{get_type_icon(card_type)} {card_type} · {rarity}{owned_text}",
            font=FONT_TINY, text_color=get_rarity_color(rarity), anchor="w"
        ).pack(fill=tk.X)

        # Skill count badge
        ctk.CTkLabel(
            header, text=f"{len(skills)} skills",
            font=FONT_TINY, text_color=TEXT_DISABLED,
            fg_color=BG_MEDIUM, corner_radius=RADIUS_FULL,
            height=20, width=60
        ).pack(side=tk.RIGHT)

        if not skills:
            ctk.CTkLabel(
                block_frame, text="No notable skills found.",
                font=FONT_BODY, text_color=TEXT_MUTED
            ).pack(pady=SPACING_SM)
            return

        # Skills list
        skills_container = ctk.CTkFrame(block_frame, fg_color="transparent")
        skills_container.pack(fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_MD))

        for skill in skills:
            skill_row = ctk.CTkFrame(
                skills_container, fg_color=BG_MEDIUM, corner_radius=RADIUS_SM
            )
            skill_row.pack(fill=tk.X, pady=2)

            # Left: skill name + source
            left_col = ctk.CTkFrame(skill_row, fg_color="transparent", width=240)
            left_col.pack(side=tk.LEFT, fill=tk.Y, padx=SPACING_SM, pady=SPACING_SM)
            left_col.pack_propagate(False)

            prefix = "✨ " if skill['golden'] else "•  "
            c_name = ACCENT_WARNING if skill['golden'] else TEXT_PRIMARY

            # Source badge color
            if skill['golden']:
                src_color = ACCENT_WARNING
            elif 'Event' in skill['source']:
                src_color = ACCENT_SECONDARY
            elif 'Hint' in skill['source']:
                src_color = ACCENT_INFO
            else:
                src_color = TEXT_MUTED

            ctk.CTkLabel(
                left_col, text=f"{prefix}{skill['name']}",
                font=FONT_BODY_BOLD, text_color=c_name, anchor="w"
            ).pack(fill=tk.X)

            # Source as colored badge
            ctk.CTkLabel(
                left_col, text=skill['source'],
                font=FONT_TINY, text_color=src_color, anchor="w"
            ).pack(fill=tk.X)

            # Right: Description
            right_col = ctk.CTkFrame(skill_row, fg_color="transparent")
            right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=SPACING_SM)

            ctk.CTkLabel(
                right_col,
                text=skill['desc'] if skill['desc'] else "No description available",
                font=FONT_SMALL, text_color=TEXT_SECONDARY,
                justify="left", anchor="w", wraplength=400
            ).pack(fill=tk.X)

    def set_card(self, card_id):
        """Show skills for a single card selection"""
        card = get_card_by_id(card_id)
        if not card:
            return
        card_id, name, rarity, card_type, max_level, url, image_path, is_owned, owned_level = card

        self.current_mode = "Single"
        self.mode_label.configure(text=f"Card: {name}", text_color=ACCENT_SECONDARY)

        self._clear_blocks()

        total_skills = 0
        hint_count = 0
        event_count = 0
        golden_count = 0
        skills = []

        hints = get_hints(card_id)
        for h_name, h_desc in hints:
            skills.append({"name": h_name, "source": "Training Hint", "desc": h_desc, "golden": False})
            total_skills += 1
            hint_count += 1

        events = get_all_event_skills(card_id)
        for event in events:
            src = "Event"
            golden = False
            if event.get('is_gold', False):
                src = "Event (Golden)"
                golden = True
                golden_count += 1
            else:
                event_count += 1
            skills.append({"name": event['skill_name'], "source": src, "desc": event['details'], "golden": golden})
            total_skills += 1

        self._render_card_block(card_id, name, rarity, card_type, image_path, is_owned, skills)
        self.stats_label.configure(
            text=f"{total_skills} skills  ·  Hints: {hint_count}  ·  Events: {event_count}  ·  Golden: {golden_count}"
        )
