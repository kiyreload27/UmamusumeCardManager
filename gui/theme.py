"""
Centralized Theme Module for Umamusume Support Card Manager
Warm charcoal & rose-gold aesthetic — comfortable for long sessions, true to the game's feel
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
# COLOR PALETTE — Warm charcoal base + rose-gold accents
# ═══════════════════════════════════════════════════════════════════════════════

# Backgrounds — Warm, layered dark surfaces (brown-tinted, not blue-tinted)
BG_DARKEST  = '#13100f'   # Deepest warm charcoal — main content backdrop
BG_DARK     = '#1d1917'   # Panels, sidebar
BG_MEDIUM   = '#272220'   # Cards, input fields
BG_LIGHT    = '#332e2b'   # Borders, dividers
BG_HIGHLIGHT = '#3f3835'  # Active states, selections
BG_ELEVATED = '#2c2724'   # Elevated card surfaces

# Glass overlay
GLASS_BG     = '#2c272480'
GLASS_BORDER = '#ffffff10'

# Accents — Warm rose / gold / sage system
ACCENT_PRIMARY   = '#d4836a'   # Dusty rose-orange (CTAs, active nav)
ACCENT_SECONDARY = '#c9a84c'   # Warm gold (secondary elements)
ACCENT_TERTIARY  = '#9b7ec8'   # Muted lavender (highlights, special items)
ACCENT_SUCCESS   = '#6dab7a'   # Sage green
ACCENT_WARNING   = '#d4924a'   # Warm amber
ACCENT_ERROR     = '#c96464'   # Muted red
ACCENT_INFO      = '#5fa8c8'   # Muted teal

# Glow variants
ACCENT_PRIMARY_GLOW   = '#d4836a28'
ACCENT_SUCCESS_GLOW   = '#6dab7a28'
ACCENT_WARNING_GLOW   = '#d4924a28'
ACCENT_ERROR_GLOW     = '#c9646428'

# Text — Warm-tinted for comfort during extended use
TEXT_PRIMARY   = '#f2ebe4'   # Warm cream (headers, main content)
TEXT_SECONDARY = '#cec5bb'   # Warm greige (body text)
TEXT_MUTED     = '#9d9089'   # Warm taupe (captions, labels)
TEXT_DISABLED  = '#6b6058'   # Dimmed (disabled states)
TEXT_INVERSE   = '#13100f'   # For text on bright backgrounds

# Rarity — Consistent, vibrant
RARITY_SSR = '#d4924a'    # Warm amber/gold
RARITY_SR  = '#b0b8c4'    # Cool silver (contrast intentional)
RARITY_R   = '#a07850'    # Warm bronze
RARITY_COLORS = {'SSR': RARITY_SSR, 'SR': RARITY_SR, 'R': RARITY_R}

# Card type colors — warmer variants of the originals
TYPE_COLORS = {
    'Speed':   '#7ab0e8',   # Soft blue
    'Stamina': '#e07860',   # Warm terracotta
    'Power':   '#d4b44a',   # Gold-yellow
    'Guts':    '#d47070',   # Warm red
    'Wisdom':  '#6dab7a',   # Sage green
    'Friend':  '#b07ad4',   # Soft purple
    'Group':   '#d4924a',   # Warm amber
}
TYPE_ICONS = {
    'Speed': '🏃', 'Stamina': '💚', 'Power': '💪',
    'Guts': '🔥', 'Wisdom': '🧠', 'Friend': '💜', 'Group': '👥'
}

# Race grade colors
GRADE_COLORS = {
    'GI':  '#d4924a', 'G1':  '#d4924a',   # Warm gold
    'GII': '#b0b8c4', 'G2':  '#b0b8c4',   # Silver
    'GIII':'#a07850', 'G3':  '#a07850',   # Bronze
    'OP':  '#9b7ec8', 'Pre-OP': '#b09ad4', # Lavender
}

# ═══════════════════════════════════════════════════════════════════════════════
# SPACING & RADIUS TOKENS
# ═══════════════════════════════════════════════════════════════════════════════

SPACING_XS  = 4
SPACING_SM  = 8
SPACING_MD  = 16
SPACING_LG  = 24
SPACING_XL  = 32
SPACING_2XL = 48

RADIUS_SM   = 6
RADIUS_MD   = 10
RADIUS_LG   = 16
RADIUS_XL   = 22
RADIUS_FULL = 100

# Sidebar
SIDEBAR_WIDTH_EXPANDED  = 220
SIDEBAR_WIDTH_COLLAPSED = 58

# ═══════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY
# ═══════════════════════════════════════════════════════════════════════════════

FONT_FAMILY      = 'Segoe UI'
FONT_FAMILY_MONO = 'Consolas'

FONT_DISPLAY    = (FONT_FAMILY, 26, 'bold')
FONT_TITLE      = (FONT_FAMILY, 20, 'bold')
FONT_HEADER     = (FONT_FAMILY, 15, 'bold')
FONT_SUBHEADER  = (FONT_FAMILY, 13, 'bold')
FONT_BODY       = (FONT_FAMILY, 12)
FONT_BODY_BOLD  = (FONT_FAMILY, 12, 'bold')
FONT_SMALL      = (FONT_FAMILY, 11)
FONT_TINY       = (FONT_FAMILY, 10)
FONT_MONO       = (FONT_FAMILY_MONO, 12)
FONT_MONO_SMALL = (FONT_FAMILY_MONO, 11)

# ═══════════════════════════════════════════════════════════════════════════════
# TTK STYLE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def configure_styles(root: tk.Tk):
    """Configure ttk styles for legacy widgets (Treeview, Scrollbar, etc.)"""
    style = ttk.Style()
    style.theme_use('clam')

    style.configure('TFrame', background=BG_DARK)
    style.configure('TLabel', background=BG_DARK, foreground=TEXT_SECONDARY, font=FONT_BODY)
    style.configure('TLabelframe', background=BG_DARK, foreground=TEXT_SECONDARY)
    style.configure('TLabelframe.Label', background=BG_DARK, foreground=ACCENT_PRIMARY, font=FONT_SUBHEADER)

    style.configure('Title.TLabel',     font=FONT_TITLE,     foreground=TEXT_PRIMARY,   background=BG_DARK)
    style.configure('Header.TLabel',    font=FONT_HEADER,    foreground=ACCENT_PRIMARY, background=BG_DARK)
    style.configure('Subheader.TLabel', font=FONT_SUBHEADER, foreground=TEXT_PRIMARY,   background=BG_DARK)
    style.configure('Subtitle.TLabel',  font=FONT_SMALL,     foreground=TEXT_MUTED,     background=BG_DARK)
    style.configure('Stats.TLabel',     font=FONT_SMALL,     foreground=TEXT_SECONDARY, background=BG_MEDIUM, padding=8)
    style.configure('Accent.TLabel',    font=FONT_BODY,      foreground=ACCENT_PRIMARY, background=BG_DARK)

    style.configure('TButton', padding=(12, 6), font=FONT_BODY, background=BG_LIGHT, foreground=TEXT_PRIMARY)
    style.map('TButton',
              background=[('active', BG_HIGHLIGHT), ('pressed', ACCENT_PRIMARY)],
              foreground=[('active', TEXT_PRIMARY), ('pressed', TEXT_PRIMARY)])
    style.configure('Accent.TButton', padding=(12, 6), font=FONT_BODY_BOLD,
                    background=ACCENT_PRIMARY, foreground=TEXT_PRIMARY)
    style.configure('Small.TButton', padding=(8, 4), font=FONT_SMALL)

    style.configure('TCheckbutton', background=BG_DARK, foreground=TEXT_SECONDARY, font=FONT_BODY)
    style.map('TCheckbutton', background=[('active', BG_DARK)], foreground=[('active', TEXT_PRIMARY)])
    style.configure('Large.TCheckbutton', font=FONT_BODY_BOLD, background=BG_DARK, foreground=TEXT_PRIMARY)

    style.configure('TEntry', fieldbackground=BG_MEDIUM, foreground=TEXT_PRIMARY,
                    insertcolor=TEXT_PRIMARY, padding=6)
    style.configure('TCombobox', fieldbackground=BG_MEDIUM, background=BG_LIGHT,
                    foreground=TEXT_PRIMARY, arrowcolor=TEXT_MUTED, padding=4)
    style.map('TCombobox', fieldbackground=[('readonly', BG_MEDIUM)],
              selectbackground=[('readonly', BG_HIGHLIGHT)])

    style.configure('TNotebook', background=BG_DARK, borderwidth=0)
    style.configure('TNotebook.Tab', padding=(20, 10), font=FONT_BODY_BOLD,
                    background=BG_MEDIUM, foreground=TEXT_MUTED)
    style.map('TNotebook.Tab',
              background=[('selected', BG_LIGHT), ('active', BG_HIGHLIGHT)],
              foreground=[('selected', ACCENT_PRIMARY), ('active', TEXT_PRIMARY)],
              expand=[('selected', (0, 0, 0, 2))])

    # Treeview
    style.configure('Treeview',
                    background=BG_MEDIUM, foreground=TEXT_SECONDARY,
                    fieldbackground=BG_MEDIUM, font=FONT_BODY, rowheight=36)
    style.configure('Treeview.Heading',
                    font=FONT_BODY_BOLD, background=BG_LIGHT,
                    foreground=TEXT_PRIMARY, padding=8)
    style.map('Treeview',
              background=[('selected', ACCENT_PRIMARY)],
              foreground=[('selected', TEXT_INVERSE)])
    style.map('Treeview.Heading', background=[('active', BG_HIGHLIGHT)])

    style.configure('CardList.Treeview',
                    background=BG_MEDIUM, foreground=TEXT_SECONDARY,
                    fieldbackground=BG_MEDIUM, font=FONT_BODY, rowheight=80)
    style.configure('DeckList.Treeview',
                    background=BG_MEDIUM, foreground=TEXT_SECONDARY,
                    fieldbackground=BG_MEDIUM, font=FONT_BODY, rowheight=80)
    style.map('DeckList.Treeview', background=[('selected', ACCENT_PRIMARY)])

    style.configure('TScale', background=BG_DARK, troughcolor=BG_MEDIUM, sliderthickness=18)
    style.configure('TScrollbar', background=BG_LIGHT, troughcolor=BG_DARKEST,
                    borderwidth=0, arrowsize=0, width=6)
    style.map('TScrollbar', background=[('active', BG_HIGHLIGHT), ('pressed', ACCENT_PRIMARY)])
    style.configure('TPanedwindow', background=BG_DARK)

    root.configure(bg=BG_DARKEST)


# ═══════════════════════════════════════════════════════════════════════════════
# CTK WIDGET FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════

def create_styled_entry(parent, textvariable=None, **kwargs):
    """Styled CTkEntry with warm focus feel"""
    kwargs.pop('bg', None); kwargs.pop('fg', None)
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
    """Styled CTkButton with warm variants"""
    _fg = {
        'default':   BG_LIGHT,
        'accent':    ACCENT_PRIMARY,
        'secondary': ACCENT_SECONDARY,
        'success':   ACCENT_SUCCESS,
        'warning':   ACCENT_WARNING,
        'danger':    ACCENT_ERROR,
        'ghost':     'transparent',
    }
    _hover = {
        'default':   BG_HIGHLIGHT,
        'accent':    '#bf6e58',
        'secondary': '#b4923e',
        'success':   '#5a9467',
        'warning':   '#bf7e3c',
        'danger':    '#b45050',
        'ghost':     BG_LIGHT,
    }
    _text = {
        'default':   TEXT_PRIMARY,
        'accent':    TEXT_PRIMARY,
        'secondary': TEXT_INVERSE,
        'success':   TEXT_PRIMARY,
        'warning':   TEXT_INVERSE,
        'danger':    TEXT_PRIMARY,
        'ghost':     TEXT_SECONDARY,
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
    """Sidebar nav button with warm active indicator"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'fg', 'activebackground', 'activeforeground', 'padx', 'pady')}
    bg_color   = BG_HIGHLIGHT if active else 'transparent'
    text_color = ACCENT_PRIMARY if active else TEXT_MUTED
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=bg_color, hover_color=BG_LIGHT,
        text_color=text_color, font=FONT_BODY_BOLD,
        corner_radius=RADIUS_MD, anchor='w', height=42,
        border_width=0, **safe
    )


