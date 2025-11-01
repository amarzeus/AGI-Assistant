# AGI Assistant - Deployment Guide

## Prerequisites

### System Requirements
- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB free space
- **CPU**: Dual-core processor minimum

### Optional Dependencies
- **Playwright**: For browser automation
- **Win32com**: For Office automation
- **Tesseract OCR**: For text verification

## Building from Source

### 1. Setup Environment

```bash
# Clone repository
git clone <repository-url>
cd agi-assistant

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### 3. Build Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller agi_assistant.spec

# Output: dist/AGI_Assistant.exe
```

## Deployment Options

### Option 1: Standalone Executable

**Best for**: End users, demos, hackathons

1. Build executable (see above)
2. Copy `dist/AGI_Assistant.exe` to target machine
3. Run executable (no installation needed)

**Pros**:
- No Python required
- Single file distribution
- Easy to deploy

**Cons**:
- Larger file size (~200-500MB)
- Slower startup time

### Option 2: Python Package

**Best for**: Developers, customization

1. Package as wheel:
```bash
python setup.py bdist_wheel
```

2. Install on target:
```bash
pip install agi_assistant-1.0.0-py3-none-any.whl
```

3. Run:
```bash
python -m agi_assistant
```

**Pros**:
- Smaller distribution
- Faster updates
- Easy customization

**Cons**:
- Requires Python
- Dependency management

### Option 3: Installer

**Best for**: Enterprise deployment

1. Create installer with NSIS/Inno Setup
2. Include:
   - Executable
   - Documentation
   - Example workflows
   - Uninstaller

**Pros**:
- Professional deployment
- Start menu integration
- Easy uninstall

**Cons**:
- More complex setup
- Requires installer creation

## Configuration

### Default Configuration

Located at: `~/.agi_assistant/config.json`

```json
{
  "capture": {
    "screenshot_interval": 2.0,
    "video_segment_duration": 300,
    "quality": "medium"
  },
  "storage": {
    "max_storage_gb": 10,
    "retention_days": 30,
    "auto_cleanup": true
  },
  "automation": {
    "max_actions_per_minute": 60,
    "action_timeout": 30,
    "verify_actions": true
  },
  "safety": {
    "emergency_stop_hotkey": "ctrl+shift+esc",
    "enable_rate_limiting": true
  }
}
```

### Environment Variables

```bash
# Data directory
AGI_ASSISTANT_DATA_DIR=C:\Users\<user>\AppData\Local\AGI_Assistant

# Log level
AGI_ASSISTANT_LOG_LEVEL=INFO

# Demo mode (no dependencies required)
AGI_ASSISTANT_DEMO_MODE=false
```

## Database Setup

### SQLite Database

Automatically created at: `~/.agi_assistant/data/agi_assistant.db`

**Tables**:
- sessions
- actions
- patterns
- transcriptions
- workflow_suggestions

**Backup**:
```bash
# Manual backup
copy %USERPROFILE%\.agi_assistant\data\agi_assistant.db backup.db

# Automated backup (scheduled task)
schtasks /create /tn "AGI Assistant Backup" /tr "backup_script.bat" /sc daily
```

## Security Considerations

### Data Protection

1. **Local Storage Only**: No cloud uploads
2. **Encrypted Sensitive Data**: Passwords encrypted at rest
3. **Secure Deletion**: Overwrite files when deleting
4. **Access Control**: File permissions restricted

### Privacy Settings

1. **Excluded Applications**: Configure in Privacy panel
2. **Session Isolation**: Separate data per session
3. **User Consent**: Prompt before recording
4. **Data Retention**: Auto-delete old data

### Network Security

- **No External Connections**: Runs completely offline
- **No Telemetry**: No usage data collected
- **No Updates**: Manual update process

## Monitoring

### Health Checks

```python
# Check service status
from src.services.application_coordinator import ApplicationCoordinator

coordinator = ApplicationCoordinator()
status = await coordinator.get_service_status()

for service, is_running in status.items():
    print(f"{service}: {'✅' if is_running else '❌'}")
```

### Performance Metrics

Monitor in Debug panel:
- CPU usage
- Memory consumption
- Disk I/O
- Operation durations

### Logging

**Log Locations**:
- Application: `~/.agi_assistant/logs/app.log`
- Errors: `~/.agi_assistant/logs/error.log`
- Automation: `~/.agi_assistant/logs/automation.log`

**Log Rotation**:
- Max size: 10MB per file
- Keep last 5 files
- Compress old logs

## Troubleshooting Deployment

### Issue: Executable won't start

**Solutions**:
1. Check Windows Defender/antivirus
2. Run as administrator
3. Check event viewer for errors
4. Verify system requirements

### Issue: Missing dependencies

**Solutions**:
1. Install optional dependencies:
```bash
pip install playwright
playwright install chromium

pip install pywin32
```

2. Or run in demo mode:
```bash
set AGI_ASSISTANT_DEMO_MODE=true
AGI_Assistant.exe
```

### Issue: Database errors

**Solutions**:
1. Delete corrupted database:
```bash
del %USERPROFILE%\.agi_assistant\data\agi_assistant.db
```

2. Restart application (auto-recreates)

### Issue: High resource usage

**Solutions**:
1. Reduce capture interval
2. Lower screenshot quality
3. Enable auto-cleanup
4. Increase retention days

## Maintenance

### Regular Tasks

**Daily**:
- Monitor disk usage
- Check error logs
- Review failed executions

**Weekly**:
- Backup database
- Clean old sessions
- Update workflows

**Monthly**:
- Review performance metrics
- Update documentation
- Archive old data

### Updates

1. Download new version
2. Backup current data
3. Replace executable
4. Test critical workflows
5. Monitor for issues

## Support

### Getting Help

1. Check documentation
2. Review logs
3. Search known issues
4. Contact support with:
   - Version number
   - Error logs
   - Steps to reproduce

### Reporting Issues

Include:
- OS version
- Application version
- Error message
- Log files
- Screenshots

---

For more information, see docs/
