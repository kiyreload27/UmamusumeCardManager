
import os
import sys

def resolve_image_path(db_path):
    """
    Resolve the absolute path to an image file.
    Handles the case where the database contains paths from a different machine/drive.
    Searches multiple locations:
    1. Bundled resources (_MEIPASS for PyInstaller)
    2. Local 'images' folder next to the .exe or project root
    3. The directory containing the source files
    """
    if not db_path:
        return None
        
    filename = os.path.basename(db_path)
    
    # List of directories to search
    search_dirs = []
    
    # 1. Check if running as frozen executable
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            # Bundled images folder in _MEIPASS
            search_dirs.append(os.path.join(sys._MEIPASS, 'images'))
        
        # Folder next to the .exe
        exe_dir = os.path.dirname(sys.executable)
        search_dirs.append(os.path.join(exe_dir, 'images'))
        search_dirs.append(exe_dir) # Maybe images are flat in exe dir
    
    # 2. Source code directory
    source_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs.append(os.path.join(source_dir, 'images'))
    search_dirs.append(os.path.join(source_dir, 'assets', 'characters'))
    search_dirs.append(os.path.join(source_dir, 'assets', 'cards'))
    
    # 3. Parent of source code (project root)
    project_root = os.path.dirname(source_dir)
    search_dirs.append(os.path.join(project_root, 'images'))
    search_dirs.append(os.path.join(project_root, 'assets', 'characters'))
    search_dirs.append(os.path.join(project_root, 'assets', 'cards'))

    # Try each search directory
    for d in search_dirs:
        if not d: continue
        test_path = os.path.join(d, filename)
        if os.path.exists(test_path):
            return test_path
            
    # Fallback: if we haven't found it, return what would be the standard local path
    # even if it doesn't exist (helpful for debugging)
    return os.path.join(source_dir, 'images', filename)
