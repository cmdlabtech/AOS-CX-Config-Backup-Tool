# AOS-CX Config Backup Tool - AI Coding Instructions

## ⚠️ CRITICAL RULES

### Git Workflow
**DO NOT commit or push to GitHub until explicitly instructed by the user.** Always wait for approval before making any Git operations.

### Security Requirements
Always follow best security practices:
- **Windows Security**: Consider UAC, file permissions, antivirus compatibility, secure temp file handling
- **AOS-CX Connectivity**: Use TLS/SSL verification where possible, validate certificates, secure session management
- **Credential Storage**: Maintain Fernet encryption for all secrets, never log passwords, ensure key file protection

## Project Overview
Single-file Python GUI application for automated AOS-CX switch configuration backups via REST API (v10.04). Runs from system tray with scheduling capabilities and multi-destination support (local/Git/Wasabi S3).

## Architecture & Key Components

### Monolithic Design
- **Single file**: `AOS-CX.Config.Backup.Tool_3.3.py` contains entire application
- `SwitchBackup` class manages all functionality: GUI, scheduling, backups, uploads
- System tray integration keeps app running in background
- Threading isolates scheduled backups from GUI operations

### Critical Data Flow
1. **CSV Inventory** → Switch backup loop → REST API retrieval (v10.04 endpoint)
2. **Local save** → Git upload (if enabled) → Wasabi upload (if enabled)
3. **Status tracking** persisted to `switch_status.json` after each operation

### Configuration Files (base_dir_path)
- `backup_config.json`: Encrypted credentials, schedule settings, integration configs
- `switch_status.json`: Per-switch backup history and upload results
- `encryption_key.key`: Fernet key for credential encryption (auto-generated)
- `switch_backup.log`: Application logging

## REST API Integration Patterns

### Authentication Flow
```python
# Session-based: login → get config → logout (always cleanup)
session.post(f"https://{ip}/rest/v10.04/login", ...)
session.get(f"https://{ip}/rest/v10.04/configs/running-config", headers={"Accept": "text/plain"})
session.post(f"https://{ip}/rest/v10.04/logout", ...)
```

### Retry Logic
- 3 attempts with 5-second delays for config retrieval
- Connectivity pre-check before authentication
- Logout always attempted in `finally` block

## Key Conventions

### Credential Security
- All passwords/tokens encrypted using Fernet before JSON persistence
- `_encrypt()` / `_decrypt()` used for `default_password`, `git_token`, Wasabi keys
- CSV can include per-switch credentials (fallback to defaults)

### Backup Retention
- `max_backups = 5` per switch (oldest deleted automatically)
- Filename format: `{switch_name}_{ip}_{timestamp}.txt`
- Directory structure: `{base_dir}/{switch_name}/{backups...}`

### Multi-Destination Uploads
- **Conditional execution**: Only proceed to Git/Wasabi if ALL switch backups succeed
- Each destination has `{service}_enabled` flag and separate status tracking
- Upload methods update global `last_{service}_status` shown in status tree

### PyInstaller Compatibility
- `sys.frozen` detection for executable vs. script paths
- `resource_path()` method handles bundled resources (icon.ico)
- `sys._MEIPASS` for temporary extraction directory

## Security Best Practices

### Windows-Specific Security
- Respect Windows file permissions when creating config files in `base_dir_path`
- Handle paths safely - avoid directory traversal vulnerabilities
- Consider Windows Defender/antivirus when timing network operations
- Use appropriate file modes (`'wb'` for binary keys, proper encoding for configs)

### AOS-CX Switch Connectivity
- Current implementation disables SSL warnings (`verify=False`) - document security implications
- Always use `timeout` parameter in requests to prevent hanging connections
- Session cleanup in `finally` blocks prevents authentication session leaks
- Connectivity pre-check avoids credential exposure to unreachable hosts

### Credential Management
- **Never log plaintext passwords** - existing code properly excludes credentials from logs
- Encryption key (`encryption_key.key`) should have restricted file permissions
- Git tokens require `repo` scope only (principle of least privilege)
- Wasabi keys stored encrypted - ensure S3 bucket policies are restrictive
- Consider key rotation strategy when updating security documentation

## Development Workflows

### Running from Source
```bash
python AOS-CX.Config.Backup.Tool_3.3.py
```
No virtual environment files present - manual setup required.

### Testing Manual Backup
1. Ensure CSV has valid switch IPs (firmware ≥10.04 required)
2. Set credentials via GUI (saves encrypted to config)
3. Disable schedule to avoid interference
4. Use "Run Now" button - check `switch_backup.log` for errors

### Debugging REST API Issues
- Enable logging captures full request/response flow
- Check `connectivity test` log entry before auth attempts
- Verify `Accept: text/plain` header for config retrieval (not JSON)

## External Dependencies

### GUI & System Integration
- **ttkbootstrap**: Dark theme (`darkly`) GUI with custom styles
- **infi.systray**: System tray icon/menu (requires `icon.ico` in resource_path)
- **tkinter**: Base GUI framework (standard library)

### Cloud Integration
- **PyGithub**: Git uploads using personal access token (repo scope needed)
- **boto3**: Wasabi S3 via custom endpoint URL (`s3.{region}.wasabisys.com`)
- Both optional - controlled by `{service}_enabled` flags

### Scheduling
- **schedule** library: Simple time-based execution
- Runs in daemon thread with 60s check interval
- `schedule_enabled` toggle preserves settings without clearing schedule

## Common Pitfalls

1. **Missing base_dir**: All backups fail silently if backup directory not set
2. **CSV columns**: Must have `name` and `ip` columns (case-sensitive)
3. **API version**: Hardcoded to v10.04 endpoints (no version negotiation)
4. **Backup lock**: `backup_lock` prevents concurrent backups but isn't timeout-protected
5. **Status persistence**: `save_status()` called after each switch, not transactional
6. **Git repo format**: Expects `github.com/{owner}/{repo}` (strips https/git)

## Extending the Application

### Adding New Upload Destinations
Follow the pattern in `git_upload()` / `wasabi_upload()`:
- Add config fields with encryption for secrets
- Create `{service}_enabled` toggle and settings UI
- Implement upload method with `last_{service}_status` tracking
- Call after successful backups in `backup_switches()`

### Switch to Multi-File Architecture
Consider extracting:
- `ConfigManager`: Encryption, JSON persistence
- `RestApiClient`: Switch communication, retry logic
- `BackupService`: Orchestration, retention management
- `UploadProvider` (abstract): Git/Wasabi/future implementations

### Adding Schedule Types
Extend `schedule_frequency` options in `update_schedule_details()` and `setup_schedule()`.
Current: daily (multiple times), weekly, custom. Potentially add: hourly intervals, specific dates.
