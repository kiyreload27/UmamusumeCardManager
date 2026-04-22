"""
AETHER OPS — Main Window (PySide6 edition)
Top hub chrome + sub-module strip + QStackedWidget content area.
Navigation: hub pill → sub-nav pill → QStackedWidget.setCurrentWidget()
"""

import sys
import os
import threading

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSizePolicy, QApplication, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, Signal, QMetaObject, Q_ARG
from PySide6.QtGui import QShortcut, QKeySequence, QIcon, QPixmap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_database_stats, get_owned_count
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_HEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_MD, RADIUS_FULL,
    create_styled_button,
)
from utils import resolve_image_path
from version import VERSION

# ─── Navigation structure ────────────────────────────────────────────────────

NAV_GROUPS = {
    "COLLECTION": [
        ("Dashboard", "📦", "Dashboard"),
        ("Cards", "📔", "Card Library"),
        ("Effects", "🔎", "Effect Search"),
    ],
    "PLANNING": [
        ("Deck", "🃏", "Deck Builder"),
        ("Skills", "🔍", "Skill Search"),
        ("DeckSkills", "📜", "Deck Skills"),
    ],
    "REFERENCE": [
        ("Tracks", "🏟", "Racetracks"),
        ("Calendar", "🗓️", "Race Calendar"),
    ]
}

VIEW_ORDER = [v_id for group in NAV_GROUPS.values() for v_id, icon, text in group]
VIEW_LABELS = {v_id: text for group in NAV_GROUPS.values() for v_id, icon, text in group}


