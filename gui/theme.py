"""
Centralized Theme Module for Umamusume Support Card Manager
Modern glassmorphism-inspired dark theme with consistent styling
"""

import tkinter as tk
from tkinter import ttk

# ═══════════════════════════════════════════════════════════════════════════════
# COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════════════════

# Primary backgrounds (rich purplish-blues with depth)
BG_DARKEST = '#0d0d1a'       # Deepest background
BG_DARK = '#151528'           # Main application background  
BG_MEDIUM = '#1e1e3f'         # Card/panel backgrounds
BG_LIGHT = '#2a2a5a'          # Elevated elements, hover states
BG_HIGHLIGHT = '#3d3d7a'      # Active/selected backgrounds

# Accents (vibrant but refined)
ACCENT_PRIMARY = '#ff6b9d'    # Pink accent (main action color)
ACCENT_SECONDARY = '#7c5cff'  # Purple accent (secondary actions)
ACCENT_TERTIARY = '#5ce1e6'   # Cyan accent (info/highlights)
ACCENT_SUCCESS = '#4ade80'    # Green for success states
ACCENT_WARNING = '#fbbf24'    # Amber for warnings
ACCENT_ERROR = '#ff6b6b'      # Red for errors

# Text colors
TEXT_PRIMARY = '#ffffff'      # Primary text (headings, important)
TEXT_SECONDARY = '#e0e0f0'    # Secondary text (body text)
TEXT_MUTED = '#9090b0'        # Muted text (labels, hints)
TEXT_DISABLED = '#606080'     # Disabled text

# Rarity colors (enhanced with glow effect potential)
RARITY_SSR = '#ffd700'        # Gold
RARITY_SR = '#c0c0c0'         # Silver
RARITY_R = '#cd853f'          # Bronze (warmer)

RARITY_COLORS = {
    'SSR': RARITY_SSR,
    'SR': RARITY_SR,
    'R': RARITY_R
}

# Type colors (for card types)
TYPE_COLORS = {
    'Speed': '#3b82f6',       # Blue
    'Stamina': '#f97316',     # Orange
    'Power': '#eab308',       # Yellow
    'Guts': '#ef4444',        # Red
    'Wisdom': '#22c55e',      # Green
    'Friend': '#a855f7',      # Purple
    'Group': '#f59e0b'        # Amber
}

# Type icons
TYPE_ICONS = {
    'Speed': '🏃',
    'Stamina': '💚',
    'Power': '💪',
    'Guts': '🔥',
    'Wisdom': '🧠',
    'Friend': '💜',
    'Group': '👥'
}

# ═══════════════════════════════════════════════════════════════════════════════
# FONTS
# ═══════════════════════════════════════════════════════════════════════════════

FONT_FAMILY = 'Segoe UI'
FONT_FAMILY_MONO = 'Consolas'

FONT_TITLE = (FONT_FAMILY, 18, 'bold')
FONT_HEADER = (FONT_FAMILY, 14, 'bold')
FONT_SUBHEADER = (FONT_FAMILY, 12, 'bold')
FONT_BODY = (FONT_FAMILY, 11)
FONT_BODY_BOLD = (FONT_FAMILY, 11, 'bold')
FONT_SMALL = (FONT_FAMILY, 10)
FONT_TINY = (FONT_FAMILY, 9)
FONT_MONO = (FONT_FAMILY_MONO, 11)
FONT_MONO_SMALL = (FONT_FAMILY_MONO, 10)

