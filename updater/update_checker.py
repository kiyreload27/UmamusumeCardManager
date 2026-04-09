"""
Update checker for UmamusumeCardManager
Checks GitHub Releases for new versions and handles downloading updates.
"""

import os
import sys
import tempfile
import subprocess
import requests
from typing import Optional, Callable, Tuple

# Import version info
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from version import VERSION, GITHUB_API_URL, APP_NAME


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """
    Parse a version string into a tuple of integers.
    Handles formats like "1.0.0", "v1.0.0", "1.2.3-beta", etc.
    """
    # Remove 'v' prefix if present
    version_str = version_str.lstrip('v').lstrip('V')
    
    # Remove any suffix like -beta, -rc1, etc.
    if '-' in version_str:
        version_str = version_str.split('-')[0]
    
    parts = version_str.split('.')
    
    # Ensure we have at least 3 parts
    while len(parts) < 3:
        parts.append('0')
    
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return (0, 0, 0)


def compare_versions(local: str, remote: str) -> int:
    """
    Compare two version strings.
    Returns:
        -1 if local < remote (update available)
         0 if local == remote (up to date)
         1 if local > remote (local is newer)
    """
    local_tuple = parse_version(local)
    remote_tuple = parse_version(remote)
    
    if local_tuple < remote_tuple:
        return -1
    elif local_tuple > remote_tuple:
        return 1
    else:
        return 0