# ─── Main Window ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Top hub chrome + sub-nav + QStackedWidget content."""

    # Signal for thread-safe UI updates from background threads
    _update_flag_signal = Signal(str)
    _stats_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AETHER OPS — Support Card Manager")

        # Responsive initial size
        screen_w = QApplication.primaryScreen().geometry().width()
        if screen_w >= 1920:
            self.resize(1680, 920)
        elif screen_w >= 1280:
            self.resize(1360, 840)
        else:
            self.resize(1150, 760)
        self.setMinimumSize(960, 640)

        # Window icon
        try:
            icon_path = resolve_image_path("umaappicon.png")
            if icon_path and os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

        self.last_selected_levels = {}
        self.selected_card_id = None
        self.views: dict[str, QWidget] = {}
        self.current_view_id = None
        self._nav_btns: dict[str, QPushButton] = {}

        self._update_flag_signal.connect(self._flag_update_available)
        self._stats_signal.connect(self._set_stats_label)

        self._build_shell()
        self._bind_shortcuts()

        self._navigate("Dashboard")
        self.refresh_stats()

        QTimer.singleShot(600,  self._check_first_run)
        QTimer.singleShot(2000, self._run_background_update_check)

    # ─── Shell layout ────────────────────────────────────────────────────────

    def _build_shell(self):
        root = QWidget()
        root.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARKEST}; }}")
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        outer.addWidget(self._build_sidebar())

        # Divider
        rule = QFrame()
        rule.setFrameShape(QFrame.Shape.VLine)
        rule.setFixedWidth(1)
        rule.setStyleSheet(f"background-color: {BG_LIGHT}; border: none;")
        outer.addWidget(rule)

        # Content
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARKEST}; }}")
        outer.addWidget(self._stack, stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")

        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(SPACING_LG, SPACING_XL, SPACING_LG, SPACING_LG)
        lay.setSpacing(SPACING_SM)

        # Wordmark
        mark_lay = QHBoxLayout()
        mark_lay.setContentsMargins(0, 0, 0, SPACING_LG)
        logo = QLabel("🐴")
        logo.setFont(FONT_HEADER)
        logo.setStyleSheet("background: transparent;")
        
        texts = QVBoxLayout()
        texts.setSpacing(0)
        t1 = QLabel("Umamusume")
        t1.setFont(FONT_BODY_BOLD)
        t1.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent;")
        t2 = QLabel(f"v{VERSION}")
        t2.setFont(FONT_TINY)
        t2.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        texts.addWidget(t1)
        texts.addWidget(t2)
        
        mark_lay.addWidget(logo)
        mark_lay.addLayout(texts)
        mark_lay.addStretch()
        lay.addLayout(mark_lay)

        # Navigation Groups
        def _nav_btn(v_id, icon, text):
            btn = QPushButton(f"{icon}   {text}")
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  text-align: left; padding-left: 12px; background: transparent; color: {TEXT_SECONDARY};"
                f"  border: none; border-radius: {RADIUS_MD}px; font-weight: normal; font-size: 13px;"
                f"}}"
                f"QPushButton:hover:!checked {{"
                f"  background: {BG_MEDIUM}; color: {TEXT_PRIMARY};"
                f"}}"
                f"QPushButton:checked {{"
                f"  background: {BG_ELEVATED}; color: {ACCENT_PRIMARY}; font-weight: bold;"
                f"}}"
            )
            btn.clicked.connect(lambda checked, v=v_id: self._navigate(v))
            return btn

        for group_name, items in NAV_GROUPS.items():
            grp_lbl = QLabel(group_name)
            grp_lbl.setFont(FONT_TINY)
            grp_lbl.setStyleSheet(f"color: {TEXT_DISABLED}; background: transparent; padding-top: {SPACING_MD}px; letter-spacing: 1px;")
            lay.addWidget(grp_lbl)
            
            for v_id, icon, text in items:
                btn = _nav_btn(v_id, icon, text)
                lay.addWidget(btn)
                self._nav_btns[v_id] = btn

        lay.addStretch()

        # Action buttons + stats
        act_lay = QVBoxLayout()
        act_lay.setSpacing(SPACING_XS)
        
        self._stats_label = QLabel("")
        self._stats_label.setFont(FONT_TINY)
        self._stats_label.setStyleSheet(f"color: {TEXT_DISABLED}; background: transparent;")
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        act_lay.addWidget(self._stats_label)
        
        # Grid layout for bottom action buttons (2x2)
        btn_grid_lay = QGridLayout()
        btn_grid_lay.setContentsMargins(0, 0, 0, 0)
        btn_grid_lay.setSpacing(4)
        
        actions = [
            ("Backup",  self.show_backup_dialog),
            ("Data",    self.show_data_update_dialog),
            ("Updates", self.show_update_dialog),
            ("Logs",    self.show_debug_panel),
        ]
        
        for i, (text, slot) in enumerate(actions):
            b = create_styled_button(sidebar, text=text, command=slot, style_type="ghost", height=28)
            setattr(self, f"_{text.lower()}_btn", b)
            btn_grid_lay.addWidget(b, i // 2, i % 2)
            
        act_lay.addLayout(btn_grid_lay)
        lay.addLayout(act_lay)

        return sidebar

    # ─── Navigation ──────────────────────────────────────────────────────────

    def _navigate(self, view_id: str):
        if view_id not in VIEW_ORDER:
            return

        self.current_view_id = view_id
        
        for vid, btn in self._nav_btns.items():
            btn.setChecked(vid == view_id)

        self.setWindowTitle(f"Support Card Manager  ·  {VIEW_LABELS.get(view_id, view_id)}")

        if view_id not in self.views:
            view = self._build_view(view_id)
            if view:
                self._stack.addWidget(view)
                self.views[view_id] = view
            # Pass selected card to newly created views
            if self.selected_card_id:
                if view_id == "Effects" and "Effects" in self.views:
                    self.views["Effects"].set_card(self.selected_card_id)
                elif view_id == "DeckSkills" and "DeckSkills" in self.views:
                    self.views["DeckSkills"].set_card(self.selected_card_id)

        if view_id in self.views:
            self._stack.setCurrentWidget(self.views[view_id])

    def _build_view(self, view_id: str) -> QWidget | None:
        parent = self._stack
        if view_id == "Dashboard":
            from gui.collection_dashboard import CollectionDashboard
            return CollectionDashboard(
                parent, navigate_to_cards_callback=lambda: self._navigate("Cards")
            )
        if view_id == "Cards":
            from gui.card_view import CardListFrame
            return CardListFrame(
                parent,
                on_card_selected_callback=self.on_card_selected,
                on_stats_updated_callback=self.refresh_stats,
                navigate_to_card_callback=self.navigate_to_card,
            )
        if view_id == "Effects":
            from gui.effects_view import EffectsFrame
            return EffectsFrame(parent, navigate_to_card_callback=self.navigate_to_card)
        if view_id == "Deck":
            from gui.deck_builder import DeckBuilderFrame
            return DeckBuilderFrame(parent)
        if view_id == "Skills":
            from gui.hints_skills_view import SkillSearchFrame
            return SkillSearchFrame(parent, navigate_to_card_callback=self.navigate_to_card)
        if view_id == "DeckSkills":
            from gui.deck_skills_view import DeckSkillsFrame
            return DeckSkillsFrame(
                parent,
                navigate_to_card_callback=self.navigate_to_card,
                navigate_to_skill_callback=self.navigate_to_skill,
            )
        if view_id == "Tracks":
            from gui.track_view import TrackViewFrame
            return TrackViewFrame(parent)
        if view_id == "Calendar":
            from gui.race_calendar_view import RaceCalendarViewFrame
            return RaceCalendarViewFrame(parent)
        return None

    # ─── Cross-view navigation callbacks ─────────────────────────────────────

    def navigate_to_card(self, card_id):
        self._navigate("Cards")
        if "Cards" in self.views:
            self.views["Cards"].navigate_to_card(card_id)

    def navigate_to_skill(self, skill_name):
        self._navigate("Skills")
        if "Skills" in self.views:
            view = self.views["Skills"]
            view.search_entry.setText(skill_name)
            view.filter_skills()
            view.on_skill_selected(skill_name)

    def on_card_selected(self, card_id, card_name, level=None):
        if level is not None:
            self.last_selected_levels[card_id] = level
        self.selected_card_id = card_id
        if "Effects" in self.views:
            self.views["Effects"].set_card(card_id)
        if "DeckSkills" in self.views:
            self.views["DeckSkills"].set_card(card_id)

    # ─── Stats ───────────────────────────────────────────────────────────────

    def refresh_stats(self):
        try:
            stats = get_database_stats()
            owned = get_owned_count()
            total = stats.get("total_cards", 0)
            by_rarity = stats.get("by_rarity", {})
            pct = f"{owned / total * 100:.0f}%" if total else "0%"
            text = (
                f"{owned}/{total} owned  {pct}  │  "
                f"SSR {by_rarity.get('SSR', 0)}  "
                f"SR {by_rarity.get('SR', 0)}  "
                f"R {by_rarity.get('R', 0)}"
            )
        except Exception:
            text = ""
        self._stats_signal.emit(text)

    def _set_stats_label(self, text: str):
        self._stats_label.setText(text)

    # ─── Dialog launchers ────────────────────────────────────────────────────

    def show_backup_dialog(self):
        def on_restore():
            self.refresh_stats()
            if "Cards" in self.views:
                self.views["Cards"].filter_cards()
            if "Dashboard" in self.views:
                self.views["Dashboard"].refresh()

        from gui.backup_dialog import BackupDialog
        dlg = BackupDialog(self, on_restore_callback=on_restore)
        dlg.exec()

    def show_update_dialog(self):
        from gui.update_dialog import UpdateDialog
        dlg = UpdateDialog(self)
        dlg.exec()

    def show_debug_panel(self):
        from gui.debug_panel import DebugPanel
        dlg = DebugPanel(self)
        dlg.exec()

    def show_data_update_dialog(self):
        def on_complete():
            self.refresh_stats()
            if "Dashboard" in self.views:
                self.views["Dashboard"].refresh()
            if "Cards" in self.views:
                self.views["Cards"].filter_cards()

        from gui.data_update_dialog import DataUpdateDialog
        dlg = DataUpdateDialog(self, on_complete_callback=on_complete)
        dlg.exec()

    # ─── Background update check ──────────────────────────────────────────────

    def _run_background_update_check(self):
        def _check():
            try:
                from updater.update_checker import check_for_updates
                update_info = check_for_updates()
                if update_info and update_info.get("has_update"):
                    self._update_flag_signal.emit(update_info.get("version", "?"))
            except Exception:
                pass
        threading.Thread(target=_check, daemon=True).start()

    def _flag_update_available(self, new_version: str):
        if hasattr(self, "_updates_btn"):
            self._updates_btn.setText(f"Upd {new_version}")
            self._updates_btn.setStyleSheet(
                self._updates_btn.styleSheet() +
                f" QPushButton {{ color: {ACCENT_PRIMARY}; font-weight: bold; }}"
            )

    # ─── First run check ─────────────────────────────────────────────────────

    def _check_first_run(self):
        from gui.first_run_dialog import should_show_first_run, FirstRunDialog
        if should_show_first_run():
            dlg = FirstRunDialog(self, on_complete_callback=self._on_first_run_complete)
            dlg.exec()

    def _on_first_run_complete(self):
        self.refresh_stats()
        if "Dashboard" in self.views:
            self.views["Dashboard"].refresh()

    # ─── Keyboard shortcuts ───────────────────────────────────────────────────

    def _bind_shortcuts(self):
        for idx, view_id in enumerate(VIEW_ORDER):
            n = idx + 1
            if n <= 9:
                sc = QShortcut(QKeySequence(f"Ctrl+{n}"), self)
                sc.activated.connect(lambda v=view_id: self._navigate(v))

        sc_debug = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        sc_debug.activated.connect(self.show_debug_panel)
