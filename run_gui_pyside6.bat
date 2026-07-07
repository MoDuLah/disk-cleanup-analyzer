@echo off
chcp 65001 >nul
title Disk Cleanup Analyzer - Modern PySide6 GUI

echo ========================================
echo   Disk Cleanup Analyzer - Modern GUI
echo   Using PySide6 (Qt for Python)
echo ========================================
echo.

python -m pip install PySide6 --quiet
if errorlevel 1 (
    echo ERROR: Failed to install PySide6
    echo Please install it manually: pip install PySide6
    pause
    exit /b 1
)

echo.
echo Starting Modern GUI...
echo.

python disk_cleanup_gui_pyside6.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start GUI
    echo Make sure PySide6 is installed: pip install PySide6
    pause
)

pause
