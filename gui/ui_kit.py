"""
AETHER UI primitives — buttons, surfaces, inputs built on design tokens.
"""

import customtkinter as ctk

from gui.design_system import (
    VOID_0, VOID_1, SURFACE, SURFACE_ELEVATED, BORDER_SUBTLE, BORDER_STRONG,
    SIGNAL_PRIMARY, SIGNAL_SECONDARY, SIGNAL_MINT, SIGNAL_ROSE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_ON_SIGNAL,
    FONT_BODY, FONT_BODY_BOLD, FONT_CAPTION, FONT_MICRO,
    RAD_STD, RAD_LG, RAD_PILL,
    S2, S3, S4,
)


def aether_button(parent, text, command=None, variant="ghost", width=None, height=36):
    """variant: primary | secondary | ghost | danger"""
    cfg = {
        "primary": {
            "fg": SIGNAL_PRIMARY, "hover": "#6d73e8", "text": TEXT_ON_SIGNAL,
            "font": FONT_BODY_BOLD,
        },
        "secondary": {
            "fg": SIGNAL_SECONDARY, "hover": "#a855f7", "text": TEXT_ON_SIGNAL,
            "font": FONT_BODY_BOLD,
        },
        "ghost": {
            "fg": "transparent", "hover": SURFACE_ELEVATED, "text": TEXT_SECONDARY,
            "font": FONT_BODY,
        },
        "danger": {
            "fg": SIGNAL_ROSE, "hover": "#f43f5e", "text": TEXT_ON_SIGNAL,
            "font": FONT_BODY_BOLD,
        },
    }
    c = cfg.get(variant, cfg["ghost"])
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=c["fg"], hover_color=c["hover"], text_color=c["text"],
        font=c["font"], corner_radius=RAD_STD, border_width=0,
        height=height, width=width or 120,
    )


def aether_surface(parent, elevated=False, **kwargs):
    return ctk.CTkFrame(
        parent,
        fg_color=SURFACE_ELEVATED if elevated else SURFACE,
        corner_radius=RAD_LG,
        border_width=1,
        border_color=BORDER_SUBTLE,
        **kwargs,
    )


def aether_input(parent, textvariable=None, placeholder="", **kwargs):
    return ctk.CTkEntry(
        parent, textvariable=textvariable, placeholder_text=placeholder,
        fg_color=VOID_1, border_color=BORDER_STRONG,
        text_color=TEXT_PRIMARY, font=FONT_BODY,
        corner_radius=RAD_STD, border_width=1, height=40,
        **kwargs,
    )


def aether_chip(parent, text, command=None, active=False):
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=SIGNAL_PRIMARY if active else SURFACE,
        hover_color=SURFACE_ELEVATED,
        text_color=TEXT_ON_SIGNAL if active else TEXT_MUTED,
        font=FONT_CAPTION, corner_radius=RAD_PILL, height=28, width=80,
        border_width=1 if not active else 0,
        border_color=BORDER_SUBTLE,
    )