# ═══════════════════════════════════════════════════════════════════════════════
# STYLE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def configure_styles(root: tk.Tk):
    """Configure all ttk styles for the application"""
    style = ttk.Style()
    
    # Use clam theme as base for better customization
    style.theme_use('clam')
    
    # ─────────────────────────────────────────────────────────────────────────
    # General Frame and Label styles
    # ─────────────────────────────────────────────────────────────────────────
    style.configure('TFrame', background=BG_DARK)
    style.configure('TLabel', background=BG_DARK, foreground=TEXT_SECONDARY, font=FONT_BODY)
    style.configure('TLabelframe', background=BG_DARK, foreground=TEXT_SECONDARY)
    style.configure('TLabelframe.Label', background=BG_DARK, foreground=ACCENT_PRIMARY, font=FONT_SUBHEADER)
    
    # Header styles
    style.configure('Title.TLabel', font=FONT_TITLE, foreground=TEXT_PRIMARY, background=BG_DARK)
    style.configure('Header.TLabel', font=FONT_HEADER, foreground=ACCENT_PRIMARY, background=BG_DARK)
    style.configure('Subheader.TLabel', font=FONT_SUBHEADER, foreground=TEXT_PRIMARY, background=BG_DARK)
    style.configure('Subtitle.TLabel', font=FONT_SMALL, foreground=TEXT_MUTED, background=BG_DARK)
    style.configure('Stats.TLabel', font=FONT_SMALL, foreground=TEXT_SECONDARY, background=BG_MEDIUM, padding=8)
    style.configure('Accent.TLabel', font=FONT_BODY, foreground=ACCENT_PRIMARY, background=BG_DARK)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Button styles
    # ─────────────────────────────────────────────────────────────────────────
    style.configure('TButton',
                    padding=(12, 6),
                    font=FONT_BODY,
                    background=BG_LIGHT,
                    foreground=TEXT_PRIMARY)
    style.map('TButton',
              background=[('active', BG_HIGHLIGHT), ('pressed', ACCENT_PRIMARY)],
              foreground=[('active', TEXT_PRIMARY), ('pressed', TEXT_PRIMARY)])
    
    style.configure('Accent.TButton',
                    padding=(12, 6),
                    font=FONT_BODY_BOLD,
                    background=ACCENT_PRIMARY,
                    foreground=TEXT_PRIMARY)
    style.map('Accent.TButton',
              background=[('active', '#ff8ab5'), ('pressed', '#e55a88')])
    
    style.configure('Small.TButton',
                    padding=(8, 4),
                    font=FONT_SMALL)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Checkbutton styles
    # ─────────────────────────────────────────────────────────────────────────
    style.configure('TCheckbutton',
                    background=BG_DARK,
                    foreground=TEXT_SECONDARY,
                    font=FONT_BODY)
    style.map('TCheckbutton',
              background=[('active', BG_DARK)],
              foreground=[('active', TEXT_PRIMARY)])
    
    style.configure('Large.TCheckbutton',
                    font=FONT_BODY_BOLD,
                    background=BG_DARK,
                    foreground=TEXT_PRIMARY)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Entry and Combobox styles
    # ─────────────────────────────────────────────────────────────────────────
    style.configure('TEntry',
                    fieldbackground=BG_MEDIUM,
                    foreground=TEXT_PRIMARY,
                    insertcolor=TEXT_PRIMARY,
                    padding=6)
    
    style.configure('TCombobox',
                    fieldbackground=BG_MEDIUM,
                    background=BG_LIGHT,
                    foreground=TEXT_PRIMARY,
                    arrowcolor=TEXT_MUTED,
                    padding=4)
    style.map('TCombobox',
              fieldbackground=[('readonly', BG_MEDIUM)],
              selectbackground=[('readonly', BG_HIGHLIGHT)])
    
    # ─────────────────────────────────────────────────────────────────────────
    # Notebook (Tab) styles
    # ─────────────────────────────────────────────────────────────────────────
    style.configure('TNotebook', 
                    background=BG_DARK,
                    borderwidth=0)
    style.configure('TNotebook.Tab',
                    padding=(20, 10),
                    font=FONT_BODY_BOLD,
                    background=BG_MEDIUM,
                    foreground=TEXT_MUTED)
    style.map('TNotebook.Tab',
              background=[('selected', BG_LIGHT), ('active', BG_HIGHLIGHT)],
              foreground=[('selected', ACCENT_PRIMARY), ('active', TEXT_PRIMARY)],
              expand=[('selected', (0, 0, 0, 2))])
    
    # ─────────────────────────────────────────────────────────────────────────
    # Treeview styles
    # ─────────────────────────────────────────────────────────────────────────
    style.configure('Treeview',
                    background=BG_MEDIUM,
                    foreground=TEXT_SECONDARY,
                    fieldbackground=BG_MEDIUM,
                    font=FONT_BODY,
                    rowheight=28)
    style.configure('Treeview.Heading',
                    font=FONT_BODY_BOLD,
                    background=BG_LIGHT,
                    foreground=TEXT_PRIMARY,
                    padding=6)
    style.map('Treeview',
              background=[('selected', ACCENT_PRIMARY)],
              foreground=[('selected', TEXT_PRIMARY)])
    style.map('Treeview.Heading',
              background=[('active', BG_HIGHLIGHT)])
    
    # Card list with larger rows for thumbnails
    style.configure('CardList.Treeview',
                    background=BG_MEDIUM,
                    foreground=TEXT_SECONDARY,
                    fieldbackground=BG_MEDIUM,
                    font=FONT_BODY,
                    rowheight=60)
    
    # Deck list style
    style.configure('DeckList.Treeview',
                    background=BG_MEDIUM,
                    foreground=TEXT_SECONDARY,
                    fieldbackground=BG_MEDIUM,
                    font=FONT_BODY,
                    rowheight=60)
    style.map('DeckList.Treeview',
              background=[('selected', ACCENT_PRIMARY)])
    
    # ─────────────────────────────────────────────────────────────────────────
    # Scale (Slider) styles
    # ─────────────────────────────────────────────────────────────────────────
    style.configure('TScale',
                    background=BG_DARK,
                    troughcolor=BG_MEDIUM,
                    sliderthickness=18)
    style.configure('Horizontal.TScale',
                    background=BG_DARK)
    
    
    # ─────────────────────────────────────────────────────────────────────────
    # Scrollbar styles
    # ─────────────────────────────────────────────────────────────────────────
    style.configure('TScrollbar',
                    background=BG_LIGHT,
                    troughcolor=BG_MEDIUM,
                    borderwidth=0,
                    arrowsize=14)
    style.map('TScrollbar',
              background=[('active', BG_HIGHLIGHT), ('pressed', ACCENT_PRIMARY)])
    
    # ─────────────────────────────────────────────────────────────────────────
    # PanedWindow styles
    # ─────────────────────────────────────────────────────────────────────────
    style.configure('TPanedwindow', background=BG_DARK)
    
    # Set root background
    root.configure(bg=BG_DARK)


