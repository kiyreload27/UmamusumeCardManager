"""
Deck Skills View - Detailed breakdown of all skills in a deck or for a single card
Premium redesign with compact collapsible skill rows, sticky card headers, and top summary bar
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

    def __init__(self, parent, navigate_to_card_callback=None, navigate_to_skill_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_to_card = navigate_to_card_callback
        self.navigate_to_skill = navigate_to_skill_callback
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

        # === Summary stats bar — shown prominently at top ===
        self.summary_frame = ctk.CTkFrame(
            self, fg_color=BG_MEDIUM, corner_radius=RADIUS_MD,
            border_width=1, border_color=BG_LIGHT
        )
        self.summary_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))

        self.stats_total = ctk.CTkLabel(
            self.summary_frame, text="—  Skills",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        )
        self.stats_total.pack(side=tk.LEFT, padx=SPACING_LG, pady=SPACING_SM)

        self.stats_hints = ctk.CTkLabel(
            self.summary_frame, text="Hints: —",
            font=FONT_SMALL, text_color=ACCENT_INFO
        )
        self.stats_hints.pack(side=tk.LEFT, padx=SPACING_MD)

        self.stats_events = ctk.CTkLabel(
            self.summary_frame, text="Events: —",
            font=FONT_SMALL, text_color=ACCENT_SECONDARY
        )
        self.stats_events.pack(side=tk.LEFT, padx=SPACING_SM)

        self.stats_golden = ctk.CTkLabel(
            self.summary_frame, text="Golden: —",
            font=FONT_SMALL, text_color=ACCENT_WARNING
        )
        self.stats_golden.pack(side=tk.LEFT, padx=SPACING_SM)

        # Results scroll
        self.results_container = ctk.CTkFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        self.results_container.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))

        self.scroll_area = ctk.CTkScrollableFrame(self.results_container, fg_color="transparent")
        self.scroll_area.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=SPACING_SM)

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

    def _update_summary(self, total_skills, hint_count, event_count, golden_count):
        """Update the top summary bar with skill counts"""
        self.stats_total.configure(text=f"{total_skills}  Skills")
        self.stats_hints.configure(text=f"Hints: {hint_count}")
        self.stats_events.configure(text=f"Events: {event_count}")
        self.stats_golden.configure(text=f"✨ Golden: {golden_count}")

    def show_deck_skills(self, deck_id):
        self._clear_blocks()
        self._block_render_gen += 1
        my_gen = self._block_render_gen

        deck_cards = get_deck_cards(deck_id)
        if not deck_cards:
            self._update_summary(0, 0, 0, 0)
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

        self._update_summary(total_skills, hint_count, event_count, golden_count)
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
        """Render a card block with compact collapsible skill rows"""
        block_frame = ctk.CTkFrame(
            self.scroll_area, fg_color=BG_DARK,
            corner_radius=RADIUS_MD, border_width=1,
            border_color=ACCENT_SUCCESS if is_owned else BG_LIGHT
        )
        block_frame.pack(fill=tk.X, pady=SPACING_SM, padx=SPACING_XS)
        self.card_blocks.append(block_frame)

        # Sticky header
        header = ctk.CTkFrame(block_frame, fg_color=BG_MEDIUM, corner_radius=RADIUS_SM)
        header.pack(fill=tk.X, padx=SPACING_XS, pady=(SPACING_XS, 0))

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
        ).pack(side=tk.LEFT, padx=(SPACING_SM, SPACING_SM), pady=SPACING_XS)

        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

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

        ctk.CTkLabel(
            header, text=f"{len(skills)} skills",
            font=FONT_TINY, text_color=TEXT_DISABLED,
            fg_color=BG_LIGHT, corner_radius=RADIUS_FULL,
            height=20, width=60
        ).pack(side=tk.RIGHT, padx=SPACING_MD)

        if not skills:
            ctk.CTkLabel(
                block_frame, text="No notable skills found.",
                font=FONT_BODY, text_color=TEXT_MUTED
            ).pack(pady=SPACING_SM)
            return

        # Compact skills list — each skill is a single tight row
        # Clicking on a skill row expands/collapses its description
        skills_container = ctk.CTkFrame(block_frame, fg_color="transparent")
        skills_container.pack(fill=tk.X, padx=SPACING_SM, pady=(SPACING_XS, SPACING_SM))

        for skill in skills:
            self._render_compact_skill_row(skills_container, skill)

    def _render_compact_skill_row(self, parent, skill):
        """Render a single compact skill row with expand-on-click description"""
        is_golden = skill['golden']
        has_desc = bool(skill.get('desc'))

        # Source badge color
        if is_golden:
            src_color = ACCENT_WARNING
            prefix = "✨ "
            c_name = ACCENT_WARNING
        elif 'Event' in skill['source']:
            src_color = ACCENT_SECONDARY
            prefix = "◆ "
            c_name = TEXT_PRIMARY
        else:
            src_color = ACCENT_INFO
            prefix = "• "
            c_name = TEXT_SECONDARY

        # Wrapper for the row + hidden description
        row_wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        row_wrapper.pack(fill=tk.X, pady=1)

        skill_row = ctk.CTkFrame(
            row_wrapper,
            fg_color="#2a2200" if is_golden else BG_MEDIUM,
            corner_radius=RADIUS_SM
        )
        skill_row.pack(fill=tk.X)

        # Skill name
        name_label = ctk.CTkLabel(
            skill_row,
            text=f"{prefix}{skill['name']}",
            font=FONT_BODY_BOLD if is_golden else FONT_SMALL,
            text_color=c_name, anchor="w",
            cursor="hand2" if (self.navigate_to_skill or has_desc) else ""
        )
        name_label.pack(side=tk.LEFT, padx=SPACING_SM, pady=4)

        # Source badge (compact)
        ctk.CTkLabel(
            skill_row, text=skill['source'],
            font=FONT_TINY, text_color=src_color,
            fg_color=BG_DARK, corner_radius=RADIUS_SM,
            height=18
        ).pack(side=tk.RIGHT, padx=SPACING_SM, pady=4)

        # Hidden description label (toggled on click)
        desc_label = None
        desc_text = skill.get('desc') or ''
        expanded = [False]

        if has_desc:
            desc_label = ctk.CTkLabel(
                row_wrapper,
                text=desc_text,
                font=FONT_TINY, text_color=TEXT_MUTED,
                anchor="w", justify="left", wraplength=600
            )
            # Not packed initially

        def toggle_desc(e):
            if not desc_label:
                return
            expanded[0] = not expanded[0]
            if expanded[0]:
                desc_label.pack(fill=tk.X, padx=(SPACING_LG, SPACING_SM), pady=(0, 2))
                skill_row.configure(fg_color=BG_HIGHLIGHT if not is_golden else "#3d3200")
            else:
                desc_label.pack_forget()
                skill_row.configure(fg_color="#2a2200" if is_golden else BG_MEDIUM)

        if has_desc:
            skill_row.bind("<Button-1>", toggle_desc)
            name_label.bind("<Button-1>", toggle_desc if not self.navigate_to_skill else
                            lambda e, sn=skill['name']: self.navigate_to_skill(sn))

        if self.navigate_to_skill and not has_desc:
            name_label.bind(
                "<Button-1>",
                lambda e, sn=skill['name']: self.navigate_to_skill(sn)
            )

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
        self._update_summary(total_skills, hint_count, event_count, golden_count)
