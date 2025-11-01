# AGI Assistant - User Guide

## Overview

AGI Assistant is a privacy-first desktop application that observes your computer activities to understand your workflows and suggest automation opportunities. Everything runs locally on your machine - no data ever leaves your computer.

## GUI Design & User Interface

### Main Window Layout

The application features a modern, clean interface with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│  AGI Assistant                                     [_][□][X] │
├─────────────────────────────────────────────────────────────┤
│  ● Recording                    [Start Recording] [Pause]    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┬──────────┬───────────┬──────────┐             │
│  │Dashboard│ Activity │ Workflows │ Settings │             │
│  └─────────┴──────────┴───────────┴──────────┘             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │              [Current Tab Content]                     │ │
│  │                                                         │ │
│  │                                                         │ │
│  └───────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Ready - Local processing only                              │
└─────────────────────────────────────────────────────────────┘
```

### System Tray Integration

The app minimizes to the system tray for background operation:

```
System Tray Icon (Green Circle)
├─ Show Window
├─ Hide Window
├─ ─────────────
├─ Start Recording
├─ Pause
├─ ─────────────
└─ Quit
```

---

## How to Use the Application

### 1. Starting the Application

**Launch:**
```bash
python src/main.py
```

**First Launch:**
- The app will request screen capture permissions
- Grant microphone access if you want audio transcription
- The main window will appear with a green "Ready" indicator

### 2. Recording Your Activities

#### Starting a Recording Session

1. **Click "Start Recording"** button (green button in header)
   - The status indicator (●) turns **green**
   - Button changes to red "Stop Recording"
   - Timer starts showing elapsed time (HH:MM:SS)
   - Status bar shows "Recording session - XX:XX:XX elapsed"

2. **What Gets Recorded:**
   - Screenshots every 2-5 seconds (when you're active)
   - Video segments (30-60 second clips)
   - Audio transcription (if enabled)
   - Detected actions (clicks, typing, navigation)

#### Pausing/Resuming

1. **Click "Pause"** button (orange button)
   - Status indicator turns **orange**
   - Recording pauses but session continues
   - Button changes to "Resume"

2. **Click "Resume"** to continue recording
   - Status indicator returns to **green**
   - Recording continues in same session

#### Stopping Recording

1. **Click "Stop Recording"** button (red button)
   - Status indicator turns **gray**
   - Session ends and data is saved
   - Button returns to green "Start Recording"

### 3. Viewing Your Activity

#### Activity Feed Tab

The Activity tab shows all detected actions in real-time:

```
┌─────────────────────────────────────────────────────────────┐
│  Recent Actions                                    [Clear]   │
├──────────────────────────┬──────────────────────────────────┤
│                          │  Action Details                   │
│  🖱 Click on 'Button1'   │                                   │
│  App: Chrome             │  Action Type: Click               │
│  Time: 14:23:45          │  Timestamp: 2025-10-27 14:23:45  │
│  Confidence: 87% ████    │  Application: Chrome              │
│                          │  Window Title: Google Search      │
│  ⌨ Type: 'search query'  │  Target Element: Button1          │
│  App: Chrome             │  Confidence: 87%                  │
│  Time: 14:23:42          │  Action ID: action-001            │
│  Confidence: 92% █████   │                                   │
│                          │  ┌─────────────────────────────┐ │
│  🌐 Navigate to URL      │  │                             │ │
│  App: Chrome             │  │   [Screenshot Preview]      │ │
│  Time: 14:23:40          │  │                             │ │
│  Confidence: 95% █████   │  └─────────────────────────────┘ │
└──────────────────────────┴──────────────────────────────────┘
```

**Features:**
- **Left Panel:** Scrollable list of recent actions
  - Color-coded by action type (Click=Green, Type=Blue, Navigate=Orange)
  - Shows app, time, and confidence score
  - Confidence bar (Green >80%, Orange >60%, Red <60%)

- **Right Panel:** Detailed information about selected action
  - Complete action metadata
  - Screenshot preview (if available)
  - Resizable splitter between panels

**Action Types & Colors:**
- 🖱 **Click** (Green) - Mouse clicks
- ⌨ **Type** (Blue) - Keyboard input
- 🌐 **Navigate** (Orange) - URL/page navigation
- 📱 **Open App** (Purple) - Application launch
- ❌ **Close App** (Red) - Application close
- 💾 **Save File** (Gray) - File save operations
- 📁 **Open File** (Gray) - File open operations
- ↕ **Scroll** (Brown) - Page scrolling
- 📋 **Copy/Paste** (Cyan) - Clipboard operations

### 4. Workflow Execution & Suggestions

The Workflows tab shows detected patterns and can execute automation:

```
┌─────────────────────────────────────────────────────────────┐
│  Detected Workflow Patterns                                  │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📊 Excel Data Entry Workflow                          │  │
│  │ Detected 5 times | Confidence: 92% | Time saved: 8min│  │
│  │                                                        │  │
│  │ Steps:                                                │  │
│  │ 1. Open Excel                                         │  │
│  │ 2. Enter data in column A                            │  │
│  │ 3. Apply formula in column B                         │  │
│  │ 4. Save file                                          │  │
│  │                                                        │  │
│  │ [View Details] [Execute Workflow] [Export Workflow]    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🌐 Browser Research Workflow                          │  │
│  │ Detected 3 times | Confidence: 85% | Time saved: 5min│  │
│  │ ...                                                    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Pattern frequency and confidence scores
- Estimated time savings
- Step-by-step workflow breakdown
- Export to JSON/YAML for automation

