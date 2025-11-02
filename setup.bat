@echo off
REM Setup script for Windows

echo ================================================
echo   Apache Jira Scraper - Setup
echo ================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Python found
python --version
echo.

REM Create virtual environment
echo [2/5] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)
echo.

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

REM Install dependencies
echo [4/5] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully
echo.

REM Setup configuration
echo [5/5] Setting up configuration...
if exist .env (
    echo Configuration file .env already exists
) else (
    copy .env.example .env
    echo Configuration file .env created from template
    echo Please edit .env to customize settings
)
echo.

REM Create directories
if not exist output mkdir output
if not exist state mkdir state

echo ================================================
echo   Setup Complete!
echo ================================================
echo.
echo To run the scraper:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run: python run.py
echo.
echo For more information, see README.md
echo.
pause
