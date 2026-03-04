"""
Main Window for Umamusume Support Card Manager
Premium interface with grouped sidebar navigation and refined content area
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
from gui.theme import (
    configure_styles, create_styled_button, create_sidebar_button,
    create_badge, create_divider,
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


# Navigation structure: groups with items
NAV_GROUPS = [
    {
        "label": "COLLECTION",
        "items": [
            ("Cards", "📋", "Card Library"),
            ("Effects", "📊", "Effect Search"),
        ]
    },
    {
        "label": "PLANNING",
        "items": [
            ("Deck", "🎴", "Deck Builder"),
            ("Skills", "🔍", "Skill Search"),
            ("DeckSkills", "📜", "Deck Skills"),
        ]
    },
    {
        "label": "REFERENCE",
        "items": [
            ("Tracks", "🏟️", "Racetracks"),
            ("Calendar", "📅", "Race Calendar"),
        ]
    },
]


class MainWindow:
    """Main application window with premium sidebar navigation"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Umamusume Support Card Manager")

        # Screen resolution check
        screen_width = self.root.winfo_screenwidth()
        if screen_width >= 1920:
            self.root.geometry("1600x900")
        else:
            self.root.geometry("1400x850")

        self.root.minsize(1350, 800)

        try:
            icon_path = resolve_image_path("1_Special Week.png")
            if icon_path and os.path.exists(icon_path):
                icon_img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon_img)
        except Exception:
            pass

        configure_styles(self.root)

        # Main container
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # State
        self.last_selected_levels = {}
        self.current_view_name = None
        self.views = {}
        self.sidebar_buttons = {}
        self.nav_indicators = {}

        self.create_sidebar()
        self.create_main_area()

        # Load views
        self.init_views()

        # Start on default view
        self.show_view("Cards")
        
        # Keyboard shortcuts for view switching
        for idx, group in enumerate(NAV_GROUPS):
            for item_idx, (view_id, icon, label) in enumerate(group["items"]):
                pass  # We'll bind below with a counter
        
        shortcut_idx = 1
        for group in NAV_GROUPS:
            for view_id, icon, label in group["items"]:
                if shortcut_idx <= 9:
                    self.root.bind(
                        f'<Control-Key-{shortcut_idx}>',
                        lambda e, vid=view_id: self.show_view(vid)
                    )
                    shortcut_idx += 1

    def create_sidebar(self):
        """Build the left navigation sidebar with grouped items"""
        self.sidebar_frame = ctk.CTkFrame(
            self.root, width=250, corner_radius=0, fg_color=BG_DARK
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # ─── App Branding ───
        branding_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        branding_frame.pack(pady=(SPACING_LG, SPACING_SM), padx=SPACING_LG, fill="x")

        # App name with accent color
        title_frame = ctk.CTkFrame(branding_frame, fg_color="transparent")
        title_frame.pack(fill="x")
        
        ctk.CTkLabel(
            title_frame, text="Umamusume",
            font=FONT_HEADER, text_color=TEXT_PRIMARY, anchor="w"
        ).pack(side=tk.LEFT)
        
        # Version badge
        ver_badge = ctk.CTkLabel(
            title_frame, text=f"v{VERSION}",
            font=FONT_TINY, text_color=TEXT_MUTED,
            fg_color=BG_LIGHT, corner_radius=6,
            height=20, width=50
        )
        ver_badge.pack(side=tk.RIGHT)

        ctk.CTkLabel(
            branding_frame, text="Support Card Manager",
            font=FONT_SMALL, text_color=ACCENT_PRIMARY, anchor="w"
        ).pack(fill="x", pady=(2, 0))

        # Thin separator
        ctk.CTkFrame(
            self.sidebar_frame, fg_color=BG_LIGHT, height=1
        ).pack(fill="x", padx=SPACING_LG, pady=(SPACING_MD, SPACING_SM))

        # ─── Navigation Groups ───
        self.nav_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.nav_frame.pack(fill="x", padx=12, pady=SPACING_SM)

        for group_idx, group in enumerate(NAV_GROUPS):
            # Group label
            ctk.CTkLabel(
                self.nav_frame, text=group["label"],
                font=FONT_TINY, text_color=TEXT_DISABLED, anchor="w"
            ).pack(fill="x", padx=SPACING_SM, pady=(SPACING_MD if group_idx > 0 else SPACING_SM, SPACING_XS))

            for view_id, icon, label in group["items"]:
                # Button container with indicator strip
                row_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent", height=44)
                row_frame.pack(fill="x", pady=1)
                row_frame.pack_propagate(False)

                # Active indicator strip (left edge)
                indicator = ctk.CTkFrame(
                    row_frame, fg_color="transparent",
                    width=3, corner_radius=2
                )
                indicator.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0))
                self.nav_indicators[view_id] = indicator

                btn = create_sidebar_button(
                    row_frame,
                    text=f"  {icon}  {label}",
                    command=lambda vid=view_id: self.show_view(vid)
                )
                btn.pack(fill="both", expand=True, padx=(2, 0))
                self.sidebar_buttons[view_id] = btn

        # ─── Spacer ───
        ctk.CTkFrame(self.sidebar_frame, fg_color="transparent").pack(fill="both", expand=True)

        # ─── Bottom Section: Stats + Update ───
        bottom_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=SPACING_LG, pady=SPACING_LG)

        # Quick stats as compact badges
        stats_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, SPACING_MD))

        self.stats_label = ctk.CTkLabel(
            stats_row, text="Loading...",
            font=FONT_TINY, text_color=TEXT_MUTED, justify="left", anchor="w"
        )
        self.stats_label.pack(fill="x")

        # Update button
        create_styled_button(
            bottom_frame, text="🔄  Check Updates",
            command=self.show_update_dialog, style_type='ghost',
            height=36
        ).pack(fill="x")

        self.refresh_stats()

    def create_main_area(self):
        """Create the right content area shell"""
        self.content_shell = ctk.CTkFrame(
            self.root, fg_color=BG_DARKEST, corner_radius=0
        )
        self.content_shell.grid(row=0, column=1, sticky="nsew")
        self.content_shell.grid_rowconfigure(0, weight=1)
        self.content_shell.grid_columnconfigure(0, weight=1)

        # Content container with padding
        self.view_container = ctk.CTkFrame(self.content_shell, fg_color="transparent")
        self.view_container.grid(
            row=0, column=0, sticky="nsew",
            padx=SPACING_LG, pady=SPACING_LG
        )
        self.view_container.grid_rowconfigure(0, weight=1)
        self.view_container.grid_columnconfigure(0, weight=1)

    def init_views(self):
        """Setup view constructors to lazy-load on demand to prevent handle exhaustion"""
        self.view_classes = {
            "Cards": lambda: CardListFrame(
                self.view_container,
                on_card_selected_callback=self.on_card_selected,
                on_stats_updated_callback=self.refresh_stats
            ),
            "Effects": lambda: EffectsFrame(self.view_container),
            "Deck": lambda: DeckBuilderFrame(self.view_container),
            "Skills": lambda: SkillSearchFrame(self.view_container),
            "DeckSkills": lambda: DeckSkillsFrame(self.view_container),
            "Tracks": lambda: TrackViewFrame(self.view_container),
            "Calendar": lambda: RaceCalendarViewFrame(self.view_container)
        }

    def show_view(self, view_id):
        """Switch to a specific view by name with visual feedback"""
        if self.current_view_name == view_id:
            return

        # Deactivate old view
        if self.current_view_name and self.current_view_name in self.views:
            self.views[self.current_view_name].grid_remove()
            if self.current_view_name in self.sidebar_buttons:
                self.sidebar_buttons[self.current_view_name].configure(
                    fg_color="transparent", text_color=TEXT_MUTED
                )
            if self.current_view_name in self.nav_indicators:
                self.nav_indicators[self.current_view_name].configure(
                    fg_color="transparent"
                )

        # Lazy load new view if needed
        if view_id not in self.views and view_id in self.view_classes:
            self.views[view_id] = self.view_classes[view_id]()
            self.views[view_id].grid(row=0, column=0, sticky="nsew")

            # Post-load hooks
            if getattr(self, 'selected_card_id', None):
                if view_id == "Effects":
                    self.views[view_id].set_card(self.selected_card_id)
                elif view_id == "DeckSkills":
                    self.views[view_id].set_card(self.selected_card_id)

        # Activate new view
        self.current_view_name = view_id
        if view_id in self.views:
            self.views[view_id].grid()
            self.views[view_id].tkraise()

            # Update sidebar styling
            if view_id in self.sidebar_buttons:
                self.sidebar_buttons[view_id].configure(
                    fg_color=BG_HIGHLIGHT, text_color=ACCENT_PRIMARY
                )
            if view_id in self.nav_indicators:
                self.nav_indicators[view_id].configure(
                    fg_color=ACCENT_PRIMARY
                )

        # Update window title
        view_label = ""
        for group in NAV_GROUPS:
            for vid, icon, label in group["items"]:
                if vid == view_id:
                    view_label = label
                    break
        self.root.title(f"Umamusume • {view_label}" if view_label else "Umamusume Support Card Manager")

    def on_card_selected(self, card_id, card_name, level=None):
        if level is not None:
            self.last_selected_levels[card_id] = level
        self.selected_card_id = card_id

        if hasattr(self, 'views'):
            if "Effects" in self.views:
                self.views["Effects"].set_card(card_id)
            if "DeckSkills" in self.views:
                self.views["DeckSkills"].set_card(card_id)

    def refresh_stats(self):
        stats = get_database_stats()
        owned = get_owned_count()
        total = stats.get('total_cards', 0)
        by_rarity = stats.get('by_rarity', {})

        stat_lines = [
            f"📋 {total} Cards  ·  ✅ {owned} Owned",
            f"SSR {by_rarity.get('SSR', 0)}  ·  SR {by_rarity.get('SR', 0)}  ·  R {by_rarity.get('R', 0)}"
        ]
        if hasattr(self, 'stats_label'):
            self.stats_label.configure(text="\n".join(stat_lines))

    def show_update_dialog(self):
        show_update_dialog(self.root)

    def run(self):
        self.root.mainloop()


def main():
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
