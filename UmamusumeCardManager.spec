# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import importlib

# ── Playwright ────────────────────────────────────────────────────────────────
try:
    playwright_path = os.path.dirname(importlib.import_module("playwright").__file__)
except ImportError:
    playwright_path = None

# ── PySide6 Qt plugins ────────────────────────────────────────────────────────
try:
    import PySide6
    pyside6_dir = os.path.dirname(PySide6.__file__)
    qt_plugins_dir = os.path.join(pyside6_dir, "Qt", "plugins")
except Exception:
    pyside6_dir = None
    qt_plugins_dir = None

# ── Datas ─────────────────────────────────────────────────────────────────────
datas_list = [
    ('images',                     'images'),
    ('assets',                     'assets'),
    ('database/umamusume_seed.db', 'database'),
    ('version.py',                 '.'),
    ('updater',                    'updater'),
]

if playwright_path:
    datas_list.append((playwright_path, 'playwright'))

# Bundle Qt plugins required for a windowed PySide6 app on Windows
if qt_plugins_dir and os.path.isdir(qt_plugins_dir):
    for plugin_subdir in ('platforms', 'styles', 'imageformats', 'iconengines'):
        src = os.path.join(qt_plugins_dir, plugin_subdir)
        if os.path.isdir(src):
            datas_list.append((src, os.path.join('PySide6', 'Qt', 'plugins', plugin_subdir)))

# ── Hidden imports ────────────────────────────────────────────────────────────
hidden = [
    'requests',
    'PIL',
    # PySide6 internals that PyInstaller sometimes misses
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    'shiboken6',
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['customtkinter', 'tkinter', '_tkinter'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='UmamusumeCardManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
