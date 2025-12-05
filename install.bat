@echo off
REM Installation script for Prediction Analyzer (Windows)
echo ========================================
echo Prediction Analyzer - Installation
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo Python found. Installing dependencies...
echo.

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo.
echo Installing required packages...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo You can now run the analyzer with:
echo   python run.py
echo.
pause
