import os
import time
import logging
import asyncio
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.utils import load_config
from app.services.pusher import push_to_channel
from database import DatabaseManager

logger = logging.getLogger('RadarApp')
DB_PATH = 'radar_platform.db'

# 全局状态
scanner_state = {
    "cycle_count": 0,
    "next_scan_at": None,
    "running": False,
    "logs": []
}
scanner_instance = None
scheduler = BackgroundScheduler()
scheduler.start()

scanning_lock = threading.Lock()

def run_scan_cycle():
    """执行一次完整的 扫描→AI分析→推送 循环"""
    global scanner_state

    config = load_config()
    notifications = config.get('notifications', [])
    threshold = config.get('relevance_threshold', 0)
    proxy = os.getenv("HTTP_PROXY")

    try:
        scanner_state['logs'].append("📡 开始扫描选定的院校网站...")

        from scanner import UniversityScanner
        # 💡 每次都重新实例化以加载最新的 universities.yaml 配置文件
        scanner_instance = UniversityScanner('universities.yaml')

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scanner_instance.scan())
        # 释放 httpx 连接池资源，防止连接泄漏
        loop.run_until_complete(scanner_instance.close())
        loop.close()

        scanner_state['logs'].append("✅ 扫描完毕！")
    except Exception as e:
        scanner_state['logs'].append(f"❌ 扫描出错: {e}")
        logger.error(f"扫描异常: {e}")

    # 推送环节
    try:
        db = DatabaseManager(DB_PATH)
        new_events = db.get_unrouted_announcements(min_relevance=threshold)

        if new_events:
            scanner_state['logs'].append(f"📬 发现 {len(new_events)} 条新情报，开始推送...")

            for event in new_events:
                push_ok = False
                for ch in notifications:
                    result = push_to_channel(ch, event, proxy)
                    if result:
                        push_ok = True
                        scanner_state['logs'].append(f"    ✅ → {ch.get('channel', '?')}")
                    else:
                        scanner_state['logs'].append(f"    ❌ → {ch.get('channel', '?')} 失败")

                if push_ok:
                    db.mark_as_routed(event['id'])
        else:
            scanner_state['logs'].append("ℹ️ 没有新情报需要推送。")
    except Exception as e:
        scanner_state['logs'].append(f"❌ 推送异常: {e}")
        logger.error(f"推送异常: {e}")

def scheduler_job():
    """APScheduler 调用的定时任务包装器"""
    global scanner_state
    
    if not scanning_lock.acquire(blocking=False):
        logger.warning("上一轮扫描尚未结束，跳过本轮触发")
        return
        
    try:
        scanner_state['cycle_count'] += 1
        cycle = scanner_state['cycle_count']
        
        log_msg = f"🔄 ===== 第 {cycle} 轮院校全量扫描开始 ====="
        scanner_state['logs'].append(log_msg)
        logger.info(log_msg)

        run_scan_cycle()

        interval = load_config().get('scan_interval', 15)
        next_run = time.strftime("%H:%M:%S", time.localtime(time.time() + interval * 60))
        scanner_state['next_scan_at'] = next_run
        
        done_msg = f"🎉 第 {cycle} 轮扫描完成！预计下一轮: {next_run}"
        scanner_state['logs'].append(done_msg)
        logger.info(done_msg)
    finally:
        scanning_lock.release()

def start_scan_job():
    global scanner_state

    config = load_config()
    interval = config.get('scan_interval', 15)

    scheduler.remove_all_jobs()
    scheduler.add_job(
        id='radar_scan_job',
        func=scheduler_job,
        trigger=IntervalTrigger(minutes=interval),
        replace_existing=True
    )
    
    # 立即触发一次全量扫描流程
    threading.Thread(target=scheduler_job, daemon=True).start()
    scanner_state['running'] = True
    scanner_state['logs'] = ["🚀 周期性监控引擎已启动，正在执行首次数据同步..."]
    return True

def stop_scan_job():
    global scanner_state
    scheduler.remove_all_jobs()
    scanner_state['running'] = False
    scanner_state['logs'].append("⏹ 监控已通过调度中心安全停止。")
    return True
