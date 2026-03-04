"""
Centralized Theme Module for Umamusume Support Card Manager
Premium dark theme with glassmorphism, refined palette, and rich widget factories
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
# COLOR PALETTE — Deep indigo/violet accent system with layered surfaces
# ═══════════════════════════════════════════════════════════════════════════════

# Backgrounds — Rich, layered dark surfaces
BG_DARKEST  = '#080b14'   # Deepest — main content backdrop
BG_DARK     = '#0f1523'   # Sidebar, panels
BG_MEDIUM   = '#171e2e'   # Cards, input fields
BG_LIGHT    = '#1e2a3f'   # Hover, borders
BG_HIGHLIGHT = '#283650'  # Active states, selection
BG_ELEVATED = '#1a2236'   # Glassmorphism card surfaces

# Glass overlay — for subtle frosted-glass panels
GLASS_BG     = '#16203080'  # Semi-transparent for glassmorphism simulation
GLASS_BORDER = '#ffffff12'  # Very subtle white border

# Accents — Refined indigo/violet primary system
ACCENT_PRIMARY   = '#818cf8'   # Indigo-400 (Main CTA, active nav)
ACCENT_SECONDARY = '#a78bfa'   # Violet-400 (Secondary elements)
ACCENT_TERTIARY  = '#f472b6'   # Pink-400 (Highlights, special items)
ACCENT_SUCCESS   = '#34d399'   # Emerald-400
ACCENT_WARNING   = '#fbbf24'   # Amber-400
ACCENT_ERROR     = '#f87171'   # Red-400
ACCENT_INFO      = '#38bdf8'   # Sky-400

# Accent glow variants (for active/hover states)
ACCENT_PRIMARY_GLOW   = '#818cf830'
ACCENT_SUCCESS_GLOW   = '#34d39930'
ACCENT_WARNING_GLOW   = '#fbbf2430'
ACCENT_ERROR_GLOW     = '#f8717130'

# Text — Carefully calibrated for readability
TEXT_PRIMARY   = '#f1f5f9'   # Slate-100 (Headers, main content)
TEXT_SECONDARY = '#cbd5e1'   # Slate-300 (Body text)
TEXT_MUTED     = '#94a3b8'   # Slate-400 (Captions, labels)
TEXT_DISABLED  = '#64748b'   # Slate-500 (Disabled states)
TEXT_INVERSE   = '#0f172a'   # Slate-900 (Text on bright backgrounds)

# Rarity — Distinct, vibrant for each tier
RARITY_SSR = '#fbbf24'    # Gold/Amber
RARITY_SR  = '#c0c7d0'    # Silver
RARITY_R   = '#f97316'    # Orange/Bronze
RARITY_COLORS = {'SSR': RARITY_SSR, 'SR': RARITY_SR, 'R': RARITY_R}

# Card type colours & icons
TYPE_COLORS = {
    'Speed': '#60a5fa', 'Stamina': '#fb923c', 'Power': '#facc15',
    'Guts': '#f97373', 'Wisdom': '#34d399', 'Friend': '#c084fc', 'Group': '#fbbf24'
}
TYPE_ICONS = {
    'Speed': '🏃', 'Stamina': '💚', 'Power': '💪',
    'Guts': '🔥', 'Wisdom': '🧠', 'Friend': '💜', 'Group': '👥'
}

# Race grade colors
GRADE_COLORS = {
    'GI': '#fbbf24', 'G1': '#fbbf24',
    'GII': '#c0c7d0', 'G2': '#c0c7d0',
    'GIII': '#d97706', 'G3': '#d97706',
    'OP': '#818cf8', 'Pre-OP': '#a78bfa',
}

# ═══════════════════════════════════════════════════════════════════════════════
# SPACING & RADIUS TOKENS
# ═══════════════════════════════════════════════════════════════════════════════

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32
SPACING_2XL = 48

RADIUS_SM  = 6
RADIUS_MD  = 10
RADIUS_LG  = 14
RADIUS_XL  = 20
RADIUS_FULL = 100  # Pill shape

# Sidebar
SIDEBAR_WIDTH_EXPANDED  = 220
SIDEBAR_WIDTH_COLLAPSED = 60

# ═══════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY — Clear typographic scale
# ═══════════════════════════════════════════════════════════════════════════════

FONT_FAMILY = 'Segoe UI'
FONT_FAMILY_MONO = 'Consolas'

FONT_DISPLAY   = (FONT_FAMILY, 28, 'bold')   # Page/view titles
FONT_TITLE     = (FONT_FAMILY, 22, 'bold')    # Section titles
FONT_HEADER    = (FONT_FAMILY, 16, 'bold')    # Panel headers
FONT_SUBHEADER = (FONT_FAMILY, 14, 'bold')    # Sub-sections
FONT_BODY      = (FONT_FAMILY, 12)            # Default body
FONT_BODY_BOLD = (FONT_FAMILY, 12, 'bold')    # Emphasized body
FONT_SMALL     = (FONT_FAMILY, 11)            # Captions, meta
FONT_TINY      = (FONT_FAMILY, 10)            # Overline, badges
FONT_MONO      = (FONT_FAMILY_MONO, 12)       # Code/data
FONT_MONO_SMALL = (FONT_FAMILY_MONO, 11)

# ═══════════════════════════════════════════════════════════════════════════════
# TTK STYLE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def configure_styles(root: tk.Tk):
    """Configure ttk styles for legacy widgets (Treeview, Scrollbar, etc.)"""
    style = ttk.Style()
    style.theme_use('clam')

    # General frames/labels
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
    style.map('Accent.TButton', background=[('active', '#9580ff'), ('pressed', '#7c6fe0')])
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
                    fieldbackground=BG_MEDIUM, font=FONT_BODY, rowheight=36)
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

    # Scrollbars — minimal, blends with background
    style.configure('TScrollbar', background=BG_LIGHT, troughcolor=BG_DARK,
                    borderwidth=0, arrowsize=0, width=8)
    style.map('TScrollbar', background=[('active', BG_HIGHLIGHT), ('pressed', ACCENT_PRIMARY)])

    # PanedWindow
    style.configure('TPanedwindow', background=BG_DARK)

    root.configure(bg=BG_DARKEST)


# ═══════════════════════════════════════════════════════════════════════════════
# CTK WIDGET FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════

def create_styled_entry(parent, textvariable=None, **kwargs):
    """Create a styled CTkEntry with focus-glow feel"""
    kwargs.pop('bg', None)
    kwargs.pop('fg', None)
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bd', 'relief', 'insertbackground', 'selectbackground',
                         'selectforeground', 'highlightthickness')}
    return ctk.CTkEntry(
        parent, textvariable=textvariable,
        font=FONT_BODY, fg_color=BG_MEDIUM, text_color=TEXT_PRIMARY,
        border_width=1, border_color=BG_LIGHT, corner_radius=RADIUS_MD,
        height=38, **safe
    )


def create_styled_button(parent, text, command=None, style_type='default', **kwargs):
    """Create a styled CTkButton with multiple variants"""
    _fg = {
        'default': BG_LIGHT, 'accent': ACCENT_PRIMARY, 'secondary': ACCENT_SECONDARY,
        'success': ACCENT_SUCCESS, 'warning': ACCENT_WARNING, 'danger': ACCENT_ERROR,
        'ghost': 'transparent',
    }
    _hover = {
        'default': BG_HIGHLIGHT, 'accent': '#6366f1', 'secondary': '#8b5cf6',
        'success': '#10b981', 'warning': '#f59e0b', 'danger': '#ef4444',
        'ghost': BG_LIGHT,
    }
    _text = {
        'default': TEXT_PRIMARY, 'accent': TEXT_PRIMARY, 'secondary': TEXT_PRIMARY,
        'success': TEXT_PRIMARY, 'warning': TEXT_INVERSE, 'danger': TEXT_PRIMARY,
        'ghost': TEXT_SECONDARY,
    }
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'bd', 'relief', 'activebackground',
                         'activeforeground', 'padx', 'pady')}
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=_fg.get(style_type, BG_LIGHT),
        hover_color=_hover.get(style_type, BG_HIGHLIGHT),
        text_color=_text.get(style_type, TEXT_PRIMARY),
        font=FONT_BODY_BOLD if style_type in ('accent', 'secondary') else FONT_BODY,
        corner_radius=RADIUS_MD, border_width=0, **safe
    )


def create_sidebar_button(parent, text, command=None, active=False, **kwargs):
    """Create a styled CTkButton for sidebar navigation with active indicator"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'fg', 'activebackground', 'activeforeground', 'padx', 'pady')}

    bg_color = BG_HIGHLIGHT if active else "transparent"
    text_color = ACCENT_PRIMARY if active else TEXT_MUTED
    hover_color = BG_LIGHT

    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=bg_color,
        hover_color=hover_color,
        text_color=text_color,
        font=FONT_BODY_BOLD,
        corner_radius=RADIUS_MD,
        anchor="w",
        height=44,
        border_width=0, **safe
    )


