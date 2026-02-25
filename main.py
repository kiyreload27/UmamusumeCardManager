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
        import traceback
        error_msg = f"An error occurred while running the scraper:\n\n{e}\n\n{traceback.format_exc()}"
        logging.error(error_msg)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Scraper Error", error_msg)
        except:
            pass
        sys.exit(1)

def run_track_scraper():
    try:
        from scraper.track_scraper import run_track_scraper as scrape_tracks
        scrape_tracks()
    except Exception as e:
        import traceback
        error_msg = f"An error occurred while running the track scraper:\n\n{e}\n\n{traceback.format_exc()}"
        logging.error(error_msg)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Track Scraper Error", error_msg)
        except:
            pass
        sys.exit(1)

def run_gui():
    try:
        from gui.main_window import MainWindow
        app = MainWindow()
        app.run()
    except Exception as e:
        import traceback
        error_msg = f"An error occurred while launching the GUI:\n\n{e}\n\n{traceback.format_exc()}"
        logging.error(error_msg)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Application Error", error_msg)
        except:
            pass
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Umamusume Support Card Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python main.py                # Launch the GUI (default)
  python main.py --gui          # Launch the GUI
  python main.py --scrape       # Run the support card scraper
  python main.py --scrape-tracks  # Run the racetrack scraper
        """
    )
    
    parser.add_argument(
        '--scrape', 
        action='store_true',
        help='Run the web scraper to fetch support card data from GameTora'
    )
    parser.add_argument(
        '--scrape-tracks', 
        action='store_true',
        help='Run the racetrack scraper to fetch track/course data from GameTora'
    )
    parser.add_argument(
        '--gui', 
        action='store_true',
        help='Launch the GUI application (default action)'
    )
    
    args = parser.parse_args()
    
    if args.scrape:
        print("Starting support card scraper...")
        run_scraper()
    elif args.scrape_tracks:
        print("Starting racetrack scraper...")
        run_track_scraper()
    else:
        # Default to GUI
        print("Launching Umamusume Support Card Manager...")
        run_gui()

if __name__ == "__main__":
    main()