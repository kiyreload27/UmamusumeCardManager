"""
Race Calendar View - Combined character selection and race suggestion calendar
PySide6 edition with grade-colored slots, aptitude badges, and visual calendar grid
"""

import os
import sys
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QComboBox, QPushButton, QDialog, QLineEdit, QTabWidget
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_characters, get_all_races, save_race_schedule, load_race_schedule, clear_race_schedule
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY,
    ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_ERROR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    GRADE_COLORS, create_styled_entry
)
from utils import resolve_image_path

YEARS = ["Junior Year", "Classic Year", "Senior Year"]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
HALF_MONTHS = ["First Half", "Second Half"]

GRADE_RANK_COLORS = {
    'S': '#fbbf24', 'A': '#34d399', 'B': '#60a5fa',
    'C': '#94a3b8', 'D': '#f97316', 'E': '#f87171',
    'F': '#ef4444', 'G': '#991b1b'
}

def format_half_month(month, half):
    return f"{month}, {half}"

def clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()
            else: clear_layout(item.layout())

class ClickableFrame(QFrame):
    clicked = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    def enterEvent(self, event):
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)
    def leaveEvent(self, event):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)

class CharacterSelectionDialog(QDialog):
    def __init__(self, characters, icon_cache, on_select_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Character")
        self.resize(660, 520)
        self.setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}")
        
        self.on_select_callback = on_select_callback
        self.characters = characters
        self.icon_cache = icon_cache
        
        self._build_ui()
        self._render_chars(self.characters)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QFrame()
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        
        t_lbl = QLabel("👤  Choose a Character")
        t_lbl.setFont(FONT_HEADER)
        t_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        hdr_lay.addWidget(t_lbl)
        hdr_lay.addStretch()

        self.search_entry = create_styled_entry(None, placeholder="Search...")
        self.search_entry.setFixedWidth(160)
        self.search_entry.textChanged.connect(self._filter)
        hdr_lay.addWidget(self.search_entry)
        lay.addWidget(hdr)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")
        self.grid_w = QWidget()
        self.grid_w.setStyleSheet("background: transparent;")
        self.grid_lay = QGridLayout(self.grid_w)
        self.grid_lay.setContentsMargins(SPACING_SM, 0, SPACING_SM, SPACING_SM)
        self.grid_lay.setSpacing(SPACING_SM)
        self.grid_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        for i in range(5):
            self.grid_lay.setColumnStretch(i, 1)

        self.scroll.setWidget(self.grid_w)
        lay.addWidget(self.scroll, stretch=1)

    def _filter(self, term):
        term = term.lower()
        if term:
            filtered = [c for c in self.characters if term in c[1].lower()]
        else:
            filtered = self.characters
        self._render_chars(filtered)

    def _render_chars(self, chars):
        clear_layout(self.grid_lay)

        row, col = 0, 0
        for char in chars:
            char_id = char[0]
            name = char[1]
            img_path = char[3]

            card = ClickableFrame()
            base_css = f".QFrame {{ background: {BG_MEDIUM}; border-radius: {RADIUS_MD}px; border: 2px solid transparent; }}"
            hover_css = f"QFrame[hover=true] {{ border-color: {ACCENT_PRIMARY}; }}"
            card.setStyleSheet(base_css + hover_css)
            card.clicked.connect(lambda cid=char_id: self._on_select(cid))
            
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
            c_lay.setSpacing(SPACING_SM)
            c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

            img = self.icon_cache.get(char_id)
            if not img:
                rp = resolve_image_path(img_path)
                if rp and os.path.exists(rp):
                    try:
                        img = QPixmap(rp).scaled(65, 65, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.icon_cache[char_id] = img
                    except: pass
            
            i_lbl = QLabel()
            i_lbl.setFixedSize(65, 65)
            if img:
                i_lbl.setPixmap(img)
            else:
                i_lbl.setText("?")
                i_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                i_lbl.setStyleSheet(f"background: {BG_DARK}; border-radius: {RADIUS_SM}px;")
            c_lay.addWidget(i_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

            disp_name = name[:11] + "…" if len(name) > 11 else name
            n_lbl = QLabel(disp_name)
            n_lbl.setFont(FONT_TINY)
            n_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
            n_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_lay.addWidget(n_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

            self.grid_lay.addWidget(card, row, col)

            col += 1
            if col > 4:
                col = 0
                row += 1

    def _on_select(self, cid):
        self.on_select_callback(cid)
        self.accept()

class RaceCalendarViewFrame(QWidget):
    """Race Calendar tab with grade-colored slots and aptitude badges"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.characters = []
        self.races = []

        self.current_character = None
        self.aptitudes = {k: 'C' for k in ['Turf', 'Dirt', 'Sprint', 'Mile', 'Medium', 'Long']}

        self.selected_races = {}
        self._image_refs = {}
        self._race_image_cache = {}
        self.slot_frames = {}
        self._apt_combos = {}
        self._dist_filter_vars = {k: True for k in ['Sprint', 'Mile', 'Medium', 'Long']}
        self._min_grade_var = 'C'
        self._dist_chip_btns = {}

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        main_lay.setSpacing(SPACING_SM)

        # ─── TOP SECTION ───
        top_f = QFrame()
        top_f.setStyleSheet(f".QFrame {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        top_lay = QHBoxLayout(top_f)
        top_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)

        char_f = QFrame()
        char_f.setStyleSheet("background: transparent; border: none;")
        char_lay = QHBoxLayout(char_f)
        char_lay.setContentsMargins(0, 0, 0, 0)
        
        self.char_img_label = QLabel("?")
        self.char_img_label.setFixedSize(75, 75)
        self.char_img_label.setFont(FONT_HEADER)
        self.char_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.char_img_label.setStyleSheet(f"background: {BG_MEDIUM}; border-radius: {RADIUS_MD}px; color: {TEXT_MUTED};")
        char_lay.addWidget(self.char_img_label)

        char_info = QVBoxLayout()
        char_info.setContentsMargins(SPACING_MD, 0, 0, 0)
        self.char_name_label = QLabel("No Character Selected")
        self.char_name_label.setFont(FONT_SUBHEADER)
        self.char_name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        char_info.addWidget(self.char_name_label)
        
        sel_btn = QPushButton("👤  Choose Character...")
        sel_btn.setFixedSize(180, 32)
        sel_btn.setStyleSheet(f"QPushButton {{ background: {BG_MEDIUM}; color: {TEXT_PRIMARY}; border-radius: {RADIUS_SM}px; }} QPushButton:hover {{ background: {BG_HIGHLIGHT}; }}")
        sel_btn.clicked.connect(self._open_character_selector)
        char_info.addWidget(sel_btn)
        char_info.addStretch()
        char_lay.addLayout(char_info)
        top_lay.addWidget(char_f, stretch=1)

        stats_f = QFrame()
        stats_f.setStyleSheet("background: transparent; border: none;")
        stats_lay = QVBoxLayout(stats_f)
        stats_lay.setContentsMargins(0, 0, 0, 0)
        
        s_lbl = QLabel("📊  Aptitudes")
        s_lbl.setFont(FONT_BODY_BOLD)
        s_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        stats_lay.addWidget(s_lbl)

        s_row = QHBoxLayout()
        s_row.setContentsMargins(0, 0, 0, 0)
        s_row.setSpacing(SPACING_XS)
        
        for apt_name in self.aptitudes.keys():
            col = QVBoxLayout()
            d_name = 'Short' if apt_name == 'Sprint' else apt_name
            l = QLabel(d_name)
            l.setFont(FONT_TINY)
            l.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
            col.addWidget(l)

            c = QComboBox()
            c.setFixedSize(55, 28)
            c.addItems(['S', 'A', 'B', 'C', 'D', 'E', 'F', 'G'])
            c.setCurrentText(self.aptitudes[apt_name])
            c.currentTextChanged.connect(lambda val, an=apt_name: self._on_apt_change(val, an))
            col.addWidget(c)
            self._apt_combos[apt_name] = c
            s_row.addLayout(col)

        s_row.addStretch()
        stats_lay.addLayout(s_row)
        top_lay.addWidget(stats_f, stretch=2)
        main_lay.addWidget(top_f)

        # ─── CALENDAR SECTION ───
        cal_f = QFrame()
        cal_f.setStyleSheet(f".QFrame {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        cal_lay = QVBoxLayout(cal_f)
        cal_lay.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)

        hdr = QHBoxLayout()
        hdr_l = QLabel("📅  Scheduled Races")
        hdr_l.setFont(FONT_HEADER)
        hdr_l.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        hdr.addWidget(hdr_l)
        hdr.addStretch()

        filt_f = QFrame()
        filt_f.setStyleSheet(f"background: {BG_MEDIUM}; border-radius: {RADIUS_MD}px; border: none;")
        filt_lay = QHBoxLayout(filt_f)
        filt_lay.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)

        mg_l = QLabel("Min Grade")
        mg_l.setFont(FONT_TINY)
        mg_l.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        filt_lay.addWidget(mg_l)

        self.grade_combo = QComboBox()
        self.grade_combo.setFixedSize(58, 26)
        self.grade_combo.addItems(['S', 'A', 'B', 'C', 'D'])
        self.grade_combo.setCurrentText(self._min_grade_var)
        self.grade_combo.currentTextChanged.connect(self._on_min_grade_change)
        filt_lay.addWidget(self.grade_combo)

        sep = QFrame()
        sep.setFixedSize(1, 28)
        sep.setStyleSheet(f"background: {BG_LIGHT}; border: none;")
        filt_lay.addWidget(sep)

        d_l = QLabel("Dist")
        d_l.setFont(FONT_TINY)
        d_l.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        filt_lay.addWidget(d_l)

        for dk, dl in {'Sprint': 'Short', 'Mile': 'Mile', 'Medium': 'Med', 'Long': 'Long'}.items():
            btn = QPushButton(dl)
            btn.setFixedSize(56, 24)
            btn.setFont(FONT_TINY)
            btn.setStyleSheet(f"QPushButton {{ background: {ACCENT_PRIMARY}; color: {TEXT_PRIMARY}; border-radius: {RADIUS_SM}px; border: none; padding: 2px 6px; }}")
            btn.clicked.connect(lambda _, k=dk: self._toggle_dist_filter(k))
            filt_lay.addWidget(btn)
            self._dist_chip_btns[dk] = btn
        
        hdr.addWidget(filt_f)

        save_btn = QPushButton("💾  Save Schedule")
        save_btn.setFixedSize(130, 32)
        save_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT_SUCCESS}; color: {BG_DARKEST}; border-radius: {RADIUS_SM}px; font-weight: bold; }}")
        save_btn.clicked.connect(self._save_schedule)
        hdr.addWidget(save_btn)

        clr_btn = QPushButton("🗑  Clear Schedule")
        clr_btn.setFixedSize(130, 32)
        clr_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: 1px solid {TEXT_MUTED}; color: {TEXT_MUTED}; border-radius: {RADIUS_SM}px; }} QPushButton:hover {{ background: {BG_HIGHLIGHT}; color: {TEXT_PRIMARY}; }}")
        clr_btn.clicked.connect(self._clear_schedule)
        hdr.addWidget(clr_btn)
        cal_lay.addLayout(hdr)

        self.calendar_tabs = QTabWidget()
        self.calendar_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar::tab {{ background: {BG_LIGHT}; color: {TEXT_MUTED}; padding: 6px 12px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
            QTabBar::tab:selected {{ background: {ACCENT_PRIMARY}; color: {TEXT_PRIMARY}; }}
        """)
        
        for y in YEARS:
            tw = QWidget()
            t_lay = QVBoxLayout(tw)
            t_lay.setContentsMargins(0, SPACING_SM, 0, 0)
            self._build_year_grid(t_lay, y)
            self.calendar_tabs.addTab(tw, y)
        
        self.calendar_tabs.currentChanged.connect(self._on_year_tab_changed)
        cal_lay.addWidget(self.calendar_tabs, stretch=1)

        main_lay.addWidget(cal_f, stretch=1)

    def _build_year_grid(self, parent_lay, year):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        cw = QWidget()
        cw.setStyleSheet("background: transparent;")
        c_lay = QGridLayout(cw)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(SPACING_SM)

        for i in range(4): c_lay.setColumnStretch(i, 1)

        row, col = 0, 0
        for month in MONTHS:
            for half in HALF_MONTHS:
                ds = format_half_month(month, half)
                
                sf = QFrame()
                sf.setStyleSheet(f".QFrame {{ background: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_MD}px; }}")
                sf_lay = QVBoxLayout(sf)
                sf_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
                sf_lay.setSpacing(SPACING_XS)

                ui_half = "Early" if half == "First Half" else "Late"
                dlbl = QLabel(f"{ui_half} {month[:3]}")
                dlbl.setFont(FONT_TINY)
                dlbl.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
                sf_lay.addWidget(dlbl)

                cnt = QFrame()
                cnt.setStyleSheet("background: transparent; border: none;")
                cnt_lay = QVBoxLayout(cnt)
                cnt_lay.setContentsMargins(0, 0, 0, 0)
                cnt_lay.setSpacing(0)

                abtn = QPushButton("＋")
                abtn.setFixedSize(36, 28)
                abtn.setFont(FONT_SMALL)
                abtn.setStyleSheet(f"QPushButton {{ background: transparent; color: {TEXT_DISABLED}; border: none; padding: 0; }} QPushButton:hover {{ background: {BG_HIGHLIGHT}; border-radius: {RADIUS_SM}px; }}")
                abtn.clicked.connect(lambda _, y=year, d=ds: self._suggest_race_for_slot(y, d))
                cnt_lay.addWidget(abtn, alignment=Qt.AlignmentFlag.AlignCenter)
                
                sf_lay.addWidget(cnt, stretch=1)
                self.slot_frames[(year, ds)] = cnt

                c_lay.addWidget(sf, row, col)
                col += 1
                if col > 3:
                    col = 0
                    row += 1

        scroll.setWidget(cw)
        parent_lay.addWidget(scroll)

    def _open_character_selector(self):
        if not self.characters: return
        CharacterSelectionDialog(self.characters, self._image_refs, self._on_character_select_id, self).exec()

    def load_data(self):
        self.characters = get_all_characters()
        self.races = get_all_races()

        if self.characters:
            self._on_character_select_id(self.characters[0][0])
        else:
            self.char_name_label.setText("No characters found")

    def _on_apt_change(self, val, apt_name):
        self.aptitudes[apt_name] = val
        c = self._apt_combos.get(apt_name)
        if c:
            col = GRADE_RANK_COLORS.get(val, TEXT_MUTED)
            c.setStyleSheet(f"color: {col};")
        QTimer.singleShot(150, self._do_stat_refresh)

    def _do_stat_refresh(self):
        idx = self.calendar_tabs.currentIndex()
        if idx >= 0:
            year = YEARS[idx]
            for m in MONTHS:
                for h in HALF_MONTHS:
                    self._refresh_slot(year, format_half_month(m, h))

    def _on_character_select_id(self, char_id):
        char = next((c for c in self.characters if c[0] == char_id), None)
        if not char: return

        self.current_character = char
        self.char_name_label.setText(char[1])

        img = self._image_refs.get(char_id)
        if not img:
            rp = resolve_image_path(char[3])
            if rp and os.path.exists(rp):
                try:
                    img = QPixmap(rp).scaled(75, 75, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self._image_refs[char_id] = img
                except: pass
        
        if img:
            self.char_img_label.setPixmap(img)
            self.char_img_label.setText("")
        else:
            self.char_img_label.setPixmap(QPixmap())
            self.char_img_label.setText("?")

        self.aptitudes['Turf'] = char[4] or 'G'
        self.aptitudes['Dirt'] = char[5] or 'G'
        self.aptitudes['Sprint'] = char[6] or 'G'
        self.aptitudes['Mile'] = char[7] or 'G'
        self.aptitudes['Medium'] = char[8] or 'G'
        self.aptitudes['Long'] = char[9] or 'G'

        for an, v in self.aptitudes.items():
            self._apt_combos[an].setCurrentText(v)
            self._apt_combos[an].setStyleSheet(f"color: {GRADE_RANK_COLORS.get(v, TEXT_MUTED)};")

        self.selected_races.clear()
        self._load_schedule_from_db()
        self._refresh_calendar()

    _GRADE_ORDER = ['S', 'A', 'B', 'C', 'D', 'E', 'F', 'G']

    def _grade_passes(self, grade, min_grade):
        try: return self._GRADE_ORDER.index(grade) <= self._GRADE_ORDER.index(min_grade)
        except ValueError: return False

    def _toggle_dist_filter(self, dk):
        self._dist_filter_vars[dk] = not self._dist_filter_vars[dk]
        btn = self._dist_chip_btns.get(dk)
        if btn:
            if self._dist_filter_vars[dk]:
                btn.setStyleSheet(f"QPushButton {{ background: {ACCENT_PRIMARY}; color: {TEXT_PRIMARY}; border-radius: {RADIUS_SM}px; border: none; padding: 2px 6px; }}")
            else:
                btn.setStyleSheet(f"QPushButton {{ background: {BG_LIGHT}; color: {TEXT_DISABLED}; border-radius: {RADIUS_SM}px; border: none; padding: 2px 6px; }}")

        self._on_filter_change()

    def _on_min_grade_change(self, v):
        self._min_grade_var = v
        self._on_filter_change()

    def _on_filter_change(self):
        QTimer.singleShot(150, self._do_stat_refresh)

    def _is_eligible(self, race_data):
        if not race_data: return False
        ter = race_data[7] or ""
        dt = race_data[8] or ""
        if dt == "Short": dt = "Sprint"

        if dt and not self._dist_filter_vars.get(dt, True): return False

        mg = self._min_grade_var
        sg = self.aptitudes.get(ter, 'E')
        if not self._grade_passes(sg, mg): return False

        dg = self.aptitudes.get(dt, 'E')
        if not self._grade_passes(dg, mg): return False

        return True

    def _get_eligible_races_for_date(self, year, ds, check_aptitude=True):
        if not self.current_character: return []
        el = []
        cm = {"Junior Year": "Junior Class", "Classic Year": "Classic Class", "Senior Year": "Senior Class"}
        rc = cm.get(year, "")

        for r in self.races:
            if r[12] == ds:
                r_c = r[13] or ""
                if r_c == rc: pass
                elif r_c == "Classic/Senior Class" and rc in ("Classic Class", "Senior Class"): pass
                elif r_c == "": pass
                elif rc == "Senior Class" and r_c == "Classic Class": pass
                else: continue

                if not check_aptitude or self._is_eligible(r):
                    el.append(r)
        return el

    def _suggest_race_for_slot(self, year, ds):
        el = self._get_eligible_races_for_date(year, ds)
        if not el: return

        cur = self.selected_races.get((year, ds))
        if cur:
            try:
                idx = next(i for i, r in enumerate(el) if r[0] == cur[0])
                self.selected_races[(year, ds)] = el[(idx + 1) % len(el)]
            except: self.selected_races[(year, ds)] = el[0]
        else:
            self.selected_races[(year, ds)] = el[0]

        self._autosave_slot(year, ds)
        self._refresh_slot(year, ds)

    def _remove_race_from_slot(self, year, ds):
        if (year, ds) in self.selected_races:
            del self.selected_races[(year, ds)]
        self._autosave_slot(year, ds)
        self._refresh_slot(year, ds)

    def _autosave_slot(self, year, ds):
        if not self.current_character: return
        cid = self.current_character[0]
        sk = f"{year}||{ds}"
        race = self.selected_races.get((year, ds))
        rid = race[0] if race else None
        save_race_schedule(cid, year, sk, rid)

    def _save_schedule(self):
        if not self.current_character: return
        cid = self.current_character[0]
        for y in YEARS:
            for m in MONTHS:
                for h in HALF_MONTHS:
                    ds = format_half_month(m, h)
                    sk = f"{y}||{ds}"
                    race = self.selected_races.get((y, ds))
                    rid = race[0] if race else None
                    save_race_schedule(cid, y, sk, rid)

    def _clear_schedule(self):
        if not self.current_character: return
        cid = self.current_character[0]
        for y in YEARS: clear_race_schedule(cid, y)
        self.selected_races.clear()
        self._refresh_calendar()

    def _load_schedule_from_db(self):
        if not self.current_character: return
        cid = self.current_character[0]
        rbid = {r[0]: r for r in self.races}
        for y in YEARS:
            svd = load_race_schedule(cid, y)
            for sk, rid in svd.items():
                pts = sk.split('||', 1)
                if len(pts) == 2:
                    yr, ds = pts
                    r = rbid.get(rid)
                    if r: self.selected_races[(yr, ds)] = r

    def _on_year_tab_changed(self, idx):
        if idx >= 0:
            y = YEARS[idx]
            for m in MONTHS:
                for h in HALF_MONTHS:
                    self._refresh_slot(y, format_half_month(m, h))

    def _refresh_calendar(self):
        for y in YEARS:
            for m in MONTHS:
                for h in HALF_MONTHS:
                    self._refresh_slot(y, format_half_month(m, h))

    def _refresh_slot(self, year, ds):
        cnt = self.slot_frames.get((year, ds))
        if not cnt: return

        clear_layout(cnt.layout())

        race = self.selected_races.get((year, ds))
        if race:
            n = race[1] or race[2]
            g = race[3] or ""
            gc = GRADE_COLORS.get(g, ACCENT_PRIMARY)

            warn = False
            if g in ['GI', 'G1']:
                ter = race[7] or ""
                dt = race[8] or ""
                if dt == "Short": dt = "Sprint"
                sg = self.aptitudes.get(ter, 'S')
                dg = self.aptitudes.get(dt, 'S')
                vm = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0, 'F': -1, 'G': -2}
                if vm.get(sg, 0) < 4 or vm.get(dg, 0) < 4: warn = True

            bc = ACCENT_ERROR if warn else gc
            crd = QFrame()
            crd.setStyleSheet(f".QFrame {{ background: {BG_ELEVATED}; border: 1px solid {bc}; border-radius: {RADIUS_SM}px; }}")
            cnt.layout().addWidget(crd, stretch=1)

            c_lay = QVBoxLayout(crd)
            c_lay.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_XS, SPACING_XS)
            c_lay.setSpacing(2)
            c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if warn:
                wl = QLabel("⚠️ Hard")
                wl.setFont(FONT_TINY)
                wl.setStyleSheet(f"color: {ACCENT_ERROR}; border: none;")
                wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                c_lay.addWidget(wl)

            gl = QLabel(g)
            gl.setFont(FONT_SMALL)
            gl.setStyleSheet(f"color: {gc}; border: none;")
            gl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_lay.addWidget(gl)

            sn = n[:14] + "…" if len(n) > 14 else n
            tip = race[14] if len(race) > 14 else None
            if tip:
                cimg = self._race_image_cache.get(tip)
                if not cimg:
                    rp = resolve_image_path(tip)
                    if rp and os.path.exists(rp):
                        try:
                            cimg = QPixmap(rp).scaled(80, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            self._race_image_cache[tip] = cimg
                        except: pass
                
                if cimg:
                    il = QLabel()
                    il.setPixmap(cimg)
                    il.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    c_lay.addWidget(il)

            nl = QLabel(sn)
            nl.setFont(FONT_TINY)
            nl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
            nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_lay.addWidget(nl)

            tt = race[7] or ""
            dtt = race[8] or ""
            if tt or dtt:
                bdg = QHBoxLayout()
                bdg.setContentsMargins(0, 0, 0, 0)
                bdg.setSpacing(2)
                bdg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if tt:
                    si = "🌿" if tt == "Turf" else "🟤"
                    tl = QLabel(f"{si}{tt}")
                    tl.setFont(FONT_TINY)
                    tl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
                    bdg.addWidget(tl)
                if dtt:
                    dl = QLabel(dtt)
                    dl.setFont(FONT_TINY)
                    dl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
                    bdg.addWidget(dl)
                c_lay.addLayout(bdg)

            act = QHBoxLayout()
            act.setContentsMargins(0, 0, 0, 0)
            act.setSpacing(4)
            act.setAlignment(Qt.AlignmentFlag.AlignCenter)

            sbtn = QPushButton("🔄")
            sbtn.setFixedSize(24, 24)
            sbtn.setStyleSheet(f"QPushButton {{ background: transparent; color: {TEXT_MUTED}; border: none; padding: 0; }} QPushButton:hover {{ background: {BG_HIGHLIGHT}; border-radius: {RADIUS_SM}px; }}")
            sbtn.clicked.connect(lambda _, y=year, d=ds: self._suggest_race_for_slot(y, d))
            act.addWidget(sbtn)

            rbtn = QPushButton("✕")
            rbtn.setFixedSize(24, 24)
            rbtn.setStyleSheet(f"QPushButton {{ background: transparent; color: {TEXT_MUTED}; border: none; padding: 0; }} QPushButton:hover {{ background: transparent; color: {ACCENT_ERROR}; border-radius: {RADIUS_SM}px; }}")
            rbtn.clicked.connect(lambda _, y=year, d=ds: self._remove_race_from_slot(y, d))
            act.addWidget(rbtn)
            
            c_lay.addLayout(act)

        else:
            ec = len(self._get_eligible_races_for_date(year, ds, True))
            af = len(self._get_eligible_races_for_date(year, ds, False))
            he = ec > 0

            if af == 0:
                # No races scheduled for this period at all — show a clear empty marker
                lbl = QLabel("—")
                lbl.setFont(FONT_SMALL)
                lbl.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setToolTip("No races scheduled for this period")
                cnt.layout().addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                if not he and self.current_character:
                    # Races exist but aptitude is too low — show ⛔ badge + dashed disabled button
                    rl = QLabel("⛔ Apt")
                    rl.setFont(FONT_TINY)
                    rl.setStyleSheet(f"color: {ACCENT_ERROR}; border: none;")
                    rl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    rl.setToolTip("Aptitude too low for all races in this period")
                    cnt.layout().addWidget(rl)

                abtn = QPushButton("＋")
                abtn.setFixedSize(36, 28)
                abtn.setFont(FONT_SMALL)

                if he:
                    # Clickable: bordered button with hover glow
                    abtn.setStyleSheet(
                        f"QPushButton {{ background: transparent; color: {TEXT_MUTED};"
                        f" border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_SM}px; padding: 0; }}"
                        f" QPushButton:hover {{ background: {BG_HIGHLIGHT}; color: {TEXT_PRIMARY};"
                        f" border-color: {ACCENT_PRIMARY}; }}"
                    )
                    s = "s" if ec != 1 else ""
                    abtn.setToolTip(f"{ec} eligible race{s} — click to assign")
                    abtn.clicked.connect(lambda _, y=year, d=ds: self._suggest_race_for_slot(y, d))
                else:
                    # Not clickable: dashed border, dim text, no hover
                    abtn.setStyleSheet(
                        f"QPushButton {{ background: transparent; color: {TEXT_DISABLED};"
                        f" border: 1px dashed {BG_LIGHT}; border-radius: {RADIUS_SM}px; padding: 0; }}"
                        f" QPushButton:disabled {{ color: {TEXT_DISABLED}; }}"
                    )
                    abtn.setToolTip("No eligible races — improve aptitude or adjust filters")
                    abtn.setEnabled(False)

                cnt.layout().addWidget(abtn, alignment=Qt.AlignmentFlag.AlignCenter)
