
import os
import sys

def resolve_image_path(db_path):
    """
    Resolve the absolute path to an image file.
    Handles the case where the database contains paths from a different machine/drive.
    Searches multiple locations:
    1. The exact relative path from project root (e.g. assets/races/...)
    2. Bundled resources (_MEIPASS for PyInstaller)
    3. Local 'images' folder next to the .exe or project root
    4. The directory containing the source files
    """
    if not db_path:
        return None

    filename = os.path.basename(db_path)

    # Determine project root (handles both source and frozen exe layouts)
    if getattr(sys, 'frozen', False):
        source_dir = os.path.dirname(sys.executable)
        meipass = getattr(sys, '_MEIPASS', source_dir)
    else:
        source_dir = os.path.dirname(os.path.abspath(__file__))
        meipass = source_dir

    # 1. Try db_path as a relative path from project root (covers assets/races/, assets/tracks/, etc.)
    for root_dir in [source_dir, meipass]:
        candidate = os.path.normpath(os.path.join(root_dir, db_path))
        if os.path.exists(candidate):
            return candidate

    # 2. Build search dirs list (basename fallback)
    search_dirs = []
    if getattr(sys, 'frozen', False):
        search_dirs += [
            os.path.join(meipass, 'images'),
            os.path.join(meipass, 'assets', 'characters'),
            os.path.join(meipass, 'assets', 'cards'),
            os.path.join(meipass, 'assets', 'races'),
            os.path.join(meipass, 'assets', 'tracks'),
            os.path.join(source_dir, 'images'),
            source_dir,
        ]
    else:
        search_dirs += [
            os.path.join(source_dir, 'images'),
            os.path.join(source_dir, 'assets', 'characters'),
            os.path.join(source_dir, 'assets', 'cards'),
            os.path.join(source_dir, 'assets', 'races'),
            os.path.join(source_dir, 'assets', 'tracks'),
        ]

    for d in search_dirs:
        if not d:
            continue
        test_path = os.path.join(d, filename)
        if os.path.exists(test_path):
            return test_path

    # Fallback: return a best-guess path even if it doesn't exist
    return os.path.join(source_dir, 'images', filename)
