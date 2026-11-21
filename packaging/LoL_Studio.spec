# -*- mode: python ; coding: utf-8 -*-


import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(ROOT_DIR, 'main_gui.py')],
    pathex=[os.path.join(ROOT_DIR, 'scripts'), ROOT_DIR],
    binaries=[],
    datas=[
        (os.path.join(ROOT_DIR, 'web'), 'web'),
        (os.path.join(ROOT_DIR, 'scripts'), 'scripts'),
        (os.path.join(ROOT_DIR, 'all_lol_skins_database.json'), '.'),
        (os.path.join(ROOT_DIR, 'vgmstream'), 'vgmstream')
    ],
    hiddenimports=['webview', 'webview.platforms.winforms', 'webview.platforms.edgechromium', 'server_backend', 'http.server', 'socketserver', 'metadata_manager', 'event_categorizer', 'lol_voice_extractor_expert', 'extract_target_references', 'analyze_competitor_channels', 'xml.etree.ElementTree', 'concurrent.futures', 'zstandard', 'urllib.request'],
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
    [],
    exclude_binaries=True,
    name='LoL_Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LoL_Studio',
)
