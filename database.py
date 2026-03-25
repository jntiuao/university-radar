import os
import logging
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger('DatabaseManager')
Base = declarative_base()

class Announcement(Base):
    __tablename__ = 'global_announcements'
    id = Column(Integer, primary_key=True, autoincrement=True)
    university = Column(String(255))
    module = Column(String(255))
    title = Column(Text)
    link = Column(Text, index=True)
    publish_date = Column(String(50))
    category = Column(String(100))
    major = Column(String(100))
    urgency = Column(String(20))
    relevance_score = Column(Integer)
    relevance_reason = Column(Text)
    ai_summary = Column(Text)
    ai_action_suggestion = Column(Text)
    is_pdf = Column(Boolean, default=False)
    status = Column(Integer, default=0)
    full_text = Column(Text)
    content_hash = Column(String(64), index=True)
    target_year = Column(Integer)
    historical_ref_id = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String(100), primary_key=True)
    value = Column(Text)

class DatabaseManager:
    def __init__(self, db_url=None):
        # 优先使用环境变量中的 DATABASE_URL (用于云端 Postgres)
        # 否则回退到本地 SQLite
        if not db_url:
            db_url = os.getenv("DATABASE_URL")
            
        if not db_url:
            db_url = "sqlite:///radar_platform.db"
        
        # 处理 Heroku/Render 等平台可能提供的 postgres:// 协议（SQLAlchemy 2.0 只认 postgresql://）
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.SessionFactory = scoped_session(sessionmaker(bind=self.engine))
        Base.metadata.create_all(self.engine)
        logger.info(f"数据库引擎已就绪: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    def get_session(self):
        return self.SessionFactory()

    def get_setting(self, key, default=None):
        session = self.get_session()
        try:
            row = session.query(Setting).filter_by(key=key).first()
            if row:
                try:
                    return json.loads(row.value)
                except:
                    return row.value
            return default
        finally:
            session.close()

    def save_setting(self, key, value):
        session = self.get_session()
        try:
            val_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            item = session.query(Setting).filter_by(key=key).first()
            if item:
                item.value = val_str
            else:
                item = Setting(key=key, value=val_str)
                session.add(item)
            session.commit()
        finally:
            session.close()

    def get_ai_cache(self, content_hash):
        if not content_hash: return None
        session = self.get_session()
        try:
            row = session.query(Announcement).filter_by(content_hash=content_hash).filter(Announcement.ai_summary != "").order_by(Announcement.id.desc()).first()
            if row:
                return {
                    "category": row.category,
                    "major": row.major,
                    "urgency": row.urgency,
                    "relevance_score": row.relevance_score,
                    "relevance_reason": row.relevance_reason,
                    "summary": row.ai_summary,
                    "action": row.ai_action_suggestion,
                    "target_year": row.target_year
                }
        finally:
            session.close()
        return None

    def is_link_scanned(self, link):
        session = self.get_session()
        try:
            row = session.query(Announcement).filter_by(link=link).first()
            return row.content_hash if row else None
        finally:
            session.close()

    def check_duplicate_title(self, uni, title, module=None):
        session = self.get_session()
        try:
            query = session.query(Announcement).filter_by(university=uni, title=title)
            if module:
                query = query.filter_by(module=module)
            return query.first() is not None
        finally:
            session.close()

    def save_announcement(self, university, module, title, link, date, ai_data, is_pdf=False, full_text=None, content_hash=None):
        session = self.get_session()
        try:
            item = Announcement(
                university=university,
                module=module,
                title=title,
                link=link,
                publish_date=date,
                category=ai_data.get('category', '通知'),
                major=ai_data.get('major', ''),
                urgency=ai_data.get('urgency', '中'),
                relevance_score=ai_data.get('relevance_score', 50),
                relevance_reason=ai_data.get('relevance_reason', ''),
                ai_summary=ai_data.get('summary', ''),
                ai_action_suggestion=ai_data.get('action', ''),
                is_pdf=is_pdf,
                full_text=full_text,
                content_hash=content_hash,
                target_year=ai_data.get('target_year'),
                historical_ref_id=ai_data.get('historical_ref_id')
            )
            session.add(item)
            session.commit()
        finally:
            session.close()

    def update_content(self, link, full_text, content_hash, ai_data):
        session = self.get_session()
        try:
            item = session.query(Announcement).filter_by(link=link).first()
            if item:
                item.full_text = full_text
                item.content_hash = content_hash
                item.ai_summary = ai_data.get('summary', '')
                item.ai_action_suggestion = ai_data.get('action', '')
                item.target_year = ai_data.get('target_year')
                item.historical_ref_id = ai_data.get('historical_ref_id')
                item.status = 0
                session.commit()
                logger.info(f"已更新公告内容异动: {link}")
        finally:
            session.close()

    def get_historical_match(self, university, category, major, current_year):
        session = self.get_session()
        try:
            row = session.query(Announcement).filter(
                Announcement.university == university,
                Announcement.category == category,
                Announcement.target_year < current_year
            ).order_by(Announcement.target_year.desc(), Announcement.id.desc()).first()
            if row:
                return {"ai_summary": row.ai_summary, "id": row.id}
        finally:
            session.close()
        return None

    def get_unrouted_announcements(self, min_relevance=0):
        session = self.get_session()
        try:
            rows = session.query(Announcement).filter(
                Announcement.status == 0,
                Announcement.relevance_score >= min_relevance
            ).all()
            return [self._to_dict(r) for r in rows]
        finally:
            session.close()

    def mark_as_routed(self, event_id):
        session = self.get_session()
        try:
            item = session.query(Announcement).filter_by(id=event_id).first()
            if item:
                item.status = 1
                session.commit()
        finally:
            session.close()

    def get_recent_announcements(self, limit=50):
        session = self.get_session()
        try:
            rows = session.query(Announcement).order_by(Announcement.id.desc()).limit(limit).all()
            return [self._to_dict(r) for r in rows]
        finally:
            session.close()

    def _to_dict(self, row):
        return {c.name: getattr(row, c.name) for c in row.__table__.columns}

    def clear_junk_data(self):
        session = self.get_session()
        try:
            count = session.query(Announcement).filter(
                (Announcement.relevance_score < 50) | (Announcement.category == '杂项通知')
            ).delete()
            session.commit()
            if count > 0:
                logger.info(f"✨ [数据清理] 已清理 {count} 条杂项干扰信息")
            return count
        finally:
            session.close()

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