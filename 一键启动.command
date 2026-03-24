#!/bin/bash
# 院校雷达 MacOS / Linux 一键启动脚本

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "=========================================="
echo "          院校雷达 启动脚本"
echo "=========================================="
echo ""

# 检查 Python 环境
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[错误] 未检测到 Python，请安装 Python 3.8 或以上版本。"
    echo "MacOS 推荐使用 Homebrew 安装: brew install python"
    exit 1
fi

echo "✓ 检测到 Python 环境: $($PYTHON_CMD --version)"

# 检查 pip
if ! command -v pip3 &>/dev/null && ! command -v pip &>/dev/null; then
    echo "[错误] 未检测到 pip，请确保 Python 环境完整。"
    exit 1
fi
PIP_CMD="pip3"
if ! command -v pip3 &>/dev/null; then PIP_CMD="pip"; fi

echo ""
echo "[1/3] 检查并安装必要依赖..."
if ! $PYTHON_CMD -c "import flask, yaml, apscheduler" &>/dev/null; then
    echo "  [提示] 正在安装依赖，仅首次运行需要..."
    $PYTHON_CMD -m $PIP_CMD install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --disable-pip-version-check
else
    echo "  ✓ 基础依赖已就绪"
fi

echo ""
echo "[2/3] 检查无头浏览器引擎..."
if ! $PYTHON_CMD -c "from playwright.sync_api import sync_playwright" &>/dev/null; then
    echo "  [提示] 正在安装 Playwright 内核，这可能需要几分钟..."
    $PYTHON_CMD -m playwright install chromium
else
    echo "  ✓ 浏览器引擎已就绪"
fi

echo ""
echo "[3/3] 正在启动 院校雷达 服务..."
echo "=========================================="
echo "提示：保持此终端窗口打开，关闭则停止服务"
echo "启动后会自动在浏览器打开后台面板"
echo "=========================================="

export PYTHONIOENCODING=utf-8
$PYTHON_CMD app.py
