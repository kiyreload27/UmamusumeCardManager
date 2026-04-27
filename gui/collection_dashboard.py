"""
Collection Progress Dashboard — PySide6 edition.
Visual overview of card collection with stats, ring charts (QPainter),
and type breakdown progress bars.
"""

import sys
import os
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_database_stats, get_owned_count, get_collection_stats
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER,
    FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
    RARITY_COLORS, TYPE_COLORS, get_type_icon,
    create_styled_button,
)


# ─── Ring Chart Widget ────────────────────────────────────────────────────────

class RingChart(QWidget):
    """Custom QPainter ring/donut chart."""

    def __init__(self, pct: float, color: str, label: str, owned: int, total: int, parent=None):
        super().__init__(parent)
        self.pct = pct
        self.color = QColor(color)
        self.label = label
        self.owned = owned
        self.total = total
        self.setFixedSize(130, 150)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = 110
        thickness = 14
        margin = (self.width() - size) // 2
        rect = QRect(margin, 4, size, size)

        # Background ring
        bg_pen = QPen(QColor(BG_MEDIUM))
        bg_pen.setWidth(thickness)
        bg_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(bg_pen)
        p.drawArc(rect, 0, 360 * 16)

        # Foreground ring
        if self.pct > 0:
            fg_pen = QPen(self.color)
            fg_pen.setWidth(thickness)
            fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(fg_pen)
            span = int(self.pct / 100 * 360 * 16)
            p.drawArc(rect, 90 * 16, -span)

        # Center text: rarity label
        p.setPen(self.color)
        lbl_font = QFont(FONT_TITLE)
        lbl_font.setPointSize(13)
        lbl_font.setBold(True)
        p.setFont(lbl_font)
        p.drawText(rect.adjusted(0, -6, 0, -6), Qt.AlignmentFlag.AlignCenter, self.label)

        # Percent below label
        p.setPen(QColor(TEXT_MUTED))
        pct_font = QFont(FONT_TINY)
        pct_font.setPointSize(9)
        p.setFont(pct_font)
        p.drawText(rect.adjusted(0, 16, 0, 16), Qt.AlignmentFlag.AlignCenter, f"{self.pct:.0f}%")

        # Count below ring
        p.setPen(QColor(TEXT_SECONDARY))
        count_font = QFont(FONT_SMALL)
        count_font.setPointSize(10)
        p.setFont(count_font)
        count_rect = QRect(0, size + 10, self.width(), 20)
        p.drawText(count_rect, Qt.AlignmentFlag.AlignCenter, f"{self.owned} / {self.total}")

        p.end()


# ─── Stat card helper ─────────────────────────────────────────────────────────

class ClickableStatCard(QFrame):
    def __init__(self, parent=None, on_click=None):
        super().__init__(parent)
        self.on_click = on_click
        if on_click:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if self.on_click and event.button() == Qt.MouseButton.LeftButton:
            self.on_click()
        super().mousePressEvent(event)

def _stat_card(icon, label, value, color, parent=None, on_click=None):
    card = ClickableStatCard(parent, on_click)
    card.setStyleSheet(
        f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT};"
        f"border-radius: {RADIUS_LG}px; }}"
    )
    inner = QVBoxLayout(card)
    inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
    inner.setSpacing(SPACING_XS)
    inner.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)

    i_lbl = QLabel(icon)
    i_lbl.setFont(FONT_DISPLAY)
    i_lbl.setStyleSheet(f"color: {color}; background: transparent;")
    i_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    inner.addWidget(i_lbl)

    v_lbl = QLabel(str(value))
    v_lbl.setFont(FONT_DISPLAY)
    v_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
    v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    inner.addWidget(v_lbl)

    l_lbl = QLabel(label)
    l_lbl.setFont(FONT_SMALL)
    l_lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
    l_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    inner.addWidget(l_lbl)

    return card


# ─── Main Dashboard ───────────────────────────────────────────────────────────

