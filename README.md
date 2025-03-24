# AOS-CX Config Backup Tool
Automates configuration backups for AOS-CX switches via REST API, with scheduling or manual trigger.

# Requirements
 - v10.13 API - Released with 10.13.1000

***Manual EXE Execution***
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

***Install as a service***
1. Follow steps in "Manual EXE Execution" section above
2. Download NSSM - https://nssm.cc/download
3. Extract ZIP
4. Open a command prompt with administrator privileges (right-click Command Prompt and select "Run as administrator").
5. Run the following command to install the service:
   - %USERPROFILE%\Downloads\nssm-2.24\nssm-2.24\win64\nssm.exe install SwitchBackupService
6. In the NSSM GUI that appears:
   - Path: Set to C:\path\to\your\script\dist\AOS-CX-Config-Export.exe.
   - Startup directory: Set to C:\path\to\your\script\dist.
   - Arguments: Leave blank (the executable doesn’t need arguments).
   - Service name: Ensure it’s set to SwitchBackupService.
   - Click "Install service".
8. Start the service
   - net start SwitchBackupService
