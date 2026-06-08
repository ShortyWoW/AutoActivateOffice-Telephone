@echo off
title Office Phone Activator - Build EXE
cd /d "%~dp0"

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist\OfficePhoneActivator rmdir /s /q dist\OfficePhoneActivator

echo Checking for Python...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python.
    pause
    exit /b 1
)

echo Checking for virtual environment (.venv)...
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b %ERRORLEVEL%
    )
)

echo Installing/updating dependencies inside virtual environment...
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b %ERRORLEVEL%
)


echo Checking for Tesseract OCR installation on host...
if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo Tesseract OCR not found. Installing via winget...
    winget install --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements
)

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    if not exist tesseract (
        echo Copying Tesseract files from system to project root...
        mkdir tesseract
        xcopy /s /e /y "C:\Program Files\Tesseract-OCR" tesseract\ >nul
    )
)

echo Building portable single-file executable with bundled Tesseract and Icon using PyInstaller...
.venv\Scripts\python -m PyInstaller --onefile --noconsole --noconfirm --name OfficePhoneActivator --clean --paths . --icon "assets/app_icon.ico" --add-data "tesseract;tesseract" --add-data "assets;assets" --distpath ./dist --workpath ./build src/main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo BUILD COMPLETED SUCCESSFULLY
    echo Standalone executable is available at: dist\OfficePhoneActivator.exe
    echo ============================================================
    echo.
    echo Done! You can now copy the single "dist\OfficePhoneActivator.exe" file to a USB drive.
) else (
    echo.
    echo [ERROR] PyInstaller compilation failed. See above errors.
)
pause
