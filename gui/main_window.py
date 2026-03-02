"""
Main Window for Umamusume Support Card Manager
Modern interface with sidebar navigation
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
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_SMALL
)
from utils import resolve_image_path
from version import VERSION


class MainWindow:
    """Main application window with sidebar navigation"""
    
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
        except Exception as e:
            pass
        
        configure_styles(self.root)
        
        # Main container: row=0, col=0 for sidebar, col=1 for content
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # State
        self.last_selected_levels = {}
        self.current_view_name = None
        self.views = {}
        self.sidebar_buttons = {}
        
        self.create_sidebar()
        self.create_main_area()
        
        # Load views
        self.init_views()
        
        # Start on default view
        self.show_view("Cards")
        
    def create_sidebar(self):
        """Build the left navigation sidebar"""
        self.sidebar_frame = ctk.CTkFrame(self.root, width=240, corner_radius=0, fg_color=BG_DARK)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        
        # App branding
        branding_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        branding_frame.pack(pady=(25, 20), padx=20, fill="x")
        
        ctk.CTkLabel(branding_frame, text="Umamusume", font=FONT_HEADER, text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(branding_frame, text="Support Card Manager", font=FONT_BODY, text_color=ACCENT_PRIMARY, anchor="w").pack(fill="x")
        ctk.CTkLabel(branding_frame, text=f"v{VERSION}", font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w").pack(fill="x", pady=(5,0))
        
        # Navigation
        self.nav_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.nav_frame.pack(fill="x", padx=15, pady=10)
        
        nav_items = [
            ("Cards", "📋 Card List"),
            ("Effects", "📊 Search Effects"),
            ("Deck", "🎴 Deck Builder"),
            ("Skills", "🔍 Skill Search"),
            ("DeckSkills", "📜 Deck Skills"),
            ("Tracks", "🏟️ Tracks"),
            ("Calendar", "📅 Race Calendar")
        ]
        
        for view_id, text in nav_items:
            btn = create_sidebar_button(
                self.nav_frame, 
                text=text, 
                command=lambda vid=view_id: self.show_view(vid)
            )
            btn.pack(fill="x", pady=2)
            self.sidebar_buttons[view_id] = btn
            
        # Spacer
        ctk.CTkFrame(self.sidebar_frame, fg_color="transparent").pack(fill="both", expand=True)
        
        # Bottom area (Updater, Stats)
        bottom_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=20)
        
        self.stats_label = ctk.CTkLabel(bottom_frame, text="Loading...", font=FONT_SMALL, text_color=TEXT_MUTED, justify="left")
        self.stats_label.pack(anchor="w", pady=(0, 10))
        
        create_styled_button(
            bottom_frame, text="🔄 Updates", 
            command=self.show_update_dialog, style_type='default'
        ).pack(fill="x")
        
        self.refresh_stats()

    def create_main_area(self):
        """Create the right content area shell"""
        self.content_shell = ctk.CTkFrame(self.root, fg_color=BG_DARKEST, corner_radius=0)
        self.content_shell.grid(row=0, column=1, sticky="nsew")
        self.content_shell.grid_rowconfigure(0, weight=1)
        self.content_shell.grid_columnconfigure(0, weight=1)
        
        # The container where views actually live with padding
        self.view_container = ctk.CTkFrame(self.content_shell, fg_color="transparent")
        self.view_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.view_container.grid_rowconfigure(0, weight=1)
        self.view_container.grid_columnconfigure(0, weight=1)
        
    def init_views(self):
        """Setup view constructors to lazy-load on demand to prevent handle exhaustion"""
        self.view_classes = {
            "Cards": lambda: CardListFrame(self.view_container, 
                                            on_card_selected_callback=self.on_card_selected,
                                            on_stats_updated_callback=self.refresh_stats),
            "Effects": lambda: EffectsFrame(self.view_container),
            "Deck": lambda: DeckBuilderFrame(self.view_container),
            "Skills": lambda: SkillSearchFrame(self.view_container),
            "DeckSkills": lambda: DeckSkillsFrame(self.view_container),
            "Tracks": lambda: TrackViewFrame(self.view_container),
            "Calendar": lambda: RaceCalendarViewFrame(self.view_container)
        }

    def show_view(self, view_id):
        """Switch to a specific view by name"""
        if self.current_view_name == view_id:
            return
            
        # Hide old
        if self.current_view_name and self.current_view_name in self.views:
            self.views[self.current_view_name].grid_remove()
            if self.current_view_name in self.sidebar_buttons:
                self.sidebar_buttons[self.current_view_name].configure(
                    fg_color="transparent", text_color=TEXT_SECONDARY
                )
                
        # Lazy load new view if not exists
        if view_id not in self.views and view_id in self.view_classes:
            self.views[view_id] = self.view_classes[view_id]()
            self.views[view_id].grid(row=0, column=0, sticky="nsew")
            
            # Post-load hooks for selected cards
            if getattr(self, 'selected_card_id', None):
                if view_id == "Effects":
                    self.views[view_id].set_card(self.selected_card_id)
                elif view_id == "DeckSkills":
                    self.views[view_id].set_card(self.selected_card_id)
            
        # Show new
        self.current_view_name = view_id
        if view_id in self.views:
            self.views[view_id].grid()
            self.views[view_id].tkraise()
            
            # Update button
            if view_id in self.sidebar_buttons:
                self.sidebar_buttons[view_id].configure(
                    fg_color=BG_MEDIUM, text_color=ACCENT_PRIMARY
                )
        
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
        
        lines = [
            f"Cards:\t{total} ({owned} Owned)",
            f"SSR:\t{stats.get('by_rarity', {}).get('SSR', 0)}",
            f"SR:\t{stats.get('by_rarity', {}).get('SR', 0)}",
            f"R:\t{stats.get('by_rarity', {}).get('R', 0)}"
        ]
        if hasattr(self, 'stats_label'):
            self.stats_label.configure(text="\n".join(lines))
            
    def show_update_dialog(self):
        show_update_dialog(self.root)

    def run(self):
        self.root.mainloop()

def main():
    app = MainWindow()
    app.run()

if __name__ == "__main__":
    main()
