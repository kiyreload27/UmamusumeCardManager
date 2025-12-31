import argparse
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_scraper():
    try:
        from scraper.gametora_scraper import run_scraper as scrape
        scrape()
    except Exception as e:
        logging.error(f"An error occurred while running the scraper: {e}")
        sys.exit(1)

def run_gui():
    try:
        from gui.main_window import MainWindow
        app = MainWindow()
        app.run()
    except Exception as e:
        logging.error(f"An error occurred while launching the GUI: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Umamusume Support Card Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
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