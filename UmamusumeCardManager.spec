# -*- mode: python ; coding: utf-8 -*-
import os
import importlib

try:
    playwright_path = os.path.dirname(importlib.import_module("playwright").__file__)
except ImportError:
    playwright_path = None

datas_list = [
    ('images', 'images'), 
    ('assets', 'assets'), 
    ('database/umamusume_seed.db', 'database'), 
    ('version.py', '.'), 
    ('updater', 'updater')
]

if playwright_path:
    datas_list.append((playwright_path, 'playwright'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=['requests', 'PIL', 'PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
