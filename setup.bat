@echo off
cd /d "%~dp0"
title Setup — Installing Dependencies

echo ============================================================
echo  Triaxial Corrected Area App — First-time Setup
echo ============================================================
echo.

:: Find Python
set PYTHON=
where py >nul 2>&1 && set PYTHON=py
if "%PYTHON%"=="" (
    where python >nul 2>&1 && set PYTHON=python
)
if "%PYTHON%"=="" (
    where python3 >nul 2>&1 && set PYTHON=python3
)

if "%PYTHON%"=="" (
    echo ERROR: Python not found.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo Found Python: %PYTHON%
echo.
echo Installing required packages...
echo.

%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install streamlit pandas numpy

echo.
echo ============================================================
echo  Setup complete! Run "run_app.bat" to start the app.
echo ============================================================
echo.
pause
