
import os
import sys

def resolve_image_path(db_path):
    """
    Resolve the absolute path to an image file.
    Handles the case where the database contains paths from a different machine/drive.
    Also handles frozen (PyInstaller) state.
    """
    if not db_path:
        return None
        
    filename = os.path.basename(db_path)
    
    # Check if running as frozen executable
    if getattr(sys, 'frozen', False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if hasattr(sys, '_MEIPASS'):
            root_dir = sys._MEIPASS
        else:
            root_dir = os.path.dirname(sys.executable)
    else:
        # Get the project root directory (directory where this utils.py resides)
        root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct optimal path
    return os.path.join(root_dir, 'images', filename)
