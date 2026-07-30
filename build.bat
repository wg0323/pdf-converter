@echo off
title PDF Converter Build Script
echo ==========================================
echo    PDF Converter Build Tool
echo    Version: 4.0.0
echo ==========================================
echo.

REM Check Python environment
echo [1/5] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please make sure Python is installed and added to PATH.
    pause
    exit /b 1
)
echo [OK] Python environment is ready

REM Check dependencies
echo.
echo [2/5] Checking and installing dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Clean old build files
echo.
echo [3/5] Cleaning old build files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo [OK] Cleanup finished

REM Run PyInstaller
echo.
echo [4/5] Building...
echo This may take several minutes, please wait...
echo.
pyinstaller PDFConverter.spec --clean -y

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

REM Check output file
echo.
echo [5/5] Checking output file...
if exist "dist\PDFConverter.exe" (
    echo [OK] Build succeeded!
    echo.
    echo ==========================================
    echo    Build Completed!
    echo ==========================================
    echo.
    echo Output file: dist\PDFConverter.exe
    
    REM Get file size
    for %%I in ("dist\PDFConverter.exe") do (
        echo File size: %%~zI bytes
    )
    
    echo.
    echo Usage:
    echo   Double-click dist\PDFConverter.exe to run
    echo.
    echo Features:
    echo   - PDF to Word (.docx)
    echo   - Task queue management
    echo   - Sequential conversion (stable)
    echo   - Black cat theme icon
    echo.
) else (
    echo [ERROR] Output file not found
    pause
    exit /b 1
)

echo Press any key to exit...
pause >nul
