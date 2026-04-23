@echo off
chcp 65001 >nul
title PDF Converter 打包脚本
echo ==========================================
echo    PDF Converter 打包工具
echo    版本: 2.0.0
echo ==========================================
echo.

REM 检查Python环境
echo [1/5] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)
echo [OK] Python环境正常

REM 检查依赖
echo.
echo [2/5] 检查并安装依赖...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [OK] 依赖安装完成

REM 清理旧的构建文件
echo.
echo [3/5] 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo [OK] 清理完成

REM 执行打包
echo.
echo [4/5] 开始打包...
echo 这可能需要几分钟时间，请耐心等待...
echo.
pyinstaller PDFConverter.spec --clean -y

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

REM 检查输出文件
echo.
echo [5/5] 检查输出文件...
if exist "dist\PDFConverter.exe" (
    echo [OK] 打包成功！
    echo.
    echo ==========================================
    echo    打包完成！
    echo ==========================================
    echo.
    echo 输出文件: dist\PDFConverter.exe
    
    REM 获取文件大小
    for %%I in ("dist\PDFConverter.exe") do (
        echo 文件大小: %%~zI 字节
    )
    
    echo.
    echo 使用方法:
    echo   双击运行 dist\PDFConverter.exe
    echo.
    echo 功能特点:
    echo   - PDF转Word (.docx) 
    echo   - PDF转Markdown (.md)
    echo   - 任务队列管理
    echo   - 并发转换 (最多3个)
    echo   - 黑色猫主题图标
    echo.
) else (
    echo [错误] 未找到输出文件
    pause
    exit /b 1
)

echo 按任意键退出...
pause >nul
