# Build Instructions for AOS-CX Config Backup Tool

## Prerequisites

- Windows 10/11
- Python 3.11 or higher
- pip package manager

## Install Dependencies

```bash
pip install -r requirements.txt
```

Or manually install:
```bash
pip install pyinstaller requests ttkbootstrap schedule infi.systray PyGithub cryptography boto3 Pillow
```

## Building the Windows Executable

**Note: The executable must be built on a Windows machine.**

### Option 1: Use the Build Script (Recommended)

1. Install Python 3.11 or higher from [python.org](https://python.org)
2. Double-click `.build/build_windows.bat` or run in Command Prompt:
   ```cmd
   .build\build_windows.bat
   ```
3. The script will automatically install dependencies, build, and place the executable in the root directory

### Option 2: Manual Build

1. Install Python and dependencies (see above)
2. Build using the Windows spec file:
   ```cmd
   pyinstaller .build/AOS-CX.Config.Backup.Tool_Windows.spec --clean --noconfirm
   ```
3. The executable will be created in `dist/AOS-CX.Config.Backup.Tool.exe`

### Building with Parallels Desktop (macOS Users)

If you're on macOS using Parallels Desktop with Windows 11:

1. **Share the project folder**: In Parallels, enable shared folders (Parallels > Configure > Options > Sharing)
2. **In Windows VM**: The project folder will appear in `\\Mac\Home\Documents\GitHub\AOS-CX-Config-Backup-Tool`
3. **Open Command Prompt** as Administrator (right-click Start > Command Prompt (Admin))
4. Navigate to the shared folder:
   ```cmd
   cd \\Mac\Home\Documents\GitHub\AOS-CX-Config-Backup-Tool
   ```
5. Run the build script:
   ```cmd
   .build\build_windows.bat
   ```
6. The executable will be available in both Windows and macOS (shared folder)

## Icon Information

- Icon source: cmdlab.tech logo
- Location: `.build/icon.ico` and `.build/icon.png`
- Format: .ico (Windows compatible)
- The icon is embedded in the executable during build

## Build Artifacts

After building:
- `build/` - Temporary build files (can be deleted)
- `dist/` - Final executable (distribute this)
- `.build/AOS-CX.Config.Backup.Tool_Windows.spec` - PyInstaller configuration file

## Troubleshooting

### Missing Dependencies
If PyInstaller fails to detect a module, add it to `hiddenimports` in the .spec file.

### Icon Issues
- Windows requires .ico format
- The build script automatically converts PNG to ICO if needed

### tkinter Issues
If tkinter fails to build, ensure Tcl/Tk is properly installed:
- Usually included with Python installer (ensure "tcl/tk and IDLE" is checked during installation)
- Reinstall Python with the tcl/tk option if needed

## File Permissions

The application automatically sets restrictive permissions on:
- `encryption_key.key` (owner read/write only)
- Configuration backup files (owner read/write only)
