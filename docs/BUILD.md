# Build Instructions for AOS-CX Config Backup Tool

## Prerequisites

Install Python 3.8 or higher and pip.

## Install Dependencies

```bash
pip install -r requirements.txt
```

Or manually install:
```bash
pip install pyinstaller requests ttkbootstrap schedule infi.systray PyGithub cryptography boto3 Pillow
```

## Building the Executable

### macOS Build

1. Navigate to the project directory:
   ```bash
   cd /path/to/AOS-CX-Config-Backup-Tool
   ```

2. Build using the macOS spec file:
   ```bash
   pyinstaller .build/AOS-CX.Config.Backup.Tool.spec --clean --noconfirm
   ```

3. The application will be created in `dist/AOS-CX Config Backup Tool.app`

### Windows Build

**Note: Windows .exe files must be built on a Windows machine.**

1. Copy all files to your Windows machine
2. Install Python and dependencies (see above)
3. Build using the Windows spec file:
   ```powershell
   pyinstaller .build/AOS-CX.Config.Backup.Tool_Windows.spec --clean --noconfirm
   ```

4. The executable will be created in `dist/AOS-CX.Config.Backup.Tool.exe`

## Icon Information

- Icon source: cmdlab.tech logo (transparent PNG)
- Location: `.build/icon.ico` and `.build/icon.png`
- Included in: Both macOS and Windows builds

## Build Artifacts

After building:
- `build/` - Temporary build files (can be deleted)
- `dist/` - Final executable/app (distribute this)
- `*.spec` - PyInstaller configuration files

## Troubleshooting

### Missing Dependencies
If PyInstaller fails to detect a module, add it to `hiddenimports` in the .spec file.

### Icon Issues
- macOS: .icns format preferred but .ico works
- Windows: Must use .ico format
- The icon is embedded in the executable during build

### tkinter Issues
If tkinter fails to build, ensure Tcl/Tk is properly installed:
- **macOS**: `brew install python-tk@3.14`
- **Windows**: Usually included with Python installer (ensure "tcl/tk and IDLE" is checked)

## File Permissions

The application automatically sets restrictive permissions on:
- `encryption_key.key` (600 - owner read/write only)
- Configuration backup files (600 - owner read/write only)

## Cross-Platform Notes

- macOS builds create `.app` bundles
- Windows builds create standalone `.exe` files
- Linux builds create executables without extension
- Each platform must build on its native OS for best compatibility
