"""
Main Window for Umamusume Support Card Manager
Tabbed interface for card browsing, effects, deck builder, and hints
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_database_stats, get_owned_count
from gui.card_view import CardListFrame
from gui.effects_view import EffectsFrame
from gui.hints_skills_view import HintsSkillsFrame
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
        self.root = tk.Tk()
        self.root.title("Umamusume Support Card Manager")
        self.root.geometry("1350x800")
        self.root.minsize(1350, 800)
        
        # Set icon
        try:
            icon_path = resolve_image_path("1_Special Week.png")
            if icon_path and os.path.exists(icon_path):
                icon_img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon_img)
        except Exception as e:
            print(f"Failed to set icon: {e}")
        
        # Configure all styles using centralized theme
        configure_styles(self.root)
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Header with stats
        self.create_header(main_container)
        
        # Status bar - Create BEFORE notebook to anchor it to bottom
        self.create_status_bar(main_container)
        
        # Tabbed notebook
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)
        
        # Create tabs
        self.create_tabs()
    
    def create_header(self, parent):
        """Create header with database statistics and update button"""
        # Header container with subtle bottom border effect
        header_outer = tk.Frame(parent, bg=BG_DARK)
        header_outer.pack(fill=tk.X)
        
        header_frame = tk.Frame(header_outer, bg=BG_DARK)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        # Left side: Title and version
        title_frame = tk.Frame(header_frame, bg=BG_DARK)
        title_frame.pack(side=tk.LEFT)
        
        # App icon and title
        title_label = tk.Label(
            title_frame, 
            text="🏇 Umamusume Support Card Manager",
            font=FONT_TITLE,
            bg=BG_DARK,
            fg=ACCENT_PRIMARY
        )
        title_label.pack(side=tk.LEFT)
        
        # Version badge
        version_frame = tk.Frame(title_frame, bg=ACCENT_SECONDARY, padx=8, pady=2)
        version_frame.pack(side=tk.LEFT, padx=12)
        version_label = tk.Label(
            version_frame,
            text=f"v{VERSION}",
            font=FONT_SMALL,
            bg=ACCENT_SECONDARY,
            fg=TEXT_PRIMARY
        )
        version_label.pack()
        
        # Right side: Update button and stats
        right_frame = tk.Frame(header_frame, bg=BG_DARK)
        right_frame.pack(side=tk.RIGHT)
        
        # Update button with modern styling
        self.update_button = create_styled_button(
            right_frame,
            text="🔄 Check for Updates",
            command=self.show_update_dialog,
            style_type='default'
        )
        self.update_button.pack(side=tk.RIGHT, padx=(15, 0))
        
        # Stats panel with card-like appearance
        stats_frame = tk.Frame(right_frame, bg=BG_MEDIUM, padx=15, pady=8)
        stats_frame.pack(side=tk.RIGHT)
        
        stats = get_database_stats()
        owned = get_owned_count()
        
        # Build stats text with better formatting
        stats_parts = [
            f"📊 {stats.get('total_cards', 0)} Cards",
            f"✨ {owned} Owned",
            f"🏆 {stats.get('by_rarity', {}).get('SSR', 0)} SSR",
            f"⭐ {stats.get('by_rarity', {}).get('SR', 0)} SR",
            f"● {stats.get('by_rarity', {}).get('R', 0)} R"
        ]
        stats_text = "  │  ".join(stats_parts)
        
        self.stats_label = tk.Label(
            stats_frame,
            text=stats_text,
            font=FONT_SMALL,
            bg=BG_MEDIUM,
            fg=TEXT_SECONDARY
        )
        self.stats_label.pack()
        
        # Subtle separator line
        separator = tk.Frame(header_outer, bg=BG_LIGHT, height=1)
        separator.pack(fill=tk.X, padx=15)
    
    def create_tabs(self):
        """Create all tab frames"""
        # Card List Tab
        self.card_frame = CardListFrame(self.notebook, on_card_selected_callback=self.on_card_selected)
        self.notebook.add(self.card_frame, text="  📋 Card List  ")
        
        # Effects Tab
        self.effects_frame = EffectsFrame(self.notebook)
        self.notebook.add(self.effects_frame, text="  📊 Effects  ")
        
        # Deck Builder Tab
        self.deck_frame = DeckBuilderFrame(self.notebook)
        self.notebook.add(self.deck_frame, text="  🎴 Deck Builder  ")
        
        # Hints & Skills Tab
        self.hints_frame = HintsSkillsFrame(self.notebook)
        self.notebook.add(self.hints_frame, text="  💡 Hints & Skills  ")
    
    def create_status_bar(self, parent):
        """Create status bar at bottom"""
        status_outer = tk.Frame(parent, bg=BG_MEDIUM)
        status_outer.pack(fill=tk.X, side=tk.BOTTOM)
        
        status_frame = tk.Frame(status_outer, bg=BG_MEDIUM)
        status_frame.pack(fill=tk.X, padx=15, pady=8)
        
        self.status_label = tk.Label(
            status_frame,
            text="✓ Ready",
            font=FONT_SMALL,
            bg=BG_MEDIUM,
            fg=TEXT_MUTED
        )
        self.status_label.pack(side=tk.LEFT)
        
        tk.Label(
            status_frame,
            text="Data from gametora.com",
            font=FONT_SMALL,
            bg=BG_MEDIUM,
            fg=TEXT_MUTED
        ).pack(side=tk.RIGHT)
        
        tk.Label(
            status_frame,
            text="Made by Kiyreload  │  ",
            font=FONT_SMALL,
            bg=BG_MEDIUM,
            fg=ACCENT_TERTIARY
        ).pack(side=tk.RIGHT)
    
    def on_card_selected(self, card_id, card_name):
        """Handle card selection from card list"""
        # Update other tabs with selected card
        if hasattr(self, 'effects_frame'):
            self.effects_frame.set_card(card_id)
        if hasattr(self, 'hints_frame'):
            self.hints_frame.set_card(card_id)
        
        self.status_label.config(text=f"📌 Selected: {card_name}")
    
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
        
        self.stats_label.config(text=stats_text)
    
    def show_update_dialog(self):
        """Show the update dialog"""
        show_update_dialog(self.root)
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Entry point for GUI"""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
