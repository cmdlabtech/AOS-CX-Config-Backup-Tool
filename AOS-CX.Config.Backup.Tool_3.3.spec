# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['AOS-CX.Config.Backup.Tool_3.3.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.')],
    hiddenimports=['tkinter', 'ttkbootstrap', 'ttkbootstrap.style', 'ttkbootstrap.constants', 'ttkbootstrap.localization.msgs', 'cryptography', 'boto3', 'github', 'infi.systray'],
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
    name='AOS-CX.Config.Backup.Tool_3.3',
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
    icon=['icon.ico'],
)
