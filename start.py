import os
import sys
import subprocess
import shutil
import time

def run_command(command):
    try:
        subprocess.check_call([sys.executable, "-m"] + command)
        return True
    except subprocess.CalledProcessError:
        return False

def check_dependencies():
    print("📋 [1/3] 检查运行环境与依赖...")
    try:
        import flask
        import yaml
        import apscheduler
        import playwright
        import fitz
        import selectolax
        import socks
        print("  ✓ 核心依赖已就绪")
    except ImportError:
        print("  [提示] 正在安装必要依赖，仅在首次运行或依赖缺失时执行...")
        # 即使 requirements.txt 是精简的，也要确保能一次性装好
        mirrors = "https://pypi.tuna.tsinghua.edu.cn/simple"
        if not run_command(["pip", "install", "-r", "requirements.txt", "-i", mirrors, "--disable-pip-version-check"]):
            print("\n❌ 依赖安装失败，请检查网络或权限。")
            return False
    return True

def check_playwright():
    print("\n🌐 [2/3] 检查无头浏览器内核...")
    # 查找是否有 chromium 目录
    # Playwright 默认安装在 %LOCALAPPDATA%\ms-playwright
    local_appdata = os.environ.get('LOCALAPPDATA', '')
    playwright_path = os.path.join(local_appdata, 'ms-playwright')
    found_chromium = False
    if os.path.exists(playwright_path):
        for item in os.listdir(playwright_path):
            if item.startswith('chromium-'):
                found_chromium = True
                break
    
    if not found_chromium:
        print("  [提示] 正在初始化浏览器内核，这可能需要几分钟...")
        if not run_command(["playwright", "install", "chromium"]):
             print("\n❌ 浏览器内核安装失败。")
             return False
    else:
        print("  ✓ 浏览器内核已就绪")
    return True

def start_main():
    print("\n🚀 [3/3] 正在启动 院校雷达 v1.0.6 服务...")
    print("==========================================")
    print("提示：保持此窗口打开，关闭则停止服务")
    print("==========================================")
    
    # 设置编码
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        # 直接运行 app.py 并获取其返回状态
        process = subprocess.Popen([sys.executable, "app.py"])
        process.wait()
        
        # 如果 app.py 是非正常退出的（比如报错崩了），提示用户
        if process.returncode != 0 and process.returncode != None:
            print(f"\n❌ 程序异常退出 (退出码: {process.returncode})")
            input("\n[调试信息] 程序似乎崩溃了，请截图此窗口并发送给开发者进行排查。输入回车键退出...")
    except KeyboardInterrupt:
        print("\n👋 已手动停止服务。")
    except Exception as e:
        print(f"\n❌ 启动器运行错误: {e}")
        input("\n按回车键退出...")

if __name__ == "__main__":
    print("==========================================")
    print("          院校雷达 极速引导启动器")
    print("==========================================")
    
    # 切换当前目录到脚本所在目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if check_dependencies() and check_playwright():
        start_main()
    else:
        input("\n按回车键退出...")