def create_styled_text(parent, height=10, **kwargs):
    """Styled CTkTextbox"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'fg', 'selectbackground', 'selectforeground',
                         'relief', 'insertbackground', 'padx', 'pady', 'wrap')}
    return ctk.CTkTextbox(
        parent, height=height * 22,
        font=FONT_MONO, corner_radius=RADIUS_MD,
        text_color=TEXT_PRIMARY, fg_color=BG_DARK,
        border_color=BG_LIGHT, border_width=1, **safe
    )


def create_card_frame(parent, elevated=False, **kwargs):
    """Styled card frame with warm surface"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'highlightthickness', 'highlightbackground')}
    return ctk.CTkFrame(
        parent,
        corner_radius=RADIUS_LG,
        fg_color=BG_ELEVATED if elevated else BG_MEDIUM,
        border_width=1,
        border_color=BG_LIGHT,
        **safe,
    )


def create_glass_frame(parent, **kwargs):
    """Elevated glass-style panel"""
    safe = {k: v for k, v in kwargs.items()
            if k not in ('bg', 'highlightthickness', 'highlightbackground')}
    return ctk.CTkFrame(
        parent, corner_radius=RADIUS_LG,
        fg_color=BG_ELEVATED, border_width=1, border_color=BG_LIGHT, **safe,
    )


