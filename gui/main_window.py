"""
Main Window for Umamusume Support Card Manager
Premium interface with collapsible sidebar navigation and responsive content area
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
    configure_styles, create_styled_button, create_sidebar_button,
    create_badge, create_divider,
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_MD, RADIUS_LG,
    SIDEBAR_WIDTH_EXPANDED, SIDEBAR_WIDTH_COLLAPSED,
)
from utils import resolve_image_path
from version import VERSION


# Navigation structure: groups with items
NAV_GROUPS = [
    {
        "label": "COLLECTION",
        "items": [
            ("Dashboard", "📊", "Dashboard"),
            ("Cards", "📋", "Card Library"),
            ("Effects", "🔎", "Effect Search"),
        ]
    },
    {
        "label": "PLANNING",
        "items": [
            ("Deck", "🎴", "Deck Builder"),
            ("Skills", "🔍", "Skill Search"),
            ("DeckSkills", "📜", "Deck Skills"),
            ("Timeline", "📅", "Training Timeline"),
            ("Upgrade", "📈", "Upgrade Planner"),
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
    """Main application window with collapsible sidebar navigation"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Umamusume Support Card Manager")

        # Responsive initial size
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

        # Main container
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # State
        self.last_selected_levels = {}
        self.current_view_name = None
        self.views = {}
        self.sidebar_buttons = {}
        self.nav_indicators = {}
        self.sidebar_expanded = True
        self.nav_labels = {}       # view_id -> label widget (hidden when collapsed)
        self.group_labels = []     # group label widgets (hidden when collapsed)

        self.create_sidebar()
        self.create_main_area()

        # Load views
        self.init_views()

        # Start on default view (Dashboard)
        self.show_view("Dashboard")

        # Keyboard shortcuts for view switching
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
        """Build the left navigation sidebar with collapse toggle"""
        self.sidebar_frame = ctk.CTkFrame(
            self.root, width=SIDEBAR_WIDTH_EXPANDED, corner_radius=0, fg_color=BG_DARK
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # ─── Top: Toggle + Branding ───
        top_row = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=SPACING_SM, pady=(SPACING_SM, 0))

        # Collapse toggle button
        self.toggle_btn = ctk.CTkButton(
            top_row, text="☰", width=36, height=36,
            font=FONT_HEADER, fg_color="transparent",
            hover_color=BG_HIGHLIGHT, text_color=TEXT_MUTED,
            corner_radius=RADIUS_MD,
            command=self.toggle_sidebar
        )
        self.toggle_btn.pack(side=tk.LEFT)

        # Branding (hidden when collapsed)
        self.branding_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        self.branding_frame.pack(side=tk.LEFT, fill="x", expand=True, padx=(SPACING_XS, 0))

        ctk.CTkLabel(
            self.branding_frame, text="Umamusume",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, anchor="w"
        ).pack(side=tk.LEFT)

        ctk.CTkLabel(
            self.branding_frame, text=f"v{VERSION}",
            font=FONT_TINY, text_color=TEXT_MUTED,
            fg_color=BG_LIGHT, corner_radius=6,
            height=18, width=40
        ).pack(side=tk.RIGHT)

        # Thin separator
        ctk.CTkFrame(
            self.sidebar_frame, fg_color=BG_LIGHT, height=1
        ).pack(fill="x", padx=SPACING_SM, pady=(SPACING_SM, SPACING_XS))

        # ─── Navigation Groups ───
        self.nav_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.nav_frame.pack(fill="x", padx=SPACING_XS, pady=SPACING_XS)

        for group_idx, group in enumerate(NAV_GROUPS):
            # Group label (hidden when collapsed)
            grp_label = ctk.CTkLabel(
                self.nav_frame, text=group["label"],
                font=FONT_TINY, text_color=TEXT_DISABLED, anchor="w"
            )
            grp_label.pack(fill="x", padx=SPACING_SM,
                           pady=(SPACING_MD if group_idx > 0 else SPACING_XS, SPACING_XS))
            self.group_labels.append(grp_label)

            for view_id, icon, label in group["items"]:
                # Button container with indicator strip
                row_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent", height=40)
                row_frame.pack(fill="x", pady=1)
                row_frame.pack_propagate(False)

                # Active indicator strip (left edge)
                indicator = ctk.CTkFrame(
                    row_frame, fg_color="transparent",
                    width=3, corner_radius=2
                )
                indicator.pack(side=tk.LEFT, fill=tk.Y)
                self.nav_indicators[view_id] = indicator

                # In expanded mode: icon + label. In collapsed: just icon
                btn = ctk.CTkButton(
                    row_frame,
                    text=f"  {icon}  {label}",
                    command=lambda vid=view_id: self.show_view(vid),
                    fg_color="transparent",
                    hover_color=BG_LIGHT,
                    text_color=TEXT_MUTED,
                    font=FONT_BODY_BOLD,
                    corner_radius=RADIUS_MD,
                    anchor="w",
                    height=40,
                    border_width=0
                )
                btn.pack(fill="both", expand=True, padx=(2, 0))
                self.sidebar_buttons[view_id] = btn
                # Store full and short text for toggle
                btn._full_text = f"  {icon}  {label}"
                btn._icon_text = f" {icon}"

        # ─── Spacer ───
        ctk.CTkFrame(self.sidebar_frame, fg_color="transparent").pack(fill="both", expand=True)

        # ─── Bottom Section: Stats + Buttons ───
        self.bottom_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.bottom_frame.pack(fill="x", padx=SPACING_SM, pady=SPACING_SM)

        # Quick stats
        self.stats_label = ctk.CTkLabel(
            self.bottom_frame, text="Loading...",
            font=FONT_TINY, text_color=TEXT_MUTED, justify="left", anchor="w"
        )
        self.stats_label.pack(fill="x", pady=(0, SPACING_SM))

        # Backup button
        self.backup_btn = ctk.CTkButton(
            self.bottom_frame, text="💾  Backup",
            command=self.show_backup_dialog,
            font=FONT_TINY, height=30,
            fg_color="transparent", hover_color=BG_LIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_MD,
        )
        self.backup_btn.pack(fill="x", pady=(0, 2))

        # Update button
        self.update_btn = ctk.CTkButton(
            self.bottom_frame, text="🔄  Updates",
            command=self.show_update_dialog,
            font=FONT_TINY, height=30,
            fg_color="transparent", hover_color=BG_LIGHT,
            text_color=TEXT_MUTED, corner_radius=RADIUS_MD,
        )
        self.update_btn.pack(fill="x")

        self.refresh_stats()

    def toggle_sidebar(self):
        """Toggle sidebar between expanded and collapsed modes"""
        self.sidebar_expanded = not self.sidebar_expanded

        if self.sidebar_expanded:
            width = SIDEBAR_WIDTH_EXPANDED
            self.branding_frame.pack(side=tk.LEFT, fill="x", expand=True, padx=(SPACING_XS, 0))
            for lbl in self.group_labels:
                lbl.pack(fill="x", padx=SPACING_SM)
            for vid, btn in self.sidebar_buttons.items():
                btn.configure(text=btn._full_text, anchor="w")
            self.stats_label.pack(fill="x", pady=(0, SPACING_SM))
            self.backup_btn.configure(text="💾  Backup")
            self.update_btn.configure(text="🔄  Updates")
        else:
            width = SIDEBAR_WIDTH_COLLAPSED
            self.branding_frame.pack_forget()
            for lbl in self.group_labels:
                lbl.pack_forget()
            for vid, btn in self.sidebar_buttons.items():
                btn.configure(text=btn._icon_text, anchor="center")
            self.stats_label.pack_forget()
            self.backup_btn.configure(text="💾")
            self.update_btn.configure(text="🔄")

        self.sidebar_frame.configure(width=width)

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
            padx=SPACING_MD, pady=SPACING_MD
        )
        self.view_container.grid_rowconfigure(0, weight=1)
        self.view_container.grid_columnconfigure(0, weight=1)

    def init_views(self):
        """Setup view constructors to lazy-load on demand to prevent handle exhaustion"""
        self.view_classes = {
            "Dashboard": lambda: self._create_dashboard(),
            "Cards": lambda: CardListFrame(
                self.view_container,
                on_card_selected_callback=self.on_card_selected,
                on_stats_updated_callback=self.refresh_stats,
                navigate_to_card_callback=self.navigate_to_card
            ),
            "Effects": lambda: EffectsFrame(
                self.view_container,
                navigate_to_card_callback=self.navigate_to_card
            ),
            "Deck": lambda: DeckBuilderFrame(self.view_container),
            "Skills": lambda: SkillSearchFrame(
                self.view_container,
                navigate_to_card_callback=self.navigate_to_card
            ),
            "DeckSkills": lambda: DeckSkillsFrame(
                self.view_container,
                navigate_to_card_callback=self.navigate_to_card,
                navigate_to_skill_callback=self.navigate_to_skill
            ),
            "Timeline": lambda: TrainingTimelineFrame(
                self.view_container,
                navigate_to_card_callback=self.navigate_to_card
            ),
            "Upgrade": lambda: UpgradePlannerFrame(self.view_container),
            "Tracks": lambda: TrackViewFrame(self.view_container),
            "Calendar": lambda: RaceCalendarViewFrame(self.view_container)
        }

    def _create_dashboard(self):
        """Create the Collection Progress Dashboard inline"""
        from gui.collection_dashboard import CollectionDashboard
        return CollectionDashboard(
            self.view_container,
            navigate_to_cards_callback=lambda: self.show_view("Cards")
        )

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

    def navigate_to_card(self, card_id):
        """Navigate to the Cards view and select a specific card (cross-view linking)"""
        self.show_view("Cards")
        if "Cards" in self.views:
            self.views["Cards"].navigate_to_card(card_id)

    def navigate_to_skill(self, skill_name):
        """Navigate to the Skills view and search for a specific skill"""
        self.show_view("Skills")
        if "Skills" in self.views:
            view = self.views["Skills"]
            view.search_var.set(skill_name)
            view.filter_skills()
            view.on_skill_selected(skill_name)

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
            f"📋 {total} Cards · ✅ {owned} Owned",
            f"SSR {by_rarity.get('SSR', 0)} · SR {by_rarity.get('SR', 0)} · R {by_rarity.get('R', 0)}"
        ]
        if hasattr(self, 'stats_label'):
            self.stats_label.configure(text="\n".join(stat_lines))

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
