# GitHub Actions CI/CD Guide

## Overview

This project uses GitHub Actions to automatically build Windows and macOS executables whenever code is pushed to the repository or when a new version tag is created.

## Workflow File

`.github/workflows/build.yml` - Automated build pipeline

## How It Works

### Automatic Builds

The workflow triggers on:
1. **Push to main/master branch** - Builds both platforms, stores artifacts for 90 days
2. **Pull requests** - Builds to verify changes work on both platforms
3. **Manual trigger** - Run via GitHub Actions tab (workflow_dispatch)
4. **Version tags** - Creates a GitHub Release with downloadable executables

### Build Process

#### Windows Build
- Runs on: `windows-latest`
- Python: 3.11
- Output: `AOS-CX.Config.Backup.Tool.exe` (single-file executable)
- Spec: `AOS-CX.Config.Backup.Tool_Windows.spec`

#### macOS Build
- Runs on: `macos-latest`
- Python: 3.11
- Output: `AOS-CX Config Backup Tool.app` (zipped .app bundle)
- Spec: `AOS-CX.Config.Backup.Tool.spec`

## Usage

### 1. Regular Development Workflow

```bash
# Make changes to code
git add .
git commit -m "Your changes"
git push origin main
```

**Result**: GitHub Actions automatically builds both versions. Download from Actions tab.

### 2. Creating a Release

```bash
# Create and push a version tag
git tag -a v3.2 -m "Release version 3.2"
git push origin v3.2
```

**Result**: 
- Builds both platforms
- Creates a GitHub Release automatically
- Attaches executables to the release
- Generates release notes from commits

### 3. Manual Build Trigger

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Select "Build Multi-Platform Executables" workflow
4. Click "Run workflow" button
5. Choose branch and click "Run workflow"

**Result**: Builds on-demand without pushing code changes.

## Downloading Built Executables

### From Actions (Development Builds)

1. Go to repository → Actions tab
2. Click on the workflow run
3. Scroll to "Artifacts" section
4. Download:
   - `AOS-CX-Config-Backup-Tool-Windows` (Windows .exe)
   - `AOS-CX-Config-Backup-Tool-macOS` (macOS .app in zip)

### From Releases (Tagged Versions)

1. Go to repository → Releases
2. Click on the desired version
3. Download from "Assets" section

## Requirements

All dependencies are automatically installed from `requirements.txt`:
- pyinstaller
- requests
- ttkbootstrap
- schedule
- infi.systray
- PyGithub
- cryptography
- boto3
- Pillow

## Artifact Retention

- **Development builds**: 90 days
- **Release builds**: Permanent (stored with GitHub Release)

## Troubleshooting

### Build Failures

**Check the logs:**
1. Go to Actions tab
2. Click on the failed workflow run
3. Expand the failed step to see error details

**Common issues:**
- Missing dependencies → Update `requirements.txt`
- Import errors → Add modules to `hiddenimports` in spec files
- Platform-specific errors → Test locally on that platform first

### Missing Icon

If icon.ico is not in the repo:
- Add `icon.ico` to root directory
- Ensure it's not in `.gitignore`
- Commit and push: `git add icon.ico && git commit -m "Add icon" && git push`

### PyInstaller Updates

If PyInstaller version causes issues:
```yaml
# In .github/workflows/build.yml, pin version:
pip install pyinstaller==6.19.0
```

## Security Notes

- Workflow runs in isolated GitHub runners
- No credentials are stored in the workflow
- Artifacts are private (only repo collaborators can download)
- Use GitHub Secrets for any API keys (not currently needed)

## Customization

### Change Python Version

Edit in `.github/workflows/build.yml`:
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'  # Change here
```

### Add Code Signing (macOS)

```yaml
- name: Sign macOS app
  run: |
    codesign --deep --force --verify --verbose --sign "Developer ID Application: YOUR_IDENTITY" "dist/AOS-CX Config Backup Tool.app"
```

### Add Code Signing (Windows)

```yaml
- name: Sign Windows exe
  run: |
    signtool sign /f certificate.pfx /p ${{ secrets.CERT_PASSWORD }} /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist/AOS-CX.Config.Backup.Tool.exe"
```

## First-Time Setup

After committing the workflow file:

1. **Push all files**:
   ```bash
   git add .
   git commit -m "Add GitHub Actions build workflow"
   git push origin main
   ```

2. **Verify workflow runs**:
   - Go to Actions tab on GitHub
   - Watch the build progress
   - Ensure both Windows and macOS builds succeed

3. **Test artifacts**:
   - Download both versions
   - Test on respective platforms
   - Verify all features work

4. **Create first release** (optional):
   ```bash
   git tag -a v3.2 -m "Initial release with GitHub Actions"
   git push origin v3.2
   ```

## Monitoring

GitHub will email you if builds fail. You can also:
- Watch the Actions tab for real-time progress
- Enable notifications for workflow runs
- Review build logs for warnings/errors

## Cost

GitHub Actions are **free** for public repositories and include generous free minutes for private repositories:
- Public repos: Unlimited minutes
- Private repos: 2,000 minutes/month free (then $0.008/minute)

Typical build times:
- Windows: ~5-7 minutes
- macOS: ~6-8 minutes
- **Total per run**: ~15 minutes

## Next Steps

1. Commit the workflow file (when ready)
2. Push to GitHub
3. Monitor first build in Actions tab
4. Download and test executables
5. Create release tag for distribution
