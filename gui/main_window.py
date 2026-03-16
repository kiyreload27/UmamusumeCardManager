"""
Main Window for Umamusume Support Card Manager
Collapsible left sidebar navigation with grouped sections
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_database_stats, get_owned_count
from gui.card_view import CardListFrame
from gui.effects_view import EffectsFrame
from gui.hints_skills_view import SkillSearchFrame
from gui.deck_skills_view import DeckSkillsFrame
from gui.track_view import TrackViewFrame
from gui.deck_builder import DeckBuilderFrame
from gui.race_calendar_view import RaceCalendarViewFrame
from gui.update_dialog import show_update_dialog
from gui.backup_dialog import show_backup_dialog
from gui.training_timeline import TrainingTimelineFrame
from gui.upgrade_planner import UpgradePlannerFrame
from gui.theme import (
    configure_styles, create_styled_button,
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY, FONT_SUBHEADER,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    SIDEBAR_WIDTH_EXPANDED, SIDEBAR_WIDTH_COLLAPSED,
)
from utils import resolve_image_path
from version import VERSION


# Navigation structure: (view_id, icon, label, group)
NAV_ITEMS = [
    # group headers are ('__group__', label)
    ('__group__', 'Collection'),
    ('Dashboard',  '📊', 'Dashboard',      'Collection'),
    ('Cards',      '🃏', 'Card Library',   'Collection'),
    ('Effects',    '🔎', 'Effect Search',  'Collection'),
    ('__group__', 'Planning'),
    ('Deck',       '🎴', 'Deck Builder',   'Planning'),
    ('Skills',     '🔍', 'Skill Search',   'Planning'),
    ('DeckSkills', '📜', 'Deck Skills',    'Planning'),
    ('__group__', 'Reference'),
    ('Tracks',     '🏟', 'Racetracks',     'Reference'),
    ('Calendar',   '📅', 'Race Calendar',  'Reference'),
]

# Keyboard shortcut order (skipping group headers)
VIEW_ORDER = [item[0] for item in NAV_ITEMS if item[0] != '__group__']


class MainWindow:
    """Main application window — collapsible left sidebar + content area"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title('Umamusume Support Card Manager')

        screen_w = self.root.winfo_screenwidth()
        if screen_w >= 1920:
            self.root.geometry('1600x900')
        elif screen_w >= 1280:
            self.root.geometry('1280x800')
        else:
            self.root.geometry('1100x720')
        self.root.minsize(900, 600)

        try:
            icon_path = resolve_image_path('1_Special Week.png')
            if icon_path and os.path.exists(icon_path):
                self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
        except Exception:
            pass

        configure_styles(self.root)

        # State
        self.last_selected_levels = {}
        self.selected_card_id = None
        self.views = {}
        self.current_view_id = None
        self._nav_buttons = {}   # view_id -> CTkButton
        self._nav_labels  = {}   # view_id -> (icon, label) for collapse mode
        self._sidebar_expanded = True

        # Root layout: sidebar | content
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_content_area()
        self._bind_shortcuts()

        # Launch to Dashboard
        self._navigate('Dashboard')
        self.refresh_stats()

    # ─────────────────────────────────────────────────────────────────
    # Sidebar
    # ─────────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.root,
            fg_color=BG_DARK,
            corner_radius=0,
            width=SIDEBAR_WIDTH_EXPANDED,
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky='nsew')
        self.sidebar.grid_propagate(False)
        self.sidebar.rowconfigure(2, weight=1)  # nav section expands

        # ── Top: branding + toggle ──
        top = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        top.grid(row=0, column=0, sticky='ew', padx=SPACING_SM, pady=(SPACING_MD, SPACING_XS))
        top.columnconfigure(0, weight=1)

        self._brand_frame = ctk.CTkFrame(top, fg_color='transparent')
        self._brand_frame.grid(row=0, column=0, sticky='w')

        self._brand_title = ctk.CTkLabel(
            self._brand_frame, text='🐴 Umamusume',
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        )
        self._brand_title.pack(side=tk.LEFT)

        self._version_badge = ctk.CTkLabel(
            self._brand_frame, text=f'v{VERSION}',
            font=FONT_TINY, text_color=TEXT_MUTED,
            fg_color=BG_LIGHT, corner_radius=RADIUS_SM,
            height=18, width=44, padx=4
        )
        self._version_badge.pack(side=tk.LEFT, padx=(SPACING_XS, 0))

        self._toggle_btn = ctk.CTkButton(
            top, text='◀', width=28, height=28,
            fg_color='transparent', hover_color=BG_LIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_SM,
            font=FONT_SMALL, command=self._toggle_sidebar
        )
        self._toggle_btn.grid(row=0, column=1, sticky='e')

        # ── Stats strip ──
        self._stats_label = ctk.CTkLabel(
            self.sidebar, text='',
            font=FONT_TINY, text_color=TEXT_DISABLED,
            wraplength=200, justify='left', anchor='w'
        )
        self._stats_label.grid(row=1, column=0, sticky='ew',
                               padx=SPACING_MD, pady=(0, SPACING_SM))

        # ── Divider ──
        ctk.CTkFrame(self.sidebar, fg_color=BG_LIGHT, height=1
                     ).grid(row=1, column=0, sticky='ew', padx=0,
                            pady=(SPACING_XL, 0))

        # ── Nav ──
        self._nav_scroll = ctk.CTkScrollableFrame(
            self.sidebar, fg_color='transparent', corner_radius=0
        )
        self._nav_scroll.grid(row=2, column=0, sticky='nsew', padx=0, pady=0)
        self._nav_scroll.columnconfigure(0, weight=1)

        self._build_nav_items()

        # ── Bottom: backup + updates ──
        bottom = ctk.CTkFrame(self.sidebar, fg_color=BG_DARKEST, corner_radius=0)
        bottom.grid(row=3, column=0, sticky='ew')

        self._backup_btn = ctk.CTkButton(
            bottom, text='💾  Backup / Restore',
            command=self.show_backup_dialog,
            fg_color='transparent', hover_color=BG_LIGHT,
            text_color=TEXT_MUTED, font=FONT_SMALL,
            anchor='w', height=36, corner_radius=0,
        )
        self._backup_btn.pack(fill=tk.X, padx=SPACING_XS)

        self._update_btn = ctk.CTkButton(
            bottom, text='🔄  Check for Updates',
            command=self.show_update_dialog,
            fg_color='transparent', hover_color=BG_LIGHT,
            text_color=TEXT_MUTED, font=FONT_SMALL,
            anchor='w', height=36, corner_radius=0,
        )
        self._update_btn.pack(fill=tk.X, padx=SPACING_XS)

    def _build_nav_items(self):
        """Populate the scrollable nav with group headers and buttons."""
        for w in self._nav_scroll.winfo_children():
            w.destroy()
        self._nav_buttons.clear()

        for item in NAV_ITEMS:
            if item[0] == '__group__':
                # Section header
                self._group_label = ctk.CTkLabel(
                    self._nav_scroll, text=item[1].upper(),
                    font=FONT_TINY, text_color=TEXT_DISABLED, anchor='w'
                )
                self._group_label.pack(
                    fill=tk.X, padx=SPACING_MD,
                    pady=(SPACING_MD, SPACING_XS)
                )
            else:
                view_id, icon, label, _ = item
                is_active = (view_id == self.current_view_id)
                display = f'{icon}  {label}' if self._sidebar_expanded else icon

                btn = ctk.CTkButton(
                    self._nav_scroll,
                    text=display,
                    command=lambda vid=view_id: self._navigate(vid),
                    fg_color=BG_HIGHLIGHT if is_active else 'transparent',
                    hover_color=BG_LIGHT,
                    text_color=ACCENT_PRIMARY if is_active else TEXT_MUTED,
                    font=FONT_BODY_BOLD if is_active else FONT_BODY,
                    corner_radius=RADIUS_MD,
                    anchor='w' if self._sidebar_expanded else 'center',
                    height=40,
                    border_width=0,
                )
                btn.pack(
                    fill=tk.X, padx=SPACING_XS,
                    pady=1
                )
                self._nav_buttons[view_id] = btn

    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        w = SIDEBAR_WIDTH_EXPANDED if self._sidebar_expanded else SIDEBAR_WIDTH_COLLAPSED
        self.sidebar.configure(width=w)

        if self._sidebar_expanded:
            self._toggle_btn.configure(text='◀')
            self._brand_title.pack(side=tk.LEFT)
            self._version_badge.pack(side=tk.LEFT, padx=(SPACING_XS, 0))
            self._stats_label.configure(wraplength=200)
            self._backup_btn.configure(text='💾  Backup / Restore', anchor='w')
            self._update_btn.configure(text='🔄  Check for Updates', anchor='w')
        else:
            self._toggle_btn.configure(text='▶')
            self._brand_title.pack_forget()
            self._version_badge.pack_forget()
            self._stats_label.configure(wraplength=50)
            self._backup_btn.configure(text='💾', anchor='center')
            self._update_btn.configure(text='🔄', anchor='center')

        self._build_nav_items()

    def _update_nav_active(self, active_id):
        for vid, btn in self._nav_buttons.items():
            is_active = (vid == active_id)
            icon_label = vid
            for item in NAV_ITEMS:
                if item[0] == vid and len(item) == 4:
                    icon_label = f"{item[1]}  {item[2]}" if self._sidebar_expanded else item[1]
                    break

            btn.configure(
                fg_color=BG_HIGHLIGHT if is_active else 'transparent',
                text_color=ACCENT_PRIMARY if is_active else TEXT_MUTED,
                font=FONT_BODY_BOLD if is_active else FONT_BODY,
                text=icon_label,
            )

    # ─────────────────────────────────────────────────────────────────
    # Content area
    # ─────────────────────────────────────────────────────────────────

    def _build_content_area(self):
        self.content_area = ctk.CTkFrame(
            self.root, fg_color=BG_DARKEST, corner_radius=0
        )
        self.content_area.grid(row=0, column=1, sticky='nsew')
        self.content_area.rowconfigure(0, weight=1)
        self.content_area.columnconfigure(0, weight=1)

    # ─────────────────────────────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────────────────────────────

    def _navigate(self, view_id):
        if view_id not in VIEW_ORDER:
            return

        self.current_view_id = view_id
        self._update_nav_active(view_id)
        self.root.title(f'Umamusume  ·  {self._label_for(view_id)}')

        # Hide all existing view frames
        for child in self.content_area.winfo_children():
            child.grid_remove()

        # Lazy-load or re-show view
        if view_id not in self.views:
            view = self._build_view(view_id, self.content_area)
            if view:
                view.grid(row=0, column=0, sticky='nsew')
                self.views[view_id] = view

            # Post-load hooks
            if self.selected_card_id:
                if view_id == 'Effects' and view_id in self.views:
                    self.views[view_id].set_card(self.selected_card_id)
                elif view_id == 'DeckSkills' and view_id in self.views:
                    self.views[view_id].set_card(self.selected_card_id)
        else:
            self.views[view_id].grid(row=0, column=0, sticky='nsew')

    def _build_view(self, view_id, parent):
        if view_id == 'Dashboard':
            from gui.collection_dashboard import CollectionDashboard
            return CollectionDashboard(
                parent,
                navigate_to_cards_callback=lambda: self._navigate('Cards')
            )
        elif view_id == 'Cards':
            return CardListFrame(
                parent,
                on_card_selected_callback=self.on_card_selected,
                on_stats_updated_callback=self.refresh_stats,
                navigate_to_card_callback=self.navigate_to_card
            )
        elif view_id == 'Effects':
            return EffectsFrame(parent, navigate_to_card_callback=self.navigate_to_card)
        elif view_id == 'Deck':
            return DeckBuilderFrame(parent)
        elif view_id == 'Skills':
            return SkillSearchFrame(parent, navigate_to_card_callback=self.navigate_to_card)
        elif view_id == 'DeckSkills':
            return DeckSkillsFrame(
                parent,
                navigate_to_card_callback=self.navigate_to_card,
                navigate_to_skill_callback=self.navigate_to_skill
            )
        elif view_id == 'Timeline':
            return TrainingTimelineFrame(parent, navigate_to_card_callback=self.navigate_to_card)
        elif view_id == 'Upgrade':
            return UpgradePlannerFrame(parent)
        elif view_id == 'Tracks':
            return TrackViewFrame(parent)
        elif view_id == 'Calendar':
            return RaceCalendarViewFrame(parent)
        return None

    def _label_for(self, view_id):
        for item in NAV_ITEMS:
            if item[0] == view_id:
                return item[2]
        return view_id

    # ─────────────────────────────────────────────────────────────────
    # Cross-view navigation
    # ─────────────────────────────────────────────────────────────────

    def navigate_to_card(self, card_id):
        self._navigate('Cards')
        if 'Cards' in self.views:
            self.views['Cards'].navigate_to_card(card_id)

    def navigate_to_skill(self, skill_name):
        self._navigate('Skills')
        if 'Skills' in self.views:
            view = self.views['Skills']
            view.search_var.set(skill_name)
            view.filter_skills()
            view.on_skill_selected(skill_name)

    def on_card_selected(self, card_id, card_name, level=None):
        if level is not None:
            self.last_selected_levels[card_id] = level
        self.selected_card_id = card_id
        if 'Effects' in self.views:
            self.views['Effects'].set_card(card_id)
        if 'DeckSkills' in self.views:
            self.views['DeckSkills'].set_card(card_id)

    # ─────────────────────────────────────────────────────────────────
    # Stats / dialogs
    # ─────────────────────────────────────────────────────────────────

    def refresh_stats(self):
        try:
            stats = get_database_stats()
            owned = get_owned_count()
            total = stats.get('total_cards', 0)
            by_rarity = stats.get('by_rarity', {})
            pct = f'{owned / total * 100:.0f}%' if total else '0%'
            text = (
                f'{owned}/{total} owned  ({pct})\n'
                f'SSR {by_rarity.get("SSR",0)}  '
                f'SR {by_rarity.get("SR",0)}  '
                f'R {by_rarity.get("R",0)}'
            )
        except Exception:
            text = ''
        if hasattr(self, '_stats_label'):
            self._stats_label.configure(text=text)

    def show_backup_dialog(self):
        def on_restore():
            self.refresh_stats()
            if 'Cards' in self.views:
                self.views['Cards'].filter_cards()
            if 'Dashboard' in self.views:
                self.views['Dashboard'].refresh()
        show_backup_dialog(self.root, on_restore_callback=on_restore)

    def show_update_dialog(self):
        show_update_dialog(self.root)

    # ─────────────────────────────────────────────────────────────────
    # Keyboard shortcuts
    # ─────────────────────────────────────────────────────────────────

    def _bind_shortcuts(self):
        for idx, view_id in enumerate(VIEW_ORDER):
            n = idx + 1
            if n <= 9:
                self.root.bind(
                    f'<Control-Key-{n}>',
                    lambda e, vid=view_id: self._navigate(vid)
                )

    def run(self):
        self.root.mainloop()


def main():
    app = MainWindow()
    app.run()


if __name__ == '__main__':
    main()
