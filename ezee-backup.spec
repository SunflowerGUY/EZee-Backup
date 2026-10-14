# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ezee-backup.py'],
    pathex=[],
    binaries=[],
    datas=[('ezee-backup.ico', '.'), ('EZeeBACK Logo.jpg', '.'), ('backup-info.png', '.'), ('EZ-guitar.wav', '.'), ('EZ-error.wav', '.'), ('EZ-short-alert1.wav', '.')],
    hiddenimports=[],
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
    name='ezee-backup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ezee-backup.ico'],
)
