# AGI Assistant GUI Launcher
# This script activates the virtual environment and launches the GUI

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "AGI Assistant - AI-Powered Workflow Automation" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
Write-Host ""

# Get the script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "Please ensure the venv folder exists and contains the virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Virtual environment activated successfully." -ForegroundColor Green
Write-Host ""
Write-Host "Starting GUI application..." -ForegroundColor Yellow
Write-Host ""

# Run the GUI launcher
python launch_agi_gui.py

# The GUI will run until closed by the user
