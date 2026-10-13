@echo off
REM Developer environment setup script for Windows
REM
REM Creates a virtual environment and installs all dependencies
REM (both core student packages and dev-only tools).
REM
REM Usage:
REM   developer\setup.bat
REM   (or double-click this file)

setlocal enabledelayedexpansion

echo ================================================
echo Getting Started with JABS - Developer Environment Setup
echo ================================================
echo.

REM Check if .venv already exists
if exist ".venv" (
    echo.
    echo WARNING: Virtual environment already exists at .\.venv
    set /p choice="Do you want to recreate it? (y/n): "
    if /i "!choice!"=="y" (
        echo Removing existing venv...
        rmdir /s /q .venv
    ) else (
        echo Using existing venv. Skipping creation.
        set SKIP_CREATION=true
    )
)

REM Create virtual environment
if not defined SKIP_CREATION (
    echo Creating virtual environment...
    python -m .venv @@
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        exit /b 1
    )
    echo [OK] Virtual environment created
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Upgrade pip, setuptools, wheel
echo Upgrading pip, setuptools, and wheel...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1
echo [OK] Package managers upgraded
echo.

REM Install core dependencies
echo Installing core dependencies (requirements.txt)...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to install core dependencies
    exit /b 1
)
echo [OK] Core dependencies installed
echo.

REM Install dev dependencies
echo Installing development dependencies (requirements-dev.txt)...
pip install -r requirements-dev.txt >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to install dev dependencies
    exit /b 1
)
echo [OK] Dev dependencies installed
echo.

REM Run environment verification
echo Verifying environment...
python student_scripts\verify_environment.py
echo.

REM Install pre-commit hooks
echo Setting up pre-commit hooks...
pre-commit install >nul 2>&1
echo [OK] Pre-commit hooks installed
echo.

REM Register Jupyter kernel
echo Registering .venv as Jupyter kernel...
python -m ipykernel install --user --name getting-started-with-jabs --display-name "Python (getting-started-with-jabs)" >nul 2>&1
echo [OK] Jupyter kernel registered (getting-started-with-jabs)
echo.

echo ================================================
echo [SUCCESS] Setup Complete!
echo ================================================
echo.
echo Next steps:
echo   1. The .venv should already be activated in this terminal
echo      (you'll see (.venv) in the prompt)
echo.
echo   2. Start working on notebooks:
echo      jupyter notebook student_notebooks\
echo.
echo To activate the .venv in a new terminal:
echo   .venv\Scripts\activate.bat
echo.
pause
