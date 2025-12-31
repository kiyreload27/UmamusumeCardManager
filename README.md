# Umamusume Support Card Manager

A tool for managing support cards and their effects in Umamusume (Granblue Fantasy Relink).

## Features

- Web scraping of support card data from GameTora
- Database storage of card information including effects at different levels
- GUI application for viewing and managing support cards
- Deck building functionality
- Character art downloading

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
├── updater/                # Update checking functionality
├── database/               # Database files
├── images/                 # Character art images
├── build/                  # Build artifacts
└── dist/                   # Distribution files
```

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python main.py`

## Usage

### GUI Mode (default)
```bash
python main.py
```

### Scraping Mode
```bash
python main.py --scrape
```

## Development

### Code Structure
- `main.py`: Entry point and argument parsing
- `scraper/gametora_scraper.py`: Web scraping logic
- `db/db_init.py`: Database schema initialization
- `gui/`: GUI components (MainWindow, views, etc.)
- `updater/update_checker.py`: Update checking functionality

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License
MIT