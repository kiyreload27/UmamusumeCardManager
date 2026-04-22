"""
Track View - Browse racetracks and their course details
PySide6 edition with premium 3-panel layout: Track Grid | Course List | Course Detail
"""

import os
import sys
import json
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_tracks, get_track_courses, get_course_detail
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_ELEVATED, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY, ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY, FONT_MONO, FONT_FAMILY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_entry
)

SURFACE_COLORS = {
    'Turf': '#22c55e',
    'Dirt': '#d97706',
}
SURFACE_ICONS = {
    'Turf': '🌿',
    'Dirt': '🟤',
}
DIRECTION_ICONS = {
    'Left': '↰',
    'Right': '↱',
    'Straight': '↑',
}

def resolve_track_image(image_path):
    if not image_path: return None
    if os.path.isabs(image_path) and os.path.exists(image_path): return image_path
    
    filename = os.path.basename(image_path)
    search_dirs = []
    
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bd = sys._MEIPASS
        search_dirs.extend([
            os.path.join(bd, 'assets', 'tracks', 'maps'),
            os.path.join(bd, 'assets', 'tracks'),
            os.path.join(bd, 'images'),
        ])
        
    src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    search_dirs.extend([
        os.path.join(src, 'assets', 'tracks', 'maps'),
        os.path.join(src, 'assets', 'tracks'),
        os.path.join(src, 'assets'),
    ])
    
    if getattr(sys, 'frozen', False):
        exe = os.path.dirname(sys.executable)
        search_dirs.extend([
            os.path.join(exe, 'assets', 'tracks', 'maps'),
            os.path.join(exe, 'assets', 'tracks'),
        ])
        
    for d in search_dirs:
        tp = os.path.join(d, filename)
        if os.path.exists(tp):
            return tp
    return image_path

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


class ResizingMapLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(100, 100)
    
    def setPixmapOriginal(self, pixmap):
        self.original_pixmap = pixmap
        self.update_map()
        
    def resizeEvent(self, event):
        self.update_map()
        super().resizeEvent(event)
        
    def update_map(self):
        if self.original_pixmap and not self.original_pixmap.isNull():
            w = self.width() - 10
            if w < 100: w = 100
            scaled = self.original_pixmap.scaledToWidth(w, Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(scaled)


class TrackViewFrame(QWidget):
    """Track browser with premium 3-panel layout"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracks = []
        self.current_track_id = None
        self.current_course_id = None
        self.track_thumbnails = {}
        self._course_cache = {}

        self._build_ui()
        self.load_tracks()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        main_lay.setSpacing(SPACING_SM)

        # ─── Top Bar ───
        top_f = QFrame()
        top_f.setStyleSheet("background: transparent;")
        top_lay = QHBoxLayout(top_f)
        top_lay.setContentsMargins(0, 0, 0, 0)

        t_lbl = QLabel("🏟️  Racetracks")
        t_lbl.setFont(FONT_TITLE)
        t_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; border: none;")
        top_lay.addWidget(t_lbl)
        
        top_lay.addStretch()

        self.count_label = QLabel("")
        self.count_label.setFont(FONT_TINY)
        self.count_label.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
        top_lay.addWidget(self.count_label)

        self.search_entry = create_styled_entry(None, placeholder="🔍  Search by name, turf, long, dirt…")
        self.search_entry.setFixedWidth(260)
        self.search_entry.textChanged.connect(self.filter_tracks)
        top_lay.addWidget(self.search_entry)

        main_lay.addWidget(top_f)

        # ─── 3 Panels ───
        p_w = QWidget()
        p_lay = QHBoxLayout(p_w)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(SPACING_XS)

        # 1. Track Panel
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(340)
        self.left_panel.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        lp_lay = QVBoxLayout(self.left_panel)
        lp_lay.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)

        l_hdr = QLabel("Tracks")
        l_hdr.setFont(FONT_HEADER)
        l_hdr.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        lp_lay.addWidget(l_hdr)

        self.track_scroll = QScrollArea()
        self.track_scroll.setWidgetResizable(True)
        self.track_scroll.setStyleSheet("border: none; background: transparent;")
        self.track_w = QWidget()
        self.track_w.setStyleSheet("background: transparent;")
        self.track_lay = QVBoxLayout(self.track_w)
        self.track_lay.setContentsMargins(0, 0, 0, 0)
        self.track_lay.setSpacing(4)
        self.track_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.track_scroll.setWidget(self.track_w)
        lp_lay.addWidget(self.track_scroll)
        p_lay.addWidget(self.left_panel)

        # 2. Course Panel
        self.mid_panel = QFrame()
        self.mid_panel.setFixedWidth(340)
        self.mid_panel.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        mp_lay = QVBoxLayout(self.mid_panel)
        mp_lay.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)

        self.track_name_label = QLabel("Select a Track")
        self.track_name_label.setFont(FONT_HEADER)
        self.track_name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        mp_lay.addWidget(self.track_name_label)

        self.track_info_label = QLabel("")
        self.track_info_label.setFont(FONT_TINY)
        self.track_info_label.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        mp_lay.addWidget(self.track_info_label)

        self.track_image_label = QLabel("No image")
        self.track_image_label.setFixedHeight(130)
        self.track_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.track_image_label.setStyleSheet(f"background: {BG_MEDIUM}; border-radius: {RADIUS_SM}px; color: {TEXT_DISABLED};")
        mp_lay.addWidget(self.track_image_label)

        m_hdr = QLabel("Courses")
        m_hdr.setFont(FONT_SUBHEADER)
        m_hdr.setStyleSheet(f"color: {ACCENT_TERTIARY}; border: none; margin-top: {SPACING_MD}px;")
        mp_lay.addWidget(m_hdr)

        self.course_scroll = QScrollArea()
        self.course_scroll.setWidgetResizable(True)
        self.course_scroll.setStyleSheet("border: none; background: transparent;")
        self.course_w = QWidget()
        self.course_w.setStyleSheet("background: transparent;")
        self.course_lay = QVBoxLayout(self.course_w)
        self.course_lay.setContentsMargins(0, 0, 0, 0)
        self.course_lay.setSpacing(4)
        self.course_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.course_scroll.setWidget(self.course_w)
        mp_lay.addWidget(self.course_scroll)
        p_lay.addWidget(self.mid_panel)

        # 3. Detail Panel
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet(f".QFrame {{ background-color: {BG_DARK}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_LG}px; }}")
        rp_lay = QVBoxLayout(self.right_panel)
        rp_lay.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)

        self.detail_header = QLabel("Course Details")
        self.detail_header.setFont(FONT_HEADER)
        self.detail_header.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        rp_lay.addWidget(self.detail_header)

        self.detail_subtitle = QLabel("Select a course to view details")
        self.detail_subtitle.setFont(FONT_TINY)
        self.detail_subtitle.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        rp_lay.addWidget(self.detail_subtitle)

        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setStyleSheet("border: none; background: transparent;")
        self.detail_w = QWidget()
        self.detail_w.setStyleSheet("background: transparent;")
        self.detail_lay = QVBoxLayout(self.detail_w)
        self.detail_lay.setContentsMargins(0, SPACING_SM, 0, 0)
        self.detail_lay.setSpacing(SPACING_SM)
        self.detail_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.detail_scroll.setWidget(self.detail_w)
        rp_lay.addWidget(self.detail_scroll)
        p_lay.addWidget(self.right_panel, stretch=1)

        main_lay.addWidget(p_w, stretch=1)

    def load_tracks(self):
        self.tracks = get_all_tracks()
        self._course_cache.clear()
        for t in self.tracks:
            self._course_cache[t[0]] = get_track_courses(t[0])
        self.render_track_list(self.tracks)

    def _get_distance_keywords(self, distance):
        if not distance: return []
        try: d = int(distance)
        except: return []
        if d < 1400: return ['sprint', 'short']
        elif d < 1800: return ['mile']
        elif d < 2400: return ['medium']
        else: return ['long']

    def _track_matches(self, track, term):
        if not term: return True
        term = term.lower()
        track_id, name, location = track[0], track[1], track[2] or ''
        if term in name.lower() or term in location.lower(): return True
        for c in self._course_cache.get(track_id, []):
            surf = (c[2] or '').lower()
            dirc = (c[3] or '').lower()
            dkw = self._get_distance_keywords(c[1])
            if term in surf or term in dirc or any(term == kw for kw in dkw):
                return True
        return False

    def filter_tracks(self):
        term = self.search_entry.text().strip().lower()
        filtered = [t for t in self.tracks if self._track_matches(t, term)]
        self.render_track_list(filtered)

    def render_track_list(self, tracks):
        clear_layout(self.track_lay)
        self.count_label.setText(f"{len(tracks)} tracks")

        if not tracks:
            lbl = QLabel("No tracks found.\nRun: python main.py --scrape-tracks")
            lbl.setFont(FONT_BODY)
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.track_lay.addWidget(lbl)
            return

        for t in tracks:
            self._create_track_card(*t)

    def _create_track_card(self, track_id, name, location, image_path, course_count):
        f = ClickableFrame()
        f.setObjectName(f"track_{track_id}")
        base_css = f".QFrame {{ background: {BG_MEDIUM}; border-radius: {RADIUS_SM}px; }}"
        hover_css = f"QFrame[hover=true] {{ background: {BG_LIGHT}; }}"
        sel_css = f"QFrame[selected=true] {{ background: {BG_LIGHT}; border: 1px solid {ACCENT_PRIMARY}; }}"
        f.setStyleSheet(base_css + hover_css + sel_css)
        f.clicked.connect(lambda: self.select_track(track_id))
        self.track_lay.addWidget(f)

        l = QHBoxLayout(f)
        l.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        l.setSpacing(SPACING_SM)

        thumb = self.track_thumbnails.get(track_id)
        if not thumb and image_path:
            rp = resolve_track_image(image_path)
            if rp and os.path.exists(rp):
                try:
                    thumb = QPixmap(rp).scaled(56, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.track_thumbnails[track_id] = thumb
                except: pass

        t_lbl = QLabel()
        t_lbl.setFixedSize(56, 38)
        if thumb:
            t_lbl.setPixmap(thumb)
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            t_lbl.setText(name[:2].upper())
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_lbl.setFont(FONT_BODY_BOLD)
            t_lbl.setStyleSheet(f"background: {BG_DARK}; color: {TEXT_MUTED}; border-radius: {RADIUS_SM}px;")
        l.addWidget(t_lbl)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(2)
        n_lbl = QLabel(name)
        n_lbl.setFont(FONT_BODY_BOLD)
        n_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        info.addWidget(n_lbl)
        
        subs = []
        if location: subs.append(location)
        subs.append(f"{course_count} course{'s' if course_count != 1 else ''}")
        s_lbl = QLabel(" · ".join(subs))
        s_lbl.setFont(FONT_TINY)
        s_lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
        info.addWidget(s_lbl)
        l.addLayout(info, stretch=1)

    def _course_matches(self, course, term):
        if not term: return True
        surf = (course[2] or '').lower()
        dirc = (course[3] or '').lower()
        dkw = self._get_distance_keywords(course[1])
        return (term in surf or term in dirc or any(term == kw for kw in dkw))

    def select_track(self, track_id):
        self.current_track_id = track_id
        self.current_course_id = None

        track = next((t for t in self.tracks if t[0] == track_id), None)
        if not track: return

        track_id, name, location, image_path, course_count = track

        self.track_name_label.setText(f"🏟️  {name}")
        info_text = f"{course_count} course{'s' if course_count != 1 else ''}"
        if location: info_text = f"{location}  ·  {info_text}"
        self.track_info_label.setText(info_text)

        self._load_track_image(image_path)

        for i in range(self.track_lay.count()):
            w = self.track_lay.itemAt(i).widget()
            if w:
                if w.objectName() == f"track_{track_id}":
                    w.setProperty("selected", True)
                else:
                    w.setProperty("selected", False)
                w.style().unpolish(w)
                w.style().polish(w)

        courses = get_track_courses(track_id)
        term = self.search_entry.text().strip().lower()
        fc = [c for c in courses if self._course_matches(c, term)] if term else courses
        self.render_course_list(fc)

        self.detail_header.setText("Course Details")
        self.detail_subtitle.setText("Select a course to view details")
        clear_layout(self.detail_lay)

    def _load_track_image(self, image_path):
        rp = resolve_track_image(image_path)
        if rp and os.path.exists(rp):
            pix = QPixmap(rp).scaled(276, 125, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.track_image_label.setPixmap(pix)
            self.track_image_label.setText("")
        else:
            self.track_image_label.setPixmap(QPixmap())
            self.track_image_label.setText("No image available")

    def render_course_list(self, courses):
        clear_layout(self.course_lay)

        if not courses:
            lbl = QLabel("No courses found")
            lbl.setFont(FONT_BODY)
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.course_lay.addWidget(lbl)
            return

        for c in courses:
            self._create_course_card(*c)

    def _create_course_card(self, course_id, distance, surface, direction, corner_count, final_straight):
        f = ClickableFrame()
        f.setObjectName(f"course_{course_id}")
        base_css = f".QFrame {{ background: {BG_MEDIUM}; border-radius: {RADIUS_SM}px; }}"
        hover_css = f"QFrame[hover=true] {{ background: {BG_LIGHT}; }}"
        sel_css = f"QFrame[selected=true] {{ background: {BG_LIGHT}; border: 1px solid {ACCENT_TERTIARY}; }}"
        f.setStyleSheet(base_css + hover_css + sel_css)
        f.clicked.connect(lambda: self.select_course(course_id))
        self.course_lay.addWidget(f)

        l = QVBoxLayout(f)
        l.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        l.setSpacing(SPACING_XS)

        t_row = QHBoxLayout()
        t_row.setContentsMargins(0, 0, 0, 0)
        
        d_lbl = QLabel(f"{distance}m")
        d_lbl.setFont(FONT_BODY_BOLD)
        d_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
        t_row.addWidget(d_lbl)

        s_icon = SURFACE_ICONS.get(surface, '')
        s_col = SURFACE_COLORS.get(surface, TEXT_SECONDARY)
        s_lbl = QLabel(f" {s_icon} {surface or '?'} ")
        s_lbl.setFont(FONT_TINY)
        s_lbl.setStyleSheet(f"color: {s_col}; background: {BG_DARK}; border-radius: {RADIUS_SM}px;")
        t_row.addWidget(s_lbl)

        if direction:
            d_icon = DIRECTION_ICONS.get(direction, '')
            dir_lbl = QLabel(f" {d_icon} {direction} ")
            dir_lbl.setFont(FONT_TINY)
            dir_lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
            t_row.addWidget(dir_lbl)

        t_row.addStretch()
        l.addLayout(t_row)

        dets = []
        if corner_count: dets.append(f"🔄 {corner_count}")
        if final_straight: dets.append(f"📏 {final_straight}")
        if dets:
            det_lbl = QLabel("   ·   ".join(dets))
            det_lbl.setFont(FONT_TINY)
            det_lbl.setStyleSheet(f"color: {TEXT_DISABLED}; border: none;")
            l.addWidget(det_lbl)

    def select_course(self, course_id):
        self.current_course_id = course_id

        for i in range(self.course_lay.count()):
            w = self.course_lay.itemAt(i).widget()
            if w:
                if w.objectName() == f"course_{course_id}":
                    w.setProperty("selected", True)
                else:
                    w.setProperty("selected", False)
                w.style().unpolish(w)
                w.style().polish(w)

        detail = get_course_detail(course_id)
        if not detail: return

        (cid, distance, surface, direction, corner_count,
         final_straight, slope_info, weather_data,
         phases_json, corners_json, straights_json, other_json,
         raw_json, map_image_path, track_name) = detail

        surf_icon = SURFACE_ICONS.get(surface, '')
        self.detail_header.setText(f"{track_name} — {distance}m {surf_icon} {surface or ''}")
        subs = []
        if direction: subs.append(f"Direction: {direction}")
        if corner_count: subs.append(f"Corners: {corner_count}")
        if final_straight: subs.append(f"Final: {final_straight}")
        self.detail_subtitle.setText("  ·  ".join(subs) if subs else "")

        clear_layout(self.detail_lay)

        if map_image_path:
            rp = resolve_track_image(map_image_path)
            if rp and os.path.exists(rp):
                mf = QFrame()
                mf.setStyleSheet(f"background: {BG_MEDIUM}; border-radius: {RADIUS_MD}px; padding: {SPACING_XS}px;")
                ml = QVBoxLayout(mf)
                ml.setContentsMargins(0, 0, 0, 0)
                mlab = ResizingMapLabel()
                mlab.setPixmapOriginal(QPixmap(rp))
                ml.addWidget(mlab)
                self.detail_lay.addWidget(mf)

        self._add_detail_section("📋  Overview", [
            ("Distance", f"{distance} m"),
            ("Surface", f"{surf_icon} {surface}" if surface else "N/A"),
            ("Direction", f"{DIRECTION_ICONS.get(direction, '')} {direction}" if direction else "N/A"),
            ("Corners", str(corner_count) if corner_count else "N/A"),
            ("Final Straight", final_straight or "N/A"),
            ("Slope", slope_info or "—"),
        ])

        if phases_json:
            try:
                phases = json.loads(phases_json)
                if phases:
                    rows = []
                    for pn, d in phases.items():
                        if isinstance(d, dict):
                            rows.append((pn, f"{d.get('start', '?')} m → {d.get('end', '?')} m"))
                        else:
                            rows.append((pn, str(d)))
                    self._add_detail_section("🏁  Phases", rows)
            except: pass

        if corners_json:
            try:
                corners = json.loads(corners_json)
                if corners:
                    rows = [(c.get('name', 'Corner'), f"{c.get('start', '?')} m → {c.get('end', '?')} m") for c in corners]
                    self._add_detail_section("🔄  Corners", rows)
            except: pass

        if straights_json:
            try:
                strs = json.loads(straights_json)
                if strs:
                    rows = [(s.get('name', 'Straight'), f"{s.get('start', '?')} m → {s.get('end', '?')} m") for s in strs]
                    self._add_detail_section("📏  Straights", rows)
            except: pass

        if other_json:
            try:
                oth = json.loads(other_json)
                if oth:
                    rows = []
                    for k, v in oth.items():
                        lbl = k.replace('_', ' ').title()
                        if isinstance(v, dict):
                            pts = []
                            if 'start' in v: pts.append(f"Start: {v['start']} m")
                            if 'end' in v: pts.append(f"End: {v['end']} m")
                            if 'note' in v and v['note']: pts.append(v['note'])
                            rows.append((lbl, "  ·  ".join(pts) if pts else str(v)))
                        else:
                            rows.append((lbl, str(v)))
                    self._add_detail_section("📊  Other", rows)
            except: pass

        extra = []
        if weather_data: extra.append(("Weather", weather_data))
        if slope_info: extra.append(("Slope Info", slope_info))
        if extra: self._add_detail_section("🌤️  Conditions", extra)

    def _add_detail_section(self, title, rows):
        f = QFrame()
        f.setStyleSheet(f".QFrame {{ background: {BG_MEDIUM}; border: 1px solid {BG_LIGHT}; border-radius: {RADIUS_MD}px; }}")
        self.detail_lay.addWidget(f)

        lay = QVBoxLayout(f)
        lay.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        lay.setSpacing(0)

        hdr = QLabel(title)
        hdr.setFont(FONT_SUBHEADER)
        hdr.setStyleSheet(f"color: {ACCENT_TERTIARY}; border: none;")
        lay.addWidget(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {BG_LIGHT}; border: none;")
        lay.addWidget(sep)
        lay.addSpacing(SPACING_XS)

        for l, v in rows:
            r = QHBoxLayout()
            lbl = QLabel(l)
            lbl.setFont(FONT_BODY)
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none;")
            lbl.setFixedWidth(140)
            r.addWidget(lbl)

            v_lbl = QLabel(v)
            v_lbl.setFont(FONT_BODY_BOLD)
            v_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; border: none;")
            v_lbl.setWordWrap(True)
            r.addWidget(v_lbl, stretch=1)
            lay.addLayout(r)
            lay.addSpacing(2)
