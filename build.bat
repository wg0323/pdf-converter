@echo off
title PDF Converter Build Script
echo ==========================================
echo    PDF Converter Build Tool
echo    Version: 4.0.0
echo ==========================================
echo.
echo Usage: build.bat        (fast incremental build)
echo        build.bat full   (install deps + clean rebuild)
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

REM Install dependencies only in full mode (skip for fast incremental builds)
echo.
if /i "%~1"=="full" (
    echo [2/5] Installing dependencies...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
) else (
    echo [2/5] Skipping dependency install ^(use "build.bat full" to install^)
)

REM Clean: full mode wipes PyInstaller cache; fast mode keeps build\ for incremental speed
echo.
echo [3/5] Preparing build directories...
if /i "%~1"=="full" (
    if exist "build" rmdir /s /q "build"
)
if exist "dist" rmdir /s /q "dist"
echo [OK] Ready

REM Run PyInstaller (--clean only in full mode, incremental cache speeds up rebuilds)
echo.
echo [4/5] Building...
echo This may take several minutes, please wait...
echo.
if /i "%~1"=="full" (
    pyinstaller PDFConverter.spec --clean -y
) else (
    pyinstaller PDFConverter.spec -y
)

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

REM Check output file (onedir mode: dist\PDFConverter\PDFConverter.exe)
echo.
echo [5/5] Checking output file...
if exist "dist\PDFConverter\PDFConverter.exe" (
    echo [OK] Build succeeded!
    echo.
    echo ==========================================
    echo    Build Completed!
    echo ==========================================
    echo.
    echo Output folder: dist\PDFConverter\
    echo Launcher:      dist\PDFConverter\PDFConverter.exe
    
    REM Get file size
    for %%I in ("dist\PDFConverter\PDFConverter.exe") do (
        echo Launcher size: %%~zI bytes
    )
    
    echo.
    echo Usage:
    echo   Distribute the whole dist\PDFConverter folder
    echo   Double-click PDFConverter.exe inside it to run
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
