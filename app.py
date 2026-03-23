import time
import threading
import webbrowser
from app import create_app
from app.services.scheduler import start_scan_job

app = create_app()

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  * 院校通知监控系统 v4.0 - 全量扫描模式")
    print("  * 服务启动中，正在连接本地数据中心...")
    print("="*50 + "\n")

    # 1. 服务启动初始化：自动执行数据校准与监控引擎
    def auto_start_logic():
        time.sleep(3) # 等待服务器完全就绪
        try:
            # 🧹 [数据清洗] 启动前先对数据库执行存量数据校准
            from database import DatabaseManager
            db = DatabaseManager('radar_platform.db')
            db.clear_junk_data()

            if start_scan_job():
                print("🚀 [系统启动] 监控服务已激活，正在按预定频率执行扫描任务...")
        except Exception as e:
            print(f"⚠️ 启动异常: {e}")

    threading.Thread(target=auto_start_logic, daemon=True).start()

    # 2. 自动打开浏览器
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:5000/terminal')

    threading.Thread(target=open_browser, daemon=True).start()

    # 3. 运行 Flask
    app.run(host='127.0.0.1', port=5000, debug=False)
