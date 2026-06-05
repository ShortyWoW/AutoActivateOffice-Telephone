@echo off
title Office Phone Activator - Build EXE
cd /d "%~dp0"

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist\OfficePhoneActivator rmdir /s /q dist\OfficePhoneActivator

echo Checking for PyInstaller...
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller not found. Installing via pip...
    pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] PyInstaller installation failed.
        pause
        exit /b %ERRORLEVEL%
    )
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

echo Building portable single-file executable with bundled Tesseract & Icon using PyInstaller...
pyinstaller --onefile --noconsole --noconfirm --name OfficePhoneActivator --clean --paths . --icon "assets/app_icon.ico" --add-data "tesseract;tesseract" --add-data "assets;assets" --distpath ./dist --workpath ./build src/main.py

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
