"""
Diagnostic / Debug Panel
Accessible via Ctrl+Shift+D or the 🛠 sidebar button.
Shows app state, DB info, log tail — designed for use when remoting
into a user's machine to diagnose issues.
"""

import tkinter as tk
import customtkinter as ctk
import sys
import os
import platform
import sqlite3
import webbrowser
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_ERROR, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY, FONT_MONO_SMALL,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_button,
)


def _get_db_path() -> str:
    """Return current DB_PATH from db_queries."""
    try:
        from db.db_queries import DB_PATH
        return DB_PATH
    except Exception:
        return "Unknown"


def _get_log_path() -> str:
    """Return the resolved log path (same logic as main.py)."""
    try:
        from main import get_log_path
        return get_log_path()
    except Exception:
        pass
    # Fallback: reconstruct
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(appdata, "UmamusumeCardManager", "logs", "app.log")
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, "logs", "app.log")


def _read_log_tail(log_path: str, lines: int = 100) -> str:
    """Read the last N lines of the log file."""
    try:
        if not os.path.exists(log_path):
            return "(Log file not found)"
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return "".join(tail)
    except Exception as e:
        return f"(Could not read log: {e})"


def _get_db_stats() -> dict:
    """Collect DB statistics safely."""
    stats = {}
    db_path = _get_db_path()
    try:
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            stats["db_size"] = f"{size_bytes / 1024:.1f} KB"
        else:
            stats["db_size"] = "File not found"

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        for table, label in [
            ("support_cards", "Total Cards"),
            ("owned_cards",   "Owned Cards"),
            ("user_decks",    "Saved Decks"),
            ("tracks",        "Racetracks"),
            ("characters",    "Characters"),
            ("races",         "Races"),
        ]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[label] = cur.fetchone()[0]
            except Exception:
                stats[label] = "—"

        # Scraper timestamps
        try:
            cur.execute("SELECT scraper_type, last_run_timestamp FROM scraper_meta")
            for stype, ts in cur.fetchall():
                stats[f"Last scrape: {stype}"] = ts or "Never"
        except Exception:
            pass

        # App version in DB
        try:
            cur.execute("SELECT value FROM system_metadata WHERE key='app_version'")
            row = cur.fetchone()
            stats["DB app_version"] = row[0] if row else "—"
        except Exception:
            stats["DB app_version"] = "—"

        conn.close()
    except Exception as e:
        stats["error"] = str(e)

    return stats


def _build_diagnostics_text() -> str:
    """Build a plain-text diagnostics summary for clipboard."""
    from version import VERSION, APP_NAME
    try:
        from version import BUILD_DATE
    except ImportError:
        BUILD_DATE = "unknown"

    db_path = _get_db_path()
    log_path = _get_log_path()
    db_stats = _get_db_stats()
    log_tail = _read_log_tail(log_path, lines=20)

    lines = [
        "=" * 60,
        f"  {APP_NAME} — Diagnostic Report",
        f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        "[ App ]",
        f"  Version:    v{VERSION}  (built {BUILD_DATE})",
        f"  Mode:       {'Frozen EXE' if getattr(sys, 'frozen', False) else 'Python Source'}",
        f"  Python:     {sys.version}",
        f"  Platform:   {platform.system()} {platform.release()} ({platform.machine()})",
        "",
        "[ Database ]",
        f"  Path:       {db_path}",
    ]
    for k, v in db_stats.items():
        lines.append(f"  {k+':':24} {v}")
    lines += [
        "",
        "[ Logs ]",
        f"  Log path:   {log_path}",
        "",
        "[ Last 20 log lines ]",
        log_tail,
        "=" * 60,
    ]
    return "\n".join(lines)


