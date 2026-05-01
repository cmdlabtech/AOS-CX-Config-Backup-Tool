# AOS-CX Config Backup Tool

**Automate configuration backups for AOS-CX switches with ease. Schedule backups, store locally or upload to Git/Wasabi S3, all from a system tray app.**

A Windows desktop tool for network admins who need reliable, unattended AOS-CX config backups without complex setups.

## 📥 Download Latest Version

| Platform | Download | Requirements |
|----------|----------|--------------|
| **🪟 Windows** | [**Download EXE (V3.7)**](https://github.com/cmdlabtech/AOS-CX-Config-Backup-Tool/releases/download/V3.7/AOS-CX.Config.Backup.Tool.exe) | Windows 10/11 |

### Installation

**Windows:**  
Run the EXE directly. If Windows Defender warns you, click "More info" → "Run anyway".

---

## ✨ Features

- **🔄 Scheduled Backups** - Set daily, weekly, or custom schedules for automatic config pulls
- **📁 Local Storage** - Save backups to any directory with automatic retention (max 5 per switch)
- **☁️ Cloud Upload** - Optional upload to GitHub repos or Wasabi S3 buckets
- **🖥️ System Tray** - Runs discreetly in the background, no service installation needed
- **🔐 Secure Credentials** - Encrypted storage of API credentials and tokens
- **📊 Status Tracking** - Real-time backup status and history per switch
- **⚡ Manual Mode** - Run on-demand backups anytime
- **🔒 REST API v10.04** - Compatible with AOS-CX firmware 10.04+

---

## 🚀 Usage

1. Create a CSV file with switch details:

   | name    | ip           |
   |---------|--------------|
   | switch1 | 192.168.1.1  |
   | switch2 | 192.168.1.2  |
   | switch3 | 192.168.1.3  |

2. Launch the app
3. Select your CSV file
4. Choose a backup directory
5. Enter REST API credentials (operator role recommended)
6. (Optional) Enable scheduling and cloud uploads
7. (Optional) Click "Run Now" for immediate backup

![Screenshot](https://github.com/user-attachments/assets/eeb18fd3-120e-4d2c-a258-9af097163791)

---

## 📋 Requirements

- Windows 10/11
- AOS-CX switch firmware ≥10.04
- CSV formatted file which includes the name of ip(s) of the switches that you want backed up

---

## 🔄 Changelog

### V3.6
- Fixed GUI freeze during backups by running in background thread
- Fixed thread safety for all GUI updates (scheduled and manual backups)
- Fixed crash on corrupted config/status JSON files
- Fixed logout firing unnecessarily on failed login retries
- Improved Git repo URL parsing (accepts multiple formats)
- Added log rotation (5MB max, 3 backups) to prevent unbounded growth
- Updated GitHub Actions release action to v2

### V3.4
- Fixed app opening errors related to tkinter compatibility and DLL issues
- Switched to dark theme for better usability
- Improved build process with hidden imports for better exe compatibility

### V3.3
- Initial release with scheduling, local backups, and cloud integrations

---

## 📝 License

MIT License - Copyright © 2026

---

**Made by Cameron**
