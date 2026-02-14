@echo off
REM Windows Build Script for AOS-CX Config Backup Tool
REM Run this script in Windows (Parallels VM) to build the executable

echo ========================================
echo AOS-CX Config Backup Tool - Windows Build
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher from python.org
    pause
    exit /b 1
)

echo [1/3] Installing required packages...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

echo.
echo [2/3] Building Windows executable with PyInstaller...
pyinstaller .build\AOS-CX.Config.Backup.Tool_Windows.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [3/3] Moving executable to root directory...
if exist "dist\AOS-CX.Config.Backup.Tool.exe" (
    move /Y "dist\AOS-CX.Config.Backup.Tool.exe" "AOS-CX.Config.Backup.Tool.exe"
    echo.
    echo ========================================
    echo BUILD SUCCESSFUL!
    echo ========================================
    echo Executable location: AOS-CX.Config.Backup.Tool.exe
    echo.
) else (
    echo ERROR: Executable not found in dist folder
    pause
    exit /b 1
)

pause
