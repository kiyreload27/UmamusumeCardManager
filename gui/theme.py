"""
Centralized Theme Module for Umamusume Support Card Manager
Modern dark theme with CustomTkinter
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ═══════════════════════════════════════════════════════════════════════════════
# COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════════════════

# Backgrounds — deep blue/purple neutrals
BG_DARKEST = '#050816'
BG_DARK = '#070b1a'
BG_MEDIUM = '#101624'
BG_LIGHT = '#1b2335'
BG_HIGHLIGHT = '#25324a'

# Accents — softer, modern neon-inspired
ACCENT_PRIMARY = '#7dd3fc'     # Cyan — main action color
ACCENT_SECONDARY = '#c4b5fd'   # Soft purple
ACCENT_TERTIARY = '#f9a8d4'    # Pink highlight
ACCENT_SUCCESS = '#4ade80'     # Green
ACCENT_WARNING = '#facc15'     # Amber
ACCENT_ERROR = '#fb7185'       # Red

# Text
TEXT_PRIMARY = '#e5e7eb'
TEXT_SECONDARY = '#cbd5f5'
TEXT_MUTED = '#9ca3c7'
TEXT_DISABLED = '#4b5563'

# Rarity — brighter for contrast against new background
RARITY_SSR = '#facc15'
RARITY_SR = '#e5e7eb'
RARITY_R = '#f97316'
RARITY_COLORS = {'SSR': RARITY_SSR, 'SR': RARITY_SR, 'R': RARITY_R}

# Card type colours & icons (slightly softened to match new palette)
TYPE_COLORS = {
    'Speed': '#60a5fa', 'Stamina': '#fb923c', 'Power': '#facc15',
    'Guts': '#f97373', 'Wisdom': '#34d399', 'Friend': '#a855f7', 'Group': '#fbbf24'
}
TYPE_ICONS = {
    'Speed': '🏃', 'Stamina': '💚', 'Power': '💪',
    'Guts': '🔥', 'Wisdom': '🧠', 'Friend': '💜', 'Group': '👥'
}

# ═══════════════════════════════════════════════════════════════════════════════
# FONTS
# ═══════════════════════════════════════════════════════════════════════════════

FONT_FAMILY = 'Segoe UI'
FONT_FAMILY_MONO = 'Consolas'

FONT_TITLE = (FONT_FAMILY, 22, 'bold')
FONT_HEADER = (FONT_FAMILY, 16, 'bold')
FONT_SUBHEADER = (FONT_FAMILY, 14, 'bold')
FONT_BODY = (FONT_FAMILY, 12)
FONT_BODY_BOLD = (FONT_FAMILY, 12, 'bold')
FONT_SMALL = (FONT_FAMILY, 11)
FONT_TINY = (FONT_FAMILY, 10)
FONT_MONO = (FONT_FAMILY_MONO, 12)
FONT_MONO_SMALL = (FONT_FAMILY_MONO, 11)

# ═══════════════════════════════════════════════════════════════════════════════
# TTK STYLE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def configure_styles(root: tk.Tk):
    """Configure ttk styles for legacy widgets (Treeview, Scrollbar, etc.)"""
    style = ttk.Style()
    style.theme_use('clam')

    # General
    style.configure('TFrame', background=BG_DARK)
    style.configure('TLabel', background=BG_DARK, foreground=TEXT_SECONDARY, font=FONT_BODY)
    style.configure('TLabelframe', background=BG_DARK, foreground=TEXT_SECONDARY)
    style.configure('TLabelframe.Label', background=BG_DARK, foreground=ACCENT_PRIMARY, font=FONT_SUBHEADER)

    # Named label styles
    style.configure('Title.TLabel', font=FONT_TITLE, foreground=TEXT_PRIMARY, background=BG_DARK)
    style.configure('Header.TLabel', font=FONT_HEADER, foreground=ACCENT_PRIMARY, background=BG_DARK)
    style.configure('Subheader.TLabel', font=FONT_SUBHEADER, foreground=TEXT_PRIMARY, background=BG_DARK)
    style.configure('Subtitle.TLabel', font=FONT_SMALL, foreground=TEXT_MUTED, background=BG_DARK)
    style.configure('Stats.TLabel', font=FONT_SMALL, foreground=TEXT_SECONDARY, background=BG_MEDIUM, padding=8)
    style.configure('Accent.TLabel', font=FONT_BODY, foreground=ACCENT_PRIMARY, background=BG_DARK)

    # Buttons
    style.configure('TButton', padding=(12, 6), font=FONT_BODY, background=BG_LIGHT, foreground=TEXT_PRIMARY)
    style.map('TButton',
              background=[('active', BG_HIGHLIGHT), ('pressed', ACCENT_PRIMARY)],
              foreground=[('active', TEXT_PRIMARY), ('pressed', TEXT_PRIMARY)])
    style.configure('Accent.TButton', padding=(12, 6), font=FONT_BODY_BOLD,
                    background=ACCENT_PRIMARY, foreground=TEXT_PRIMARY)
    style.map('Accent.TButton', background=[('active', '#ff8ab5'), ('pressed', '#e55a88')])
    style.configure('Small.TButton', padding=(8, 4), font=FONT_SMALL)

    # Checkbutton
    style.configure('TCheckbutton', background=BG_DARK, foreground=TEXT_SECONDARY, font=FONT_BODY)
    style.map('TCheckbutton', background=[('active', BG_DARK)], foreground=[('active', TEXT_PRIMARY)])
    style.configure('Large.TCheckbutton', font=FONT_BODY_BOLD, background=BG_DARK, foreground=TEXT_PRIMARY)

    # Entry / Combobox
    style.configure('TEntry', fieldbackground=BG_MEDIUM, foreground=TEXT_PRIMARY,
                    insertcolor=TEXT_PRIMARY, padding=6)
    style.configure('TCombobox', fieldbackground=BG_MEDIUM, background=BG_LIGHT,
                    foreground=TEXT_PRIMARY, arrowcolor=TEXT_MUTED, padding=4)
    style.map('TCombobox', fieldbackground=[('readonly', BG_MEDIUM)],
              selectbackground=[('readonly', BG_HIGHLIGHT)])

    # Notebook
    style.configure('TNotebook', background=BG_DARK, borderwidth=0)
    style.configure('TNotebook.Tab', padding=(20, 10), font=FONT_BODY_BOLD,
                    background=BG_MEDIUM, foreground=TEXT_MUTED)
    style.map('TNotebook.Tab',
              background=[('selected', BG_LIGHT), ('active', BG_HIGHLIGHT)],
              foreground=[('selected', ACCENT_PRIMARY), ('active', TEXT_PRIMARY)],
              expand=[('selected', (0, 0, 0, 2))])

    # Treeview (default)
    style.configure('Treeview',
                    background=BG_MEDIUM, foreground=TEXT_SECONDARY,
                    fieldbackground=BG_MEDIUM, font=FONT_BODY, rowheight=32)
    style.configure('Treeview.Heading',
                    font=FONT_BODY_BOLD, background=BG_LIGHT,
                    foreground=TEXT_PRIMARY, padding=8)
    style.map('Treeview',
              background=[('selected', ACCENT_PRIMARY)],
              foreground=[('selected', TEXT_PRIMARY)])
    style.map('Treeview.Heading', background=[('active', BG_HIGHLIGHT)])

    # Card list — tall rows for thumbnails
    style.configure('CardList.Treeview',
                    background=BG_MEDIUM, foreground=TEXT_SECONDARY,
                    fieldbackground=BG_MEDIUM, font=FONT_BODY, rowheight=80)

    # Deck list
    style.configure('DeckList.Treeview',
                    background=BG_MEDIUM, foreground=TEXT_SECONDARY,
                    fieldbackground=BG_MEDIUM, font=FONT_BODY, rowheight=80)
    style.map('DeckList.Treeview', background=[('selected', ACCENT_PRIMARY)])

    # Scales
    style.configure('TScale', background=BG_DARK, troughcolor=BG_MEDIUM, sliderthickness=18)
    style.configure('Horizontal.TScale', background=BG_DARK)

    # Scrollbars
    style.configure('TScrollbar', background=BG_LIGHT, troughcolor=BG_MEDIUM,
                    borderwidth=0, arrowsize=14)
    style.map('TScrollbar', background=[('active', BG_HIGHLIGHT), ('pressed', ACCENT_PRIMARY)])

    # PanedWindow
    style.configure('TPanedwindow', background=BG_DARK)

    root.configure(bg=BG_DARK)

# ═══════════════════════════════════════════════════════════════════════════════
# CTK WIDGET FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════

def create_styled_entry(parent, textvariable=None, **kwargs):
    """Create a styled CTkEntry"""
    kwargs.pop('bg', None)
    kwargs.pop('fg', None)
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bd', 'relief', 'insertbackground', 'selectbackground',
                         'selectforeground', 'highlightthickness')}
    return ctk.CTkEntry(
        parent, textvariable=textvariable,
        font=FONT_BODY, fg_color=BG_MEDIUM, text_color=TEXT_PRIMARY,
        border_width=1, border_color=BG_LIGHT, corner_radius=8,
        height=36, **safe
    )


def create_styled_button(parent, text, command=None, style_type='default', **kwargs):
    """Create a styled CTkButton"""
    _fg = {
        'default': BG_LIGHT, 'accent': ACCENT_PRIMARY, 'secondary': ACCENT_SECONDARY,
        'success': ACCENT_SUCCESS, 'warning': ACCENT_WARNING, 'danger': ACCENT_ERROR,
    }
    _hover = {
        'default': BG_HIGHLIGHT, 'accent': '#ff8ab5', 'secondary': '#9580ff',
        'success': '#6ee7a0', 'warning': '#fcd34d', 'danger': '#ff8a8a',
    }
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'bd', 'relief', 'activebackground',
                         'activeforeground', 'padx', 'pady')}
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=_fg.get(style_type, BG_LIGHT),
        hover_color=_hover.get(style_type, BG_HIGHLIGHT),
        text_color=TEXT_PRIMARY,
        font=FONT_BODY_BOLD if style_type == 'accent' else FONT_BODY,
        corner_radius=8, border_width=0, **safe
    )


def create_styled_text(parent, height=10, **kwargs):
    """Create a styled CTkTextbox"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'fg', 'selectbackground', 'selectforeground',
                         'relief', 'insertbackground', 'padx', 'pady', 'wrap')}
    return ctk.CTkTextbox(
        parent, height=height * 22,
        font=FONT_MONO, corner_radius=10,
        text_color=TEXT_PRIMARY, fg_color=BG_DARK,
        border_color=BG_LIGHT, border_width=1,
        **safe
    )


