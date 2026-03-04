"""
Update Dialog for UmamusumeCardManager
Provides a modal dialog for the update process.
Updated for CustomTkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import threading
import sys
import os
from typing import Optional, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from updater.update_checker import check_for_updates, download_update, apply_update, get_current_version
from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_MD, RADIUS_LG,
    create_styled_button
)


class UpdateDialog:
    """Modal dialog for checking and applying updates."""
    
    def __init__(self, parent: ctk.CTk, on_close_callback: Optional[Callable] = None):
        self.parent = parent
        self.on_close_callback = on_close_callback
        self.update_info = None
        self.download_thread = None
        self.is_downloading = False
        
        # Create the dialog window
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Check for Updates")
        self.dialog.geometry("520x600")
        self.dialog.resizable(True, True)
        self.dialog.minsize(480, 500)
        
        # Set transient/grab to make it modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.center_on_parent()
        
        # Set up the UI
        self.setup_ui()
        
        # Start checking for updates
        self.check_for_updates()
        
        # Handle close window event
        self.dialog.protocol("WM_DELETE_WINDOW", self.close)
    
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
        self.dialog.configure(fg_color=BG_DARK)

        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=SPACING_LG)
        
        # Title
        self.title_label = ctk.CTkLabel(
            main_frame, 
            text="🔄  Checking for Updates...",
            font=FONT_HEADER,
            text_color=ACCENT_PRIMARY
        )
        self.title_label.pack(pady=(0, SPACING_SM))
        
        # Status message
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Connecting to GitHub...",
            font=FONT_BODY,
            text_color=TEXT_MUTED,
            wraplength=460
        )
        self.status_label.pack(pady=(0, SPACING_SM))
        
        # Version info frame
        self.version_frame = ctk.CTkFrame(main_frame, fg_color=BG_MEDIUM, corner_radius=RADIUS_MD)
        self.version_frame.pack(fill=tk.X, pady=(0, SPACING_MD), padx=SPACING_XS)
        
        self.current_version_label = ctk.CTkLabel(
            self.version_frame,
            text=f"Current Version: v{get_current_version()}",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        self.current_version_label.pack(anchor='w', padx=15, pady=5)
        
        self.new_version_label = ctk.CTkLabel(
            self.version_frame,
            text="Latest Version: Checking...",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY
        )
        self.new_version_label.pack(anchor='w', padx=15, pady=5)
        
        # Release Notes Area
        self.notes_label = ctk.CTkLabel(
            main_frame,
            text="What's New:",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY
        )
        self.notes_label.pack(anchor='w', pady=(0, 5))
        
        # Text box for release notes
        self.notes_text = ctk.CTkTextbox(
            main_frame,
            height=200, 
            fg_color=BG_MEDIUM,
            text_color=TEXT_SECONDARY,
            font=FONT_SMALL,
            border_width=1,
            border_color=BG_LIGHT,
            corner_radius=RADIUS_MD
        )
        self.notes_text.pack(fill=tk.BOTH, expand=True, pady=(0, SPACING_MD))
        self.notes_text.insert("1.0", "Checking for release notes...")
        self.notes_text.configure(state=tk.DISABLED)
        
        # Progress bar (hidden initially)
        self.progress_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        )
        self.progress_label.pack(anchor='w', pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            mode='indeterminate',
            width=400
        )
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.start()
        
        # Button frame
        self.button_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=SPACING_LG, pady=SPACING_LG)
        
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
        # Pack when ready

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
        self.notes_text.configure(state=tk.NORMAL)
        self.notes_text.delete("1.0", tk.END)
        
        if self.update_info:
            # Update available!
            self.title_label.configure(text="🎉 Update Available!")
            self.status_label.configure(
                text="A new version is available.",
                text_color=ACCENT_SUCCESS
            )
            self.new_version_label.configure(
                text=f"Latest Version: {self.update_info['new_version']}",
                text_color=ACCENT_SUCCESS
            )
            
            # Show Release Notes
            notes = self.update_info.get('release_notes', 'No release notes available.')
            self.notes_text.insert(tk.END, notes)
            
            # Show update button
            self.update_button.pack(side=tk.RIGHT, padx=(0, 10))
        else:
            # Up to date or error
            self.title_label.configure(text="✅ You're Up to Date!")
            self.status_label.configure(
                text=f"You are running the latest version.",
                text_color=TEXT_SECONDARY
            )
            self.new_version_label.configure(
                text=f"Latest Version: v{get_current_version()}",
                text_color=ACCENT_SUCCESS
            )
            self.notes_text.insert(tk.END, "You are using the latest version of Umamusume Support Card Manager.\n\nEnjoy!")
            
        self.notes_text.configure(state=tk.DISABLED)
            
    def start_download(self):
        """Start downloading the update."""
        if self.is_downloading or not self.update_info:
            return
        
        self.is_downloading = True
        self.update_button.configure(state=tk.DISABLED, text="Downloading...")
        self.close_button.configure(state=tk.DISABLED)
        
        self.title_label.configure(text="⬇️ Downloading Update...")
        self.status_label.configure(text="Please wait...", text_color=TEXT_MUTED)
        
        # Configure progress bar for determinate mode
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        self.progress_bar.configure(mode='determinate')
        self.progress_bar.set(0)
        self.progress_bar.pack(fill=tk.X)
        
        def download():
            def progress_callback(downloaded, total):
                if total > 0:
                    percent = downloaded / total # 0.0 to 1.0 for CTk
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total / (1024 * 1024)
                    self.dialog.after(0, lambda: self.update_progress(percent, mb_downloaded, mb_total))
            
            download_path = download_update(self.update_info['download_url'], progress_callback)
            self.dialog.after(0, lambda: self.download_complete(download_path))
        
        self.download_thread = threading.Thread(target=download, daemon=True)
        self.download_thread.start()
    
    def update_progress(self, percent: float, downloaded_mb: float, total_mb: float):
        """Update the progress bar."""
        self.progress_bar.set(percent)
        self.progress_label.configure(text=f"Downloaded: {downloaded_mb:.1f} MB / {total_mb:.1f} MB ({int(percent*100)}%)")
    
    def download_complete(self, download_path: Optional[str]):
        """Called when the download is complete."""
        self.is_downloading = False
        
        if download_path:
            self.title_label.configure(text="✅ Download Complete!")
            self.status_label.configure(
                text="Update ready to install.",
                text_color=ACCENT_SUCCESS
            )
            
            # Change button to install
            self.update_button.configure(
                state=tk.NORMAL,
                text="🔄 Install & Restart",
                command=lambda: self.install_update(download_path)
            )
            self.close_button.configure(state=tk.NORMAL)
        else:
            self.title_label.configure(text="❌ Download Failed")
            self.status_label.configure(
                text="Failed not download update.",
                text_color=ACCENT_ERROR
            )
            self.update_button.configure(state=tk.NORMAL, text="⬇️ Retry Download")
            self.close_button.configure(state=tk.NORMAL)
    
    def install_update(self, download_path: str):
        """Install the downloaded update."""
        self.title_label.configure(text="🔄 Installing Update...")
        self.status_label.configure(text="Applying update...", text_color=TEXT_MUTED)
        self.update_button.configure(state=tk.DISABLED)
        self.close_button.configure(state=tk.DISABLED)
        
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


def show_update_dialog(parent: ctk.CTk, on_close_callback: Optional[Callable] = None) -> UpdateDialog:
    """
    Show the update dialog.
    """
    return UpdateDialog(parent, on_close_callback)
