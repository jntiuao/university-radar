@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 院校雷达
echo.

echo 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请安装 Python 3.8+ 并勾选 "Add Python to PATH"
    echo.
    pause
    exit /b
)

echo.
echo [1/3] 检查运行环境...
python -m pip list | findstr "Flask PyYAML APScheduler" >nul
if errorlevel 1 (
    echo [提示] 正在安装必要依赖，仅在首次运行或依赖缺失时执行...
    python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --disable-pip-version-check
)

echo.
echo [2/3] 检查无头浏览器...
if not exist "%LOCALAPPDATA%\ms-playwright\chromium-*" (
    echo [提示] 正在初始化浏览器内核...
    python -m playwright install chromium
)

echo.
echo [3/3] 正在启动 院校雷达 服务...
echo ==========================================
echo 提示：保持此窗口打开，关闭则停止服务
echo 启动后会自动在浏览器打开后台面板
echo ==========================================
set PYTHONIOENCODING=utf-8
python app.py

pause
