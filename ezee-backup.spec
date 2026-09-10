# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ezee-backup.py'],
    pathex=[],
    binaries=[],
    datas=[('EZeeBACK Logo.jpg', '.'), ('ezee-backup.ico', '.'), ('backup-info.png', '.'), ('EZ-guitar.wav', '.'), ('EZ-error.wav', '.')],
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
    name='EZee-Backup',
    icon='ezee-backup.ico',
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
)
