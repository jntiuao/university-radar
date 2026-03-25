import os
import logging
import json
import sqlite3
from datetime import datetime

logger = logging.getLogger('DatabaseManager')

class DatabaseManager:
    def __init__(self, db_path=None):
        # 由于不再支持云端 Postgres，直接锁定本地 SQLite
        if not db_path:
            db_path = "radar_platform.db"
        
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        return conn

    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            # 创建公告表
            conn.execute('''
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
            # 创建索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_link ON global_announcements (link)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_hash ON global_announcements (content_hash)')
            
            # 创建设置表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.commit()
        logger.info(f"💾 数据库层已就绪 (原生驱动): {self.db_path}")

    def get_setting(self, key, default=None):
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except:
                    return row['value']
            return default

    def save_setting(self, key, value):
        val_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        with self._get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val_str))
            conn.commit()

    def get_ai_cache(self, content_hash):
        if not content_hash: return None
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT category, major, urgency, relevance_score, relevance_reason, ai_summary, ai_action_suggestion, target_year "
                "FROM global_announcements WHERE content_hash = ? AND ai_summary != '' ORDER BY id DESC LIMIT 1",
                (content_hash,)
            ).fetchone()
            if row:
                return {
                    "category": row['category'],
                    "major": row['major'],
                    "urgency": row['urgency'],
                    "relevance_score": row['relevance_score'],
                    "relevance_reason": row['relevance_reason'],
                    "summary": row['ai_summary'],
                    "action": row['ai_action_suggestion'],
                    "target_year": row['target_year']
                }
        return None

    def is_link_scanned(self, link):
        with self._get_connection() as conn:
            row = conn.execute("SELECT content_hash FROM global_announcements WHERE link = ?", (link,)).fetchone()
            return row['content_hash'] if row else None

    def check_duplicate_title(self, uni, title, module=None):
        with self._get_connection() as conn:
            if module:
                row = conn.execute(
                    "SELECT 1 FROM global_announcements WHERE university=? AND title=? AND module=?",
                    (uni, title, module)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT 1 FROM global_announcements WHERE university=? AND title=?",
                    (uni, title)
                ).fetchone()
            return row is not None

    def save_announcement(self, university, module, title, link, date, ai_data, is_pdf=False, full_text=None, content_hash=None):
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO global_announcements (
                    university, module, title, link, publish_date, 
                    category, major, urgency, relevance_score, relevance_reason, 
                    ai_summary, ai_action_suggestion, is_pdf, full_text, content_hash, 
                    target_year, historical_ref_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                university, module, title, link, date,
                ai_data.get('category', '通知'),
                ai_data.get('major', ''),
                ai_data.get('urgency', '中'),
                ai_data.get('relevance_score', 50),
                ai_data.get('relevance_reason', ''),
                ai_data.get('summary', ''),
                ai_data.get('action', ''),
                is_pdf, full_text, content_hash,
                ai_data.get('target_year'),
                ai_data.get('historical_ref_id')
            ))
            conn.commit()

    def update_content(self, link, full_text, content_hash, ai_data):
        with self._get_connection() as conn:
            conn.execute('''
                UPDATE global_announcements SET 
                    full_text=?, content_hash=?, ai_summary=?, 
                    ai_action_suggestion=?, target_year=?, historical_ref_id=?, status=0
                WHERE link=?
            ''', (
                full_text, content_hash, ai_data.get('summary', ''),
                ai_data.get('action', ''), ai_data.get('target_year'),
                ai_data.get('historical_ref_id'), link
            ))
            conn.commit()
            logger.info(f"已更新公告内容异动: {link}")

    def get_historical_match(self, university, category, major, current_year):
        with self._get_connection() as conn:
            row = conn.execute('''
                SELECT ai_summary, id FROM global_announcements 
                WHERE university=? AND category=? AND target_year < ?
                ORDER BY target_year DESC, id DESC LIMIT 1
            ''', (university, category, current_year)).fetchone()
            if row:
                return {"ai_summary": row['ai_summary'], "id": row['id']}
        return None

    def get_unrouted_announcements(self, min_relevance=0):
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM global_announcements WHERE status = 0 AND relevance_score >= ?",
                (min_relevance,)
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_as_routed(self, event_id):
        with self._get_connection() as conn:
            conn.execute("UPDATE global_announcements SET status = 1 WHERE id = ?", (event_id,))
            conn.commit()

    def get_recent_announcements(self, limit=50):
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM global_announcements ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def clear_junk_data(self):
        with self._get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM global_announcements WHERE relevance_score < 50 OR category = '杂项通知'"
            )
            count = cur.rowcount
            conn.commit()
            if count > 0:
                logger.info(f"✨ [数据清理] 已清理 {count} 条杂项干扰信息")
            return count

    # 兼容性存根，防止外部调用报错（虽然搜索没搜到，但保留空实现以策安全）
    def get_session(self):
        class DummySession:
            def close(self): pass
        return DummySession()