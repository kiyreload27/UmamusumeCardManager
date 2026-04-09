"""
Data Update Dialog — allows users to re-run any scraper from within the app.
Accessible via the "📥 Update Data" sidebar button.
Shows last-run timestamps, prerequisite checks and a live log console.
"""

import tkinter as tk
import customtkinter as ctk
import threading
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_playwright import get_persistent_browsers_path, ensure_playwright_browsers_path
# Ensure the env var is set in this process too (in case dialog is imported before main.py sets it)
ensure_playwright_browsers_path()

from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_ERROR, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    FONT_MONO_SMALL,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_button,
)


def _is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def _check_playwright() -> tuple[bool, str]:
    try:
        import playwright  # noqa
        return True, "✅ Playwright installed"
    except ImportError:
        return False, "❌ Playwright not installed"


def _check_chromium() -> tuple[bool, str]:
    """Check if Chromium is installed at our persistent browsers path."""
    browsers_root = get_persistent_browsers_path()
    # Fast path: walk the persistent dir looking for the chromium executable
    if os.path.isdir(browsers_root):
        for dirpath, dirnames, filenames in os.walk(browsers_root):
            for fname in filenames:
                if fname.lower() in ("chrome.exe", "chromium.exe",
                                     "chrome-headless-shell.exe",
                                     "chrome", "chromium"):
                    return True, "✅ Chromium installed"
    # Slow path: ask Playwright directly (may fail in frozen EXE, but worth trying)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
            if path and os.path.exists(path):
                return True, "✅ Chromium installed"
    except Exception:
        pass
    return False, "❌ Chromium not installed"


def _get_scraper_timestamps() -> dict:
    """Fetch last-run timestamps from scraper_meta table."""
    try:
        from db.db_queries import get_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT scraper_type, last_run_timestamp FROM scraper_meta")
        rows = {r[0]: r[1] for r in cur.fetchall()}
        conn.close()
        return rows
    except Exception:
        return {}


def _fmt_ts(ts: str | None) -> str:
    if not ts:
        return "Never run"
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d  %H:%M")
    except Exception:
        return ts


# ─────────────────────────────────────────────────────────────────────────────
# Scraper descriptors
# ─────────────────────────────────────────────────────────────────────────────

SCRAPERS = [
    {
        "key":    "cards",
        "label":  "Support Cards",
        "icon":   "🃏",
        "desc":   "All support card stats, effects, hints and events from GameTora",
        "module": "scraper.gametora_scraper",
        "fn":     "run_scraper",
        "time_key": "cards",
    },
    {
        "key":    "tracks",
        "label":  "Racetracks",
        "icon":   "🏟",
        "desc":   "Track names, locations, course distances, surfaces and phases",
        "module": "scraper.track_scraper",
        "fn":     "run_track_scraper",
        "time_key": "tracks",
    },
    {
        "key":    "characters",
        "label":  "Characters",
        "icon":   "🐴",
        "desc":   "Character aptitude data (surface, distance, running style)",
        "module": "scraper.character_scraper",
        "fn":     "run_character_scraper",
        "time_key": "characters",
    },
    {
        "key":    "races",
        "label":  "Races",
        "icon":   "🏁",
        "desc":   "Individual race details, grades, terrain and badge images",
        "module": "scraper.race_scraper",
        "fn":     "run_race_scraper",
        "time_key": "races",
    },
]