### 5. Settings & Configuration

The Settings tab provides configuration options:

```
┌─────────────────────────────────────────────────────────────┐
│  ┌─────────┬──────────┬─────────┬─────────┐                │
│  │ General │ Capture  │ Storage │ Privacy │                │
│  └─────────┴──────────┴─────────┴─────────┘                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Storage Settings                                      │  │
│  │                                                        │  │
│  │ Maximum Storage: [10] GB  [5-50 GB]                  │  │
│  │ Current Usage: 2.3 GB (23%)                           │  │
│  │                                                        │  │
│  │ Retention Policy:                                     │  │
│  │ • Structured Data: [7] days                           │  │
│  │ • Screenshots: [3] days                               │  │
│  │ • Video: [1] day                                      │  │
│  │                                                        │  │
│  │ [Manual Cleanup]                                      │  │
│  │                                                        │  │
│  │ Privacy Settings                                      │  │
│  │                                                        │  │
│  │ ☑ Enable audio transcription                         │  │
│  │ ☑ Show privacy indicator                             │  │
│  │                                                        │  │
│  │ Excluded Applications:                                │  │
│  │ • Password Manager                                    │  │
│  │ • Banking Apps                                        │  │
│  │ [Add Application]                                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 6. Background Operation

**Minimize to Tray:**
- Click the window close button (X)
- App minimizes to system tray (doesn't quit)
- Recording continues in background
- Notification: "Application minimized to system tray"

**System Tray Actions:**
- **Double-click icon:** Show/hide window
- **Right-click icon:** Access quick menu
  - Start/Stop recording
  - Pause/Resume
  - Show/Hide window
  - Quit application

**Tray Icon Colors:**
- 🟢 **Green:** Recording active
- 🟠 **Orange:** Recording paused
- ⚪ **Gray:** Ready (not recording)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+P` | Pause/Resume recording |
| `Ctrl+Shift+S` | Start/Stop recording |
| `Ctrl+Q` | Quit application |

---

## Data Export

### Exporting Workflow Data

**Via Command Line:**
```bash
# Export last 7 days as JSON
python export_data.py workflows --format json --days 7

# Export specific session
python export_data.py workflows --session-id session-001 --format yaml

# Generate analytics report
python export_data.py analytics --days 30
```

**Export Formats:**
- **JSON:** For automation frameworks (Playwright, Selenium)
- **YAML:** Human-readable format
- **CSV:** For spreadsheet analysis

**What Gets Exported:**
- Session metadata
- Action sequences with timestamps
- Pattern analysis results
- Automation suggestions
- Confidence scores

---

## Privacy & Security

### Local Processing Only

✅ **All data stays on your computer**
- No cloud uploads
- No external API calls
- No internet required (except for initial setup)

### Privacy Indicator

The status bar always shows: **"Ready - Local processing only"**

### Data Control

**You can:**
- Pause recording anytime
- Exclude specific applications
- Delete sessions manually
- Set automatic cleanup policies
- Export your data anytime

**Application Exclusions:**
Add apps you don't want recorded:
1. Go to Settings → Privacy
2. Click "Add Application"
3. Select application to exclude
4. Recording automatically pauses when that app is active

---

## Storage Management

### Automatic Cleanup

The app automatically manages storage:

**When storage reaches 90% of limit:**
1. Deletes oldest videos first
2. Then deletes oldest screenshots
3. Keeps structured data (actions, patterns)
4. Compresses older data before deletion

**Retention Priority:**
1. **Structured Data** (7 days) - Highest priority
2. **Screenshots** (3 days) - Medium priority
3. **Videos** (1 day) - Lowest priority

### Manual Cleanup

**Via Settings:**
1. Go to Settings → Storage
2. Click "Manual Cleanup"
3. Review what will be deleted
4. Confirm cleanup

