"""
Main Window for Umamusume Support Card Manager
Tabbed interface for card browsing, effects, deck builder, and hints
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
from gui.deck_builder import DeckBuilderFrame
from gui.update_dialog import show_update_dialog
from gui.theme import (
    configure_styles, create_styled_button,
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_SMALL
)
from utils import resolve_image_path
from version import VERSION


class MainWindow:
    """Main application window with tabbed interface"""
    
    def __init__(self):
        # Initialize CTk root
        self.root = ctk.CTk()
        self.root.title("Umamusume Support Card Manager")
        self.root.geometry("1400x850") 
        self.root.minsize(1350, 800)
        
        # Set icon
        try:
            icon_path = resolve_image_path("1_Special Week.png")
            if icon_path and os.path.exists(icon_path):
                # ctk uses iconbitmap for windows usually, but iconphoto works too
                icon_img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon_img)
        except Exception as e:
            print(f"Failed to set icon: {e}")
        
        # Configure styles for legacy widgets
        configure_styles(self.root)
        
        # Create main container
        # Note: CTk already has a main frame in a way, but we'll use a container for padding
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # State
        self.last_selected_levels = {} # card_id -> level
        
        # Header with stats
        self.create_header(main_container)
        
        # Status bar
        self.create_status_bar(main_container)
        
        # Tabbed notebook -> CTkTabview
        self.tabview = ctk.CTkTabview(main_container)
        self.tabview.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_tabs()
    
    def create_header(self, parent):
        """Create header with database statistics and update button"""
        # Header container
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Left side: Title and version
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side=tk.LEFT)
        
        # App icon and title
        title_label = ctk.CTkLabel(
            title_frame, 
            text="🏇 Umamusume Support Card Manager",
            font=FONT_TITLE,
            text_color=ACCENT_PRIMARY
        )
        title_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Version badge
        version_label = ctk.CTkLabel(
            title_frame,
            text=f"v{VERSION}",
            font=FONT_SMALL,
            fg_color=ACCENT_SECONDARY,
            text_color=TEXT_PRIMARY,
            corner_radius=6,
            height=24,
            width=60
        )
        version_label.pack(side=tk.LEFT)
        
        # Right side: Update button and stats
        right_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_frame.pack(side=tk.RIGHT)
        
        # Update button
        self.update_button = create_styled_button(
            right_frame,
            text="🔄 Check for Updates",
            command=self.show_update_dialog,
            style_type='default'
        )
        self.update_button.pack(side=tk.RIGHT, padx=(15, 0))
        
        # Stats panel
        self.stats_label = ctk.CTkLabel(
            right_frame,
            text="Loading stats...",
            font=FONT_SMALL,
            fg_color=BG_MEDIUM,
            text_color=TEXT_SECONDARY,
            corner_radius=8,
            padx=15,
            pady=5
        )
        self.stats_label.pack(side=tk.RIGHT)
        
        # Initial stats load
        self.refresh_stats()
    
    def create_tabs(self):
        """Create all tab frames"""
        # Add tabs
        tab_cards = self.tabview.add("  📋 Card List  ")
        tab_effects = self.tabview.add("  📊 Search Effects  ")
        tab_deck = self.tabview.add("  🎴 Deck Builder  ")
        tab_search = self.tabview.add("  🔍 Skill Search  ")
        tab_skills = self.tabview.add("  📜 Deck Skills  ")
        
        # Card List Tab
        # Note: CardListFrame and others inherit from ttk.Frame/tk.Frame. 
        # We need to make sure they can be packed into a CTkFrame (the tab).
        self.card_frame = CardListFrame(tab_cards, 
                                        on_card_selected_callback=self.on_card_selected,
                                        on_stats_updated_callback=self.refresh_stats)
        self.card_frame.pack(fill=tk.BOTH, expand=True)
        
        # Effects Tab
        self.effects_frame = EffectsFrame(tab_effects)
        self.effects_frame.pack(fill=tk.BOTH, expand=True)
        
        # Deck Builder Tab
        self.deck_frame = DeckBuilderFrame(tab_deck)
        self.deck_frame.pack(fill=tk.BOTH, expand=True)
        
        # Skill Search Tab
        self.hints_frame = SkillSearchFrame(tab_search)
        self.hints_frame.pack(fill=tk.BOTH, expand=True)
        
        # Deck Skills Tab
        self.deck_skills_frame = DeckSkillsFrame(tab_skills)
        self.deck_skills_frame.pack(fill=tk.BOTH, expand=True)
    
    def create_status_bar(self, parent):
        """Create status bar at bottom"""
        # Using pack side=BOTTOM relative to the main container
        status_frame = ctk.CTkFrame(parent, height=30, fg_color="transparent")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="✓ Ready",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        ctk.CTkLabel(
            status_frame,
            text="Data from gametora.com",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        ).pack(side=tk.RIGHT)
        
        ctk.CTkLabel(
            status_frame,
            text="VibeCoded by Kiyreload  │  ",
            font=FONT_SMALL,
            text_color=ACCENT_TERTIARY
        ).pack(side=tk.RIGHT)
    
    def on_card_selected(self, card_id, card_name, level=None):
        """Handle card selection from card list"""
        if level is not None:
            self.last_selected_levels[card_id] = level
        self.selected_card_id = card_id 
        
        # Update other tabs
        if hasattr(self, 'effects_frame'):
            self.effects_frame.set_card(card_id)
        if hasattr(self, 'deck_skills_frame'):
            self.deck_skills_frame.set_card(card_id)
        
        self.status_label.configure(text=f"📌 Selected: {card_name}")
    
    def refresh_stats(self):
        """Refresh the statistics display"""
        stats = get_database_stats()
        owned = get_owned_count()
        
        stats_parts = [
            f"📊 {stats.get('total_cards', 0)} Cards",
            f"✨ {owned} Owned",
            f"🏆 {stats.get('by_rarity', {}).get('SSR', 0)} SSR",
            f"⭐ {stats.get('by_rarity', {}).get('SR', 0)} SR",
            f"● {stats.get('by_rarity', {}).get('R', 0)} R"
        ]
        stats_text = "  │  ".join(stats_parts)
        
        if hasattr(self, 'stats_label'):
            self.stats_label.configure(text=stats_text)
    
    def show_update_dialog(self):
        """Show the update dialog"""
        show_update_dialog(self.root)

    def run(self):
        """
        Start the GUI application and display the main window.
        """
        self.root.mainloop()


def main():
    """Entry point for GUI"""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
