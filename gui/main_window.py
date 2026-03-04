"""
Main Window for Umamusume Support Card Manager
Tab-based navigation — replaces sidebar for maximum content space
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
    FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_MD, RADIUS_LG,
)
from utils import resolve_image_path
from version import VERSION


# Tab definitions: (internal_id, tab_label)
TABS = [
    ("Dashboard",  "📊 Dashboard"),
    ("Cards",      "📋 Cards"),
    ("Effects",    "🔎 Effects"),
    ("Deck",       "🎴 Deck Builder"),
    ("Skills",     "🔍 Skills"),
    ("DeckSkills", "📜 Deck Skills"),
    ("Tracks",     "🏟️ Tracks"),
    ("Calendar",   "📅 Race Calendar"),
]


class MainWindow:
    """Main application window with top-tab navigation"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Umamusume Support Card Manager")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        if screen_width >= 1920:
            self.root.geometry("1600x900")
        elif screen_width >= 1280:
            self.root.geometry("1280x800")
        else:
            self.root.geometry("1024x700")

        self.root.minsize(900, 600)

        try:
            icon_path = resolve_image_path("1_Special Week.png")
            if icon_path and os.path.exists(icon_path):
                icon_img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon_img)
        except Exception:
            pass

        configure_styles(self.root)

        # State
        self.last_selected_levels = {}
        self.selected_card_id = None
        self.views = {}              # view_id -> widget (lazy loaded)
        self._tab_id_map = {}       # tab_label -> view_id

        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self._create_header()
        self._create_tabview()
        self._init_views()

        # Default tab
        self.tabview.set(TABS[0][1])
        self._on_tab_changed()

        # Keyboard shortcuts Ctrl+1..9
        for idx, (view_id, tab_label) in enumerate(TABS):
            n = idx + 1
            if n <= 9:
                self.root.bind(
                    f'<Control-Key-{n}>',
                    lambda e, lbl=tab_label: self._switch_tab(lbl)
                )

    # ─────────────────────────────────────────────
    # Layout
    # ─────────────────────────────────────────────

    def _create_header(self):
        """Thin header bar: branding | stats | action buttons"""
        self.header = ctk.CTkFrame(
            self.root, fg_color=BG_DARK, height=44, corner_radius=0
        )
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)
        self.header.columnconfigure(1, weight=1)

        # Branding
        brand = ctk.CTkFrame(self.header, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w", padx=SPACING_MD, pady=SPACING_XS)

        ctk.CTkLabel(
            brand, text="🐴  Umamusume",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT, padx=(0, SPACING_XS))

        ctk.CTkLabel(
            brand, text=f"v{VERSION}",
            font=FONT_TINY, text_color=TEXT_MUTED,
            fg_color=BG_LIGHT, corner_radius=6, height=18, width=44
        ).pack(side=tk.LEFT)

        # Stats label (center)
        self.stats_label = ctk.CTkLabel(
            self.header, text="Loading...",
            font=FONT_TINY, text_color=TEXT_MUTED, anchor="center"
        )
        self.stats_label.grid(row=0, column=1, sticky="ew", padx=SPACING_MD)

        # Action buttons (right)
        actions = ctk.CTkFrame(self.header, fg_color="transparent")
        actions.grid(row=0, column=2, sticky="e", padx=SPACING_MD, pady=SPACING_XS)

        ctk.CTkButton(
            actions, text="💾 Backup",
            command=self.show_backup_dialog,
            font=FONT_TINY, height=28, width=88,
            fg_color="transparent", hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_MD,
        ).pack(side=tk.LEFT, padx=(0, SPACING_XS))

        ctk.CTkButton(
            actions, text="🔄 Updates",
            command=self.show_update_dialog,
            font=FONT_TINY, height=28, width=96,
            fg_color="transparent", hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_MD,
        ).pack(side=tk.LEFT)

        self.refresh_stats()

    def _create_tabview(self):
        """Create a full-width CTkTabview row below the header"""
        self.tabview = ctk.CTkTabview(
            self.root,
            fg_color=BG_DARKEST,
            segmented_button_fg_color=BG_DARK,
            segmented_button_selected_color=ACCENT_PRIMARY,
            segmented_button_selected_hover_color=ACCENT_SECONDARY,
            segmented_button_unselected_color=BG_DARK,
            segmented_button_unselected_hover_color=BG_HIGHLIGHT,
            text_color=TEXT_MUTED,
            text_color_disabled=TEXT_DISABLED,
            corner_radius=0,
            anchor="n",
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        for view_id, tab_label in TABS:
            self.tabview.add(tab_label)
            self._tab_id_map[tab_label] = view_id
            # Each tab frame needs to expand
            tab_frame = self.tabview.tab(tab_label)
            tab_frame.grid_rowconfigure(0, weight=1)
            tab_frame.grid_columnconfigure(0, weight=1)

        self.tabview.configure(command=self._on_tab_changed)

    def _init_views(self):
        """Define lazy-load constructors for each view"""
        def _make_view(view_id, parent):
            if view_id == "Dashboard":
                from gui.collection_dashboard import CollectionDashboard
                return CollectionDashboard(
                    parent,
                    navigate_to_cards_callback=lambda: self._switch_tab(self._label_for("Cards"))
                )
            elif view_id == "Cards":
                return CardListFrame(
                    parent,
                    on_card_selected_callback=self.on_card_selected,
                    on_stats_updated_callback=self.refresh_stats,
                    navigate_to_card_callback=self.navigate_to_card
                )
            elif view_id == "Effects":
                return EffectsFrame(
                    parent,
                    navigate_to_card_callback=self.navigate_to_card
                )
            elif view_id == "Deck":
                return DeckBuilderFrame(parent)
            elif view_id == "Skills":
                return SkillSearchFrame(
                    parent,
                    navigate_to_card_callback=self.navigate_to_card
                )
            elif view_id == "DeckSkills":
                return DeckSkillsFrame(
                    parent,
                    navigate_to_card_callback=self.navigate_to_card,
                    navigate_to_skill_callback=self.navigate_to_skill
                )
            elif view_id == "Timeline":
                return TrainingTimelineFrame(
                    parent,
                    navigate_to_card_callback=self.navigate_to_card
                )
            elif view_id == "Upgrade":
                return UpgradePlannerFrame(parent)
            elif view_id == "Tracks":
                return TrackViewFrame(parent)
            elif view_id == "Calendar":
                return RaceCalendarViewFrame(parent)

        self._view_factories = {view_id: _make_view for view_id, _ in TABS}

    # ─────────────────────────────────────────────
    # Tab switching helpers
    # ─────────────────────────────────────────────

    def _label_for(self, view_id):
        for vid, lbl in TABS:
            if vid == view_id:
                return lbl
        return None

    def _id_for_label(self, label):
        return self._tab_id_map.get(label)

    def _switch_tab(self, tab_label):
        """Programmatically switch to a tab by label"""
        try:
            self.tabview.set(tab_label)
            self._on_tab_changed()
        except Exception:
            pass

    def _on_tab_changed(self, *_):
        """Called when the active tab changes — lazy-loads the view if needed"""
        current_label = self.tabview.get()
        view_id = self._id_for_label(current_label)
        if not view_id:
            return

        if view_id not in self.views:
            parent = self.tabview.tab(current_label)
            view = self._view_factories[view_id](view_id, parent)
            if view:
                view.grid(row=0, column=0, sticky="nsew")
                self.views[view_id] = view

            # Post-load hooks
            if self.selected_card_id:
                if view_id == "Effects" and view_id in self.views:
                    self.views[view_id].set_card(self.selected_card_id)
                elif view_id == "DeckSkills" and view_id in self.views:
                    self.views[view_id].set_card(self.selected_card_id)

        # Update window title
        self.root.title(f"Umamusume • {current_label.split(' ', 1)[-1]}")

    # ─────────────────────────────────────────────
    # Cross-view navigation
    # ─────────────────────────────────────────────

    def navigate_to_card(self, card_id):
        self._switch_tab(self._label_for("Cards"))
        if "Cards" in self.views:
            self.views["Cards"].navigate_to_card(card_id)

    def navigate_to_skill(self, skill_name):
        self._switch_tab(self._label_for("Skills"))
        if "Skills" in self.views:
            view = self.views["Skills"]
            view.search_var.set(skill_name)
            view.filter_skills()
            view.on_skill_selected(skill_name)

    def on_card_selected(self, card_id, card_name, level=None):
        if level is not None:
            self.last_selected_levels[card_id] = level
        self.selected_card_id = card_id

        if "Effects" in self.views:
            self.views["Effects"].set_card(card_id)
        if "DeckSkills" in self.views:
            self.views["DeckSkills"].set_card(card_id)

    def refresh_stats(self):
        stats = get_database_stats()
        owned = get_owned_count()
        total = stats.get('total_cards', 0)
        by_rarity = stats.get('by_rarity', {})
        text = (
            f"📋 {total} Cards  ✅ {owned} Owned  │  "
            f"SSR {by_rarity.get('SSR', 0)}  SR {by_rarity.get('SR', 0)}  R {by_rarity.get('R', 0)}"
        )
        if hasattr(self, 'stats_label'):
            self.stats_label.configure(text=text)

    def show_backup_dialog(self):
        def on_restore():
            self.refresh_stats()
            if "Cards" in self.views:
                self.views["Cards"].filter_cards()
            if "Dashboard" in self.views:
                self.views["Dashboard"].refresh()
        show_backup_dialog(self.root, on_restore_callback=on_restore)

    def show_update_dialog(self):
        show_update_dialog(self.root)

    def run(self):
        self.root.mainloop()


def main():
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