def create_card_frame(parent, **kwargs):
    """Create a styled CTkFrame card"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'highlightthickness', 'highlightbackground')}
    return ctk.CTkFrame(
        parent,
        corner_radius=14,
        fg_color=BG_MEDIUM,
        border_width=1,
        border_color=BG_HIGHLIGHT,
        **safe,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_rarity_color(rarity):
    return RARITY_COLORS.get(rarity, TEXT_SECONDARY)

def get_type_color(card_type):
    return TYPE_COLORS.get(card_type, TEXT_SECONDARY)

def get_type_icon(card_type):
    return TYPE_ICONS.get(card_type, '')

# ═══════════════════════════════════════════════════════════════════════════════
# TOOLTIPS
# ═══════════════════════════════════════════════════════════════════════════════

EFFECT_DESCRIPTIONS = {
    "Friendship Bonus": "Increases stats gained during Friendship Training (orange aura).",
    "Motivation Bonus": "Increases stats gained based on your Uma's motivation level.",
    "Specialty Rate": "Increases the chance of this card appearing in its specialty training.",
    "Training Bonus": "Flat percentage increase to stats gained in training where this card is present.",
    "Initial Bond": "Starting gauge value for this card.",
    "Race Bonus": "Increases stats gained from racing.",
    "Fan Count Bonus": "Increases fans gained from racing.",
    "Skill Pt Bonus": "Bonus skill points gained when training with this card.",
    "Hint Lv": "Starting level of skills taught by this card's hints.",
    "Hint Rate": "Increases chance of getting a hint event.",
    "Minigame Fail Rate": "Reduces chance of failing training.",
    "Energy Usage": "Reduces energy consumed during training.",
    "Current Energy": "Increases starting energy in scenario.",
    "Vitality": "Increases vitality gain from events.",
    "Stamina": "Increases stamina gain from training.",
    "Speed": "Increases speed gain from training.",
    "Power": "Increases power gain from training.",
    "Guts": "Increases guts gain from training.",
    "Wisdom": "Increases wisdom gain from training.",
    "Logic": "Custom logic effect.",
    "Starting Stats": "Increases initial stats at start of scenario."
}


class Tooltip:
    """Tooltip popup on hover for any widget."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self._id1 = self.widget.bind("<Enter>", self.enter)
        self._id2 = self.widget.bind("<Leave>", self.leave)
        self._id3 = self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(400, self.showtip)

    def unschedule(self):
        _id = self.id
        self.id = None
        if _id:
            self.widget.after_cancel(_id)

    def showtip(self, event=None):
        x = y = 0
        try:
            x, y, cx, cy = self.widget.bbox("insert")
        except Exception:
            pass
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tip_window, text=self.text, justify=tk.LEFT,
            background=BG_LIGHT, foreground=TEXT_PRIMARY,
            relief=tk.SOLID, borderwidth=1,
            font=FONT_SMALL, padx=10, pady=5
        )
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


def create_tooltip(widget, text):
    """Convenience wrapper."""
    return Tooltip(widget, text)
