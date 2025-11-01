# AGI Assistant - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Workflow Automation](#workflow-automation)
4. [Safety Features](#safety-features)
5. [Parameterization](#parameterization)
6. [Scheduling](#scheduling)
7. [Troubleshooting](#troubleshooting)

## Getting Started

### Installation
1. Download AGI_Assistant.exe
2. Run the executable (no installation required)
3. Grant necessary permissions when prompted

### First Launch
- The application starts in observation mode
- Click "Start Recording" to begin capturing your actions
- Perform your workflow 3+ times for pattern detection

## Dashboard Overview

### 1. Activity Panel
- View real-time action detection
- See captured screenshots
- Monitor transcription status

### 2. Workflows Panel
- View detected patterns
- Execute automations
- Configure parameters
- Schedule recurring runs

### 3. Storage Panel
- Monitor disk usage
- Manage retention policies
- Clean up old data

### 4. Privacy Panel
- Exclude sensitive applications
- Delete specific sessions
- Configure privacy settings

### 5. Settings Panel
- Adjust capture intervals
- Configure storage limits
- Set automation preferences

### 6. Debug Panel
- View system logs
- Monitor performance
- Check service status

## Workflow Automation

### Creating Workflows

1. **Pattern Detection**
   - Perform the same task 3+ times
   - System automatically detects patterns
   - Review detected workflow in Workflows panel

2. **Manual Creation**
   - Click "Create Workflow" button
   - Define actions step-by-step
   - Save with descriptive name

### Executing Workflows

1. Select workflow from list
2. Review workflow details
3. Fill in parameters (if any)
4. Click "Execute" button
5. Monitor progress in real-time

### Confidence Scores

Workflows display confidence scores:
- **Green (80-100%)**: High reliability
- **Yellow (50-79%)**: Medium reliability
- **Red (0-49%)**: Low reliability, needs review

Confidence updates automatically based on execution results.

## Safety Features

### Emergency Stop

**Hotkey**: `Ctrl+Shift+Esc`

Immediately halts all running automations. Use when:
- Automation behaves unexpectedly
- Need to regain control
- System becomes unresponsive

### Action Timeouts

Each action has a maximum execution time:
- Click/Type: 30 seconds
- Navigation: 60 seconds
- File operations: 120 seconds

Exceeded timeouts trigger automatic cancellation.

### Rate Limiting

Maximum 60 actions per minute to prevent:
- System overload
- Runaway automations
- Resource exhaustion

## Parameterization

### What is Parameterization?

Reuse workflows with different data without creating duplicates.

### Supported Parameter Types

1. **Text**: Names, emails, descriptions
2. **Number**: Quantities, prices, counts
3. **Date**: Dates and times
4. **File**: File paths
5. **Choice**: Predefined options

### Using Parameters

1. System auto-detects parameterizable values
2. Review suggested parameters
3. Provide values before execution
4. Save parameter sets for reuse

### Example

Original workflow: "Send email to john@example.com"
Parameterized: "Send email to {{email}}"

Now reusable for any email address!

## Scheduling

### Schedule Types

1. **One-Time**: Run once at specific time
2. **Daily**: Run every day at set time
3. **Weekly**: Run on specific days
4. **Interval**: Run every N minutes/hours
5. **Cron**: Advanced scheduling

### Creating Schedules

1. Select workflow
2. Click "Schedule" button
3. Choose schedule type
4. Configure time/frequency
5. Set retry policy
6. Save schedule

### Managing Schedules

- View all schedules in Schedules tab
- Enable/disable schedules
- Edit schedule configuration
- Delete obsolete schedules

## Troubleshooting

### Common Issues

**Workflow fails repeatedly**
- Check confidence score
- Review improvement suggestions
- Verify target application is accessible
- Update selectors if UI changed

**Parameters not detected**
- Ensure values are consistent across runs
- Manually add parameters if needed
- Check parameter validation rules

**Schedule doesn't run**
- Verify schedule is enabled
- Check next run time
- Review execution logs
- Ensure application is running

**High resource usage**
- Reduce capture interval
- Lower screenshot quality
- Enable storage cleanup
- Check performance metrics

### Getting Help

1. Check Debug panel for errors
2. Review execution logs
3. Consult documentation
4. Report issues with logs attached

## Keyboard Shortcuts

- `Ctrl+Shift+Esc`: Emergency Stop
- `Ctrl+R`: Start/Stop Recording
- `Ctrl+E`: Execute Selected Workflow
- `Ctrl+S`: Open Settings
- `Ctrl+Q`: Quit Application

## Best Practices

1. **Test workflows** before scheduling
2. **Use parameters** for flexibility
3. **Monitor confidence** scores
4. **Review suggestions** regularly
5. **Keep backups** of important workflows
6. **Update selectors** when UI changes
7. **Set appropriate timeouts**
8. **Use emergency stop** when needed

## Advanced Features

### Workflow Adjustments

System automatically adjusts workflows based on:
- Timing issues → Adds delays
- Coordinate problems → Shifts positions
- Selector failures → Updates selectors
- Validation errors → Adds verification

### Feedback Loop

Every execution improves the workflow:
- Success increases confidence
- Failures trigger analysis
- Patterns detected automatically
- Suggestions generated

### Performance Monitoring

Track system performance:
- CPU usage
- Memory consumption
- Operation durations
- Resource alerts

---

For more information, see the full documentation at docs/
