"""
Playwright browser path utilities.

When a PyInstaller-frozen EXE runs, Playwright extracts itself into a fresh
temporary folder (_MEIxxxxx) on every launch.  By default, Playwright looks
for its bundled browsers *relative to that temp folder*, so a browser that was
installed previously will never be found.

The fix is to force a single, persistent directory for browser storage by
setting PLAYWRIGHT_BROWSERS_PATH *before* any playwright module is imported or
the driver subprocess is started.  Both the install step and the launch step
must see the same value.
"""

import os
import sys


def get_persistent_browsers_path() -> str:
    """
    Return a stable, user-writable directory for Playwright browser binaries.

    We store them under:
        %LOCALAPPDATA%\\UmamusumeCardManager\\browsers   (Windows)
        ~/.local/share/UmamusumeCardManager/browsers    (Linux/macOS fallback)
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))

    return os.path.join(base, "UmamusumeCardManager", "browsers")


def ensure_playwright_browsers_path() -> str:
    """
    Set PLAYWRIGHT_BROWSERS_PATH to our persistent directory and return it.

    Must be called as early as possible — before any `import playwright` or
    `from playwright ...` statement anywhere in the process.
    """
    path = get_persistent_browsers_path()
    os.makedirs(path, exist_ok=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = path
    return path
