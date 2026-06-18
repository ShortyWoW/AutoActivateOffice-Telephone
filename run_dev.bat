@echo off
title AutoActivateOffice Telephone Helper - Dev Run
cd /d "%~dp0"

echo Checking for Python...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python.
    pause
    exit /b 1
)

echo Checking for virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment missing or incomplete. Creating virtual environment...
    if exist ".venv" rmdir /s /q .venv
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b %ERRORLEVEL%
    )
)

echo Verification of dependencies...
.venv\Scripts\python -c "import selenium, pytesseract, PIL, pyperclip, pyautogui, win32gui" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Missing packages. Attempting to install requirements...
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo.
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b %ERRORLEVEL%
    )
)

echo Starting AutoActivateOffice Telephone Helper...
.venv\Scripts\python src/main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %ERRORLEVEL%.
    pause
)