# ═══════════════════════════════════════════════════════════════════════════════
# WIDGET HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def create_styled_entry(parent, textvariable=None, **kwargs):
    """Create a styled tk.Entry with modern appearance"""
    entry = ttk.Entry(
        parent,
        textvariable=textvariable,
        font=FONT_BODY,
        **kwargs
    )
    return entry

def create_styled_button(parent, text, command=None, style_type='default', **kwargs):
    """Create a styled tk.Button with modern appearance"""
    bg_colors = {
        'default': BG_LIGHT,
        'accent': ACCENT_PRIMARY,
        'secondary': ACCENT_SECONDARY,
        'success': ACCENT_SUCCESS,
        'warning': ACCENT_WARNING,
        'danger': ACCENT_ERROR
    }
    hover_colors = {
        'default': BG_HIGHLIGHT,
        'accent': '#ff8ab5',
        'secondary': '#9580ff',
        'success': '#6ee7a0',
        'warning': '#fcd34d',
        'danger': '#ff8a8a'
    }
    
    bg = bg_colors.get(style_type, BG_LIGHT)
    hover_bg = hover_colors.get(style_type, BG_HIGHLIGHT)
    
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=TEXT_PRIMARY,
        font=FONT_BODY_BOLD if style_type == 'accent' else FONT_BODY,
        activebackground=hover_bg,
        activeforeground=TEXT_PRIMARY,
        bd=0,
        padx=16,
        pady=8,
        cursor='hand2',
        relief=tk.FLAT,
        **kwargs
    )
    
    # Add hover effect
    def on_enter(e):
        btn.configure(bg=hover_bg)
    def on_leave(e):
        btn.configure(bg=bg)
    
    btn.bind('<Enter>', on_enter)
    btn.bind('<Leave>', on_leave)
    
    return btn


def create_styled_text(parent, height=10, **kwargs):
    """Create a styled tk.Text widget with modern appearance"""
    text = tk.Text(
        parent,
        bg=BG_MEDIUM,
        fg=TEXT_SECONDARY,
        font=FONT_MONO,
        insertbackground=TEXT_PRIMARY,
        selectbackground=ACCENT_PRIMARY,
        selectforeground=TEXT_PRIMARY,
        relief=tk.FLAT,
        padx=12,
        pady=12,
        height=height,
        wrap=tk.WORD,
        **kwargs
    )
    return text


def create_card_frame(parent, **kwargs):
    """Create a styled frame that looks like a card"""
    frame = tk.Frame(
        parent,
        bg=BG_MEDIUM,
        highlightthickness=1,
        highlightbackground=BG_LIGHT,
        **kwargs
    )
    return frame


def get_rarity_color(rarity):
    """Get the color for a card rarity"""
    return RARITY_COLORS.get(rarity, TEXT_SECONDARY)


def get_type_color(card_type):
    """Get the color for a card type"""
    return TYPE_COLORS.get(card_type, TEXT_SECONDARY)


def get_type_icon(card_type):
    """Get the emoji icon for a card type"""
    return TYPE_ICONS.get(card_type, '')

# ═══════════════════════════════════════════════════════════════════════════════
# TOOLTIPS & HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

EFFECT_DESCRIPTIONS = {
    "Friendship Bonus": "Increases stats gained when training with this support card during Friendship Training (orange aura).",
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
    """
    Creates a tooltip for a given widget as the mouse hovers above it.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = self.y = 0
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
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        try:
            x, y, cx, cy = self.widget.bbox("insert")
        except:
             pass
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        # Creates a toplevel window
        self.tip_window = tk.Toplevel(self.widget)
        
        # Leaves only the label and removes the app window
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(
            self.tip_window, 
            text=self.text, 
            justify=tk.LEFT,
            background=BG_LIGHT, 
            foreground=TEXT_PRIMARY,
            relief=tk.SOLID, 
            borderwidth=1,
            font=FONT_SMALL,
            padx=10,
            pady=5
        )
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

def create_tooltip(widget, text):
    """Create a tooltip for a widget"""
    return Tooltip(widget, text)
