"""
Skill Search View - Find cards by the skills they teach
Premium redesign with filterable skill list, keyword category bar, and rich card results
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os
import logging
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_unique_skills, get_cards_with_skill, get_card_by_id, get_hints, get_all_event_skills
from utils import resolve_image_path
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY, ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_card_frame, get_type_icon, get_rarity_color,
    create_styled_button, create_styled_entry
)

# Keyword-based category map: category label -> keywords to match in skill name (case-insensitive)
SKILL_CATEGORIES = {
    "All":         [],
    "Speed":       ["speed", "acceleration", "escape", "start dash", "leading"],
    "Stamina":     ["stamina", "recovery", "heal", "recover", "second wind"],
    "Power":       ["power", "strength", "push"],
    "Guts":        ["guts", "tenac", "endur", "persist"],
    "Wisdom":      ["wisdom", "vision", "eye", "foresight", "strategic"],
    "Corner":      ["corner", "curve", "bend", "turn"],
    "Final":       ["final", "straight", "spurt", "last", "end close"],
    "Positioning": ["position", "pass", "overtake", "outside", "inside", "between", "leader", "chaser", "runner"],
    "Golden":      [],   # special: filtered by is_golden flag
}


class SkillSearchFrame(ctk.CTkFrame):
    """Frame for searching skills and finding cards that have them"""

    def __init__(self, parent, navigate_to_card_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_to_card = navigate_to_card_callback
        self.all_skills = []
        self.icon_cache = {}
        self.current_skill = None
        self.skill_widgets = []
        self.result_widgets = []
        self.active_category = "All"

        # Generation counters
        self._skill_render_gen = 0
        self._card_render_gen = 0
        self._skill_render_queue = []
        self._card_render_queue = []

        self.create_widgets()
        self.load_skills()

    def create_widgets(self):
        """Create the skill search interface"""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)

        # === Left Panel: Skill List ===
        left_frame = ctk.CTkFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(SPACING_SM, SPACING_XS), pady=SPACING_SM)

        # Header
        header = ctk.CTkFrame(left_frame, fg_color="transparent")
        header.pack(fill=tk.X, pady=(SPACING_LG, SPACING_SM), padx=SPACING_LG)
        ctk.CTkLabel(
            header, text="🔍  Skills",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        self.skill_count_label = ctk.CTkLabel(
            header, text="",
            font=FONT_TINY, text_color=TEXT_DISABLED
        )
        self.skill_count_label.pack(side=tk.RIGHT)

        # Search entry
        self.search_var = tk.StringVar()
        search_entry = create_styled_entry(
            left_frame, textvariable=self.search_var,
            placeholder_text="Filter skills..."
        )
        search_entry.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))
        self.search_var.trace_add('write', self.filter_skills)

        # === Category filter bar ===
        cat_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        cat_frame.pack(fill=tk.X, padx=SPACING_SM, pady=(0, SPACING_XS))

        self._cat_buttons = {}
        for cat in SKILL_CATEGORIES:
            btn = ctk.CTkButton(
                cat_frame, text=cat,
                font=FONT_TINY, height=22, width=0,
                fg_color=ACCENT_PRIMARY if cat == "All" else BG_MEDIUM,
                hover_color=BG_HIGHLIGHT,
                text_color=TEXT_PRIMARY if cat == "All" else TEXT_MUTED,
                corner_radius=RADIUS_FULL,
                command=lambda c=cat: self._set_category(c)
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            self._cat_buttons[cat] = btn

        # Skill list
        self.skill_list_scroll = ctk.CTkScrollableFrame(
            left_frame, fg_color="transparent", corner_radius=RADIUS_SM
        )
        self.skill_list_scroll.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=(0, SPACING_SM))
        self.skill_list_scroll.columnconfigure(0, weight=1)

        # === Right Panel: Results ===
        right_frame = ctk.CTkFrame(
            self, fg_color=BG_DARK, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(SPACING_XS, SPACING_SM), pady=SPACING_SM)

        # Results header
        search_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        search_frame.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_LG)

        self.result_header = ctk.CTkLabel(
            search_frame, text="Select a skill to see cards",
            font=FONT_SUBHEADER, text_color=ACCENT_PRIMARY
        )
        self.result_header.pack(side=tk.LEFT)

        # Owned filter toggle
        self.owned_only_var = tk.BooleanVar(value=False)
        self.owned_switch = ctk.CTkSwitch(
            search_frame, text="Owned Only",
            variable=self.owned_only_var,
            command=self.on_filter_changed,
            font=FONT_SMALL,
            progress_color=ACCENT_SUCCESS,
            switch_width=40, switch_height=20
        )
        self.owned_switch.pack(side=tk.RIGHT)

        # Results scroll
        self.results_scroll = ctk.CTkScrollableFrame(right_frame, fg_color="transparent")
        self.results_scroll.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=(0, SPACING_SM))

        # Stats
        self.stats_label = ctk.CTkLabel(
            right_frame, text="", font=FONT_TINY, text_color=TEXT_DISABLED
        )
        self.stats_label.pack(anchor='e', pady=SPACING_SM, padx=SPACING_LG)

    def _set_category(self, category):
        """Switch active category and re-filter skill list"""
        self.active_category = category
        # Update button styles
        for cat, btn in self._cat_buttons.items():
            if cat == category:
                btn.configure(fg_color=ACCENT_PRIMARY, text_color=TEXT_PRIMARY)
            else:
                btn.configure(fg_color=BG_MEDIUM, text_color=TEXT_MUTED)
        self.filter_skills()

    def load_skills(self):
        """Load all unique skills"""
        self.all_skills = get_all_unique_skills()
        self.update_skill_list(self._apply_category_filter(self.all_skills))

    def _apply_category_filter(self, skills):
        """Filter skills list by active category using keyword matching"""
        cat = self.active_category
        if cat == "All":
            return skills

        keywords = SKILL_CATEGORIES.get(cat, [])

        if cat == "Golden":
            # Special: only golden skills
            result = []
            for item in skills:
                if isinstance(item, tuple):
                    _, is_golden = item
                    if is_golden:
                        result.append(item)
            return result

        result = []
        for item in skills:
            if isinstance(item, tuple):
                skill_name, _ = item
            else:
                skill_name = item
            name_lower = skill_name.lower()
            if any(kw in name_lower for kw in keywords):
                result.append(item)
        return result

    def _select_skill_widget(self, skill_name, widget):
        for w in self.skill_widgets:
            w.configure(fg_color="transparent", border_width=0)
        widget.configure(fg_color=BG_HIGHLIGHT, border_width=0)
        self.on_skill_selected(skill_name)

    def update_skill_list(self, items):
        """Update skill list UI"""
        self._skill_render_gen += 1
        my_gen = self._skill_render_gen

        for w in self.skill_widgets:
            w.destroy()
        self.skill_widgets.clear()

        display_items = items[:120]
        self.skill_count_label.configure(text=f"{len(items)} skills")
        self._skill_render_queue = display_items[:]
        self._process_skill_queue(my_gen)

    def _process_skill_queue(self, gen):
        if gen != self._skill_render_gen or not self._skill_render_queue:
            return

        chunk = self._skill_render_queue[:10]
        self._skill_render_queue = self._skill_render_queue[10:]

        for item in chunk:
            if isinstance(item, tuple):
                skill_name, is_golden = item
            else:
                skill_name, is_golden = item, False

            color = ACCENT_WARNING if is_golden else TEXT_PRIMARY
            prefix = "✨ " if is_golden else "•  "

            btn = ctk.CTkButton(
                self.skill_list_scroll,
                text=f"{prefix}{skill_name}",
                font=FONT_BODY_BOLD if is_golden else FONT_BODY,
                text_color=color,
                fg_color="transparent",
                hover_color=BG_LIGHT,
                anchor="w",
                corner_radius=RADIUS_SM,
                height=36
            )
            btn.pack(fill=tk.X, pady=1, padx=SPACING_XS)
            btn.configure(command=lambda n=skill_name, b=btn: self._select_skill_widget(n, b))
            self.skill_widgets.append(btn)

        if self._skill_render_queue and gen == self._skill_render_gen:
            self.after(20, lambda: self._process_skill_queue(gen))

    def filter_skills(self, *args):
        search = self.search_var.get().lower()
        category_filtered = self._apply_category_filter(self.all_skills)

        if not search:
            self.update_skill_list(category_filtered)
            return

        filtered = []
        for item in category_filtered:
            if isinstance(item, tuple):
                skill_name, is_golden = item
                if search in skill_name.lower() or (search == "golden" and is_golden):
                    filtered.append(item)
            else:
                if search in item.lower():
                    filtered.append(item)

        self.update_skill_list(filtered)

    def on_filter_changed(self):
        if self.current_skill:
            self.show_cards_for_skill(self.current_skill)

    def on_skill_selected(self, skill_name):
        self.current_skill = skill_name
        self.show_cards_for_skill(skill_name)

    def show_cards_for_skill(self, skill_name):
        self.current_skill = skill_name
        self._card_render_gen += 1
        my_gen = self._card_render_gen

        self.result_header.configure(text=f"Cards with  ✨ {skill_name}")

        for w in self.result_widgets:
            w.destroy()
        self.result_widgets.clear()

        cards = get_cards_with_skill(skill_name)
        owned_only = self.owned_only_var.get()

        filtered_cards = []
        for card in cards:
            if owned_only and not card.get('is_owned'):
                continue
            filtered_cards.append(card)

        self.stats_label.configure(text="Loading...")
        self._card_render_queue = filtered_cards[:]
        self._card_render_row = 0
        self._card_render_col = 0
        self._card_render_count = 0
        self._process_card_queue(my_gen)

    def _process_card_queue(self, gen):
        if gen != self._card_render_gen or not self._card_render_queue:
            if gen == self._card_render_gen:
                self.stats_label.configure(
                    text=f"Found {self._card_render_count} cards teaching ✨ {self.current_skill}"
                )
            return

        chunk = self._card_render_queue[:5]
        self._card_render_queue = self._card_render_queue[5:]

        for card in chunk:
            self._card_render_count += 1
            card_id = card['card_id']
            card_type = card.get('type') or card.get('card_type') or 'Unknown'
            rarity = card.get('rarity') or 'Unknown'
            is_owned = card.get('is_owned')

            bg_color = BG_ELEVATED if is_owned else BG_DARK
            border_color = ACCENT_SUCCESS if is_owned else BG_LIGHT

            card_frame = ctk.CTkFrame(
                self.results_scroll, fg_color=bg_color,
                corner_radius=RADIUS_MD, border_width=1, border_color=border_color
            )
            card_frame.pack(fill=tk.X, padx=SPACING_XS, pady=SPACING_XS)
            self.result_widgets.append(card_frame)

            # Image
            img = self.icon_cache.get(card_id)
            if not img:
                resolved_path = resolve_image_path(card['image_path'])
                if resolved_path and os.path.exists(resolved_path):
                    try:
                        pil_img = Image.open(resolved_path)
                        pil_img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(60, 60))
                        self.icon_cache[card_id] = img
                    except (OSError, SyntaxError, ValueError) as e:
                        logging.debug(f"Failed to load skill card icon: {e}")

            ctk.CTkLabel(
                card_frame, text="", image=img if img else None,
                width=50, height=50, corner_radius=RADIUS_SM
            ).pack(side=tk.LEFT, padx=SPACING_SM, pady=SPACING_SM)

            # Info
            info = ctk.CTkFrame(card_frame, fg_color="transparent")
            info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=SPACING_XS, padx=(0, SPACING_SM))

            # Top row: Name (clickable) + type badge
            hdr = ctk.CTkFrame(info, fg_color="transparent")
            hdr.pack(fill=tk.X)

            name_label = ctk.CTkLabel(
                hdr, text=card.get('name', 'Unknown'),
                font=FONT_BODY_BOLD, text_color=ACCENT_PRIMARY, anchor="w",
                cursor="hand2"
            )
            name_label.pack(side=tk.LEFT)
            if self.navigate_to_card:
                name_label.bind("<Button-1>", lambda e, cid=card_id: self.navigate_to_card(cid))

            # Type + rarity badges
            meta_text = f"{get_type_icon(card_type)} {card_type}"
            ctk.CTkLabel(
                hdr, text=meta_text,
                font=FONT_TINY, text_color=get_rarity_color(rarity)
            ).pack(side=tk.RIGHT)

            # Source badge
            source = card.get('source', '')
            golden = card.get('is_gold', False)
            if golden:
                source = f"✨ GOLDEN {source.replace('✨ GOLDEN ', '')}"

            if source:
                source_color = ACCENT_WARNING if golden else (ACCENT_SECONDARY if 'Event' in source else ACCENT_INFO)
                ctk.CTkLabel(
                    info, text=source, font=FONT_TINY,
                    text_color=source_color, anchor="w"
                ).pack(fill=tk.X)

            # Details text
            details_text = card.get('details', '')
            if details_text:
                ctk.CTkLabel(
                    info, text=details_text,
                    font=FONT_TINY, text_color=TEXT_MUTED,
                    anchor="w", justify="left", wraplength=500
                ).pack(fill=tk.X)

        if self._card_render_queue and gen == self._card_render_gen:
            self.after(10, lambda: self._process_card_queue(gen))

    def set_card(self, card_id):
        pass
