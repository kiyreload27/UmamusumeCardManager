"""
Umamusume Support Card Manager
Main entry point for the application
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_scraper():
    """Run the web scraper to fetch card data"""
    from scraper.gametora_scraper import run_scraper as scrape
    scrape()

def run_gui():
    """Launch the Tkinter GUI application"""
    from gui.main_window import MainWindow
    app = MainWindow()
    app.run()

def main():
    parser = argparse.ArgumentParser(
        description="Umamusume Support Card Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py           # Launch the GUI (default)
  python main.py --gui     # Launch the GUI
  python main.py --scrape  # Run the web scraper
        """
    )
    
    parser.add_argument(
        '--scrape', 
        action='store_true',
        help='Run the web scraper to fetch data from GameTora'
    )
    parser.add_argument(
        '--gui', 
        action='store_true',
        help='Launch the GUI application (default action)'
    )
    
    args = parser.parse_args()
    
    if args.scrape:
        print("Starting web scraper...")
        run_scraper()
    else:
        # Default to GUI
        print("Launching Umamusume Support Card Manager...")
        run_gui()

if __name__ == "__main__":
    main()
