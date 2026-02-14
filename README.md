# AOS-CX Config Backup Tool
A lightweight utility to automate configuration backups for AOS-CX switches using the REST API. Supports both scheduled and manual backups, running discreetly from the system tray without requiring a service installation. Ensures reliable, unattended operation for scheduled tasks.

## 📥 Download

**Pre-built executables available in this repository:**
- **Windows**: `AOS-CX.Config.Backup.Tool.exe`
- **macOS**: `AOS-CX Config Backup Tool.app/`

Or download from the [Releases](../../releases) page.

## 📚 Documentation

- **[Build Instructions](docs/BUILD.md)** - Compile from source
- **[GitHub Actions Guide](docs/GITHUB_ACTIONS.md)** - CI/CD automation

# Requirements
  - Switch firmware version of at least 10.04

## Usage
1. Create CSV file with the structure below

  | name    | ip           |
  |---------|--------------|
  | switch1 | 192.168.1.1  |
  | switch2 | 192.168.1.2  |
  | switch3 | 192.168.1.3  |

2. Run exe
3. Select CSV file created in Step 1
4. Choose backup directory location
5. Set API Credentials - user can have operator built-in role for security purposes
6. (optional) Enable "Automatic Schedule"
7. (optional) Click "Run Backup Now" for a manual config backup of switches listed in csv file


![image](https://github.com/user-attachments/assets/eeb18fd3-120e-4d2c-a258-9af097163791)



   

<!-- GitAds-Verify: Z6ZHXBL5TGG74LMBZTJYZARG8DOAL5FP -->
[![Sponsored by GitAds](https://gitads.dev/v1/ad-serve?source=cmdlabtech/aos-cx-config-backup-tool@github)](https://gitads.dev/v1/ad-track?source=cmdlabtech/aos-cx-config-backup-tool@github)
