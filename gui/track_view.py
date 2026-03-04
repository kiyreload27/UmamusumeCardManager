"""
Track View - Browse racetracks and their course details
Premium 3-panel layout: Track Grid | Course List | Course Detail
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import sys
import os
import json
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_queries import get_all_tracks, get_track_courses, get_course_detail
from gui.theme import (
    BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT, BG_ELEVATED,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY, ACCENT_SUCCESS, ACCENT_WARNING, ACCENT_INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    FONT_DISPLAY, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY, FONT_MONO, FONT_FAMILY,
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
    create_styled_button, create_styled_text, create_card_frame
)

# Surface/direction colors and icons
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
    """Resolve path for track images, supporting both local and bundled assets"""
    if not image_path:
        return None

    if os.path.isabs(image_path) and os.path.exists(image_path):
        return image_path

    filename = os.path.basename(image_path)
    search_dirs = []

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_dir = sys._MEIPASS
        search_dirs.extend([
            os.path.join(bundle_dir, 'assets', 'tracks', 'maps'),
            os.path.join(bundle_dir, 'assets', 'tracks'),
            os.path.join(bundle_dir, 'images'),
        ])

    source_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    search_dirs.extend([
        os.path.join(source_dir, 'assets', 'tracks', 'maps'),
        os.path.join(source_dir, 'assets', 'tracks'),
        os.path.join(source_dir, 'assets'),
    ])

    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        search_dirs.extend([
            os.path.join(exe_dir, 'assets', 'tracks', 'maps'),
            os.path.join(exe_dir, 'assets', 'tracks'),
        ])

    for d in search_dirs:
        test_path = os.path.join(d, filename)
        if os.path.exists(test_path):
            return test_path

    return image_path


class TrackViewFrame(ctk.CTkFrame):
    """Track browser with premium 3-panel layout"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.tracks = []
        self.current_track_id = None
        self.current_course_id = None
        self.track_image = None
        self.track_thumbnails = {}

        self.current_map_path = None
        self.map_label = None
        self.map_frame = None
        self.resize_after_id = None

        self.create_widgets()
        self.load_tracks()

    def create_widgets(self):
        """Build the 3-panel layout"""
        # Top bar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill=tk.X, padx=SPACING_SM, pady=(SPACING_SM, SPACING_XS))

        ctk.CTkLabel(
            top_bar, text="🏟️  Racetracks",
            font=FONT_TITLE, text_color=ACCENT_PRIMARY
        ).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        search = ctk.CTkEntry(
            top_bar, textvariable=self.search_var,
            placeholder_text="🔍  Search tracks...",
            width=220, height=34,
            fg_color=BG_MEDIUM, border_color=BG_LIGHT,
            corner_radius=RADIUS_MD
        )
        search.pack(side=tk.RIGHT, padx=SPACING_XS)
        search.bind('<KeyRelease>', lambda e: self.filter_tracks())

        self.count_label = ctk.CTkLabel(
            top_bar, text="", font=FONT_TINY, text_color=TEXT_DISABLED
        )
        self.count_label.pack(side=tk.RIGHT, padx=SPACING_SM)

        # Main 3-panel area
        panels = ctk.CTkFrame(self, fg_color="transparent")
        panels.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=SPACING_XS)

        # Panel 1: Track list
        self.left_panel = ctk.CTkFrame(
            panels, width=340, corner_radius=RADIUS_LG,
            fg_color=BG_DARK, border_width=1, border_color=BG_LIGHT
        )
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, SPACING_XS))
        self.left_panel.pack_propagate(False)

        ctk.CTkLabel(
            self.left_panel, text="Tracks",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(pady=(SPACING_MD, SPACING_XS), padx=SPACING_MD, anchor='w')

        self.track_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.track_scroll.pack(fill=tk.BOTH, expand=True, padx=SPACING_XS, pady=(0, SPACING_XS))

        # Panel 2: Course list
        self.mid_panel = ctk.CTkFrame(
            panels, width=340, corner_radius=RADIUS_LG,
            fg_color=BG_DARK, border_width=1, border_color=BG_LIGHT
        )
        self.mid_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=SPACING_XS)
        self.mid_panel.pack_propagate(False)

        self.track_header = ctk.CTkFrame(self.mid_panel, fg_color="transparent")
        self.track_header.pack(fill=tk.X, padx=SPACING_MD, pady=(SPACING_MD, SPACING_XS))

        self.track_name_label = ctk.CTkLabel(
            self.track_header, text="Select a Track",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        )
        self.track_name_label.pack(anchor='w')

        self.track_info_label = ctk.CTkLabel(
            self.track_header, text="",
            font=FONT_TINY, text_color=TEXT_MUTED
        )
        self.track_info_label.pack(anchor='w')

        # Track image
        self.track_image_frame = ctk.CTkFrame(
            self.mid_panel, fg_color=BG_MEDIUM,
            corner_radius=RADIUS_SM, height=130
        )
        self.track_image_frame.pack(fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_XS))
        self.track_image_frame.pack_propagate(False)

        self.track_image_label = ctk.CTkLabel(
            self.track_image_frame, text="No image", text_color=TEXT_DISABLED
        )
        self.track_image_label.pack(expand=True)

        ctk.CTkLabel(
            self.mid_panel, text="Courses",
            font=FONT_SUBHEADER, text_color=ACCENT_TERTIARY
        ).pack(padx=SPACING_MD, pady=(SPACING_XS, SPACING_XS), anchor='w')

        self.course_scroll = ctk.CTkScrollableFrame(self.mid_panel, fg_color="transparent")
        self.course_scroll.pack(fill=tk.BOTH, expand=True, padx=SPACING_XS, pady=(0, SPACING_XS))

        # Panel 3: Course detail
        self.right_panel = ctk.CTkFrame(
            panels, corner_radius=RADIUS_LG,
            fg_color=BG_DARK, border_width=1, border_color=BG_LIGHT
        )
        self.right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(SPACING_XS, 0))

        self.detail_header = ctk.CTkLabel(
            self.right_panel, text="Course Details",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        )
        self.detail_header.pack(padx=SPACING_LG, pady=(SPACING_MD, SPACING_XS), anchor='w')

        self.detail_subtitle = ctk.CTkLabel(
            self.right_panel, text="Select a course to view details",
            font=FONT_TINY, text_color=TEXT_MUTED
        )
        self.detail_subtitle.pack(padx=SPACING_LG, anchor='w')

        self.detail_scroll = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.detail_scroll.pack(fill=tk.BOTH, expand=True, padx=SPACING_SM, pady=(SPACING_SM, SPACING_SM))

        self.right_panel.bind("<Configure>", self._on_detail_resize, add="+")

    # Data loading
    def load_tracks(self):
        self.tracks = get_all_tracks()
        self.render_track_list(self.tracks)

    def filter_tracks(self):
        term = self.search_var.get().strip().lower()
        if term:
            filtered = [t for t in self.tracks if term in t[1].lower()]
        else:
            filtered = self.tracks
        self.render_track_list(filtered)

    def render_track_list(self, tracks):
        for w in self.track_scroll.winfo_children():
            w.destroy()

        self.count_label.configure(text=f"{len(tracks)} tracks")

        if not tracks:
            ctk.CTkLabel(
                self.track_scroll,
                text="No tracks found.\nRun: python main.py --scrape-tracks",
                font=FONT_BODY, text_color=TEXT_MUTED, justify='center'
            ).pack(pady=SPACING_XL)
            return

        for track in tracks:
            track_id, name, location, image_path, course_count = track
            self._create_track_card(track_id, name, location, image_path, course_count)

    def _create_track_card(self, track_id, name, location, image_path, course_count):
        card = ctk.CTkFrame(
            self.track_scroll, fg_color=BG_MEDIUM,
            corner_radius=RADIUS_SM, cursor="hand2"
        )
        card.pack(fill=tk.X, pady=2, padx=SPACING_XS)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill=tk.X, padx=SPACING_SM, pady=SPACING_SM)

        # Thumbnail image (cached)
        thumb = self.track_thumbnails.get(track_id)
        if not thumb and image_path:
            resolved = resolve_track_image(image_path)
            if resolved and os.path.exists(resolved):
                try:
                    pil_img = Image.open(resolved)
                    pil_img.thumbnail((56, 38), Image.Resampling.LANCZOS)
                    thumb = ctk.CTkImage(
                        light_image=pil_img, dark_image=pil_img,
                        size=(56, 38)
                    )
                    self.track_thumbnails[track_id] = thumb
                except Exception:
                    pass

        if thumb:
            lbl = ctk.CTkLabel(
                inner, text="", image=thumb,
                width=56, height=38, corner_radius=RADIUS_SM
            )
            lbl.pack(side=tk.LEFT, padx=(0, SPACING_SM))
        else:
            # Placeholder tile with track initials
            initials = name[:2].upper()
            ctk.CTkLabel(
                inner, text=initials, width=56, height=38,
                fg_color=BG_DARK, corner_radius=RADIUS_SM,
                font=FONT_BODY_BOLD, text_color=TEXT_MUTED
            ).pack(side=tk.LEFT, padx=(0, SPACING_SM))

        text_col = ctk.CTkFrame(inner, fg_color="transparent")
        text_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        name_label = ctk.CTkLabel(
            text_col, text=name,
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, anchor='w'
        )
        name_label.pack(fill=tk.X)

        subtitle_parts = []
        if location:
            subtitle_parts.append(location)
        subtitle_parts.append(f"{course_count} course{'s' if course_count != 1 else ''}")

        ctk.CTkLabel(
            text_col, text=" · ".join(subtitle_parts),
            font=FONT_TINY, text_color=TEXT_MUTED, anchor='w'
        ).pack(fill=tk.X)

        def on_click(e, tid=track_id):
            self.select_track(tid)

        card.bind('<Button-1>', on_click)
        inner.bind('<Button-1>', on_click)
        name_label.bind('<Button-1>', on_click)
        for child in inner.winfo_children():
            child.bind('<Button-1>', on_click)
            for gc in child.winfo_children():
                gc.bind('<Button-1>', on_click)

        self._bind_scroll_recursive(card, self.track_scroll)

        def on_enter(e):
            card.configure(fg_color=BG_LIGHT)
        def on_leave(e):
            if self.current_track_id != track_id:
                card.configure(fg_color=BG_MEDIUM)

        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)
        card._track_id = track_id


    def select_track(self, track_id):
        self.current_track_id = track_id
        self.current_course_id = None

        track = None
        for t in self.tracks:
            if t[0] == track_id:
                track = t
                break
        if not track:
            return

        track_id, name, location, image_path, course_count = track

        self.track_name_label.configure(text=f"🏟️  {name}")
        info_text = f"{course_count} course{'s' if course_count != 1 else ''}"
        if location:
            info_text = f"{location}  ·  {info_text}"
        self.track_info_label.configure(text=info_text)

        self._load_track_image(image_path)

        for child in self.track_scroll.winfo_children():
            if hasattr(child, '_track_id'):
                child.configure(fg_color=BG_LIGHT if child._track_id == track_id else BG_MEDIUM)

        courses = get_track_courses(track_id)
        self.render_course_list(courses)

        self.detail_header.configure(text="Course Details")
        self.detail_subtitle.configure(text="Select a course to view details")
        for w in self.detail_scroll.winfo_children():
            w.destroy()

    def _load_track_image(self, image_path):
        resolved = resolve_track_image(image_path)
        if resolved and os.path.exists(resolved):
            try:
                img = ctk.CTkImage(
                    light_image=Image.open(resolved),
                    dark_image=Image.open(resolved),
                    size=(276, 125)
                )
                self.track_image_label.configure(image=img, text="")
                self.track_image = img
            except Exception:
                self.track_image_label.configure(image=None, text="[Image Error]")
        else:
            self.track_image_label.configure(image=None, text="No image available")

    def _on_detail_resize(self, event):
        if not self.current_map_path:
            return
        if self.resize_after_id:
            self.after_cancel(self.resize_after_id)
        self.resize_after_id = self.after(100, self._perform_map_resize)

    def _perform_map_resize(self):
        if self.current_map_path:
            self._load_course_map(self.current_map_path, is_resize=True)

    def _load_course_map(self, image_path, is_resize=False):
        self.current_map_path = image_path
        resolved = resolve_track_image(image_path)

        if resolved and os.path.exists(resolved):
            try:
                scroll_width = self.detail_scroll.winfo_width()
                if scroll_width <= 1:
                    display_width = 850 if self.winfo_width() > 1200 else 400
                else:
                    display_width = max(300, scroll_width - 40)

                orig = Image.open(resolved)
                w, h = orig.size
                display_height = int(h * (display_width / w))

                img = ctk.CTkImage(
                    light_image=orig, dark_image=orig,
                    size=(display_width, display_height)
                )

                if is_resize and self.map_label:
                    self.map_label.configure(image=img)
                    self.map_label._image = img
                    return

                if self.map_frame:
                    self.map_frame.destroy()

                self.map_frame = create_card_frame(self.detail_scroll)
                self.map_frame.pack(pady=SPACING_XS, padx=SPACING_XS, anchor="w")

                self.map_label = ctk.CTkLabel(self.map_frame, image=img, text="")
                self.map_label.pack(padx=2, pady=2)
                self.map_label._image = img

                self._bind_scroll_recursive(self.map_frame, self.detail_scroll)

            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error loading course map: {e}")

    def _propagate_scroll(self, event, scroll_frame):
        scroll_frame._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _bind_scroll_recursive(self, widget, scroll_frame):
        widget.bind("<MouseWheel>", lambda e: self._propagate_scroll(e, scroll_frame), add="+")
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child, scroll_frame)

    def render_course_list(self, courses):
        for w in self.course_scroll.winfo_children():
            w.destroy()

        if not courses:
            ctk.CTkLabel(
                self.course_scroll, text="No courses found",
                font=FONT_BODY, text_color=TEXT_MUTED
            ).pack(pady=SPACING_LG)
            return

        for course in courses:
            course_id, distance, surface, direction, corner_count, final_straight = course
            self._create_course_card(course_id, distance, surface, direction, corner_count, final_straight)

    def _create_course_card(self, course_id, distance, surface, direction, corner_count, final_straight):
        card = ctk.CTkFrame(
            self.course_scroll, fg_color=BG_MEDIUM,
            corner_radius=RADIUS_SM, cursor="hand2"
        )
        card.pack(fill=tk.X, pady=2, padx=SPACING_XS)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill=tk.X, padx=SPACING_SM, pady=SPACING_XS)

        # Top row: distance + surface badge
        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill=tk.X)

        surf_icon = SURFACE_ICONS.get(surface, '')
        surf_color = SURFACE_COLORS.get(surface, TEXT_SECONDARY)

        ctk.CTkLabel(
            top_row, text=f"{distance}m",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        # Surface badge
        ctk.CTkLabel(
            top_row, text=f" {surf_icon} {surface or '?'} ",
            font=FONT_TINY, text_color=surf_color,
            fg_color=BG_DARK, corner_radius=RADIUS_SM,
            height=20
        ).pack(side=tk.LEFT, padx=(SPACING_XS, 0))

        if direction:
            dir_icon = DIRECTION_ICONS.get(direction, '')
            ctk.CTkLabel(
                top_row, text=f" {dir_icon} {direction} ",
                font=FONT_TINY, text_color=TEXT_MUTED
            ).pack(side=tk.LEFT, padx=(SPACING_XS, 0))

        # Detail badges row
        details = []
        if corner_count:
            details.append(f"🔄 {corner_count}")
        if final_straight:
            details.append(f"📏 {final_straight}")

        if details:
            ctk.CTkLabel(
                inner, text="   ·   ".join(details),
                font=FONT_TINY, text_color=TEXT_DISABLED, anchor='w'
            ).pack(fill=tk.X)

        def on_click(e, cid=course_id):
            self.select_course(cid)

        card.bind('<Button-1>', on_click)
        inner.bind('<Button-1>', on_click)
        for child in inner.winfo_children():
            child.bind('<Button-1>', on_click)
            for gc in child.winfo_children():
                gc.bind('<Button-1>', on_click)

        def on_enter(e):
            card.configure(fg_color=BG_LIGHT)
        def on_leave(e):
            if self.current_course_id != course_id:
                card.configure(fg_color=BG_MEDIUM)

        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)
        card._course_id = course_id

        self._bind_scroll_recursive(card, self.course_scroll)

    def select_course(self, course_id):
        self.current_course_id = course_id

        for child in self.course_scroll.winfo_children():
            if hasattr(child, '_course_id'):
                child.configure(fg_color=BG_LIGHT if child._course_id == course_id else BG_MEDIUM)

        detail = get_course_detail(course_id)
        if not detail:
            return

        (cid, distance, surface, direction, corner_count,
         final_straight, slope_info, weather_data,
         phases_json, corners_json, straights_json, other_json,
         raw_json, map_image_path, track_name) = detail

        surf_icon = SURFACE_ICONS.get(surface, '')
        self.detail_header.configure(
            text=f"{track_name} — {distance}m {surf_icon} {surface or ''}"
        )
        subtitle_parts = []
        if direction:
            subtitle_parts.append(f"Direction: {direction}")
        if corner_count:
            subtitle_parts.append(f"Corners: {corner_count}")
        if final_straight:
            subtitle_parts.append(f"Final: {final_straight}")
        self.detail_subtitle.configure(
            text="  ·  ".join(subtitle_parts) if subtitle_parts else ""
        )

        for w in self.detail_scroll.winfo_children():
            w.destroy()

        # Course map
        if map_image_path:
            self._load_course_map(map_image_path)

        # Overview
        self._add_detail_section("📋  Overview", [
            ("Distance", f"{distance} m"),
            ("Surface", f"{surf_icon} {surface}" if surface else "N/A"),
            ("Direction", f"{DIRECTION_ICONS.get(direction, '')} {direction}" if direction else "N/A"),
            ("Corners", str(corner_count) if corner_count else "N/A"),
            ("Final Straight", final_straight or "N/A"),
            ("Slope", slope_info or "—"),
        ])

        # Phases
        if phases_json:
            try:
                phases = json.loads(phases_json)
                if phases:
                    rows = []
                    for phase_name, data in phases.items():
                        if isinstance(data, dict):
                            start = data.get('start', '?')
                            end = data.get('end', '?')
                            rows.append((phase_name, f"{start} m → {end} m"))
                        else:
                            rows.append((phase_name, str(data)))
                    self._add_detail_section("🏁  Phases", rows)
            except (json.JSONDecodeError, TypeError):
                pass

        # Corners
        if corners_json:
            try:
                corners = json.loads(corners_json)
                if corners:
                    rows = []
                    for c in corners:
                        name = c.get('name', 'Corner')
                        start = c.get('start', '?')
                        end = c.get('end', '?')
                        rows.append((name, f"{start} m → {end} m"))
                    self._add_detail_section("🔄  Corners", rows)
            except (json.JSONDecodeError, TypeError):
                pass

        # Straights
        if straights_json:
            try:
                straights = json.loads(straights_json)
                if straights:
                    rows = []
                    for s in straights:
                        name = s.get('name', 'Straight')
                        start = s.get('start', '?')
                        end = s.get('end', '?')
                        rows.append((name, f"{start} m → {end} m"))
                    self._add_detail_section("📏  Straights", rows)
            except (json.JSONDecodeError, TypeError):
                pass

        # Other
        if other_json:
            try:
                other = json.loads(other_json)
                if other:
                    rows = []
                    for key, val in other.items():
                        label = key.replace('_', ' ').title()
                        if isinstance(val, dict):
                            parts = []
                            if 'start' in val:
                                parts.append(f"Start: {val['start']} m")
                            if 'end' in val:
                                parts.append(f"End: {val['end']} m")
                            if 'note' in val and val['note']:
                                parts.append(val['note'])
                            rows.append((label, "  ·  ".join(parts) if parts else str(val)))
                        else:
                            rows.append((label, str(val)))
                    self._add_detail_section("📊  Other", rows)
            except (json.JSONDecodeError, TypeError):
                pass

        # Conditions
        extra_rows = []
        if weather_data:
            extra_rows.append(("Weather", weather_data))
        if slope_info:
            extra_rows.append(("Slope Info", slope_info))
        if extra_rows:
            self._add_detail_section("🌤️  Conditions", extra_rows)

    def _add_detail_section(self, title, rows):
        section = ctk.CTkFrame(
            self.detail_scroll, fg_color=BG_MEDIUM,
            corner_radius=RADIUS_MD, border_width=1, border_color=BG_LIGHT
        )
        section.pack(fill=tk.X, pady=SPACING_XS, padx=SPACING_XS)

        ctk.CTkLabel(
            section, text=title,
            font=FONT_SUBHEADER, text_color=ACCENT_TERTIARY
        ).pack(padx=SPACING_MD, pady=(SPACING_SM, SPACING_XS), anchor='w')

        sep = ctk.CTkFrame(section, height=1, fg_color=BG_LIGHT)
        sep.pack(fill=tk.X, padx=SPACING_MD, pady=(0, SPACING_XS))

        for label, value in rows:
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill=tk.X, padx=SPACING_MD, pady=1)

            ctk.CTkLabel(
                row, text=label,
                font=FONT_BODY, text_color=TEXT_MUTED,
                width=140, anchor='w'
            ).pack(side=tk.LEFT)

            ctk.CTkLabel(
                row, text=value,
                font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY, anchor='w'
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._bind_scroll_recursive(section, self.detail_scroll)

        ctk.CTkFrame(section, fg_color="transparent", height=SPACING_XS).pack()
