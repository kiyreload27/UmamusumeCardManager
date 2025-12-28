"""
Update Dialog for UmamusumeCardManager
Provides a modal dialog for the update process.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import webbrowser
from typing import Optional, Callable

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from updater.update_checker import check_for_updates, download_update, apply_update, get_current_version
from gui.theme import (
    BG_DARK, BG_DARKEST, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL,
    create_styled_button
)


class UpdateDialog:
    """Modal dialog for checking and applying updates."""
    
    def __init__(self, parent: tk.Tk, on_close_callback: Optional[Callable] = None):
        self.parent = parent
        self.on_close_callback = on_close_callback
        self.update_info = None
        self.download_thread = None
        self.is_downloading = False
        
        # Create the dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Check for Updates")
        self.dialog.geometry("520x600")
        self.dialog.resizable(True, True)
        self.dialog.minsize(480, 500)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.center_on_parent()
        
        self.dialog.configure(bg=BG_DARK)
        
        # Set up the UI
        self.setup_ui()
        
        # Start checking for updates
        self.check_for_updates()
    
    def center_on_parent(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        
        dialog_w = 520
        dialog_h = 600
        
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        
        self.dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
    
    def setup_ui(self):
        """Set up the dialog UI."""
        # Button frame (Create first to pack at bottom)
        self.button_frame = tk.Frame(self.dialog, bg=BG_DARK, pady=20, padx=20)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Close button
        self.close_button = create_styled_button(
            self.button_frame,
            text="Close",
            command=self.close,
            style_type='default'
        )
        self.close_button.pack(side=tk.RIGHT)
        
        # Update button (hidden initially)
        self.update_button = create_styled_button(
            self.button_frame,
            text="⬇️ Download & Install",
            command=self.start_download,
            style_type='accent'
        )
        # We don't pack it yet
        
        # Main container
        main_frame = tk.Frame(self.dialog, bg=BG_DARK, padx=25, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        self.title_label = tk.Label(
            main_frame, 
            text="🔄 Checking for Updates...",
            font=FONT_HEADER,
            bg=BG_DARK,
            fg=ACCENT_PRIMARY
        )
        self.title_label.pack(pady=(0, 10))
        
        # Status message
        self.status_label = tk.Label(
            main_frame,
            text="Connecting to GitHub...",
            font=FONT_BODY,
            bg=BG_DARK,
            fg=TEXT_MUTED,
            wraplength=460
        )
        self.status_label.pack(pady=(0, 10))
        
        # Version info frame
        self.version_frame = tk.Frame(main_frame, bg=BG_MEDIUM, padx=15, pady=10)
        self.version_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.current_version_label = tk.Label(
            self.version_frame,
            text=f"Current Version: v{get_current_version()}",
            font=FONT_BODY,
            bg=BG_MEDIUM,
            fg=TEXT_SECONDARY
        )
        self.current_version_label.pack(anchor='w')
        
        self.new_version_label = tk.Label(
            self.version_frame,
            text="Latest Version: Checking...",
            font=FONT_BODY,
            bg=BG_MEDIUM,
            fg=TEXT_SECONDARY
        )
        self.new_version_label.pack(anchor='w')
        
        # Release Notes Area
        self.notes_label = tk.Label(
            main_frame,
            text="What's New:",
            font=FONT_BODY_BOLD,
            bg=BG_DARK,
            fg=TEXT_PRIMARY
        )
        self.notes_label.pack(anchor='w', pady=(0, 5))
        
        # Text box for release notes
        self.notes_text = scrolledtext.ScrolledText(
            main_frame,
            height=10, 
            bg=BG_MEDIUM,
            fg=TEXT_SECONDARY,
            font=FONT_SMALL,
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10
        )
        self.notes_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        self.notes_text.insert(tk.END, "Checking for release notes...")
        self.notes_text.config(state=tk.DISABLED)
        
        # Progress bar (hidden initially)
        self.progress_frame = tk.Frame(main_frame, bg=BG_DARK)
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            font=FONT_SMALL,
            bg=BG_DARK,
            fg=TEXT_MUTED
        )
        self.progress_label.pack(anchor='w', pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='indeterminate',
            length=460
        )
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.start(10)

    def check_for_updates(self):
        """Check for updates in a background thread."""
        def check():
            self.update_info = check_for_updates()
            self.dialog.after(0, self.update_check_complete)
        
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
    
    def update_check_complete(self):
        """Called when the update check is complete."""
        self.progress_bar.stop()
        self.progress_frame.pack_forget() # Hide progress bar when check is done
        
        # Enable text box to update it
        self.notes_text.config(state=tk.NORMAL)
        self.notes_text.delete(1.0, tk.END)
        
        if self.update_info:
            # Update available!
            self.title_label.config(text="🎉 Update Available!")
            self.status_label.config(
                text="A new version is available.",
                fg=ACCENT_SUCCESS
            )
            self.new_version_label.config(
                text=f"Latest Version: {self.update_info['new_version']}",
                fg=ACCENT_SUCCESS
            )
            
            # Show Release Notes
            notes = self.update_info.get('release_notes', 'No release notes available.')
            self.notes_text.insert(tk.END, notes)
            
            # Show update button
            self.update_button.pack(side=tk.RIGHT, padx=(0, 10))
        else:
            # Up to date or error
            self.title_label.config(text="✅ You're Up to Date!")
            self.status_label.config(
                text=f"You are running the latest version.",
                fg=TEXT_SECONDARY
            )
            self.new_version_label.config(
                text=f"Latest Version: v{get_current_version()}",
                fg=ACCENT_SUCCESS
            )
            self.notes_text.insert(tk.END, "You are using the latest version of Umamusume Support Card Manager.\n\nEnjoy!")
            
        self.notes_text.config(state=tk.DISABLED)
            
    def start_download(self):
        """Start downloading the update."""
        if self.is_downloading or not self.update_info:
            return
        
        self.is_downloading = True
        self.update_button.config(state=tk.DISABLED, text="Downloading...")
        self.close_button.config(state=tk.DISABLED)
        
        self.title_label.config(text="⬇️ Downloading Update...")
        self.status_label.config(text="Please wait...", fg=TEXT_MUTED)
        
        # Configure progress bar for determinate mode
        self.progress_frame.pack(fill=tk.X, pady=(0, 10)) # Show progress frame again
        self.progress_bar.config(mode='determinate', maximum=100)
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar['value'] = 0
        
        def download():
            def progress_callback(downloaded, total):
                if total > 0:
                    percent = int((downloaded / total) * 100)
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total / (1024 * 1024)
                    self.dialog.after(0, lambda: self.update_progress(percent, mb_downloaded, mb_total))
            
            download_path = download_update(self.update_info['download_url'], progress_callback)
            self.dialog.after(0, lambda: self.download_complete(download_path))
        
        self.download_thread = threading.Thread(target=download, daemon=True)
        self.download_thread.start()
    
    def update_progress(self, percent: int, downloaded_mb: float, total_mb: float):
        """Update the progress bar."""
        self.progress_bar['value'] = percent
        self.progress_label.config(text=f"Downloaded: {downloaded_mb:.1f} MB / {total_mb:.1f} MB ({percent}%)")
    
    def download_complete(self, download_path: Optional[str]):
        """Called when the download is complete."""
        self.is_downloading = False
        
        if download_path:
            self.title_label.config(text="✅ Download Complete!")
            self.status_label.config(
                text="Update ready to install.",
                fg=ACCENT_SUCCESS
            )
            
            # Change button to install
            self.update_button.config(
                state=tk.NORMAL,
                text="🔄 Install & Restart",
                command=lambda: self.install_update(download_path)
            )
            self.close_button.config(state=tk.NORMAL)
        else:
            self.title_label.config(text="❌ Download Failed")
            self.status_label.config(
                text="Failed not download update.",
                fg=ACCENT_ERROR
            )
            self.update_button.config(state=tk.NORMAL, text="⬇️ Retry Download")
            self.close_button.config(state=tk.NORMAL)
    
    def install_update(self, download_path: str):
        """Install the downloaded update."""
        self.title_label.config(text="🔄 Installing Update...")
        self.status_label.config(text="Applying update...", fg=TEXT_MUTED)
        self.update_button.config(state=tk.DISABLED)
        self.close_button.config(state=tk.DISABLED)
        
        if apply_update(download_path):
            # Exit the application - the updater script will restart it
            self.dialog.after(1000, lambda: self.parent.quit())
        else:
            messagebox.showinfo(
                "Manual Update Required",
                f"The update was downloaded but cannot be applied automatically.\n\n"
                f"Downloaded file location:\n{download_path}\n\n"
                f"Please replace the current executable manually.",
                parent=self.dialog
            )
            self.close()

    
    def close(self):
        """Close the dialog."""
        if self.on_close_callback:
            self.on_close_callback()
        self.dialog.destroy()


def show_update_dialog(parent: tk.Tk, on_close_callback: Optional[Callable] = None) -> UpdateDialog:
    """
    Show the update dialog.
    
    Args:
        parent: The parent Tk window
        on_close_callback: Optional callback when dialog is closed
    
    Returns:
        The UpdateDialog instance
    """
    return UpdateDialog(parent, on_close_callback)
