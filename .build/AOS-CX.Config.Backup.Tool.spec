# -*- mode: python ; coding: utf-8 -*-
import os

spec_root = SPECPATH
project_root = os.path.dirname(spec_root)

block_cipher = None

a = Analysis(
    [os.path.join(project_root, 'AOS-CX.Config.Backup.Tool_3.3.py')],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AOS-CX.Config.Backup.Tool',
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
    icon=os.path.join(spec_root, 'icon.ico'),
)

app = BUNDLE(
    exe,
    name='AOS-CX Config Backup Tool.app',
    icon=os.path.join(spec_root, 'icon.ico'),
    bundle_identifier='com.cmdlabtech.aos-cx-backup',
    info_plist={
        'CFBundleName': 'AOS-CX Config Backup Tool',
        'CFBundleDisplayName': 'AOS-CX Config Backup Tool',
        'CFBundleVersion': '3.3',
        'CFBundleShortVersionString': '3.3',
        'NSHighResolutionCapable': True,
    },
)
