# Umamusume Support Card Manager

A tool for managing support cards and their effects in Umamusume.

## Features

- **Cards Management**: View and manage your support cards collection.
- **Deck Builder**: Build and optimize decks with your owned cards.
- **Effects Search**: Search for specific effects across your owned cards (e.g., "Friendship Bonus", "Skill Pt Bonus").
- **Web Scraping**: Integrated GameTora scraper to fetch the latest card data.
- **Auto-Updater**: Automatically improved application updates.
- **Maintenance Scripts**: Suite of scripts for database repair and deep scraping.

## Project Structure

```
.
├── main.py                 # Main entry point
├── version.py              # Version information
├── requirements.txt        # Python dependencies
├── scraper/                # Web scraping modules
│   └── gametora_scraper.py # GameTora scraper implementation
├── db/                     # Database modules
│   ├── db_init.py          # Database initialization
│   └── db_queries.py       # Database queries
├── gui/                    # GUI components
│   ├── main_window.py      # Main application window
│   ├── card_view.py        # Card list and details view
│   ├── deck_builder.py     # Deck construction view
│   ├── effects_view.py     # Effects search view
│   └── ...
├── updater/                # Update checking functionality
├── maintenance_scripts/    # Database repair and utility scripts
├── config/                 # Configuration files
├── database/               # Database files storage
├── images/                 # Character art images
├── build/                  # Build artifacts
└── dist/                   # Distribution files
```

## Installation

1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Run the application: `python main.py`.

## Usage

### GUI Mode (default)
```bash
python main.py
```

### Scraping Mode
To manually run the scraper:
```bash
python main.py --scrape
```

## Development

### Code Structure
- `main.py`: Entry point and argument parsing.
- `gui/`: Contains all CustomTkinter-based UI components.
- `db/`: Handles SQLite database interactions.
- `scraper/`: Logic for fetching data from GameTora.
- `maintenance_scripts/`: Tools for fixing database inconsistencies or re-fetching data.

### Contributing
1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Submit a pull request.

## License
MIT