class DebugPanel:
    """In-app diagnostic panel."""

    def __init__(self, parent: ctk.CTk):
        self.parent = parent

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("🛠  Diagnostics")
        self.dialog.geometry("720x640")
        self.dialog.resizable(True, True)
        self.dialog.minsize(600, 500)
        self.dialog.transient(parent)

        # Center
        self.dialog.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 720) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 640) // 2
        self.dialog.geometry(f"720x640+{px}+{py}")

        self._build_ui()
        self._refresh()
        self.dialog.after(100, self.dialog.lift)

    def _build_ui(self):
        self.dialog.configure(fg_color=BG_DARK)

        # Header
        hdr = ctk.CTkFrame(self.dialog, fg_color=BG_ELEVATED, corner_radius=0)
        hdr.pack(fill=tk.X)

        title_row = ctk.CTkFrame(hdr, fg_color="transparent")
        title_row.pack(fill=tk.X, padx=SPACING_LG, pady=SPACING_MD)

        ctk.CTkLabel(
            title_row, text="🛠  Diagnostics",
            font=FONT_HEADER, text_color=ACCENT_PRIMARY
        ).pack(side=tk.LEFT)

        # Action buttons in header
        
        self._report_btn = create_styled_button(
            title_row, text="🐞 Report a Bug",
            command=lambda: webbrowser.open("https://github.com/kiyreload27/UmamusumeCardManager/issues/new"), 
            style_type="ghost", height=32, width=120
        )
        self._report_btn.pack(side=tk.RIGHT, padx=(SPACING_SM, 0))

        create_styled_button(
            title_row, text="📋 Copy All",
            command=self._copy_all, style_type="accent", height=32, width=110
        ).pack(side=tk.RIGHT, padx=(SPACING_SM, 0))

        create_styled_button(
            title_row, text="🔄 Refresh",
            command=self._refresh, style_type="default", height=32, width=90
        ).pack(side=tk.RIGHT)

        # Tabbed content
        self.tabs = ctk.CTkTabview(self.dialog, fg_color=BG_DARK)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=SPACING_MD, pady=SPACING_MD)

        self.tabs.add("Overview")
        self.tabs.add("Database")
        self.tabs.add("Log File")

        self._build_overview_tab(self.tabs.tab("Overview"))
        self._build_database_tab(self.tabs.tab("Database"))
        self._build_log_tab(self.tabs.tab("Log File"))

    # ──────────────────────────── Overview tab ──────────────────────────

    def _build_overview_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        # App info section
        self._app_section = ctk.CTkFrame(scroll, fg_color=BG_MEDIUM, corner_radius=RADIUS_LG,
                                          border_width=1, border_color=BG_LIGHT)
        self._app_section.pack(fill=tk.X, pady=(0, SPACING_MD))

        ctk.CTkLabel(self._app_section, text="Application",
                     font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
                     ).pack(anchor="w", padx=SPACING_LG, pady=(SPACING_MD, SPACING_XS))

        self._app_rows_frame = ctk.CTkFrame(self._app_section, fg_color="transparent")
        self._app_rows_frame.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_MD))

        # Log info section
        self._log_section = ctk.CTkFrame(scroll, fg_color=BG_MEDIUM, corner_radius=RADIUS_LG,
                                          border_width=1, border_color=BG_LIGHT)
        self._log_section.pack(fill=tk.X, pady=(0, SPACING_MD))

        ctk.CTkLabel(self._log_section, text="Log File",
                     font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
                     ).pack(anchor="w", padx=SPACING_LG, pady=(SPACING_MD, SPACING_XS))

        self._log_path_label = ctk.CTkLabel(
            self._log_section, text="", font=FONT_MONO_SMALL, text_color=TEXT_MUTED,
            wraplength=600, justify="left"
        )
        self._log_path_label.pack(anchor="w", padx=SPACING_LG)

        self._open_log_btn = create_styled_button(
            self._log_section, text="📄 Open Log in Notepad",
            command=self._open_log, style_type="default", height=32
        )
        self._open_log_btn.pack(anchor="w", padx=SPACING_LG, pady=(SPACING_SM, SPACING_MD))

    # ──────────────────────────── Database tab ──────────────────────────

    def _build_database_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        self._db_path_section = ctk.CTkFrame(scroll, fg_color=BG_MEDIUM, corner_radius=RADIUS_LG,
                                              border_width=1, border_color=BG_LIGHT)
        self._db_path_section.pack(fill=tk.X, pady=(0, SPACING_MD))

        ctk.CTkLabel(self._db_path_section, text="Database Path",
                     font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
                     ).pack(anchor="w", padx=SPACING_LG, pady=(SPACING_MD, SPACING_XS))

        self._db_path_label = ctk.CTkLabel(
            self._db_path_section, text="",
            font=FONT_MONO_SMALL, text_color=ACCENT_INFO,
            wraplength=620, justify="left"
        )
        self._db_path_label.pack(anchor="w", padx=SPACING_LG, pady=(0, SPACING_MD))

        # Stats table
        self._db_stats_frame = ctk.CTkFrame(scroll, fg_color=BG_MEDIUM, corner_radius=RADIUS_LG,
                                             border_width=1, border_color=BG_LIGHT)
        self._db_stats_frame.pack(fill=tk.X)
        ctk.CTkLabel(self._db_stats_frame, text="Statistics",
                     font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
                     ).pack(anchor="w", padx=SPACING_LG, pady=(SPACING_MD, SPACING_XS))
        self._db_stats_inner = ctk.CTkFrame(self._db_stats_frame, fg_color="transparent")
        self._db_stats_inner.pack(fill=tk.X, padx=SPACING_LG, pady=(0, SPACING_MD))

    # ──────────────────────────── Log tab ───────────────────────────────

    def _build_log_tab(self, parent):
        self._log_textbox = ctk.CTkTextbox(
            parent, font=FONT_MONO_SMALL,
            fg_color=BG_DARKEST, text_color=TEXT_SECONDARY,
            corner_radius=RADIUS_MD
        )
        self._log_textbox.pack(fill=tk.BOTH, expand=True)

    # ──────────────────────────── Refresh ───────────────────────────────

    def _refresh(self):
        """Populate all tabs with fresh data."""
        try:
            from version import VERSION, APP_NAME
        except ImportError:
            VERSION, APP_NAME = "?", "UmamusumeCardManager"
        try:
            from version import BUILD_DATE
        except ImportError:
            BUILD_DATE = "unknown"

        mode = "Frozen EXE" if getattr(sys, 'frozen', False) else "Python Source"
        db_path = _get_db_path()
        log_path = _get_log_path()
        db_stats = _get_db_stats()

        # ── Overview: App rows ──
        for w in self._app_rows_frame.winfo_children():
            w.destroy()

        app_rows = [
            ("Version",  f"v{VERSION}   (built {BUILD_DATE})"),
            ("Mode",     mode),
            ("Python",   sys.version.split()[0]),
            ("Platform", f"{platform.system()} {platform.release()} ({platform.machine()})"),
        ]
        for label, value in app_rows:
            row = ctk.CTkFrame(self._app_rows_frame, fg_color="transparent")
            row.pack(fill=tk.X, pady=1)
            ctk.CTkLabel(row, text=label + ":", font=FONT_SMALL, text_color=TEXT_MUTED,
                         width=90, anchor="w").pack(side=tk.LEFT)
            ctk.CTkLabel(row, text=value, font=FONT_SMALL, text_color=TEXT_PRIMARY,
                         anchor="w").pack(side=tk.LEFT)

        # ── Overview: Log path ──
        self._log_path_label.configure(text=log_path)
        log_exists = os.path.exists(log_path)
        self._open_log_btn.configure(
            state="normal" if log_exists else "disabled",
            text="📄 Open Log in Notepad" if log_exists else "📄 Log file not yet created"
        )

        # ── Database tab ──
        self._db_path_label.configure(text=db_path)

        for w in self._db_stats_inner.winfo_children():
            w.destroy()

        for label, value in db_stats.items():
            row = ctk.CTkFrame(self._db_stats_inner, fg_color="transparent")
            row.pack(fill=tk.X, pady=1)
            ctk.CTkLabel(row, text=label + ":", font=FONT_SMALL, text_color=TEXT_MUTED,
                         width=200, anchor="w").pack(side=tk.LEFT)
            color = ACCENT_SUCCESS if isinstance(value, int) and value > 0 else TEXT_PRIMARY
            ctk.CTkLabel(row, text=str(value), font=FONT_SMALL, text_color=color,
                         anchor="w").pack(side=tk.LEFT)

        # ── Log tab ──
        log_content = _read_log_tail(log_path, lines=100)
        self._log_textbox.configure(state="normal")
        self._log_textbox.delete("1.0", "end")
        self._log_textbox.insert("1.0", log_content)
        self._log_textbox.see("end")
        self._log_textbox.configure(state="disabled")

    # ──────────────────────────── Actions ───────────────────────────────

    def _open_log(self):
        log_path = _get_log_path()
        try:
            os.startfile(log_path)
        except Exception:
            pass

    def _copy_all(self):
        try:
            text = _build_diagnostics_text()
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(text)
            self.dialog.update()
            # Brief visual feedback
            orig_text = "📋 Copy All"
            # find button and flash it
            self.dialog.after(100, lambda: None)  # yield
        except Exception:
            pass


def show_debug_panel(parent: ctk.CTk):
    """Open the diagnostic panel."""
    return DebugPanel(parent)