def create_styled_text(parent, height=10, **kwargs):
    """Create a styled CTkTextbox"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'fg', 'selectbackground', 'selectforeground',
                         'relief', 'insertbackground', 'padx', 'pady', 'wrap')}
    return ctk.CTkTextbox(
        parent, height=height * 22,
        font=FONT_MONO, corner_radius=RADIUS_MD,
        text_color=TEXT_PRIMARY, fg_color=BG_DARK,
        border_color=BG_LIGHT, border_width=1,
        **safe
    )


def create_card_frame(parent, elevated=False, **kwargs):
    """Create a styled CTkFrame card with optional glassmorphism elevation"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'highlightthickness', 'highlightbackground')}
    
    bg = BG_ELEVATED if elevated else BG_MEDIUM
    border = BG_LIGHT
    
    return ctk.CTkFrame(
        parent,
        corner_radius=RADIUS_LG,
        fg_color=bg,
        border_width=1,
        border_color=border,
        **safe,
    )


def create_glass_frame(parent, **kwargs):
    """Create a frosted-glass style panel for premium feel"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'highlightthickness', 'highlightbackground')}
    return ctk.CTkFrame(
        parent,
        corner_radius=RADIUS_LG,
        fg_color=BG_ELEVATED,
        border_width=1,
        border_color=BG_LIGHT,
        **safe,
    )


def create_section_header(parent, title, icon="", action_text=None, action_command=None):
    """Create a consistent section header with icon, title, and optional action button"""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    
    label_text = f"{icon}  {title}" if icon else title
    ctk.CTkLabel(
        frame, text=label_text,
        font=FONT_SUBHEADER, text_color=TEXT_PRIMARY
    ).pack(side=tk.LEFT)
    
    if action_text and action_command:
        create_styled_button(
            frame, text=action_text, command=action_command,
            style_type='ghost', height=30, width=100
        ).pack(side=tk.RIGHT)
    
    return frame


def create_badge(parent, text, color=ACCENT_PRIMARY, bg=None, font=None):
    """Create a small colored badge/pill label"""
    badge_bg = bg or BG_LIGHT
    badge_font = font or FONT_TINY
    
    badge = ctk.CTkLabel(
        parent, text=f" {text} ",
        font=badge_font,
        text_color=color,
        fg_color=badge_bg,
        corner_radius=RADIUS_FULL,
        height=22,
    )
    return badge


def create_stat_bar(parent, value, max_value=100, color=ACCENT_PRIMARY, 
                    width=120, height=8, label=None):
    """Create a horizontal stat/progress bar"""
    container = ctk.CTkFrame(parent, fg_color="transparent")
    
    if label:
        ctk.CTkLabel(
            container, text=label, font=FONT_TINY, 
            text_color=TEXT_MUTED, anchor="w"
        ).pack(fill=tk.X)
    
    bar_frame = ctk.CTkFrame(
        container, fg_color=BG_DARK, corner_radius=4,
        width=width, height=height
    )
    bar_frame.pack(fill=tk.X)
    bar_frame.pack_propagate(False)
    
    # Fill
    ratio = min(1.0, max(0.0, value / max_value)) if max_value > 0 else 0
    fill_width = max(1, int(width * ratio))
    
    fill = ctk.CTkFrame(
        bar_frame, fg_color=color, corner_radius=4,
        width=fill_width, height=height
    )
    fill.place(x=0, y=0)
    
    return container


def create_divider(parent, label=None, color=None):
    """Create a styled horizontal divider with optional label"""
    div_color = color or BG_LIGHT
    
    if label:
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=20)
        # Left line
        ctk.CTkFrame(frame, fg_color=div_color, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, pady=10
        )
        ctk.CTkLabel(
            frame, text=f"  {label}  ", font=FONT_TINY,
            text_color=TEXT_MUTED, fg_color="transparent"
        ).pack(side=tk.LEFT)
        # Right line
        ctk.CTkFrame(frame, fg_color=div_color, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, pady=10
        )
        return frame
    else:
        return ctk.CTkFrame(parent, fg_color=div_color, height=1)


def create_icon_label(parent, icon, text, font=None, color=None, icon_color=None):
    """Create a label with an icon prefix — commonly used for metadata display"""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    if icon:
        ctk.CTkLabel(
            frame, text=icon, font=font or FONT_BODY,
            text_color=icon_color or TEXT_MUTED
        ).pack(side=tk.LEFT, padx=(0, SPACING_XS))
    ctk.CTkLabel(
        frame, text=text, font=font or FONT_BODY,
        text_color=color or TEXT_SECONDARY
    ).pack(side=tk.LEFT)
    return frame


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_rarity_color(rarity):
    return RARITY_COLORS.get(rarity, TEXT_SECONDARY)

def get_type_color(card_type):
    return TYPE_COLORS.get(card_type, TEXT_SECONDARY)

def get_type_icon(card_type):
    return TYPE_ICONS.get(card_type, '')

def get_grade_color(grade):
    """Get color for a race grade"""
    return GRADE_COLORS.get(grade, ACCENT_PRIMARY)


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
    """Premium tooltip popup on hover for any widget."""

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

        # Styled tooltip frame
        frame = tk.Frame(
            self.tip_window, background=BG_ELEVATED,
            highlightbackground=BG_LIGHT, highlightthickness=1
        )
        frame.pack()
        
        label = tk.Label(
            frame, text=self.text, justify=tk.LEFT,
            background=BG_ELEVATED, foreground=TEXT_PRIMARY,
            font=FONT_SMALL, padx=12, pady=8, wraplength=300
        )
        label.pack()

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


def create_tooltip(widget, text):
    """Convenience wrapper."""
    return Tooltip(widget, text)
