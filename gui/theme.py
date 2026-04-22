"""
AETHER Theme — PySide6 Edition
Design token bridge: maps design_system.py constants to PySide6-compatible
values (hex strings, QFont objects, QSS stylesheet fragments) and provides
factory functions for styled widgets.

All color/spacing/font constant NAMES are preserved so existing views can
import them without change.  Only the values that were CTk-specific (tuples
for fonts, ctk-widget factories) have been replaced with Qt equivalents.
"""

from PySide6.QtWidgets import (
    QPushButton, QLineEdit, QLabel, QFrame, QWidget, QScrollArea
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt

# ─── Re-export all design tokens so views can do:
#     from gui.theme import BG_DARK, ACCENT_PRIMARY, FONT_BODY, ...
# ─────────────────────────────────────────────────────────────────────────────

from gui.design_system import (
    VOID_0, VOID_1, VOID_2, SURFACE, SURFACE_ELEVATED,
    BORDER_SUBTLE, BORDER_STRONG,
    SIGNAL_PRIMARY, SIGNAL_SECONDARY, SIGNAL_MINT, SIGNAL_AMBER, SIGNAL_ROSE,
    SIGNAL_CYAN, SIGNAL_PRIMARY_DIM, SIGNAL_GLOW,
    FONT_UI, FONT_FALLBACK, FONT_MONO, FONT_MONO_FB,
    S0, S1, S2, S3, S4, S5, S6, S7, S8,
    SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL, SPACE_2XL,
    RAD_TIGHT, RAD_STD, RAD_LG, RAD_XL, RAD_PILL,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED, TEXT_ON_SIGNAL,
    RARITY_COLORS, TYPE_COLORS, TYPE_ICONS, GRADE_COLORS,
)

# ─── Background aliases (legacy names used throughout the views) ──────────────

BG_DARKEST  = VOID_0
BG_DARK     = VOID_1
BG_MEDIUM   = VOID_2
BG_LIGHT    = BORDER_SUBTLE
BG_HIGHLIGHT = BORDER_STRONG
BG_ELEVATED  = SURFACE_ELEVATED

# ─── Accent aliases ───────────────────────────────────────────────────────────

ACCENT_PRIMARY   = SIGNAL_PRIMARY
ACCENT_SECONDARY = SIGNAL_SECONDARY
ACCENT_TERTIARY  = SIGNAL_CYAN
ACCENT_SUCCESS   = SIGNAL_MINT
ACCENT_WARNING   = SIGNAL_AMBER
ACCENT_ERROR     = SIGNAL_ROSE
ACCENT_INFO      = SIGNAL_CYAN

# ─── Spacing aliases (SPACING_* → S* scale) ──────────────────────────────────

SPACING_XS  = S1    # 4
SPACING_SM  = S2    # 8
SPACING_MD  = S3    # 12
SPACING_LG  = S4    # 16
SPACING_XL  = S5    # 20
SPACING_2XL = S8    # 48

# ─── Radius aliases ───────────────────────────────────────────────────────────

RADIUS_SM   = RAD_TIGHT  # 6
RADIUS_MD   = RAD_STD    # 10
RADIUS_LG   = RAD_LG     # 16
RADIUS_FULL = RAD_PILL   # 999

# ─── Font family ──────────────────────────────────────────────────────────────

FONT_FAMILY = FONT_FALLBACK


# ─── QFont helpers ───────────────────────────────────────────────────────────

def _f(size: int, bold: bool = False, family: str = FONT_FALLBACK) -> QFont:
    font = QFont(family, size)
    if bold:
        font.setBold(True)
    return font


def _fm(size: int) -> QFont:
    """Monospace font."""
    f = QFont(FONT_MONO_FB, size)
    return f


# ─── Font constants (QFont objects, same names as the old CTk tuples) ─────────

FONT_DISPLAY    = _f(26, bold=True)
FONT_TITLE      = _f(20, bold=True)
FONT_HEADER     = _f(16, bold=True)
FONT_SUBHEADER  = _f(13, bold=True)
FONT_BODY       = _f(12)
FONT_BODY_BOLD  = _f(12, bold=True)
FONT_SMALL      = _f(11)
FONT_TINY       = _f(10)
FONT_MONO       = _fm(11)
FONT_MONO_SMALL = _fm(10)

# ─── Rarity / type helpers ────────────────────────────────────────────────────

RARITY_COLORS = {
    "SSR": "#ffd77a",
    "SR":  "#b0c4de",
    "R":   "#cd7f32",
}

def get_rarity_color(rarity: str) -> str:
    return RARITY_COLORS.get(rarity, TEXT_MUTED)


def get_type_icon(card_type: str) -> str:
    return TYPE_ICONS.get(card_type, "?")


def get_type_color(card_type: str) -> str:
    return TYPE_COLORS.get(card_type, TEXT_MUTED)


# ─── Master QSS Stylesheet ───────────────────────────────────────────────────

STYLESHEET = f"""
/* ──────────────────────── Global ──────────────────────── */
QWidget {{
    background-color: {VOID_1};
    color: {TEXT_PRIMARY};
    font-family: "{FONT_FALLBACK}";
    font-size: 12px;
    border: none;
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {VOID_0};
}}

/* ──────────────────────── Buttons ──────────────────────── */
QPushButton {{
    background-color: {BORDER_SUBTLE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RAD_STD}px;
    padding: 6px 14px;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: {BORDER_STRONG};
    border-color: {SIGNAL_PRIMARY};
}}
QPushButton:pressed {{
    background-color: {VOID_2};
}}
QPushButton:disabled {{
    color: {TEXT_DISABLED};
    background-color: {VOID_1};
    border-color: {BORDER_SUBTLE};
}}

/* Accent */
QPushButton[styleType="accent"] {{
    background-color: {SIGNAL_PRIMARY};
    color: {VOID_0};
    border-color: {SIGNAL_PRIMARY};
    font-weight: bold;
}}
QPushButton[styleType="accent"]:hover {{
    background-color: {SIGNAL_PRIMARY_DIM};
    border-color: {SIGNAL_PRIMARY_DIM};
}}
QPushButton[styleType="accent"]:disabled {{
    background-color: {BORDER_SUBTLE};
    color: {TEXT_DISABLED};
    border-color: {BORDER_SUBTLE};
}}

/* Secondary */
QPushButton[styleType="secondary"] {{
    background-color: {VOID_2};
    color: {SIGNAL_SECONDARY};
    border-color: {SIGNAL_SECONDARY};
}}
QPushButton[styleType="secondary"]:hover {{
    background-color: {SURFACE};
}}

/* Success */
QPushButton[styleType="success"] {{
    background-color: {SIGNAL_MINT};
    color: {VOID_0};
    border-color: {SIGNAL_MINT};
    font-weight: bold;
}}

/* Ghost */
QPushButton[styleType="ghost"] {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border-color: {BORDER_SUBTLE};
}}
QPushButton[styleType="ghost"]:hover {{
    color: {TEXT_PRIMARY};
    border-color: {BORDER_STRONG};
    background-color: {VOID_2};
}}

/* Danger */
QPushButton[styleType="danger"] {{
    background-color: {SIGNAL_ROSE};
    color: {VOID_0};
    border-color: {SIGNAL_ROSE};
    font-weight: bold;
}}

/* Pill / chip buttons */
QPushButton[styleType="chip"] {{
    background-color: {VOID_2};
    color: {TEXT_MUTED};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: {RAD_PILL}px;
    padding: 3px 10px;
    font-size: 10px;
}}
QPushButton[styleType="chip"]:hover {{
    border-color: {SIGNAL_PRIMARY};
    color: {TEXT_PRIMARY};
}}
QPushButton[styleType="chip"][active="true"] {{
    background-color: {SIGNAL_PRIMARY};
    color: {VOID_0};
    border-color: {SIGNAL_PRIMARY};
    font-weight: bold;
}}

/* ──────────────────────── Inputs ──────────────────────── */
QLineEdit {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: {RAD_STD}px;
    padding: 5px 10px;
    selection-background-color: {SIGNAL_PRIMARY};
}}
QLineEdit:focus {{
    border-color: {SIGNAL_PRIMARY};
    background-color: {VOID_2};
}}
QLineEdit:disabled {{
    color: {TEXT_DISABLED};
    background-color: {VOID_1};
}}
QLineEdit::placeholder {{
    color: {TEXT_DISABLED};
}}

QTextEdit, QPlainTextEdit {{
    background-color: {SURFACE};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: {RAD_STD}px;
    padding: 6px;
    selection-background-color: {SIGNAL_PRIMARY};
    font-family: "{FONT_MONO_FB}";
    font-size: 11px;
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {SIGNAL_PRIMARY};
}}

/* ──────────────────────── Labels ──────────────────────── */
QLabel {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
}}

/* ──────────────────────── ComboBox ──────────────────────── */
QComboBox {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: {RAD_STD}px;
    padding: 4px 10px;
    min-height: 26px;
}}
QComboBox:focus {{
    border-color: {SIGNAL_PRIMARY};
}}
QComboBox:disabled {{
    color: {TEXT_DISABLED};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
    subcontrol-origin: padding;
    subcontrol-position: right center;
}}
QComboBox::down-arrow {{
    image: none;
    width: 8px;
    height: 5px;
}}
QComboBox QAbstractItemView {{
    background-color: {VOID_2};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RAD_STD}px;
    selection-background-color: {SIGNAL_PRIMARY};
    selection-color: {TEXT_PRIMARY};
    padding: 4px;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    border-radius: {RAD_TIGHT}px;
    min-height: 22px;
}}

/* ──────────────────────── CheckBox ──────────────────────── */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 6px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {BORDER_STRONG};
    border-radius: {RAD_TIGHT}px;
    background-color: {SURFACE};
}}
QCheckBox::indicator:checked {{
    background-color: {SIGNAL_PRIMARY};
    border-color: {SIGNAL_PRIMARY};
}}
QCheckBox::indicator:hover {{
    border-color: {SIGNAL_PRIMARY};
}}

/* ──────────────────────── Scroll bars ──────────────────────── */
QScrollBar:vertical {{
    background: {VOID_0};
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {SIGNAL_PRIMARY};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {VOID_0};
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_STRONG};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {SIGNAL_PRIMARY};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ──────────────────────── Progress bar ──────────────────────── */
QProgressBar {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: {RAD_TIGHT}px;
    text-align: center;
    color: {TEXT_PRIMARY};
    font-size: 10px;
    min-height: 10px;
}}
QProgressBar::chunk {{
    background-color: {SIGNAL_PRIMARY};
    border-radius: {RAD_TIGHT}px;
}}

/* ──────────────────────── Scroll area ──────────────────────── */
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ──────────────────────── Frames ──────────────────────── */
QFrame[frameRole="card"] {{
    background-color: {VOID_2};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: {RAD_STD}px;
}}
QFrame[frameRole="glass"] {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RAD_LG}px;
}}
QFrame[frameRole="elevated"] {{
    background-color: {SURFACE_ELEVATED};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RAD_LG}px;
}}
QFrame[frameRole="divider"] {{
    background-color: {BORDER_SUBTLE};
    border: none;
}}

/* ──────────────────────── Tables ──────────────────────── */
QTableWidget, QTreeWidget, QListWidget {{
    background-color: {VOID_2};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: {RAD_STD}px;
    gridline-color: {BORDER_SUBTLE};
    selection-background-color: {SIGNAL_PRIMARY};
    selection-color: {VOID_0};
    alternate-background-color: {SURFACE};
    outline: none;
}}
QTableWidget::item, QTreeWidget::item, QListWidget::item {{
    padding: 5px 8px;
    border: none;
}}
QTableWidget::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {{
    background-color: {BORDER_SUBTLE};
}}
QHeaderView::section {{
    background-color: {VOID_1};
    color: {TEXT_MUTED};
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid {BORDER_SUBTLE};
    font-size: 11px;
    font-weight: bold;
}}
QHeaderView::section:hover {{
    color: {TEXT_PRIMARY};
    background-color: {VOID_2};
}}

/* ──────────────────────── Tab widget ──────────────────────── */
QTabWidget::pane {{
    background-color: {VOID_1};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: {RAD_STD}px;
    top: -1px;
}}
QTabBar::tab {{
    background-color: {VOID_2};
    color: {TEXT_MUTED};
    padding: 6px 16px;
    border: 1px solid {BORDER_SUBTLE};
    border-bottom: none;
    border-top-left-radius: {RAD_TIGHT}px;
    border-top-right-radius: {RAD_TIGHT}px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {VOID_1};
    color: {TEXT_PRIMARY};
    border-color: {SIGNAL_PRIMARY};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT_PRIMARY};
    background-color: {SURFACE};
}}

/* ──────────────────────── Splitter ──────────────────────── */
QSplitter::handle {{
    background-color: {BORDER_SUBTLE};
}}
QSplitter::handle:horizontal {{
    width: 4px;
}}
QSplitter::handle:vertical {{
    height: 4px;
}}
QSplitter::handle:hover {{
    background-color: {SIGNAL_PRIMARY};
}}

/* ──────────────────────── Tooltip ──────────────────────── */
QToolTip {{
    background-color: {SURFACE_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RAD_TIGHT}px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ──────────────────────── Menu / context menu ──────────────────────── */
QMenu {{
    background-color: {VOID_2};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RAD_STD}px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: {RAD_TIGHT}px;
}}
QMenu::item:selected {{
    background-color: {SIGNAL_PRIMARY};
    color: {VOID_0};
}}
QMenu::separator {{
    height: 1px;
    background-color: {BORDER_SUBTLE};
    margin: 4px 8px;
}}
"""


# ─── Widget factory functions (mirrors the old CTk factory functions) ─────────

def _apply_style(widget: QWidget, style_type: str) -> None:
    """Apply a named style type to a widget via dynamic Qt property."""
    widget.setProperty("styleType", style_type)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def create_styled_button(
    parent: QWidget = None,
    text: str = "",
    command=None,
    style_type: str = "default",
    width: int = 0,
    height: int = 0,
    state: str = "normal",
    **kwargs
) -> QPushButton:
    """Create a styled QPushButton matching the old CTk create_styled_button API."""
    btn = QPushButton(text, parent)
    if command:
        btn.clicked.connect(command)
    _apply_style(btn, style_type)
    if width > 0:
        btn.setMinimumWidth(width)
    if height > 0:
        btn.setFixedHeight(height)
    if state == "disabled":
        btn.setEnabled(False)
    return btn


def create_styled_entry(
    parent: QWidget = None,
    placeholder_text: str = "",
    width: int = 0,
    **kwargs
) -> QLineEdit:
    """Create a styled QLineEdit matching the old CTk create_styled_entry API."""
    entry = QLineEdit(parent)
    if placeholder_text:
        entry.setPlaceholderText(placeholder_text)
    if width > 0:
        entry.setFixedWidth(width)
    return entry


def create_card_frame(parent: QWidget = None) -> QFrame:
    """Create a styled card frame."""
    frame = QFrame(parent)
    frame.setProperty("frameRole", "card")
    frame.style().unpolish(frame)
    frame.style().polish(frame)
    return frame


def create_glass_frame(parent: QWidget = None) -> QFrame:
    """Create a glass-effect frame."""
    frame = QFrame(parent)
    frame.setProperty("frameRole", "glass")
    frame.style().unpolish(frame)
    frame.style().polish(frame)
    return frame


def create_section_header(parent: QWidget = None, text: str = "", icon: str = "") -> QLabel:
    """Create a section header label."""
    label = QLabel(f"{icon}  {text}" if icon else text, parent)
    label.setFont(FONT_SUBHEADER)
    label.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; padding: 4px 0;")
    return label


def create_styled_text(parent: QWidget = None, **kwargs) -> QLabel:
    """Compatibility stub — returns a plain QLabel."""
    return QLabel(parent)


def create_divider(parent: QWidget = None, horizontal: bool = True) -> QFrame:
    """Create a visual divider line."""
    frame = QFrame(parent)
    frame.setFrameShape(QFrame.Shape.HLine if horizontal else QFrame.Shape.VLine)
    frame.setProperty("frameRole", "divider")
    frame.style().unpolish(frame)
    frame.style().polish(frame)
    return frame


def create_badge(parent: QWidget, text: str, color: str = None) -> QLabel:
    """Create a small colored badge label."""
    label = QLabel(text, parent)
    label.setFont(FONT_TINY)
    fg = color or SIGNAL_PRIMARY
    label.setStyleSheet(
        f"color: {fg}; background-color: {VOID_2}; border: 1px solid {fg};"
        f"border-radius: {RAD_TIGHT}px; padding: 1px 6px;"
    )
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def make_scroll_area(parent: QWidget = None) -> tuple:
    """
    Create a QScrollArea with a transparent inner widget+layout.
    Returns (scroll_area, inner_widget) so callers can add children to inner_widget.
    """
    from PySide6.QtWidgets import QScrollArea as _QSA, QVBoxLayout
    scroll = _QSA(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    inner = QWidget()
    inner.setStyleSheet("background: transparent;")
    scroll.setWidget(inner)
    return scroll, inner
