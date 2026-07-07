@echo off
REM Disk Cleanup Analyzer - GUI Launcher
REM Double-click this file to start the GUI

python3 disk_cleanup_gui.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start GUI
    echo Make sure Python 3 is installed and in your PATH
    pause
)
