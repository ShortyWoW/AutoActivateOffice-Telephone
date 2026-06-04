@echo off
title AutoActivateOffice Telephone Helper - Dev Run
cd /d "%~dp0"

echo Verification of dependencies...
python -c "import selenium, cv2, pytesseract, PIL, pyperclip, pyautogui, pywinauto" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Missing packages. Attempting to install requirements...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo.
        echo [ERROR] Failed to install dependencies. Please run "pip install -r requirements.txt" manually.
        pause
        exit /b %ERRORLEVEL%
    )
)

echo Starting AutoActivateOffice Telephone Helper...
python src/main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %ERRORLEVEL%.
    pause
)
