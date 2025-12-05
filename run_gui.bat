@echo off
REM Windows batch file to launch the Prediction Analyzer GUI
REM Double-click this file to start the GUI application

echo Starting Prediction Analyzer GUI...
echo.

python run_gui.py

if errorlevel 1 (
    echo.
    echo An error occurred while starting the GUI.
    echo Please check the error message above.
    pause
)
