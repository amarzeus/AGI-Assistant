@echo off
REM AGI Assistant GUI Launcher
REM This script activates the virtual environment and launches the GUI

echo ======================================
echo AGI Assistant - AI-Powered Workflow Automation
echo ======================================
echo.
echo Activating virtual environment...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    echo Please ensure the venv folder exists and contains the virtual environment
    pause
    exit /b 1
)

echo Virtual environment activated successfully.
echo.
echo Starting GUI application...
echo.

REM Run the GUI launcher
python launch_agi_gui.py

REM Deactivate virtual environment on exit
call venv\Scripts\deactivate.bat

echo.
echo GUI application closed.
pause