**Via Command Line:**
```bash
python -c "from src.services.storage_monitor import StorageMonitor; import asyncio; asyncio.run(StorageMonitor().trigger_cleanup(force=True))"
```

---

## Troubleshooting

### App Won't Start Recording

**Check:**
1. Screen capture permissions granted?
2. Sufficient disk space available?
3. Check logs in `~/agi-assistant-data/logs/`

### No Actions Detected

**Possible causes:**
1. Recording is paused
2. Application is in exclusion list
3. Low activity (screenshots only taken when active)

### High Storage Usage

**Solutions:**
1. Reduce retention days in Settings
2. Run manual cleanup
3. Disable video recording (keep screenshots only)
4. Increase cleanup threshold

### Performance Issues

**Optimize:**
1. Increase screenshot interval (Settings → Capture)
2. Disable audio transcription if not needed
3. Reduce video quality
4. Close other resource-intensive apps

---

## Best Practices

### For Best Results

1. **Start recording at beginning of work session**
2. **Let it run for at least 30 minutes** to detect patterns
3. **Perform repetitive tasks 3+ times** for pattern detection
4. **Review workflows weekly** to find automation opportunities
5. **Export data regularly** for backup

### Privacy Tips

1. **Pause before sensitive activities** (banking, passwords)
2. **Add sensitive apps to exclusion list**
3. **Review and delete sessions** containing private data
4. **Use manual cleanup** before sharing computer

### Performance Tips

1. **Close app when not needed** (stops all recording)
2. **Run cleanup regularly** to free space
3. **Monitor storage usage** in Settings
4. **Export old data** before cleanup

---

## Getting Help

### Logs Location
```
~/agi-assistant-data/logs/app.log
```

### Data Location
```
~/agi-assistant-data/
├── db/              # Database
├── sessions/        # Recordings
├── exports/         # Exported data
└── logs/           # Application logs
```

### Support

For issues or questions:
1. Check logs for error messages
2. Review this user guide
3. Check GitHub issues
4. Contact support

---

## Quick Start Checklist

- [ ] Install application
- [ ] Grant screen capture permissions
- [ ] Grant microphone permissions (optional)
- [ ] Configure storage limits
- [ ] Add sensitive apps to exclusion list
- [ ] Start recording
- [ ] Perform your normal work
- [ ] Review detected actions in Activity tab
- [ ] Check workflow suggestions
- [ ] Export data for automation

---

## Summary

**AGI Assistant helps you:**
1. 📹 **Record** your computer activities automatically
2. 🔍 **Understand** your workflows through AI analysis
3. 🤖 **Automate** repetitive tasks with generated suggestions
4. 🔒 **Stay private** with 100% local processing
5. 💾 **Manage** storage efficiently with automatic cleanup

**Remember:** Everything stays on your computer. You're in complete control of your data.
##
# 7. Workflow Execution (NEW!)

**Execute Workflows with Real Automation:**

The app can now execute detected workflows using real mouse and keyboard control:

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Execution                                          │
├─────────────────────────────────────────────────────────────┤
│  Selected: Excel Data Entry Workflow                        │
│                                                              │
│  Execution Progress:                                         │
│  ████████████████████████████████████████ 100%             │
│                                                              │
│  Steps Completed:                                           │
│  ✅ 1. Open Excel application                               │
│  ✅ 2. Navigate to cell A1                                  │
│  ✅ 3. Enter customer data                                  │
│  ✅ 4. Apply formula in column B                            │
│  ✅ 5. Save file                                            │
│                                                              │
│  Status: Execution completed successfully                    │
│  Time: 45 seconds                                           │
│                                                              │
│  [Execute Again] [Stop] [View History]                      │
└─────────────────────────────────────────────────────────────┘
```

**Execution Features:**
- **Real Automation**: Controls mouse and keyboard
- **Progress Tracking**: See each step as it executes
- **Safety Features**: Failsafe protection (move mouse to corner to stop)
- **Execution History**: Track all automation runs
- **Error Handling**: Graceful failure recovery

**Supported Actions:**
- 🖱 **Mouse Control**: Click, move, drag, scroll
- ⌨ **Keyboard Control**: Type text, press keys, hotkeys
- 🖥 **Screen Operations**: Screenshot, bounds checking
- 📱 **Application Control**: Launch, focus, close apps
- ⏱ **Timing Control**: Delays, wait conditions

**Safety Features:**
- **Failsafe**: Move mouse to top-left corner to emergency stop
- **Bounds Checking**: Prevents clicks outside screen
- **Error Recovery**: Continues execution after minor errors
- **User Confirmation**: Confirms before executing destructive actions