def check_for_updates() -> Optional[dict]:
    """
    Check GitHub Releases for a new version.
    
    Returns:
        dict with update info if available, None if up to date or error.
        {
            'current_version': str,
            'new_version': str,
            'download_url': str,
            'release_notes': str,
            'html_url': str  # Link to the release page
        }
    """
    try:
        # Add a user-agent header (GitHub API requires this)
        headers = {
            'User-Agent': f'{APP_NAME}-Updater',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        
        if response.status_code == 404:
            # No releases found
            print("No releases found on GitHub.")
            return None
        
        response.raise_for_status()
        release_data = response.json()
        
        remote_version = release_data.get('tag_name', '')
        
        # Compare versions
        if compare_versions(VERSION, remote_version) < 0:
            # Pick the right asset for the current OS
            download_url = None
            is_windows = sys.platform == "win32"
            for asset in release_data.get('assets', []):
                asset_name = asset.get('name', '').lower()
                if is_windows and asset_name.endswith('.exe'):
                    download_url = asset.get('browser_download_url')
                    break
                elif not is_windows and not asset_name.endswith('.exe') and 'linux' in asset_name:
                    download_url = asset.get('browser_download_url')
                    break

            # Fallback: first non-exe asset on Linux, first exe on Windows
            if not download_url:
                for asset in release_data.get('assets', []):
                    asset_name = asset.get('name', '').lower()
                    if is_windows and asset_name.endswith('.exe'):
                        download_url = asset.get('browser_download_url')
                        break
                    elif not is_windows and not asset_name.endswith('.exe'):
                        download_url = asset.get('browser_download_url')
                        break

            if not download_url:
                print("No suitable asset found in the latest release for this OS.")
                return None
            
            return {
                'current_version': VERSION,
                'new_version': remote_version,
                'download_url': download_url,
                'release_notes': release_data.get('body', 'No release notes provided.'),
                'html_url': release_data.get('html_url', '')
            }
        else:
            # Already up to date
            return None
            
    except requests.exceptions.Timeout:
        print("Update check timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error checking for updates: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during update check: {e}")
        return None


def download_update(download_url: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:
    """
    Download the update file.
    
    Args:
        download_url: URL to download the new exe from
        progress_callback: Optional callback function(downloaded_bytes, total_bytes)
    
    Returns:
        Path to the downloaded file, or None if failed.
    """
    try:
        headers = {
            'User-Agent': f'{APP_NAME}-Updater'
        }
        
        response = requests.get(download_url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        # Get total file size
        total_size = int(response.headers.get('content-length', 0))
        
        # Create temp file for download
        temp_dir = tempfile.gettempdir()
        ext = ".exe" if sys.platform == "win32" else ""
        temp_path = os.path.join(temp_dir, f'{APP_NAME}_update{ext}')
        
        downloaded = 0
        chunk_size = 8192
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)
        
        return temp_path
        
    except Exception as e:
        print(f"Error downloading update: {e}")
        return None


def get_current_exe_path() -> str:
    """Get the path to the current running executable."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return sys.executable
    else:
        # Running as script
        return os.path.abspath(sys.argv[0])


def apply_update(new_exe_path: str) -> bool:
    """
    Apply the update by replacing the current binary with the new one.

    Windows strategy:
      1. Launch a .bat script that waits for this process to exit.
      2. Renames the old EXE to <name>.old (works on locked files).
      3. Moves the downloaded EXE into place.
      4. Cleans up and prompts the user to relaunch.

    Linux strategy:
      1. Launch a shell script that waits for this process to exit.
      2. Replaces the binary with the new one using mv.
      3. Sets executable permissions.
      4. Prompts the user to relaunch.

    The calling code should call os._exit(0) after this returns True.

    Args:
        new_exe_path: Path to the downloaded new binary

    Returns:
        True if the updater script was launched successfully.
    """
    try:
        current_exe = get_current_exe_path()

        # If running as a script, we can't self-update
        if not getattr(sys, 'frozen', False):
            print("Cannot apply update when running as a script.")
            print(f"New version downloaded to: {new_exe_path}")
            return False

        if sys.platform == "win32":
            return _apply_update_windows(current_exe, new_exe_path)
        else:
            return _apply_update_linux(current_exe, new_exe_path)

    except Exception as e:
        print(f"Error applying update: {e}")
        return False


def _apply_update_windows(current_exe: str, new_exe_path: str) -> bool:
    """Windows update: rename-then-move via a .bat script."""
    try:
        old_exe = current_exe + ".old"
        batch_script = os.path.join(tempfile.gettempdir(), f'{APP_NAME}_updater.bat')

        script_content = f'''@echo off
title {APP_NAME} Updater
echo ========================================
echo          {APP_NAME} Updater
echo ========================================
echo.
echo Waiting for the application to fully exit...
timeout /t 4 >nul

:wait_loop
2>nul (
    >> "{current_exe}" echo off
) && goto :do_update
echo Still waiting...
timeout /t 2 >nul
goto :wait_loop

:do_update
echo.
echo Renaming old version...
if exist "{old_exe}" del /f /q "{old_exe}"
rename "{current_exe}" "{os.path.basename(old_exe)}"
if errorlevel 1 (
    echo ERROR: Could not rename old executable. Is it still running?
    pause
    exit /b 1
)

echo Moving new version into place...
move /Y "{new_exe_path}" "{current_exe}"
if errorlevel 1 (
    echo ERROR: Could not move new executable. Restoring old version...
    rename "{old_exe}" "{os.path.basename(current_exe)}"
    pause
    exit /b 1
)

echo Cleaning up...
if exist "{old_exe}" del /f /q "{old_exe}"

echo.
echo ========================================
echo    Update applied successfully!
echo ========================================
echo.
echo Please relaunch {APP_NAME} manually.
echo This window will close in 8 seconds...
timeout /t 8 >nul
exit
'''

        with open(batch_script, 'w') as f:
            f.write(script_content)

        CREATE_NEW_CONSOLE = 0x00000010
        subprocess.Popen(
            ['cmd', '/c', batch_script],
            creationflags=CREATE_NEW_CONSOLE,
            close_fds=True,
        )
        return True

    except Exception as e:
        print(f"Error launching Windows updater: {e}")
        return False


def _apply_update_linux(current_exe: str, new_exe_path: str) -> bool:
    """Linux update: replace binary via a shell script."""
    try:
        shell_script = os.path.join(tempfile.gettempdir(), f'{APP_NAME}_updater.sh')

        script_content = f'''#!/bin/bash
echo "========================================"
echo "         {APP_NAME} Updater"
echo "========================================"
echo
echo "Waiting for the application to fully exit..."
sleep 3

# Wait until the old binary is no longer locked
for i in $(seq 1 15); do
    if ! fuser "{current_exe}" > /dev/null 2>&1; then
        break
    fi
    echo "Still waiting ($i)..."
    sleep 2
done

echo
echo "Replacing binary..."
mv -f "{new_exe_path}" "{current_exe}"
if [ $? -ne 0 ]; then
    echo "ERROR: Could not replace the binary. Do you have write permissions?"
    read -p "Press Enter to exit..."
    exit 1
fi

chmod +x "{current_exe}"

echo
echo "========================================"
echo "   Update applied successfully!"
echo "========================================"
echo
echo "Please relaunch {APP_NAME} manually."
read -p "Press Enter to close this window..."
'''

        with open(shell_script, 'w') as f:
            f.write(script_content)

        os.chmod(shell_script, 0o755)

        # Try to open in a visible terminal (common desktop terminals)
        terminals = [
            ['gnome-terminal', '--', 'bash', shell_script],
            ['xterm', '-e', f'bash {shell_script}'],
            ['konsole', '-e', f'bash {shell_script}'],
            ['xfce4-terminal', '-e', f'bash {shell_script}'],
            ['lxterminal', '-e', f'bash {shell_script}'],
        ]

        for term_cmd in terminals:
            try:
                subprocess.Popen(term_cmd, close_fds=True)
                return True
            except FileNotFoundError:
                continue

        # No GUI terminal found — run headlessly in background
        subprocess.Popen(['bash', shell_script], close_fds=True)
        return True

    except Exception as e:
        print(f"Error launching Linux updater: {e}")
        return False


def get_current_version() -> str:
    """Get the current application version."""
    return VERSION
