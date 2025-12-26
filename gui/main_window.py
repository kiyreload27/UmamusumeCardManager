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
from gui.hints_skills_view import HintsSkillsFrame
from gui.deck_builder import DeckBuilderFrame
from gui.update_dialog import show_update_dialog
from utils import resolve_image_path
from version import VERSION


class MainWindow:
    """Main application window with tabbed interface"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Umamusume Support Card Manager")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        
        # Set icon
        try:
            # Use Special Week as icon if available
            icon_path = resolve_image_path("1_Special Week.png")
            if icon_path and os.path.exists(icon_path):
                icon_img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon_img)
        except Exception as e:
            print(f"Failed to set icon: {e}")
        
        # Set up styling
        self.setup_styles()
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Header with stats
        self.create_header(main_container)
        
        # Status bar - Create BEFORE notebook to anchor it to bottom
        self.create_status_bar(main_container)
        
        # Tabbed notebook
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create tabs
        self.create_tabs()
    
    def setup_styles(self):
        """Set up custom styles for the application"""
        style = ttk.Style()
        
        # Use clam theme as base for better customization
        style.theme_use('clam')
        
        # Configure colors - dark theme
        bg_dark = '#1a1a2e'
        bg_medium = '#16213e'
        bg_light = '#0f3460'
        accent = '#e94560'
        text_light = '#eaeaea'
        text_muted = '#a0a0a0'
        
        # General frame style
        style.configure('TFrame', background=bg_dark)
        style.configure('TLabel', background=bg_dark, foreground=text_light)
        style.configure('TButton', padding=6)
        style.configure('TCheckbutton', background=bg_dark, foreground=text_light)
        
        # Header styles
        style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'), 
                       foreground=accent, background=bg_dark)
        style.configure('Subtitle.TLabel', font=('Helvetica', 11), 
                       foreground=text_muted, background=bg_dark)
        style.configure('Stats.TLabel', font=('Helvetica', 10), 
                       foreground=text_light, background=bg_medium, padding=5)
        
        # Large checkbox style
        style.configure('Large.TCheckbutton', font=('Helvetica', 11, 'bold'))
        
        # Notebook (tabs)
        style.configure('TNotebook', background=bg_dark)
        style.configure('TNotebook.Tab', padding=[15, 8], font=('Helvetica', 10, 'bold'))
        
        # Treeview styling
        style.configure('Treeview', 
                       background=bg_medium, 
                       foreground=text_light,
                       fieldbackground=bg_medium,
                       font=('Helvetica', 10))
        style.configure('Treeview.Heading', 
                       font=('Helvetica', 10, 'bold'),
                       background=bg_light,
                       foreground=text_light)
        style.map('Treeview', 
                 background=[('selected', accent)])
        
        # Set root background
        self.root.configure(bg=bg_dark)
    
    def create_header(self, parent):
        """Create header with database statistics and update button"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Left side: Title and version
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=tk.LEFT)
        
        ttk.Label(title_frame, text="🏇 Umamusume Support Card Manager", 
                 style='Header.TLabel').pack(side=tk.LEFT)
        
        # Version badge
        ttk.Label(title_frame, text=f"  v{VERSION}", 
                 style='Subtitle.TLabel').pack(side=tk.LEFT, padx=(5, 0))
        
        # Right side: Update button and stats
        right_frame = ttk.Frame(header_frame)
        right_frame.pack(side=tk.RIGHT)
        
        # Update button
        self.update_button = tk.Button(
            right_frame,
            text="🔄 Check for Updates",
            command=self.show_update_dialog,
            bg='#16213e',
            fg='#eaeaea',
            font=('Helvetica', 9),
            padx=10,
            pady=3,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.update_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Stats panel
        stats_frame = ttk.Frame(right_frame)
        stats_frame.pack(side=tk.RIGHT)
        
        stats = get_database_stats()
        owned = get_owned_count()
        
        stats_text = f"📊 Cards: {stats.get('total_cards', 0)} | "
        stats_text += f"Owned: {owned} | "
        stats_text += f"SSR: {stats.get('by_rarity', {}).get('SSR', 0)} | "
        stats_text += f"SR: {stats.get('by_rarity', {}).get('SR', 0)} | "
        stats_text += f"R: {stats.get('by_rarity', {}).get('R', 0)}"
        
        self.stats_label = ttk.Label(stats_frame, text=stats_text, style='Stats.TLabel')
        self.stats_label.pack()
    
    def create_tabs(self):
        """Create all tab frames"""
        # Card List Tab
        self.card_frame = CardListFrame(self.notebook, on_card_selected_callback=self.on_card_selected)
        self.notebook.add(self.card_frame, text="📋 Card List")
        
        # Effects Tab
        self.effects_frame = EffectsFrame(self.notebook)
        self.notebook.add(self.effects_frame, text="📊 Effects")
        
        # Deck Builder Tab
        self.deck_frame = DeckBuilderFrame(self.notebook)
        self.notebook.add(self.deck_frame, text="🎴 Deck Builder")
        
        # Hints & Skills Tab
        self.hints_frame = HintsSkillsFrame(self.notebook)
        self.notebook.add(self.hints_frame, text="💡 Hints & Skills")
    
    def create_status_bar(self, parent):
        """Create status bar at bottom"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready", style='Subtitle.TLabel')
        self.status_label.pack(side=tk.LEFT)
        
        ttk.Label(status_frame, text="Data from gametora.com", 
                 style='Subtitle.TLabel').pack(side=tk.RIGHT)

        ttk.Label(status_frame, text="Made by Kiyreload | ", 
                 style='Subtitle.TLabel').pack(side=tk.RIGHT)
    
    def on_card_selected(self, card_id, card_name):
        """Handle card selection from card list"""
        # Update other tabs with selected card
        if hasattr(self, 'effects_frame'):
            self.effects_frame.set_card(card_id)
        if hasattr(self, 'hints_frame'):
            self.hints_frame.set_card(card_id)
        
        self.status_label.config(text=f"Selected: {card_name}")
    
    def refresh_stats(self):
        """Refresh the statistics display"""
        stats = get_database_stats()
        owned = get_owned_count()
        
        stats_text = f"📊 Cards: {stats.get('total_cards', 0)} | "
        stats_text += f"Owned: {owned} | "
        stats_text += f"SSR: {stats.get('by_rarity', {}).get('SSR', 0)} | "
        stats_text += f"SR: {stats.get('by_rarity', {}).get('SR', 0)} | "
        stats_text += f"R: {stats.get('by_rarity', {}).get('R', 0)}"
        
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
