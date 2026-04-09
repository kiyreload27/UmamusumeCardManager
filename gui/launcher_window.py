import tkinter as tk
import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    BG_ELEVATED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR,
    FONT_DISPLAY, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY,
    FONT_BODY_BOLD, FONT_SMALL, FONT_TINY, FONT_MONO,
    SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_2XL,
    RADIUS_MD, RADIUS_LG, RADIUS_XL, RADIUS_FULL,
    create_styled_button, create_card_frame
)
from gui.update_dialog import show_update_dialog

# NOTE: The Theme file doesn't have create_styled_label directly, I will use ctk.CTkLabel.

class LauncherWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Umamusume Support Card Manager - Launcher")
        self.geometry("800x480")
        self.configure(fg_color=BG_DARKEST)
        self.resizable(False, False)
        
        # Center window
        self.update_idletasks()
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        x = int(w/2 - 800/2)
        y = int(h/2 - 480/2)
        self.geometry(f"+{x}+{y}")
        
        # Setup Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.next_action = 'exit'
        self.build_ui()

    def build_ui(self):
        # Left Panel - Branding
        self.brand_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.brand_frame.grid(row=0, column=0, sticky="nsew")
        self.brand_frame.grid_columnconfigure(0, weight=1)
        self.brand_frame.grid_rowconfigure(0, weight=1)
        
        inner_brand = ctk.CTkFrame(self.brand_frame, fg_color="transparent")
        inner_brand.grid(row=0, column=0)
        
        title = ctk.CTkLabel(inner_brand, text="Umamusume\nCard Manager", font=FONT_DISPLAY, text_color=ACCENT_PRIMARY, justify="left")
        title.pack(anchor="w", pady=(0, SPACING_SM))
        
        subtitle = ctk.CTkLabel(inner_brand, text="Standalone Desktop Hub", font=FONT_BODY, text_color=TEXT_MUTED)
        subtitle.pack(anchor="w")
        
        # Right Panel - Dynamic Menu Container
        self.menu_container = ctk.CTkFrame(self, fg_color=BG_DARKEST, corner_radius=0)
        self.menu_container.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)
        self.menu_container.grid_columnconfigure(0, weight=1)
        self.menu_container.grid_rowconfigure(0, weight=1)
        
        self.show_main_menu()

    def show_main_menu(self):
        # Clear container
        for widget in self.menu_container.winfo_children():
            widget.destroy()
            
        frame = ctk.CTkFrame(self.menu_container, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(frame, text="MAIN MENU", font=FONT_SUBHEADER, text_color=TEXT_SECONDARY).pack(anchor="w", pady=(0, SPACING_XL))
        
        btn_launch = create_styled_button(frame, "▶  Launch App", style_type="accent", height=50, command=self.launch_app)
        btn_launch.pack(fill="x", pady=(0, SPACING_MD))
        
        btn_scrapers = create_styled_button(frame, "📥  Database Scrapers", style_type="default", height=50, command=self.show_scraper_menu)
        btn_scrapers.pack(fill="x", pady=(0, SPACING_MD))
        
        btn_diag = create_styled_button(frame, "🐞  Diagnostics & Logs", style_type="default", height=50, command=self.launch_diagnostics)
        btn_diag.pack(fill="x", pady=(0, SPACING_MD))

        btn_update = create_styled_button(frame, "🔄  Check for Updates", style_type="default", height=50, command=self.launch_updates)
        btn_update.pack(fill="x", pady=(0, SPACING_XL))
        
        btn_exit = create_styled_button(frame, "❌  Exit", style_type="ghost", height=40, command=self.destroy)
        btn_exit.pack(fill="x")

    def show_scraper_menu(self):
        # We will directly run the existing robust DataUpdateDialog
        from gui.data_update_dialog import DataUpdateDialog
        dialog = DataUpdateDialog(self)
        self.wait_window(dialog.dialog)

    def launch_app(self):
        self.next_action = 'app'
        self.destroy()

    def launch_diagnostics(self):
        from gui.debug_panel import DebugPanel
        dp = DebugPanel(self)
        dp.grab_set()

    def launch_updates(self):
        show_update_dialog(self)

    def run(self):
        self.mainloop()
