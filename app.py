import os
import time
import threading
from app import create_app
from app.services.scheduler import start_scan_job

app = create_app()

if __name__ == '__main__':
    # 隐藏 Flask 开发服务器的各种启动警告和请求日志，让命令行更干净
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    print("\n🚀 正在启动 院校雷达 v1.0.1，请稍候...")

    # 1. 服务启动初始化：自动执行数据校准与监控引擎
    def auto_start_logic():
        time.sleep(3) # 等待服务器完全就绪
        try:
            # 🧹 [数据清洗] 启动前先对数据库执行存量数据校准
            from database import DatabaseManager
            db = DatabaseManager()
            db.clear_junk_data()

            if start_scan_job():
                print("🚀 [系统启动] 监控服务已激活，正在按预定频率执行扫描任务...")
        except Exception as e:
            print(f"⚠️ 启动异常: {e}")

    threading.Thread(target=auto_start_logic, daemon=True).start()

    # 2. 自动打开浏览器
    import webbrowser
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:5000/terminal')
    threading.Thread(target=open_browser, daemon=True).start()

    print("\n* Web 管理面板: http://127.0.0.1:5000/terminal")
    print("* 按 Ctrl+C 停止服务\n")
    
    # 将 host 改为 127.0.0.1，限制仅本地访问
    app.run(host='127.0.0.1', port=5000, use_reloader=False)
    port = int(os.getenv('PORT', 7860 if IS_CLOUD else 5000))
    app.run(host=host, port=port, debug=False)
