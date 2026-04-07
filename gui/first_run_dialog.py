"""
First-Run Dialog — shown once when the app has no card data.
Welcomes the user, explains what the app does, and offers to run
the scraper immediately (with a prerequisites checklist) or skip.
"""

import tkinter as tk
import customtkinter as ctk
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY, FONT_MONO_SMALL,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_button,
)
from db.db_queries import get_database_stats


def _is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def _check_playwright() -> tuple[bool, str]:
    """Return (available, message)."""
    try:
        import playwright  # noqa
        return True, "✅ Playwright is installed"
    except ImportError:
        return False, "❌ Playwright not installed  (run: pip install playwright)"


def _check_chromium() -> tuple[bool, str]:
    """Return (available, message). Only checked if playwright is available."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Just check that the executable path exists
            browser_path = p.chromium.executable_path
            if browser_path and os.path.exists(browser_path):
                return True, "✅ Chromium browser is installed"
            return False, "❌ Chromium not installed  (run: playwright install chromium)"
    except Exception:
        return False, "❌ Chromium not installed  (run: playwright install chromium)"


class FirstRunDialog:
    """One-time welcome dialog shown when the database has no card data."""

    def __init__(self, parent: ctk.CTk, on_complete_callback=None):
        self.parent = parent
        self.on_complete = on_complete_callback   # called when dialog is dismissed
        self._scrape_thread = None
        self._cancelled = False

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Welcome to Umamusume Support Card Manager")
        self.dialog.geometry("600x680")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self._skip)

        # Center on parent
        self.dialog.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 600) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 680) // 2
        self.dialog.geometry(f"600x680+{px}+{py}")

        self._build_ui()
        self.dialog.after(100, self.dialog.lift)

    # ───────────────────────────── UI ──────────────────────────────────

    def _build_ui(self):
        self.dialog.configure(fg_color=BG_DARK)

        # Scrollable so it fits on small screens
        scroll = ctk.CTkScrollableFrame(self.dialog, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        # ── Welcome header ──
        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.pack(fill=tk.X, padx=SPACING_LG, pady=(SPACING_LG, SPACING_MD))

        ctk.CTkLabel(
            hdr, text="🐴  Welcome!",
            font=FONT_DISPLAY, text_color=ACCENT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            hdr,
            text="Umamusume Support Card Manager helps you track your card collection, "
                 "build decks, search skills and effects, and plan your race calendar —\n"
                 "all in one place.",
            font=FONT_BODY, text_color=TEXT_SECONDARY,
            justify="left", wraplength=540
        ).pack(anchor="w", pady=(SPACING_SM, 0))

        # ── Feature highlights ──
        feat_frame = ctk.CTkFrame(
            scroll, fg_color=BG_MEDIUM, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        feat_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_MD))

        features = [
            ("🃏", "Card Library",    "Browse & own your support cards"),
            ("🎴", "Deck Builder",    "Build optimised 6-card decks"),
            ("🔎", "Effect Search",   "Find cards by specific effects"),
            ("📅", "Race Calendar",   "Plan your Uma's race schedule"),
            ("🏟", "Track Browser",   "View all racetracks and courses"),
        ]
        for icon, title, desc in features:
            row = ctk.CTkFrame(feat_frame, fg_color="transparent")
            row.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_XS)
            ctk.CTkLabel(row, text=icon, font=FONT_HEADER, text_color=ACCENT_PRIMARY, width=34).pack(side=tk.LEFT)
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side=tk.LEFT, padx=SPACING_SM)
            ctk.CTkLabel(col, text=title, font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(col, text=desc, font=FONT_TINY, text_color=TEXT_MUTED).pack(anchor="w")

        ctk.CTkFrame(feat_frame, fg_color="transparent", height=SPACING_SM).pack()

        # ── Data scraper section ──
        ctk.CTkLabel(
            scroll, text="📥  Get Card Data",
            font=FONT_SUBHEADER, text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=SPACING_LG, pady=(0, SPACING_XS))

        ctk.CTkLabel(
            scroll,
            text="The app fetches card data from GameTora. "
                 "You need to run the scraper once to populate your database.",
            font=FONT_SMALL, text_color=TEXT_MUTED, wraplength=540, justify="left"
        ).pack(anchor="w", padx=SPACING_LG, pady=(0, SPACING_SM))

        if False:  # Removed frozen blockade
            pass
        else:
            self._build_scraper_section(scroll)

        # ── Bottom buttons ──
        btn_bar = ctk.CTkFrame(self.dialog, fg_color=BG_DARKEST, corner_radius=0)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._skip_btn = create_styled_button(
            btn_bar, text="Skip — I'll set up later",
            command=self._skip, style_type="ghost"
        )
        self._skip_btn.pack(side=tk.RIGHT, padx=SPACING_LG, pady=SPACING_MD)

    def _install_chromium(self):
        """Thread to run playwright install chromium natively."""
        self._scrape_btn.configure(state="disabled")
        self._recheck_btn.configure(state="disabled")
        self._skip_btn.configure(state="disabled")
        self._prog_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))
        self._prog_bar.start()
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        
        self._set_status("Installing Chromium browser (this may take a few minutes)...")
        self._log("Downloading Chromium via Playwright...\n")

        def _worker():
            try:
                from playwright._impl._driver import compute_driver_executable
                import subprocess
                driver = compute_driver_executable()
                
                cmd = [driver[0], driver[1], "install", "chromium"]
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    text=True, encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                for line in iter(process.stdout.readline, ''):
                    self._log(line.rstrip())
                    
                process.stdout.close()
                process.wait()
                
                if process.returncode == 0:
                    self._log("\n✅ Chromium installed successfully!")
                    self.dialog.after(1000, self._install_success)
                else:
                    self._log(f"\n❌ Installation failed with code {process.returncode}")
                    self.dialog.after(0, self._install_failed)
                    
            except Exception as e:
                self._log(f"\n❌ Error starting installer: {e}")
                self.dialog.after(0, self._install_failed)

        threading.Thread(target=_worker, daemon=True).start()

    def _install_success(self):
        self._prog_bar.stop()
        self.dialog.destroy()
        if hasattr(self.parent, "show_first_run_dialog"):
            # Re-spawn dialogue cleanly
            from gui.first_run_dialog import show_first_run_dialog
            show_first_run_dialog(self.parent, self.on_complete)
            
    def _install_failed(self):
        self._prog_bar.stop()
        self._set_status("Installation failed. See log.")
        self._skip_btn.configure(state="normal")

    def _build_scraper_section(self, parent):
        """Show prerequisite checker and Scrape Now button."""
        prereq_frame = ctk.CTkFrame(
            parent, fg_color=BG_MEDIUM, corner_radius=RADIUS_LG,
            border_width=1, border_color=BG_LIGHT
        )
        prereq_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))

        inner = ctk.CTkFrame(prereq_frame, fg_color="transparent")
        inner.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_LG)

        ctk.CTkLabel(
            inner, text="Prerequisites",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, SPACING_XS))

        # Check prerequisites
        pw_ok, pw_msg = _check_playwright()
        self._pw_label = ctk.CTkLabel(
            inner, text=pw_msg, font=FONT_SMALL,
            text_color=ACCENT_SUCCESS if pw_ok else ACCENT_ERROR
        )
        self._pw_label.pack(anchor="w")

        if pw_ok:
            cr_ok, cr_msg = _check_chromium()
        else:
            cr_ok, cr_msg = False, "⬜ Chromium (missing)"

        self._cr_label = ctk.CTkLabel(
            inner, text=cr_msg, font=FONT_SMALL,
            text_color=ACCENT_SUCCESS if cr_ok else (ACCENT_ERROR if pw_ok else TEXT_DISABLED)
        )
        self._cr_label.pack(anchor="w", pady=(SPACING_XS, 0))

        if not pw_ok or not cr_ok:
            info_frame = ctk.CTkFrame(inner, fg_color=BG_LIGHT, corner_radius=RADIUS_SM)
            info_frame.pack(fill=tk.X, pady=(SPACING_SM, 0), ipadx=SPACING_MD, ipady=SPACING_SM)
            
            if pw_ok and not cr_ok:
                ctk.CTkLabel(
                    info_frame,
                    text="Chromium is required to scrape game data.",
                    font=FONT_SMALL, text_color=TEXT_MUTED, justify="left"
                ).pack(side=tk.LEFT, padx=SPACING_SM)
                
                self._install_btn = create_styled_button(
                    info_frame, text="Install Browser", command=self._install_chromium,
                    style_type="accent", height=28
                )
                self._install_btn.pack(side=tk.RIGHT, padx=SPACING_SM)
            else:
                ctk.CTkLabel(
                    info_frame,
                    text="Run these commands in a terminal, then re-open the app:\n  pip install playwright\n  playwright install chromium",
                    font=FONT_MONO_SMALL, text_color=TEXT_MUTED, justify="left"
                ).pack(fill=tk.X, padx=SPACING_SM)

        # Scrape button (only enabled if prereqs are met)
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_MD))

        self._recheck_btn = create_styled_button(
            btn_row, text="🔄 Re-check",
            command=self._recheck, style_type="default", height=36
        )
        self._recheck_btn.pack(side=tk.LEFT, padx=(0, SPACING_SM))

        self._scrape_btn = create_styled_button(
            btn_row, text="▶  Scrape Card Data Now",
            command=self._start_scrape,
            style_type="accent" if (pw_ok and cr_ok) else "default",
            height=36,
            state="normal" if (pw_ok and cr_ok) else "disabled"
        )
        self._scrape_btn.pack(side=tk.LEFT)
        self._prereqs_ok = pw_ok and cr_ok

        # Progress area
        self._prog_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._prog_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))
        self._prog_frame.pack_forget()  # hidden initially

        self._prog_label = ctk.CTkLabel(
            self._prog_frame, text="Scraping support card data from GameTora...",
            font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self._prog_label.pack(anchor="w", pady=(0, SPACING_XS))

        self._prog_bar = ctk.CTkProgressBar(self._prog_frame, mode="indeterminate")
        self._prog_bar.pack(fill=tk.X)

        self._log_box = ctk.CTkTextbox(
            self._prog_frame, height=120,
            font=FONT_MONO_SMALL, fg_color=BG_MEDIUM,
            text_color=TEXT_SECONDARY, corner_radius=RADIUS_MD
        )
        self._log_box.pack(fill=tk.X, pady=(SPACING_XS, 0))
        self._log_box.configure(state="disabled")

    def _recheck(self):
        """Re-evaluate prerequisites and update labels."""
        pw_ok, pw_msg = _check_playwright()
        self._pw_label.configure(
            text=pw_msg,
            text_color=ACCENT_SUCCESS if pw_ok else ACCENT_ERROR
        )
        if pw_ok:
            cr_ok, cr_msg = _check_chromium()
        else:
            cr_ok, cr_msg = False, "⬜ Chromium (check after installing Playwright)"

        self._cr_label.configure(
            text=cr_msg,
            text_color=ACCENT_SUCCESS if cr_ok else (ACCENT_ERROR if pw_ok else TEXT_DISABLED)
        )
        self._prereqs_ok = pw_ok and cr_ok
        self._scrape_btn.configure(
            state="normal" if self._prereqs_ok else "disabled",
            fg_color=ACCENT_PRIMARY if self._prereqs_ok else BG_LIGHT
        )

    def _start_scrape(self):
        """Run all scrapers in a background thread."""
        if self._scrape_thread and self._scrape_thread.is_alive():
            return

        self._scrape_btn.configure(state="disabled", text="Scraping…")
        self._recheck_btn.configure(state="disabled")
        self._skip_btn.configure(state="disabled")
        self._prog_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))
        self._prog_bar.start()

        self._scrape_thread = threading.Thread(target=self._run_scrapers, daemon=True)
        self._scrape_thread.start()

    def _log(self, msg: str):
        """Append a line to the in-dialog log box (thread-safe via after)."""
        def _append():
            self._log_box.configure(state="normal")
            self._log_box.insert("end", msg + "\n")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        try:
            self.dialog.after(0, _append)
        except Exception:
            pass

    def _set_status(self, msg: str):
        try:
            self.dialog.after(0, lambda: self._prog_label.configure(text=msg))
        except Exception:
            pass

    def _run_scrapers(self):
        """Background thread — runs each scraper sequentially."""
        scrapers = [
            ("Support Cards", "scraper.gametora_scraper", "run_scraper"),
            ("Racetracks",    "scraper.track_scraper",    "run_track_scraper"),
            ("Characters",    "scraper.character_scraper","run_character_scraper"),
            ("Races",         "scraper.race_scraper",     "run_race_scraper"),
        ]
        errors = []
        for label, module_path, fn_name in scrapers:
            if self._cancelled:
                break
            self._set_status(f"Scraping {label}…")
            self._log(f"\n► Starting {label} scraper…")
            try:
                import importlib
                mod = importlib.import_module(module_path)
                fn = getattr(mod, fn_name)
                fn()
                self._log(f"  ✅ {label} done")
            except Exception as exc:
                self._log(f"  ❌ {label} failed: {exc}")
                errors.append(f"{label}: {exc}")

        self.dialog.after(0, lambda: self._scrape_complete(errors))

    def _scrape_complete(self, errors):
        self._prog_bar.stop()
        if errors:
            self._set_status(f"Completed with {len(errors)} error(s) — see log above")
            self._scrape_btn.configure(state="normal", text="▶  Retry")
            self._skip_btn.configure(state="normal")
        else:
            self._set_status("✅ All done! Your database is ready.")
            self._scrape_btn.configure(state="disabled", text="✅ Complete")
            self._skip_btn.configure(text="Open App →", state="normal",
                                     fg_color=ACCENT_PRIMARY, text_color=TEXT_MUTED)

    # ───────────────────────────── Actions ─────────────────────────────

    def _skip(self):
        self._cancelled = True
        self.dialog.destroy()
        if self.on_complete:
            self.on_complete()


def should_show_first_run() -> bool:
    """Return True if the app should display the first-run dialog."""
    try:
        stats = get_database_stats()
        return stats.get('total_cards', 0) == 0
    except Exception:
        return False


def show_first_run_dialog(parent: ctk.CTk, on_complete_callback=None):
    """Show the welcome dialog. Caller should check should_show_first_run() first."""
    return FirstRunDialog(parent, on_complete_callback)
