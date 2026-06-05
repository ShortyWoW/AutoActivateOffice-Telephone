@echo off
title AutoActivateOffice Telephone Helper - Build EXE
cd /d "%~dp0"

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist\AutoActivateOffice-Telephone rmdir /s /q dist\AutoActivateOffice-Telephone

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

echo Building portable single-file executable using PyInstaller...
pyinstaller --onefile --noconsole --noconfirm --name AutoActivateOffice-Telephone --clean --paths . --distpath ./dist --workpath ./build src/main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo BUILD COMPLETED SUCCESSFULLY
    echo Output directory: dist\AutoActivateOffice-Telephone\
    echo ============================================================
    echo.
    echo Creating directories in the distribution folder...
    if not exist dist\AutoActivateOffice-Telephone mkdir dist\AutoActivateOffice-Telephone
    if not exist dist\AutoActivateOffice-Telephone\logs mkdir dist\AutoActivateOffice-Telephone\logs
    if not exist dist\AutoActivateOffice-Telephone\tesseract mkdir dist\AutoActivateOffice-Telephone\tesseract
    
    echo Moving single executable into the distribution folder...
    move dist\AutoActivateOffice-Telephone.exe dist\AutoActivateOffice-Telephone\ >nul
    
    echo Copying local Tesseract binaries if present in project root...
    if exist tesseract\tesseract.exe (
        xcopy /s /e /y tesseract dist\AutoActivateOffice-Telephone\tesseract\ >nul
        echo [INFO] Bundled local "tesseract/" binaries into dist folder.
    ) else if exist Tesseract-OCR\tesseract.exe (
        xcopy /s /e /y Tesseract-OCR dist\AutoActivateOffice-Telephone\tesseract\ >nul
        echo [INFO] Bundled local "Tesseract-OCR/" binaries into dist folder.
    ) else (
        echo [WARNING] No local Tesseract binaries found in project root. dist/tesseract is empty.
    )
    
    echo Copying documentation files...
    copy README.md dist\AutoActivateOffice-Telephone\ >nul
    
    echo Done! You can now copy the "dist\AutoActivateOffice-Telephone" folder to a USB drive.
) else (
    echo.
    echo [ERROR] PyInstaller compilation failed. See above errors.
)
pause
