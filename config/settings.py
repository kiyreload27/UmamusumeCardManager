"""
Application settings and configuration
"""

import os
from pathlib import Path

# Base directory of the application
BASE_DIR = Path(__file__).parent.parent

# Database configuration
DATABASE_PATH = BASE_DIR / "database" / "umamusume.db"
DATABASE_SEED_PATH = BASE_DIR / "database" / "umamusume_seed.db"

# Image directory
IMAGES_DIR = BASE_DIR / "images"

# Application settings
APP_NAME = "UmamusumeCardManager"
VERSION = "7.0.0"

# Scraping settings
SCRAPING_DELAY_MIN = 0.2
SCRAPING_DELAY_MAX = 0.5
MAX_RETRIES = 3

# Browser settings
HEADLESS_MODE = True
BROWSER_TIMEOUT = 60000

# Database schema version
DB_SCHEMA_VERSION = "1.0"
"""
Database schema version for migration tracking
"""
