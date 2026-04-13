@echo off
echo ============================================
echo  Scale Cube Exporter - Setup
echo ============================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Installing Python 3.12...
    winget install Python.Python.3.12
    echo.
    echo Please restart this script after Python installs.
    pause
    exit /b 1
)

echo Installing dependencies...
pip install flet
echo.
echo Setup complete. Run "Scale Cube Exporter.bat" to start.
pause