class CollectionDashboard(QWidget):
    """Bento-grid collection overview."""

    def __init__(self, parent=None, navigate_to_cards_callback=None):
        super().__init__(parent)
        self.navigate_to_cards = navigate_to_cards_callback
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        self._body = QWidget()
        self._body.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARKEST}; }}")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        self._body_lay.setSpacing(SPACING_LG)

        scroll.setWidget(self._body)
        outer.addWidget(scroll)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(SPACING_SM)
        title = QLabel("PULSE DECK")
        title.setFont(FONT_DISPLAY)
        title.setStyleSheet(f"color: {ACCENT_PRIMARY}; background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        if self.navigate_to_cards:
            btn = create_styled_button(None, text="Open Library",
                                       command=self.navigate_to_cards,
                                       style_type="accent", height=36, width=140)
            hdr.addWidget(btn)
        self._body_lay.addLayout(hdr)

        # Top stats row (placeholder — populated in refresh)
        self._stats_row = QHBoxLayout()
        self._stats_row.setSpacing(SPACING_MD)
        self._body_lay.addLayout(self._stats_row)

        # Bottom bento: rarity | types
        bento = QHBoxLayout()
        bento.setSpacing(SPACING_MD)

        self._rarity_frame = QFrame()
        self._rarity_frame.setStyleSheet(
            f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT};"
            f"border-radius: {RADIUS_LG}px; }}"
        )
        self._rarity_frame.setMinimumWidth(280)
        bento.addWidget(self._rarity_frame, stretch=1)

        self._type_frame = QFrame()
        self._type_frame.setStyleSheet(
            f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT};"
            f"border-radius: {RADIUS_LG}px; }}"
        )
        bento.addWidget(self._type_frame, stretch=2)

        self._body_lay.addLayout(bento, stretch=1)

        self._recent_lay = QHBoxLayout()
        self._recent_lay.setSpacing(SPACING_SM)
        self._body_lay.addLayout(self._recent_lay)

    def refresh(self):
        try:
            stats = get_collection_stats()
        except Exception:
            stats = self._fallback_stats()

        if stats.get('total', 0) == 0:
            self._render_empty_state()
            return

        self._render_top_stats(stats)
        self._render_rarity_rings(stats)
        self._render_type_bars(stats)
        self._render_recent_cards()

    def _render_recent_cards(self):
        self._clear_layout(self._recent_lay)
        import gui.card_view
        if not gui.card_view._recent_cards: return

        lbl = QLabel("Recent:")
        lbl.setFont(FONT_TINY)
        lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        self._recent_lay.addWidget(lbl)

        from PySide6.QtCore import QSize
        from db.db_queries import get_card_by_id
        from utils import resolve_image_path
        from PySide6.QtGui import QPixmap

        for cid in gui.card_view._recent_cards:
            card = get_card_by_id(cid)
            if not card: continue
            
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            rp = resolve_image_path(card[6])
            if rp and os.path.exists(rp):
                try:
                    pix = QPixmap(rp).scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    from PySide6.QtGui import QIcon
                    btn.setIcon(QIcon(pix))
                    btn.setIconSize(QSize(36, 36))
                except: pass

            btn.setStyleSheet(f"QPushButton {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_SM}px; }} QPushButton:hover {{ border-color: {ACCENT_PRIMARY}; }}")
            # Navigate to card via main window
            btn.clicked.connect(lambda _, c=cid: self.window().navigate_to_card(c) if hasattr(self.window(), 'navigate_to_card') else None)
            self._recent_lay.addWidget(btn)
        self._recent_lay.addStretch()

    def _render_empty_state(self):
        self._clear_layout(self._stats_row)
        self._clear_widget(self._rarity_frame)
        self._clear_widget(self._type_frame)

        empty_lay = QVBoxLayout()
        empty_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📭")
        icon.setFont(QFont("Segoe UI", 48))
        icon.setStyleSheet(f"color: {TEXT_DISABLED}; background: transparent;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lay.addWidget(icon)

        t = QLabel("No card data yet")
        t.setFont(FONT_TITLE)
        t.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lay.addWidget(t)

        d = QLabel("Your database is empty. Run the scraper to fetch card data from GameTora.")
        d.setFont(FONT_BODY)
        d.setStyleSheet(f"color: {TEXT_DISABLED}; background: transparent;")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setWordWrap(True)
        empty_lay.addWidget(d)

        if self.navigate_to_cards:
            btn = create_styled_button(None, text="📋 Go to Card Library",
                                       command=self.navigate_to_cards,
                                       style_type="accent", height=40, width=200)
            empty_lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        wrapper = QFrame()
        wrapper.setStyleSheet("background: transparent; border: none;")
        wrapper.setLayout(empty_lay)
        self._stats_row.addWidget(wrapper)

    def _render_top_stats(self, stats):
        self._clear_layout(self._stats_row)
        total = stats.get('total', 0)
        owned = stats.get('owned', 0)
        pct = (owned / total * 100) if total > 0 else 0

        for icon, label, value, color, on_click in [
            ("📋", "Total Cards",  str(total),          TEXT_PRIMARY, None),
            ("✅", "Owned",        str(owned),           ACCENT_SUCCESS, None),
            ("📈", "Completion",   f"{pct:.1f}%",        ACCENT_PRIMARY, None),
            ("❌", "Missing",      str(total - owned),   ACCENT_ERROR, self._on_missing_clicked),
        ]:
            self._stats_row.addWidget(_stat_card(icon, label, value, color, on_click=on_click))

    def _on_missing_clicked(self):
        if self.navigate_to_cards:
            # We need to tell the main window to pre-filter to Missing.
            # We can use a hack by setting the global _CARD_FILTER_STATE before navigating
            import gui.card_view
            gui.card_view._CARD_FILTER_STATE['owned'] = False # Note: 'owned' False means All in the current logic. Wait, no. 'owned' only shows owned. We don't have an "unowned only" checkbox natively, we only have 'Owned Only'. So we might have to add support for "Missing" or just navigate. Wait, the user asked for #6 Clickable "Missing" stat -> pre-filtered cards view.
            # To do this correctly, we might need a signal to the card view. If we pass 'missing' to navigate_to_cards, main_window can handle it.
            self.navigate_to_cards("missing")

    def _render_rarity_rings(self, stats):
        self._clear_widget(self._rarity_frame)
        lay = QVBoxLayout(self._rarity_frame)
        lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        hdr = QLabel("⭐  By Rarity")
        hdr.setFont(FONT_SUBHEADER)
        hdr.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        lay.addWidget(hdr)

        rings_row = QHBoxLayout()
        rings_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        by_rarity = stats.get('by_rarity', {})
        for rarity in ['SSR', 'SR', 'R']:
            data = by_rarity.get(rarity, {'total': 0, 'owned': 0})
            total = data.get('total', 0)
            owned = data.get('owned', 0)
            pct = (owned / total * 100) if total > 0 else 0
            color = RARITY_COLORS.get(rarity, TEXT_MUTED)
            ring = RingChart(pct, color, rarity, owned, total)
            rings_row.addWidget(ring)
        lay.addLayout(rings_row)
        lay.addStretch()

    def _render_type_bars(self, stats):
        self._clear_widget(self._type_frame)
        lay = QVBoxLayout(self._type_frame)
        lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        hdr = QLabel("🎯  By Type")
        hdr.setFont(FONT_SUBHEADER)
        hdr.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        lay.addWidget(hdr)

        by_type = stats.get('by_type', {})
        for card_type in ['Speed', 'Stamina', 'Power', 'Guts', 'Wisdom', 'Friend', 'Group']:
            data = by_type.get(card_type, {'total': 0, 'owned': 0})
            total = data.get('total', 0)
            owned = data.get('owned', 0)
            if total == 0:
                continue
            pct = (owned / total * 100) if total > 0 else 0
            color = TYPE_COLORS.get(card_type, TEXT_MUTED)
            icon = get_type_icon(card_type)

            row = QHBoxLayout()
            row.setSpacing(SPACING_SM)

            type_lbl = QLabel(f"{icon}  {card_type}")
            type_lbl.setFont(FONT_BODY)
            type_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent; min-width: 90px;")
            row.addWidget(type_lbl)

            # Progress track
            track = QFrame()
            track.setFixedHeight(10)
            track.setStyleSheet(
                f".QFrame {{ background-color: {BG_MEDIUM}; border-radius: 5px; border: none; }}"
            )
            track.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row.addWidget(track, stretch=1)

            # Fill overlay via child widget
            fill = QFrame(track)
            fill_w = max(0, int(track.width() * pct / 100)) if pct > 0 else 0
            fill.setFixedHeight(10)
            fill.setStyleSheet(f"background-color: {color}; border-radius: 5px; border: none;")
            # Use resizeEvent trick: set relwidth via stylesheet after show
            fill._pct = pct / 100
            fill._color = color
            def make_resize(f=fill):
                def _resize(ev):
                    f.setFixedWidth(max(4, int(f.parent().width() * f._pct)))
                return _resize
            track.resizeEvent = make_resize()

            pct_lbl = QLabel(f"{pct:.0f}%")
            pct_lbl.setFont(FONT_TINY)
            pct_lbl.setStyleSheet(f"color: {TEXT_DISABLED}; background: transparent; min-width: 36px;")
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(pct_lbl)

            count_lbl = QLabel(f"{owned}/{total}")
            count_lbl.setFont(FONT_SMALL)
            count_lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; min-width: 56px;")
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(count_lbl)

            lay.addLayout(row)

        lay.addStretch()

    def _fallback_stats(self):
        db_stats = get_database_stats()
        owned = get_owned_count()
        total = db_stats.get('total_cards', 0)
        by_rarity = db_stats.get('by_rarity', {})
        return {
            'total': total,
            'owned': owned,
            'by_rarity': {r: {'total': c, 'owned': 0} for r, c in by_rarity.items()},
            'by_type': {}
        }

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _clear_widget(frame: QFrame):
        if frame.layout():
            while frame.layout().count():
                item = frame.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            # Remove old layout so new one can be set
            import shiboken6
            try:
                old = frame.layout()
                if old:
                    QWidget().setLayout(old)
            except Exception:
                pass
