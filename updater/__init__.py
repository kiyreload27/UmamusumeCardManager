"""
Updater module for UmamusumeCardManager
Handles checking for updates and downloading new versions from GitHub Releases.
"""

from updater.update_checker import check_for_updates, download_update, apply_update

__all__ = ['check_for_updates', 'download_update', 'apply_update']
