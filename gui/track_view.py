"""
Track View - Browse racetracks and their course details
3-panel layout: Track Grid | Course List | Course Detail
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
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HIGHLIGHT,
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY, ACCENT_SUCCESS, ACCENT_WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BODY_BOLD,
    FONT_SMALL, FONT_TINY, FONT_MONO, FONT_FAMILY,
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
    
    # If it's already an absolute path and exists, use it
    if os.path.isabs(image_path) and os.path.exists(image_path):
        return image_path

    filename = os.path.basename(image_path)
    search_dirs = []

    # 1. Check PyInstaller bundle internal path (_MEIPASS)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_dir = sys._MEIPASS
        search_dirs.extend([
            os.path.join(bundle_dir, 'assets', 'tracks', 'maps'),
            os.path.join(bundle_dir, 'assets', 'tracks'),
            os.path.join(bundle_dir, 'images'),
        ])

    # 2. Check local relative paths (development or external overrides)
    source_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    search_dirs.extend([
        os.path.join(source_dir, 'assets', 'tracks', 'maps'),
        os.path.join(source_dir, 'assets', 'tracks'),
        os.path.join(source_dir, 'assets'),
    ])

    # 3. Check relative to EXE directory (external assets folder)
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

    return image_path  # Fallback to original path


class TrackViewFrame(ctk.CTkFrame):
    """Track browser with 3-panel layout"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.tracks = []
        self.current_track_id = None
        self.current_course_id = None
        self.track_image = None
        self.track_thumbnails = {}  # Cache
        
        # Course Map dynamic scaling state
        self.current_map_path = None
        self.map_label = None
        self.map_frame = None
        self.resize_after_id = None

        self.create_widgets()
        self.load_tracks()

    def create_widgets(self):
        """Build the 3-panel layout"""
        # ─── Top bar: title + search ───
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill=tk.X, padx=10, pady=(10, 5))

        ctk.CTkLabel(
            top_bar, text="🏟️ Racetracks",
            font=FONT_TITLE, text_color=ACCENT_PRIMARY
        ).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        search = ctk.CTkEntry(
            top_bar, textvariable=self.search_var,
            placeholder_text="🔍 Search tracks...",
            width=220, height=34
        )
        search.pack(side=tk.RIGHT, padx=5)
        search.bind('<KeyRelease>', lambda e: self.filter_tracks())

        self.count_label = ctk.CTkLabel(
            top_bar, text="", font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self.count_label.pack(side=tk.RIGHT, padx=10)

        # ─── Main 3-panel area ───
        panels = ctk.CTkFrame(self, fg_color="transparent")
        panels.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Panel 1: Track list (left)
        self.left_panel = ctk.CTkFrame(panels, width=350, corner_radius=10)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        self.left_panel.pack_propagate(False)

        ctk.CTkLabel(
            self.left_panel, text="Tracks",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(pady=(12, 6), padx=12, anchor='w')

        # Scrollable track list
        self.track_scroll = ctk.CTkScrollableFrame(
            self.left_panel, fg_color="transparent"
        )
        self.track_scroll.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # Panel 2: Course list (middle)
        self.mid_panel = ctk.CTkFrame(panels, width=340, corner_radius=10)
        self.mid_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5)
        self.mid_panel.pack_propagate(False)

        # Track header area in mid panel
        self.track_header = ctk.CTkFrame(self.mid_panel, fg_color="transparent")
        self.track_header.pack(fill=tk.X, padx=12, pady=(12, 6))

        self.track_name_label = ctk.CTkLabel(
            self.track_header, text="Select a Track",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        )
        self.track_name_label.pack(anchor='w')

        self.track_info_label = ctk.CTkLabel(
            self.track_header, text="",
            font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self.track_info_label.pack(anchor='w')

        # Track image area
        self.track_image_frame = ctk.CTkFrame(
            self.mid_panel, fg_color=BG_MEDIUM, corner_radius=8, height=140
        )
        self.track_image_frame.pack(fill=tk.X, padx=12, pady=(0, 6))
        self.track_image_frame.pack_propagate(False)

        self.track_image_label = ctk.CTkLabel(
            self.track_image_frame, text="No image", text_color=TEXT_MUTED
        )
        self.track_image_label.pack(expand=True)

        # Course list header
        ctk.CTkLabel(
            self.mid_panel, text="Courses",
            font=FONT_SUBHEADER, text_color=ACCENT_TERTIARY
        ).pack(padx=12, pady=(6, 4), anchor='w')

        # Scrollable course list
        self.course_scroll = ctk.CTkScrollableFrame(
            self.mid_panel, fg_color="transparent"
        )
        self.course_scroll.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # Panel 3: Course detail (right)
        self.right_panel = ctk.CTkFrame(panels, corner_radius=10)
        self.right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.detail_header = ctk.CTkLabel(
            self.right_panel, text="Course Details",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        )
        self.detail_header.pack(padx=16, pady=(12, 4), anchor='w')

        self.detail_subtitle = ctk.CTkLabel(
            self.right_panel, text="Select a course to view details",
            font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self.detail_subtitle.pack(padx=16, anchor='w')

        # Detail content (scrollable)
        self.detail_scroll = ctk.CTkScrollableFrame(
            self.right_panel, fg_color="transparent"
        )
        self.detail_scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 8))
        
        # Bind resize event to the static right_panel instead of the scrollable frame itself
        # This avoid conflicts with internal canvas resizing while scrolling
        self.right_panel.bind("<Configure>", self._on_detail_resize, add="+")

    # ─────────────────────────────────────────────
    # Data Loading
    # ─────────────────────────────────────────────

    def load_tracks(self):
        """Load all tracks from DB"""
        self.tracks = get_all_tracks()
        self.render_track_list(self.tracks)

    def filter_tracks(self):
        """Filter tracks by search term"""
        term = self.search_var.get().strip().lower()
        if term:
            filtered = [t for t in self.tracks if term in t[1].lower()]
        else:
            filtered = self.tracks
        self.render_track_list(filtered)

    # ─────────────────────────────────────────────
    # Track List Rendering
    # ─────────────────────────────────────────────

    def render_track_list(self, tracks):
        """Render clickable track cards in the left panel"""
        for w in self.track_scroll.winfo_children():
            w.destroy()

        self.count_label.configure(text=f"{len(tracks)} tracks")

        if not tracks:
            ctk.CTkLabel(
                self.track_scroll,
                text="No tracks found.\nRun the scraper first:\npython main.py --scrape-tracks",
                font=FONT_BODY, text_color=TEXT_MUTED,
                justify='center'
            ).pack(pady=40)
            return

        for track in tracks:
            track_id, name, location, image_path, course_count = track
            self._create_track_card(track_id, name, location, image_path, course_count)

    def _create_track_card(self, track_id, name, location, image_path, course_count):
        """Create a single track card button"""
        card = ctk.CTkFrame(
            self.track_scroll, fg_color=BG_MEDIUM,
            corner_radius=8, cursor="hand2"
        )
        card.pack(fill=tk.X, pady=3, padx=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill=tk.X, padx=10, pady=8)

        # Track name
        name_label = ctk.CTkLabel(
            inner, text=name,
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY,
            anchor='w'
        )
        name_label.pack(fill=tk.X)

        # Subtitle
        subtitle_parts = []
        if location:
            subtitle_parts.append(location)
        subtitle_parts.append(f"{course_count} course{'s' if course_count != 1 else ''}")

        ctk.CTkLabel(
            inner, text=" · ".join(subtitle_parts),
            font=FONT_TINY, text_color=TEXT_MUTED,
            anchor='w'
        ).pack(fill=tk.X)

        # Click handler for all children
        def on_click(e, tid=track_id):
            self.select_track(tid)

        card.bind('<Button-1>', on_click)
        inner.bind('<Button-1>', on_click)
        name_label.bind('<Button-1>', on_click)
        for child in inner.winfo_children():
            child.bind('<Button-1>', on_click)

        # Ensure scroll propagation for the track card
        self._bind_scroll_recursive(card, self.track_scroll)

        # Hover effect
        def on_enter(e):
            card.configure(fg_color=BG_LIGHT)

        def on_leave(e):
            if self.current_track_id != track_id:
                card.configure(fg_color=BG_MEDIUM)

        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)

        # Store reference for highlight
        card._track_id = track_id

    # ─────────────────────────────────────────────
    # Track Selection
    # ─────────────────────────────────────────────

    def select_track(self, track_id):
        """Handle track selection"""
        self.current_track_id = track_id
        self.current_course_id = None

        # Find track info
        track = None
        for t in self.tracks:
            if t[0] == track_id:
                track = t
                break

        if not track:
            return

        track_id, name, location, image_path, course_count = track

        # Update header
        self.track_name_label.configure(text=f"🏟️ {name}")
        info_text = f"{course_count} course{'s' if course_count != 1 else ''}"
        if location:
            info_text = f"{location} · {info_text}"
        self.track_info_label.configure(text=info_text)

        # Load track image
        self._load_track_image(image_path)

        # Highlight selected track card
        for child in self.track_scroll.winfo_children():
            if hasattr(child, '_track_id'):
                if child._track_id == track_id:
                    child.configure(fg_color=BG_LIGHT)
                else:
                    child.configure(fg_color=BG_MEDIUM)

        # Load courses
        courses = get_track_courses(track_id)
        self.render_course_list(courses)

        # Clear detail panel
        self.detail_header.configure(text="Course Details")
        self.detail_subtitle.configure(text="Select a course to view details")
        for w in self.detail_scroll.winfo_children():
            w.destroy()

    def _load_track_image(self, image_path):
        """Load track image into the mid panel"""
        resolved = resolve_track_image(image_path)

        if resolved and os.path.exists(resolved):
            try:
                img = ctk.CTkImage(
                    light_image=Image.open(resolved),
                    dark_image=Image.open(resolved),
                    size=(276, 130)
                )
                self.track_image_label.configure(image=img, text="")
                self.track_image = img  # Keep reference
            except Exception:
                self.track_image_label.configure(image=None, text="[Image Error]")
        else:
            self.track_image_label.configure(image=None, text="No image available")

    def _on_detail_resize(self, event):
        """Handle resize of the detail scroll frame to rescale the course map"""
        if not self.current_map_path:
            return
            
        # Debounce to avoid excessive redraws
        if self.resize_after_id:
            self.after_cancel(self.resize_after_id)
        self.resize_after_id = self.after(100, self._perform_map_resize)

    def _perform_map_resize(self):
        """Execute the actual map redraw once resize settles"""
        if self.current_map_path:
            self._load_course_map(self.current_map_path, is_resize=True)

    def _load_course_map(self, image_path, is_resize=False):
        """Load and display course map, scaling to current available width"""
        self.current_map_path = image_path
        resolved = resolve_track_image(image_path)
        
        if resolved and os.path.exists(resolved):
            try:
                # Calculate available width (detail_scroll width minus padding/scrollbar)
                # event.width might be slightly inaccurate due to scrollbar
                scroll_width = self.detail_scroll.winfo_width()
                if scroll_width <= 1: # Window not rendered yet
                    # Fallback to a reasonable default or wait for next configure
                    display_width = 850 if self.winfo_width() > 1200 else 400
                else:
                    display_width = max(300, scroll_width - 40) # 40px buffer for scrollbar/padding

                orig = Image.open(resolved)
                w, h = orig.size
                display_height = int(h * (display_width / w))
                
                img = ctk.CTkImage(
                    light_image=orig,
                    dark_image=orig,
                    size=(display_width, display_height)
                )
                
                # If this is a resize and we already have a label, just update it
                if is_resize and self.map_label:
                    self.map_label.configure(image=img)
                    self.map_label._image = img
                    return

                # Otherwise (initial load), build the frame
                if self.map_frame:
                    self.map_frame.destroy()

                self.map_frame = create_card_frame(self.detail_scroll)
                self.map_frame.pack(pady=4, padx=4, anchor="w")
                
                self.map_label = ctk.CTkLabel(self.map_frame, image=img, text="")
                self.map_label.pack(padx=2, pady=2)
                self.map_label._image = img # Keep reference
                
                # Ensure scroll propagation for the course map
                self._bind_scroll_recursive(self.map_frame, self.detail_scroll)
                
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error loading course map: {e}")

    def _propagate_scroll(self, event, scroll_frame):
        """Manually propagate mouse wheel events to a specific scrollable canvas"""
        # On Windows, delta is usually 120
        scroll_frame._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _bind_scroll_recursive(self, widget, scroll_frame):
        """Recursively bind mouse wheel to a widget and its children, targeting a specific scroll area"""
        widget.bind("<MouseWheel>", lambda e: self._propagate_scroll(e, scroll_frame), add="+")
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child, scroll_frame)

    # ─────────────────────────────────────────────
    # Course List Rendering
    # ─────────────────────────────────────────────

    def render_course_list(self, courses):
        """Render course entries in the middle panel"""
        for w in self.course_scroll.winfo_children():
            w.destroy()

        if not courses:
            ctk.CTkLabel(
                self.course_scroll,
                text="No courses found",
                font=FONT_BODY, text_color=TEXT_MUTED
            ).pack(pady=20)
            return

        for course in courses:
            course_id, distance, surface, direction, corner_count, final_straight = course
            self._create_course_card(
                course_id, distance, surface, direction, corner_count, final_straight
            )

    def _create_course_card(self, course_id, distance, surface, direction,
                            corner_count, final_straight):
        """Create a single course card"""
        card = ctk.CTkFrame(
            self.course_scroll, fg_color=BG_MEDIUM,
            corner_radius=8, cursor="hand2"
        )
        card.pack(fill=tk.X, pady=2, padx=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill=tk.X, padx=10, pady=6)

        # Top row: distance + surface
        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill=tk.X)

        surf_icon = SURFACE_ICONS.get(surface, '')
        surf_color = SURFACE_COLORS.get(surface, TEXT_SECONDARY)

        ctk.CTkLabel(
            top_row, text=f"{distance}m",
            font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        ctk.CTkLabel(
            top_row, text=f"  {surf_icon} {surface or '?'}",
            font=FONT_SMALL, text_color=surf_color
        ).pack(side=tk.LEFT, padx=(4, 0))

        if direction:
            dir_icon = DIRECTION_ICONS.get(direction, '')
            ctk.CTkLabel(
                top_row, text=f"  {dir_icon} {direction}",
                font=FONT_SMALL, text_color=TEXT_MUTED
            ).pack(side=tk.LEFT, padx=(4, 0))

        # Bottom row: corner count + final straight
        details = []
        if corner_count:
            details.append(f"🔄 {corner_count} corners")
        if final_straight:
            details.append(f"📏 Final: {final_straight}")

        if details:
            ctk.CTkLabel(
                inner, text="  ·  ".join(details),
                font=FONT_TINY, text_color=TEXT_MUTED,
                anchor='w'
            ).pack(fill=tk.X)

        # Click handler
        def on_click(e, cid=course_id):
            self.select_course(cid)

        card.bind('<Button-1>', on_click)
        inner.bind('<Button-1>', on_click)
        for child in inner.winfo_children():
            child.bind('<Button-1>', on_click)
            for grandchild in child.winfo_children():
                grandchild.bind('<Button-1>', on_click)

        # Hover
        def on_enter(e):
            card.configure(fg_color=BG_LIGHT)

        def on_leave(e):
            if self.current_course_id != course_id:
                card.configure(fg_color=BG_MEDIUM)

        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)
        card._course_id = course_id
        
        # Ensure scroll propagation for the course card
        self._bind_scroll_recursive(card, self.course_scroll)

    # ─────────────────────────────────────────────
    # Course Detail
    # ─────────────────────────────────────────────

    def select_course(self, course_id):
        """Show full detail for a selected course"""
        self.current_course_id = course_id

        # Highlight
        for child in self.course_scroll.winfo_children():
            if hasattr(child, '_course_id'):
                if child._course_id == course_id:
                    child.configure(fg_color=BG_LIGHT)
                else:
                    child.configure(fg_color=BG_MEDIUM)

        detail = get_course_detail(course_id)
        if not detail:
            return

        (cid, distance, surface, direction, corner_count,
         final_straight, slope_info, weather_data,
         phases_json, corners_json, straights_json, other_json,
         raw_json, map_image_path, track_name) = detail

        # Update header
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
            subtitle_parts.append(f"Final Straight: {final_straight}")
        self.detail_subtitle.configure(text="  ·  ".join(subtitle_parts) if subtitle_parts else "")

        # Clear and rebuild detail content
        for w in self.detail_scroll.winfo_children():
            w.destroy()

        # ─── Course Map ───
        if map_image_path:
            self._load_course_map(map_image_path)

        # ─── Overview card ───
        self._add_detail_section("📋 Overview", [
            ("Distance", f"{distance} m"),
            ("Surface", f"{surf_icon} {surface}" if surface else "N/A"),
            ("Direction", f"{DIRECTION_ICONS.get(direction, '')} {direction}" if direction else "N/A"),
            ("Corners", str(corner_count) if corner_count else "N/A"),
            ("Final Straight", final_straight or "N/A"),
            ("Slope", slope_info or "—"),
        ])

        # ─── Phases ───
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
                    self._add_detail_section("🏁 Phases", rows)
            except (json.JSONDecodeError, TypeError):
                pass

        # ─── Corners ───
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
                    self._add_detail_section("🔄 Corners", rows)
            except (json.JSONDecodeError, TypeError):
                pass

        # ─── Straights ───
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
                    self._add_detail_section("📏 Straights", rows)
            except (json.JSONDecodeError, TypeError):
                pass

        # ─── Other ───
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
                    self._add_detail_section("📊 Other", rows)
            except (json.JSONDecodeError, TypeError):
                pass

        # ─── Weather / Slope ───
        extra_rows = []
        if weather_data:
            extra_rows.append(("Weather", weather_data))
        if slope_info:
            extra_rows.append(("Slope Info", slope_info))
        if extra_rows:
            self._add_detail_section("🌤️ Conditions", extra_rows)

    def _add_detail_section(self, title, rows):
        """Add a styled section card to the detail panel"""
        section = create_card_frame(self.detail_scroll)
        section.pack(fill=tk.X, pady=4, padx=4)

        # Title
        ctk.CTkLabel(
            section, text=title,
            font=FONT_SUBHEADER, text_color=ACCENT_TERTIARY
        ).pack(padx=12, pady=(10, 4), anchor='w')

        # Separator
        sep = ctk.CTkFrame(section, height=1, fg_color=BG_LIGHT)
        sep.pack(fill=tk.X, padx=12, pady=(0, 4))

        # Rows
        for label, value in rows:
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill=tk.X, padx=12, pady=2)

            ctk.CTkLabel(
                row, text=label,
                font=FONT_BODY, text_color=TEXT_MUTED,
                width=140, anchor='w'
            ).pack(side=tk.LEFT)

            ctk.CTkLabel(
                row, text=value,
                font=FONT_BODY_BOLD, text_color=TEXT_PRIMARY,
                anchor='w'
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Apply recursive scroll binding to the entire section
        self._bind_scroll_recursive(section, self.detail_scroll)

        # Bottom padding
        ctk.CTkFrame(section, fg_color="transparent", height=6).pack()
