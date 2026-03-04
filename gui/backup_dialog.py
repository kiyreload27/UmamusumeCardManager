"""
Backup & Restore Dialog
Export/import user data (owned cards, decks, notes/tags) as JSON files
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import export_user_data, import_user_data
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_button
)


class BackupDialog(ctk.CTkToplevel):
    """Dialog for exporting and importing user data backups"""

    def __init__(self, parent, on_restore_callback=None):
        super().__init__(parent)
        self.title("Backup & Restore")
        self.geometry("480x500")
        self.resizable(False, False)
        self.on_restore = on_restore_callback

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.after(100, self.lift)

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        header.pack(fill=tk.X)

        ctk.CTkLabel(
            header, text="💾  Backup & Restore",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(padx=SPACING_LG, pady=SPACING_LG)

        ctk.CTkLabel(
            header, text="Export your owned cards, decks, and notes to a file,\nor restore from a previous backup.",
            font=FONT_SMALL, text_color=TEXT_MUTED, justify="left"
        ).pack(padx=SPACING_LG, pady=(0, SPACING_LG))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=SPACING_LG)

        # === Export Section ===
        export_frame = ctk.CTkFrame(content, fg_color=BG_DARK, corner_radius=RADIUS_MD,
                                     border_width=1, border_color=BG_LIGHT)
        export_frame.pack(fill=tk.X, pady=(0, SPACING_MD))

        export_inner = ctk.CTkFrame(export_frame, fg_color="transparent")
        export_inner.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_LG)

        ctk.CTkLabel(
            export_inner, text="📤  Export Backup",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            export_inner, text="Save your owned cards, decks, and notes to a JSON file.",
            font=FONT_TINY, text_color=TEXT_MUTED
        ).pack(anchor="w", pady=(SPACING_XS, SPACING_SM))

        create_styled_button(
            export_inner, text="Export to File...",
            command=self._export, style_type='accent',
            width=180, height=36
        ).pack(anchor="w")

        # === Import Section ===
        import_frame = ctk.CTkFrame(content, fg_color=BG_DARK, corner_radius=RADIUS_MD,
                                     border_width=1, border_color=BG_LIGHT)
        import_frame.pack(fill=tk.X, pady=(0, SPACING_MD))

        import_inner = ctk.CTkFrame(import_frame, fg_color="transparent")
        import_inner.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_LG)

        ctk.CTkLabel(
            import_inner, text="📥  Restore from Backup",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            import_inner, text="Load a backup file. This will REPLACE all existing user data.",
            font=FONT_TINY, text_color=ACCENT_WARNING
        ).pack(anchor="w", pady=(SPACING_XS, SPACING_SM))

        ctk.CTkButton(
            import_inner, text="📂  Restore from File...",
            command=self._import,
            fg_color=BG_ELEVATED, hover_color=BG_HIGHLIGHT,
            text_color=ACCENT_WARNING, border_color=ACCENT_WARNING,
            border_width=1, corner_radius=RADIUS_MD,
            font=FONT_BODY_BOLD, width=200, height=36
        ).pack(anchor="w")

        # === Status ===
        self.status_label = ctk.CTkLabel(
            content, text="", font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self.status_label.pack(fill=tk.X, pady=(SPACING_SM, 0))

        # Close button
        create_styled_button(
            content, text="Close", command=self.destroy,
            style_type='ghost', width=100, height=32
        ).pack(anchor="e", pady=(SPACING_SM, 0))

    def _export(self):
        """Export user data to a JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"uma_backup_{timestamp}.json"

        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Export Backup",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=default_name
        )

        if not filepath:
            return

        try:
            data = export_user_data()
            data['_meta'] = {
                'app': 'UmamusumeCardManager',
                'exported_at': datetime.now().isoformat(),
                'version': '17.0.0'
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            owned_count = len(data.get('owned_cards', []))
            deck_count = len(data.get('decks', []))
            notes_count = len(data.get('notes', []))

            self.status_label.configure(
                text=f"✅ Exported: {owned_count} owned cards, {deck_count} decks, {notes_count} notes",
                text_color=ACCENT_SUCCESS
            )
        except Exception as e:
            self.status_label.configure(
                text=f"❌ Export failed: {str(e)}",
                text_color=ACCENT_ERROR
            )

    def _import(self):
        """Import user data from a JSON file"""
        filepath = filedialog.askopenfilename(
            parent=self,
            title="Import Backup",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.status_label.configure(
                text=f"❌ Invalid backup file: {str(e)}",
                text_color=ACCENT_ERROR
            )
            return

        # Confirm overwrite
        owned = len(data.get('owned_cards', []))
        decks = len(data.get('decks', []))
        notes = len(data.get('notes', []))
        meta = data.get('_meta', {})
        export_date = meta.get('exported_at', 'Unknown')

        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"This will REPLACE all your current data with:\n\n"
            f"  • {owned} owned cards\n"
            f"  • {decks} decks\n"
            f"  • {notes} notes/tags\n\n"
            f"Exported: {export_date}\n\n"
            f"Are you sure? This cannot be undone.",
            parent=self
        )

        if not confirm:
            return

        try:
            summary = import_user_data(data)
            self.status_label.configure(
                text=f"✅ Restored: {summary['owned']} cards, {summary['decks']} decks, "
                     f"{summary['notes']} notes ({summary['skipped']} skipped)",
                text_color=ACCENT_SUCCESS
            )
            if self.on_restore:
                self.on_restore()
        except Exception as e:
            self.status_label.configure(
                text=f"❌ Restore failed: {str(e)}",
                text_color=ACCENT_ERROR
            )


def show_backup_dialog(parent, on_restore_callback=None):
    """Convenience function to show the backup dialog"""
    BackupDialog(parent, on_restore_callback)
