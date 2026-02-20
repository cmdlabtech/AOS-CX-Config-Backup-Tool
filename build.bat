@echo off
echo Building AOS-CX Config Backup Tool exe...

REM Install dependencies if needed (uncomment if virtualenv is not set up)
REM pip install -r requirements.txt

REM Build the exe
pyinstaller --onefile --windowed --icon=icon.ico --add-data "icon.ico;." --hidden-import=tkinter --hidden-import=ttkbootstrap --hidden-import=ttkbootstrap.style --hidden-import=ttkbootstrap.constants --hidden-import=ttkbootstrap.localization.msgs --hidden-import=cryptography --hidden-import=boto3 --hidden-import=github --hidden-import=infi.systray AOS-CX.Config.Backup.Tool_3.3.py

echo Build complete. Check the dist folder for the exe.