def create_section_header(parent, title, icon='', action_text=None, action_command=None):
    """Consistent section header"""
    frame = ctk.CTkFrame(parent, fg_color='transparent')
    label_text = f'{icon}  {title}' if icon else title
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
    """Small colored badge/pill"""
    return ctk.CTkLabel(
        parent, text=f' {text} ',
        font=font or FONT_TINY,
        text_color=color,
        fg_color=bg or BG_LIGHT,
        corner_radius=RADIUS_FULL,
        height=22,
    )


def create_stat_bar(parent, value, max_value=100, color=ACCENT_PRIMARY,
                    width=120, height=8, label=None):
    """Horizontal stat/progress bar"""
    container = ctk.CTkFrame(parent, fg_color='transparent')
    if label:
        ctk.CTkLabel(
            container, text=label, font=FONT_TINY,
            text_color=TEXT_MUTED, anchor='w'
        ).pack(fill=tk.X)
    bar_frame = ctk.CTkFrame(
        container, fg_color=BG_DARK, corner_radius=4,
        width=width, height=height
    )
    bar_frame.pack(fill=tk.X)
    bar_frame.pack_propagate(False)
    ratio = min(1.0, max(0.0, value / max_value)) if max_value > 0 else 0
    fill_width = max(1, int(width * ratio))
    ctk.CTkFrame(
        bar_frame, fg_color=color, corner_radius=4,
        width=fill_width, height=height
    ).place(x=0, y=0)
    return container


