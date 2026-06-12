@echo off
cd /d "%~dp0"
title Triaxial Corrected Area App

:: Try py launcher first (Python for Windows), then python, then python3
where py >nul 2>&1
if %errorlevel% == 0 (
    py -m streamlit run app.py
    goto end
)

where python >nul 2>&1
if %errorlevel% == 0 (
    python -m streamlit run app.py
    goto end
)

where python3 >nul 2>&1
if %errorlevel% == 0 (
    python3 -m streamlit run app.py
    goto end
)

echo.
echo ============================================================
echo  ERROR: Python not found!
echo ============================================================
echo.
echo Please install Python from: https://www.python.org/downloads/
echo   - Check "Add Python to PATH" during installation
echo   - After installing, run setup.bat to install dependencies
echo.

:end
pause
