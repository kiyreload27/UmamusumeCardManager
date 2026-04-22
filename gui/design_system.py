"""
AETHER — design tokens for Umamusume Support Card Manager
Futuristic control-panel aesthetic: void depth, indigo signal, mint data
"""

# ═══════════════════════════════════════════════════════════════════════════════
# DEPTH LAYERS (background stack)
# ═══════════════════════════════════════════════════════════════════════════════

VOID_0 = "#050508"       # deepest void — app root
VOID_1 = "#0c0c12"       # chrome / panels
VOID_2 = "#12121c"       # raised surface
SURFACE = "#18182a"      # cards, inputs
SURFACE_ELEVATED = "#1f1f34"
BORDER_SUBTLE = "#2a2a42"
BORDER_STRONG = "#3d3d5c"

# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL (semantic colour)
# ═══════════════════════════════════════════════════════════════════════════════

SIGNAL_PRIMARY = "#818cf8"    # indigo — primary actions, focus
SIGNAL_SECONDARY = "#c084fc"  # violet — secondary
SIGNAL_MINT = "#34d399"       # success / owned
SIGNAL_AMBER = "#fbbf24"      # SSR / warning
SIGNAL_ROSE = "#fb7185"       # error / danger
SIGNAL_CYAN = "#22d3ee"       # info / links

SIGNAL_PRIMARY_DIM = "#6366f1"
SIGNAL_GLOW = "#818cf818"

# ═══════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY — pairing: UI + numeric
# ═══════════════════════════════════════════════════════════════════════════════

FONT_UI = "Segoe UI Variable"
FONT_FALLBACK = "Segoe UI"
FONT_MONO = "Cascadia Mono"
FONT_MONO_FB = "Consolas"

FONT_HERO = (FONT_FALLBACK, 32, "bold")
FONT_DISPLAY = (FONT_FALLBACK, 26, "bold")
FONT_TITLE = (FONT_FALLBACK, 20, "bold")
FONT_HEADLINE = (FONT_FALLBACK, 16, "bold")
FONT_SUBHEAD = (FONT_FALLBACK, 13, "bold")
FONT_BODY = (FONT_FALLBACK, 12)
FONT_BODY_BOLD = (FONT_FALLBACK, 12, "bold")
FONT_CAPTION = (FONT_FALLBACK, 11)
FONT_MICRO = (FONT_FALLBACK, 10)
FONT_MONO_SIZE = (FONT_MONO_FB, 11)

# ═══════════════════════════════════════════════════════════════════════════════
# SPACING SCALE (4px base)
# ═══════════════════════════════════════════════════════════════════════════════

S0, S1, S2, S3, S4, S5, S6, S7, S8 = 0, 4, 8, 12, 16, 20, 24, 32, 48

# Legacy names mapped to scale
SPACE_XS = S1
SPACE_SM = S2
SPACE_MD = S3
SPACE_LG = S4
SPACE_XL = S6
SPACE_2XL = S8

# ═══════════════════════════════════════════════════════════════════════════════
# RADIUS
# ═══════════════════════════════════════════════════════════════════════════════

RAD_TIGHT = 6
RAD_STD = 10
RAD_LG = 16
RAD_XL = 22
RAD_PILL = 999

# ═══════════════════════════════════════════════════════════════════════════════
# TEXT
# ═══════════════════════════════════════════════════════════════════════════════

TEXT_PRIMARY = "#f4f4f8"
TEXT_SECONDARY = "#a8a8c0"
TEXT_MUTED = "#71718a"
TEXT_DISABLED = "#4b4b63"
TEXT_ON_SIGNAL = "#0a0a0f"

# ═══════════════════════════════════════════════════════════════════════════════
# GAME DATA (rarity / type / grade) — tuned for dark UI
# ═══════════════════════════════════════════════════════════════════════════════

RARITY_SSR = "#ffd77a"
RARITY_SR = "#b0c4de"
RARITY_R = "#cd7f32"
RARITY_COLORS = {"SSR": RARITY_SSR, "SR": RARITY_SR, "R": RARITY_R}

TYPE_COLORS = {
    "Speed": "#38bdf8",
    "Stamina": "#fb7185",
    "Power": "#fbbf24",
    "Guts": "#f87171",
    "Wisdom": "#34d399",
    "Friend": "#c084fc",
    "Group": "#fbbf24",
    "Friendship": "#c084fc",
}

TYPE_ICONS = {
    "Speed": "S", "Stamina": "T", "Power": "P",
    "Guts": "G", "Wisdom": "W", "Friend": "F", "Group": "M",
}

GRADE_COLORS = {
    "GI": RARITY_SSR, "G1": RARITY_SSR,
    "GII": RARITY_SR, "G2": RARITY_SR,
    "GIII": RARITY_R, "G3": RARITY_R,
    "OP": "#c084fc", "Pre-OP": "#d8b4fe",
}