def create_divider(parent, label=None, color=None):
    """Horizontal divider with optional label"""
    div_color = color or BG_LIGHT
    if label:
        frame = ctk.CTkFrame(parent, fg_color='transparent', height=20)
        ctk.CTkFrame(frame, fg_color=div_color, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, pady=10)
        ctk.CTkLabel(
            frame, text=f'  {label}  ', font=FONT_TINY,
            text_color=TEXT_MUTED, fg_color='transparent'
        ).pack(side=tk.LEFT)
        ctk.CTkFrame(frame, fg_color=div_color, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, pady=10)
        return frame
    else:
        return ctk.CTkFrame(parent, fg_color=div_color, height=1)


def create_icon_label(parent, icon, text, font=None, color=None, icon_color=None):
    """Label with icon prefix"""
    frame = ctk.CTkFrame(parent, fg_color='transparent')
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
    return GRADE_COLORS.get(grade, ACCENT_PRIMARY)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLTIPS
# ═══════════════════════════════════════════════════════════════════════════════

EFFECT_DESCRIPTIONS = {
    "Friendship Bonus":  "Increases stats gained during Friendship Training (orange aura).",
    "Motivation Bonus":  "Increases stats gained based on your Uma's motivation level.",
    "Specialty Rate":    "Increases the chance of this card appearing in its specialty training.",
    "Training Bonus":    "Flat percentage increase to stats gained in training where this card is present.",
    "Initial Bond":      "Starting gauge value for this card.",
    "Race Bonus":        "Increases stats gained from racing.",
    "Fan Count Bonus":   "Increases fans gained from racing.",
    "Skill Pt Bonus":    "Bonus skill points gained when training with this card.",
    "Hint Lv":           "Starting level of skills taught by this card's hints.",
    "Hint Rate":         "Increases chance of getting a hint event.",
    "Minigame Fail Rate":"Reduces chance of failing training.",
    "Energy Usage":      "Reduces energy consumed during training.",
    "Current Energy":    "Increases starting energy in scenario.",
    "Vitality":          "Increases vitality gain from events.",
    "Stamina":           "Increases stamina gain from training.",
    "Speed":             "Increases speed gain from training.",
    "Power":             "Increases power gain from training.",
    "Guts":              "Increases guts gain from training.",
    "Wisdom":            "Increases wisdom gain from training.",
    "Logic":             "Custom logic effect.",
    "Starting Stats":    "Increases initial stats at start of scenario.",
}


class Tooltip:
    """Tooltip popup on hover"""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self._id1 = self.widget.bind('<Enter>', self.enter)
        self._id2 = self.widget.bind('<Leave>', self.leave)
        self._id3 = self.widget.bind('<ButtonPress>', self.leave)

    def enter(self, event=None):    self.schedule()
    def leave(self, event=None):    self.unschedule(); self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(400, self.showtip)

    def unschedule(self):
        _id = self.id; self.id = None
        if _id: self.widget.after_cancel(_id)

    def showtip(self, event=None):
        x = y = 0
        try:
            x, y, cx, cy = self.widget.bbox('insert')
        except Exception:
            pass
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f'+{x}+{y}')
        frame = tk.Frame(
            self.tip_window, background=BG_ELEVATED,
            highlightbackground=BG_LIGHT, highlightthickness=1
        )
        frame.pack()
        tk.Label(
            frame, text=self.text, justify=tk.LEFT,
            background=BG_ELEVATED, foreground=TEXT_PRIMARY,
            font=FONT_SMALL, padx=12, pady=8, wraplength=300
        ).pack()

    def hidetip(self):
        tw = self.tip_window; self.tip_window = None
        if tw: tw.destroy()


def create_tooltip(widget, text):
    return Tooltip(widget, text)
