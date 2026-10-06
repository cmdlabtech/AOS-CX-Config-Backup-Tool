# -*- mode: python ; coding: utf-8 -*-
# Windows-specific PyInstaller spec file (one-folder / onedir build)
# Produces dist/AOS-CX.Config.Backup.Tool/ containing the .exe and its support files

import os

spec_root = SPECPATH
project_root = os.path.dirname(spec_root)

block_cipher = None

a = Analysis(
    [os.path.join(project_root, 'AOS-CX.Config.Backup.Tool_3.6.py')],
    pathex=[],
    binaries=[],
    datas=[(os.path.join(spec_root, 'icon.ico'), '.')],
    hiddenimports=[
        'PIL._tkinter_finder',
        'ttkbootstrap',
        'github',
        'boto3',
        'botocore',
        'cryptography',
        'infi.systray',
        'schedule',
        'urllib3'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AOS-CX.Config.Backup.Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Set to False for windowed app (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(spec_root, 'icon.ico'),  # Windows will use this icon
    version=os.path.join(spec_root, 'version_info.txt'),  # Windows version-info resource
    uac_admin=False,  # Set to True if admin privileges needed
    uac_uiaccess=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AOS-CX.Config.Backup.Tool',
)
