#!/bin/bash
# 院校雷达 MacOS / Linux 一键启动脚本
cd "$(dirname "$0")"

if command -v python3 &>/dev/null; then
    python3 start.py
elif command -v python &>/dev/null; then
    python start.py
else
    echo "❌ 未检测到 Python，请安装 Python 3.8 或以上版本。"
    read -p "按回车键退出..."
fi
