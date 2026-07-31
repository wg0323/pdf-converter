@echo off
title OCR Addon Build Script
echo ==========================================
echo    OCR Addon (PP-Structure) Build Tool
echo ==========================================
echo.
echo Builds the optional OCR enhancement package into ocr_addon\ (project root).
echo This is a persistent cache; build.bat auto-copies it into the app folder.
echo It is NOT delivered separately - the final deliverable is dist\PDFConverter.
echo.

REM Check Python environment
echo [1/3] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please make sure Python is installed and added to PATH.
    pause
    exit /b 1
)
echo [OK] Python environment is ready

REM Install paddle stack into the addon folder (pinned to verified versions)
echo.
echo [2/3] Installing OCR dependencies into ocr_addon\ ...
echo This downloads several hundred MB on first run, please wait...
echo NOTE: pip may print a dependency-conflict ERROR about locally installed
echo       packages (e.g. paddlex). It refers to your dev environment, not the
echo       addon itself, and is safe to ignore as long as this script finishes.
if exist "ocr_addon" rmdir /s /q "ocr_addon"
REM python -m pip avoids PATH/permission issues with pip.exe
REM Deps go into a "site-packages" subfolder: paddle locates its native
REM libs by scanning sys.path for a dir whose name contains "site-packages";
REM otherwise it falls back to site.USER_SITE (None in frozen apps) and crashes
REM setuptools: paddle imports it at startup but pip does not pull it in
python -m pip install --target "ocr_addon\site-packages" --no-warn-script-location -q paddleocr==2.10.0 paddlepaddle==2.6.2 setuptools
if errorlevel 1 (
    echo [ERROR] Failed to install OCR dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Copy offline models (must exist in local cache; run a PP-Structure
REM conversion once in the dev environment to download them)
echo.
echo [3/3] Copying offline models...
set MODEL_SRC=%USERPROFILE%\.paddleocr\whl
if not exist "%MODEL_SRC%\det\ch\ch_PP-OCRv4_det_infer" (
    echo [ERROR] Model cache not found at %MODEL_SRC%
    echo Run a scanned-PDF conversion once in the dev environment first.
    pause
    exit /b 1
)
xcopy /e /i /q "%MODEL_SRC%\det\ch\ch_PP-OCRv4_det_infer" "ocr_addon\models\det" >nul
xcopy /e /i /q "%MODEL_SRC%\rec\ch\ch_PP-OCRv4_rec_infer" "ocr_addon\models\rec" >nul
xcopy /e /i /q "%MODEL_SRC%\layout\picodet_lcnet_x1_0_fgd_layout_cdla_infer" "ocr_addon\models\layout" >nul
echo [OK] Models copied

echo.
echo ==========================================
echo    OCR Addon Build Completed!
echo ==========================================
echo.
echo Output folder: ocr_addon\ (project root, persistent cache)
echo.
echo Next step:
echo   Just run build.bat - it auto-copies ocr_addon into the app folder.
echo   Deliver the whole dist\PDFConverter folder (OCR already inside).
echo.
echo Press any key to exit...
pause >nul