class DataUpdateDialog:
    """In-app scraper launcher dialog."""

    def __init__(self, parent: ctk.CTk, on_complete_callback=None):
        self.parent = parent
        self.on_complete = on_complete_callback
        self._running = False
        self._cancelled = False
        self._thread = None

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Update Card Data")
        self.dialog.geometry("620x700")
        self.dialog.resizable(True, True)
        self.dialog.minsize(560, 560)
        self.dialog.transient(parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self._close)

        # Center on parent
        self.dialog.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 620) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 700) // 2
        self.dialog.geometry(f"620x700+{px}+{py}")

        self._build_ui()
        self.dialog.after(100, self.dialog.lift)

    # ─────────────────────────────────── UI ──────────────────────────────────

    def _build_ui(self):
        self.dialog.configure(fg_color=BG_DARK)

        # Header
        hdr = ctk.CTkFrame(self.dialog, fg_color=BG_ELEVATED, corner_radius=0)
        hdr.pack(fill=tk.X)

        ctk.CTkLabel(
            hdr, text="📥  Update Card Data",
            font=FONT_HEADER, text_color=ACCENT_PRIMARY
        ).pack(anchor="w", padx=SPACING_LG, pady=(SPACING_MD, SPACING_XS))

        ctk.CTkLabel(
            hdr,
            text="Re-run any scraper to fetch the latest data from GameTora.\n"
                 "Your owned cards, decks, and notes are never affected.",
            font=FONT_SMALL, text_color=TEXT_MUTED, justify="left"
        ).pack(anchor="w", padx=SPACING_LG, pady=(0, SPACING_MD))

        # Body (scrollable)
        body = ctk.CTkScrollableFrame(self.dialog, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=SPACING_LG, pady=SPACING_MD)

        if False:  # Removed frozen blockade
            pass
        else:
            self._build_prereqs(body)
            self._build_scraper_cards(body)

        # Progress area (hidden until a scraper starts)
        self._prog_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        self._prog_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM))
        self._prog_frame.pack_forget()

        self._prog_label = ctk.CTkLabel(
            self._prog_frame, text="", font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self._prog_label.pack(anchor="w", pady=(0, SPACING_XS))

        self._prog_bar = ctk.CTkProgressBar(self._prog_frame, mode="indeterminate")
        self._prog_bar.pack(fill=tk.X)

        self._log_box = ctk.CTkTextbox(
            self._prog_frame, height=130,
            font=FONT_MONO_SMALL, fg_color=BG_DARKEST,
            text_color=TEXT_SECONDARY, corner_radius=RADIUS_MD
        )
        self._log_box.pack(fill=tk.X, pady=(SPACING_XS, 0))
        self._log_box.configure(state="disabled")

        # Footer buttons
        footer = ctk.CTkFrame(self.dialog, fg_color=BG_DARKEST, corner_radius=0)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        self._close_btn = create_styled_button(
            footer, text="Close", command=self._close, style_type="ghost"
        )
        self._close_btn.pack(side=tk.RIGHT, padx=SPACING_LG, pady=SPACING_MD)

    def _install_chromium(self):
        """Thread to run playwright install chromium natively."""
        self._running = True
        self._prog_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM), before=self._close_btn.master)
        self._prog_bar.start()
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        
        self._set_status("Installing Chromium browser (this may take a few minutes)...")
        self._log("Downloading Chromium via Playwright...\n")
        
        if hasattr(self, '_install_btn'):
            self._install_btn.configure(state="disabled")
        self._close_btn.configure(state="disabled")

        def _worker():
            try:
                from playwright._impl._driver import compute_driver_executable
                import subprocess
                driver = compute_driver_executable()
                
                # Build environment that pins Playwright to our persistent browser dir
                env = os.environ.copy()
                env["PLAYWRIGHT_BROWSERS_PATH"] = get_persistent_browsers_path()

                # Execute the Node driver directly
                cmd = [driver[0], driver[1], "install", "--force", "chromium"]
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
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
        self._running = False
        self._prog_bar.stop()
        parent = self.parent
        on_complete = self.on_complete
        self.dialog.destroy()
        # Re-open a fresh dialog so prereq check re-runs and shows updated status
        DataUpdateDialog(parent, on_complete)
            
    def _install_failed(self):
        self._running = False
        self._prog_bar.stop()
        self._set_status("Installation failed. See log.")
        self._close_btn.configure(state="normal")

    def _build_prereqs(self, parent):
        """Show prerequisite status badges."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, pady=(0, SPACING_SM))

        pw_ok, pw_msg = _check_playwright()
        cr_ok, cr_msg = _check_chromium() if pw_ok else (False, "⬜ Chromium  (missing)")

        self._prereqs_ok = pw_ok and cr_ok

        ctk.CTkLabel(
            row, text=pw_msg, font=FONT_SMALL,
            text_color=ACCENT_SUCCESS if pw_ok else ACCENT_ERROR
        ).pack(side=tk.LEFT, padx=(0, SPACING_MD))

        ctk.CTkLabel(
            row, text=cr_msg, font=FONT_SMALL,
            text_color=ACCENT_SUCCESS if cr_ok else (ACCENT_ERROR if pw_ok else TEXT_DISABLED)
        ).pack(side=tk.LEFT)

        if not self._prereqs_ok:
            info_frame = ctk.CTkFrame(parent, fg_color=BG_LIGHT, corner_radius=RADIUS_SM)
            info_frame.pack(fill=tk.X, pady=(0, SPACING_MD), ipadx=SPACING_MD, ipady=SPACING_SM)
            
            if pw_ok and not cr_ok:
                ctk.CTkLabel(
                    info_frame,
                    text="Chromium browser is required to scrape game data.",
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
                    text="Install prerequisites then re-open this dialog:\n  pip install playwright    →    playwright install chromium",
                    font=FONT_MONO_SMALL, text_color=TEXT_MUTED, justify="left"
                ).pack(fill=tk.X, padx=SPACING_SM)

    def _build_scraper_cards(self, parent):
        """Render one card per scraper with last-run time and a run button."""
        timestamps = _get_scraper_timestamps()

        # "Run All" banner
        run_all_frame = ctk.CTkFrame(
            parent, fg_color=BG_MEDIUM, corner_radius=RADIUS_LG,
            border_width=1, border_color=ACCENT_PRIMARY
        )
        run_all_frame.pack(fill=tk.X, pady=(0, SPACING_MD))

        run_all_inner = ctk.CTkFrame(run_all_frame, fg_color="transparent")
        run_all_inner.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_MD)

        ctk.CTkLabel(
            run_all_inner, text="Run All Scrapers",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        self._run_all_btn = create_styled_button(
            run_all_inner, text="▶  Run All",
            command=lambda: self._start([s for s in SCRAPERS]),
            style_type="accent" if self._prereqs_ok else "default",
            height=34, width=110,
            state="normal" if self._prereqs_ok else "disabled"
        )
        self._run_all_btn.pack(side=tk.RIGHT)

        ctk.CTkLabel(
            run_all_inner,
            text="Runs cards → tracks → characters → races in sequence",
            font=FONT_TINY, text_color=TEXT_MUTED
        ).pack(side=tk.LEFT, padx=(SPACING_SM, 0))

        # Individual scraper cards
        self._scraper_btns = {}
        for s in SCRAPERS:
            ts = _fmt_ts(timestamps.get(s["time_key"]))
            card = ctk.CTkFrame(
                parent, fg_color=BG_MEDIUM, corner_radius=RADIUS_MD,
                border_width=1, border_color=BG_LIGHT
            )
            card.pack(fill=tk.X, pady=(0, SPACING_SM))

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_MD)

            # Left: icon + info
            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side=tk.LEFT, fill=tk.X, expand=True)

            title_row = ctk.CTkFrame(left, fg_color="transparent")
            title_row.pack(anchor="w")
            ctk.CTkLabel(
                title_row, text=s["icon"], font=FONT_BODY, text_color=ACCENT_PRIMARY
            ).pack(side=tk.LEFT, padx=(0, SPACING_XS))
            ctk.CTkLabel(
                title_row, text=s["label"], font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
            ).pack(side=tk.LEFT)

            ctk.CTkLabel(
                left, text=s["desc"], font=FONT_TINY, text_color=TEXT_MUTED,
                justify="left", wraplength=380
            ).pack(anchor="w", pady=(SPACING_XS, 0))

            ctk.CTkLabel(
                left, text=f"Last run: {ts}", font=FONT_TINY, text_color=TEXT_DISABLED
            ).pack(anchor="w", pady=(SPACING_XS, 0))

            # Right: run button
            btn = create_styled_button(
                inner, text="▶  Run",
                command=lambda scraper=s: self._start([scraper]),
                style_type="default" if self._prereqs_ok else "ghost",
                height=32, width=80,
                state="normal" if self._prereqs_ok else "disabled"
            )
            btn.pack(side=tk.RIGHT, padx=(SPACING_MD, 0))
            self._scraper_btns[s["key"]] = btn

    # ─────────────────────────────────── Runner ───────────────────────────────

    def _start(self, scrapers: list):
        if self._running:
            return

        self._running = True
        self._cancelled = False

        # Disable all buttons
        if hasattr(self, '_run_all_btn'):
            self._run_all_btn.configure(state="disabled", text="Running…")
        for btn in getattr(self, '_scraper_btns', {}).values():
            btn.configure(state="disabled")
        self._close_btn.configure(state="disabled")

        # Show progress area
        self._prog_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_SM),
                               before=self._close_btn.master)
        self._prog_bar.start()
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

        self._thread = threading.Thread(
            target=self._run_scrapers, args=(scrapers,), daemon=True
        )
        self._thread.start()

    def _log(self, msg: str):
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

    def _run_scrapers(self, scrapers: list):
        errors = []
        for s in scrapers:
            if self._cancelled:
                break
            self._set_status(f"Scraping {s['label']}…")
            self._log(f"\n► {s['label']} scraper starting…")
            try:
                import importlib
                mod = importlib.import_module(s["module"])
                fn = getattr(mod, s["fn"])
                fn()
                self._log(f"  ✅ {s['label']} complete")
            except Exception as exc:
                self._log(f"  ❌ {s['label']} failed: {exc}")
                errors.append(f"{s['label']}: {exc}")

        self.dialog.after(0, lambda: self._done(errors))

    def _done(self, errors: list):
        self._running = False
        self._prog_bar.stop()

        if errors:
            self._set_status(f"Completed with {len(errors)} error(s) — see log above")
        else:
            self._set_status("✅ All done! Data updated successfully.")

        if hasattr(self, '_run_all_btn'):
            self._run_all_btn.configure(state="normal", text="▶  Run All")
        for btn in getattr(self, '_scraper_btns', {}).values():
            btn.configure(state="normal")
        self._close_btn.configure(state="normal")

        if self.on_complete:
            self.dialog.after(500, self.on_complete)

    def _close(self):
        self._cancelled = True
        self.dialog.destroy()
        if self.on_complete and not self._running:
            self.on_complete()


def show_data_update_dialog(parent: ctk.CTk, on_complete_callback=None):
    return DataUpdateDialog(parent, on_complete_callback)
