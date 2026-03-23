import sqlite3
import threading
import time
import logging

logger = logging.getLogger('DatabaseManager')

class DatabaseManager:
    def __init__(self, db_path='radar_platform.db'):
        self.db_path = db_path
        self.local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS global_announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                university TEXT,
                module TEXT,
                title TEXT,
                link TEXT,
                publish_date TEXT,
                category TEXT,
                major TEXT,
                urgency TEXT,
                relevance_score INTEGER,
                relevance_reason TEXT,
                ai_summary TEXT,
                ai_action_suggestion TEXT,
                is_pdf BOOLEAN,
                status INTEGER DEFAULT 0,
                full_text TEXT,
                content_hash TEXT,
                target_year INTEGER,
                historical_ref_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_link ON global_announcements(link)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_hash ON global_announcements(content_hash)')
        
        # 自动迁移：为旧数据库添加新字段
        c.execute("PRAGMA table_info(global_announcements)")
        columns = [column[1] for column in c.fetchall()]
        if 'full_text' not in columns:
            logger.info("进行数据库迁移: 增加 full_text 字段")
            c.execute("ALTER TABLE global_announcements ADD COLUMN full_text TEXT")
        if 'content_hash' not in columns:
            logger.info("进行数据库迁移: 增加 content_hash 字段")
            c.execute("ALTER TABLE global_announcements ADD COLUMN content_hash TEXT")
        if 'ai_action_suggestion' not in columns:
            logger.info("进行数据库迁移: 增加 ai_action_suggestion 字段")
            c.execute("ALTER TABLE global_announcements ADD COLUMN ai_action_suggestion TEXT")
        if 'target_year' not in columns:
            logger.info("进行数据库迁移: 增加 target_year 字段")
            c.execute("ALTER TABLE global_announcements ADD COLUMN target_year INTEGER")
        if 'historical_ref_id' not in columns:
            logger.info("进行数据库迁移: 增加 historical_ref_id 字段")
            c.execute("ALTER TABLE global_announcements ADD COLUMN historical_ref_id INTEGER")
            
        conn.commit()
        conn.close()

    def get_ai_cache(self, content_hash):
        """根据内容哈希查找是否已有 AI 解析结果 (跨院校/跨链接共享缓存)"""
        if not content_hash: return None
        c = self._get_conn().cursor()
        # 查找最新的、有摘要的记录
        c.execute('''
            SELECT category, major, urgency, relevance_score, relevance_reason, 
                   ai_summary as summary, ai_action_suggestion as action, target_year
            FROM global_announcements 
            WHERE content_hash = ? AND ai_summary != "" 
            ORDER BY id DESC LIMIT 1
        ''', (content_hash,))
        row = c.fetchone()
        return dict(row) if row else None

    def is_link_scanned(self, link):
        c = self._get_conn().cursor()
        c.execute("SELECT content_hash FROM global_announcements WHERE link = ?", (link,))
        row = c.fetchone()
        return row['content_hash'] if row else None

    def check_duplicate_title(self, uni, title, module=None):
        c = self._get_conn().cursor()
        if module:
            c.execute("SELECT id FROM global_announcements WHERE university = ? AND title = ? AND module = ?", (uni, title, module))
        else:
            c.execute("SELECT id FROM global_announcements WHERE university = ? AND title = ?", (uni, title))
        return c.fetchone() is not None

    def save_announcement(self, university, module, title, link, date, ai_data, is_pdf=False, full_text=None, content_hash=None):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('''
            INSERT INTO global_announcements 
            (university, module, title, link, publish_date, category, major, urgency, 
             relevance_score, relevance_reason, ai_summary, ai_action_suggestion, is_pdf, 
             full_text, content_hash, target_year, historical_ref_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            university, module, title, link, date, 
            ai_data.get('category', '通知'),
            ai_data.get('major', ''),
            ai_data.get('urgency', '中'),
            ai_data.get('relevance_score', 50),
            ai_data.get('relevance_reason', ''),
            ai_data.get('summary', ''),
            ai_data.get('action', ''),
            is_pdf,
            full_text,
            content_hash,
            ai_data.get('target_year'),
            ai_data.get('historical_ref_id')
        ))
        conn.commit()

    def update_content(self, link, full_text, content_hash, ai_data):
        """更新已有公告的内容和 AI 分析结果（用于异动监测）"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('''
            UPDATE global_announcements 
            SET full_text = ?, content_hash = ?, ai_summary = ?, ai_action_suggestion = ?, 
                status = 0, target_year = ?, historical_ref_id = ?
            WHERE link = ?
        ''', (
            full_text, content_hash, 
            ai_data.get('summary', ''), 
            ai_data.get('action', ''), 
            ai_data.get('target_year'),
            ai_data.get('historical_ref_id'),
            link
        ))
        conn.commit()
        logger.info(f"已更新公告内容异动: {link}")

    def get_historical_match(self, university, category, major, current_year):
        """寻找往年同类型的简报"""
        c = self._get_conn().cursor()
        # 寻找同校、同类别、且专业相关的去年记录
        # 匹配逻辑：年份为 current_year - 1
        query = '''
            SELECT ai_summary, id FROM global_announcements 
            WHERE university = ? AND category = ? AND target_year < ?
            ORDER BY target_year DESC, id DESC LIMIT 1
        '''
        # 为简化，先不进行极细粒度的专业模糊匹配，后续可增强
        c.execute(query, (university, category, current_year))
        row = c.fetchone()
        return dict(row) if row else None

    def get_unrouted_announcements(self, min_relevance=0):
        c = self._get_conn().cursor()
        c.execute("SELECT * FROM global_announcements WHERE status = 0 AND relevance_score >= ?", (min_relevance,))
        return [dict(row) for row in c.fetchall()]

    def mark_as_routed(self, event_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("UPDATE global_announcements SET status = 1 WHERE id = ?", (event_id,))
        conn.commit()

    def get_recent_announcements(self, limit=50):
        c = self._get_conn().cursor()
        c.execute("SELECT * FROM global_announcements ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in c.fetchall()]

    def get_subscribers_for_university(self, uni_name):
        # 这是一个占位符，SaaS版本需要用户表
        # 个人版暂不需要此功能，这里返回空列表防报错
        return []

    def clear_junk_data(self):
        """🧹 数据清洗：清理所有低于评分阈值的无意义记录"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM global_announcements WHERE relevance_score < 50 OR category = '杂项通知'")
        count = c.rowcount
        conn.commit()
        if count > 0:
            logger.info(f"✨ [数据清理] 已从本地数据库中清理 {count} 条杂项干扰信息")
        return count

    def inject_test_data(self):
        test_event = {
            "category": "复试通知",
            "major": "计算机/软件工程",
            "urgency": "高",
            "relevance_score": 95,
            "relevance_reason": "直接命中你的目标专业",
            "summary": "这是来自院校雷达的测试数据，用于验证推送通道是否畅通。",
            "action": "请检查手机是否收到推送;确认格式是否正确",
        }
        self.save_announcement(
            "测试大学", "研招办", "2025年硕士研究生复试名单公示(测试数据)", 
            "http://localhost/test", "2025-03-15", test_event, is_pdf=False
        )
        return 1