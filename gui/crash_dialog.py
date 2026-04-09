"""
Crash Dialog — shown when an unhandled exception occurs.
Provides a user-friendly message, the full traceback, and options to
copy the error to clipboard or open the log file.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import sys
import os
import traceback as tb_module

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    FONT_MONO_SMALL,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_MD, RADIUS_LG,
    create_styled_button,
)


class CrashDialog:
    """Modal dialog shown after an unhandled exception."""

    def __init__(self, exc_type, exc_value, exc_tb, log_path: str = None):
        self.log_path = log_path
        self.traceback_text = "".join(tb_module.format_exception(exc_type, exc_value, exc_tb))

        # Try to create a Toplevel on the running CTk root, or a standalone Tk window
        try:
            root = ctk._get_appearance_mode  # noqa – just checking ctk is usable
            self.win = ctk.CTkToplevel()
        except Exception:
            self.win = ctk.CTk()

        self.win.title("Umamusume — Unexpected Error")
        self.win.geometry("620x500")
        self.win.resizable(True, True)
        self.win.minsize(500, 400)
        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass

        self._build_ui()
        self.win.after(100, lambda: self.win.attributes("-topmost", False))

    def _build_ui(self):
        self.win.configure(fg_color=BG_DARK)

        # Header
        hdr = ctk.CTkFrame(self.win, fg_color=BG_ELEVATED, corner_radius=0)
        hdr.pack(fill=tk.X)

        ctk.CTkLabel(
            hdr, text="💥  Something went wrong",
            font=FONT_HEADER, text_color=ACCENT_ERROR
        ).pack(padx=SPACING_LG, pady=(SPACING_MD, SPACING_XS), anchor="w")

        ctk.CTkLabel(
            hdr,
            text="The application encountered an unexpected error. "
                 "You can copy the details below and send them to the developer.",
            font=FONT_SMALL, text_color=TEXT_MUTED, wraplength=560, justify="left"
        ).pack(padx=SPACING_LG, pady=(0, SPACING_MD), anchor="w")

        # Traceback box
        body = ctk.CTkFrame(self.win, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=SPACING_MD)

        ctk.CTkLabel(
            body, text="Error details:", font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, SPACING_XS))

        self.tb_box = ctk.CTkTextbox(
            body, font=FONT_MONO_SMALL,
            fg_color=BG_MEDIUM, text_color=ACCENT_ERROR,
            border_width=1, border_color=BG_LIGHT, corner_radius=RADIUS_MD,
        )
        self.tb_box.pack(fill=tk.BOTH, expand=True)
        self.tb_box.insert("1.0", self.traceback_text)
        self.tb_box.configure(state="disabled")

        # Buttons
        btn_row = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_row.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_LG))

        create_styled_button(
            btn_row, text="📋 Copy to Clipboard",
            command=self._copy, style_type="accent"
        ).pack(side=tk.LEFT, padx=(0, SPACING_SM))

        if self.log_path and os.path.exists(self.log_path):
            create_styled_button(
                btn_row, text="📄 Open Log File",
                command=self._open_log, style_type="default"
            ).pack(side=tk.LEFT, padx=(0, SPACING_SM))

        create_styled_button(
            btn_row, text="Close",
            command=self.win.destroy, style_type="ghost"
        ).pack(side=tk.RIGHT)

    def _copy(self):
        try:
            self.win.clipboard_clear()
            self.win.clipboard_append(self.traceback_text)
            self.win.update()
        except Exception:
            pass

    def _open_log(self):
        try:
            os.startfile(self.log_path)
        except Exception:
            pass

    def show(self):
        self.win.mainloop()


def show_crash_dialog(exc_type, exc_value, exc_tb, log_path: str = None):
    """Show the crash dialog. Safe to call from sys.excepthook."""
    try:
        dlg = CrashDialog(exc_type, exc_value, exc_tb, log_path)
        dlg.show()
    except Exception:
        # Last-resort fallback
        try:
            import tkinter
            from tkinter import messagebox
            r = tkinter.Tk()
            r.withdraw()
            msg = "".join(tb_module.format_exception(exc_type, exc_value, exc_tb))
            messagebox.showerror("Unexpected Error", msg[:2000])
            r.destroy()
        except Exception:
            pass
