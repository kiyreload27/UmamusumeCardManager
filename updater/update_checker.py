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
            # Find the Windows exe asset
            download_url = None
            for asset in release_data.get('assets', []):
                asset_name = asset.get('name', '').lower()
                if asset_name.endswith('.exe'):
                    download_url = asset.get('browser_download_url')
                    break
            
            if not download_url:
                print("No .exe asset found in the latest release.")
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
        temp_path = os.path.join(temp_dir, f'{APP_NAME}_update.exe')
        
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
    Apply the update by replacing the current exe with the new one.
    
    This creates a batch script that:
    1. Waits for the current process to exit
    2. Replaces the old exe with the new one
    3. Starts the new exe
    4. Cleans up the batch script
    
    Args:
        new_exe_path: Path to the downloaded new exe
    
    Returns:
        True if the update process was started successfully.
    """
    try:
        current_exe = get_current_exe_path()
        
        # If running as a script, we can't self-update
        if not getattr(sys, 'frozen', False):
            print("Cannot apply update when running as a script.")
            print(f"New version downloaded to: {new_exe_path}")
            return False
        
        # Create a batch script to perform the update
        batch_script = os.path.join(tempfile.gettempdir(), f'{APP_NAME}_updater.bat')
        
        # Simple batch script that just waits and applies the update
        # We don't auto-restart because PyInstaller temp cleanup causes DLL errors
        script_content = f'''@echo off
title {APP_NAME} Updater
echo ========================================
echo          {APP_NAME} Updater
echo ========================================
echo.
echo Waiting for application to close...
timeout /t 3 >nul

echo.
echo Applying update...
move /Y "{new_exe_path}" "{current_exe}"
if errorlevel 1 (
    echo.
    echo ERROR: Update failed!
    echo Please close the application completely and try again.
    pause
    exit /b 1
)

echo.
echo ========================================
echo       Update applied successfully!
echo ========================================
echo.
echo Please start the application manually.
echo This window will close in 5 seconds...
timeout /t 5 >nul
exit
'''
        
        with open(batch_script, 'w') as f:
            f.write(script_content)
        
        # Start the batch script with a visible window so user can see progress
        CREATE_NEW_CONSOLE = 0x00000010
        subprocess.Popen(
            ['cmd', '/c', batch_script],
            creationflags=CREATE_NEW_CONSOLE
        )
        
        return True
        
    except Exception as e:
        print(f"Error applying update: {e}")
        return False


def get_current_version() -> str:
    """Get the current application version."""
    return VERSION
