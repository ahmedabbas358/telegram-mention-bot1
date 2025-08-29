from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from contextlib import contextmanager
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional, Generator
import config

logger = logging.getLogger(__name__)
Base = declarative_base()

# محرك وقاعدة الجلسات
engine = create_engine(
    config.DB_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    future=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Group(Base):
    __tablename__ = "groups"
    group_id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String(255), nullable=True)
    group_type = Column(String(50), nullable=True)
    group_language = Column(Enum(*config.SUPPORTED_LANGUAGES), default=config.DEFAULT_LANGUAGE)
    mention_hour = Column(Integer, default=config.DEFAULT_MENTION_HOUR)
    mention_minute = Column(Integer, default=config.DEFAULT_MENTION_MINUTE)
    is_active = Column(Boolean, default=True)
    is_bot_admin = Column(Boolean, default=False)
    bot_permissions = Column(JSON, nullable=True)
    mention_count_today = Column(Integer, default=0)
    last_mention_date = Column(DateTime, default=datetime.utcnow)
    settings = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    members = relationship("Member", back_populates="group", cascade="all, delete-orphan")
    mention_logs = relationship("MentionLog", back_populates="group", cascade="all, delete-orphan")

    def can_mention_today(self) -> bool:
        if config.MAX_MENTIONS_PER_DAY == 0:
            return True
        if self.last_mention_date.date() < datetime.utcnow().date():
            self.mention_count_today = 0
            self.last_mention_date = datetime.utcnow()
            return True
        return self.mention_count_today < config.MAX_MENTIONS_PER_DAY

    def increment_mention_count(self) -> None:
        self.mention_count_today += 1
        self.last_mention_date = datetime.utcnow()

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_bot = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    joined_date = Column(DateTime, default=datetime.utcnow)
    settings = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    group = relationship("Group", back_populates="members")

class MentionLog(Base):
    __tablename__ = "mention_logs"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False)
    mention_type = Column(String(50), nullable=False)
    mention_count = Column(Integer, default=0)
    mentioned_members = Column(JSON, default=[])
    message_text = Column(String, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("Group", back_populates="mention_logs")

class RateLimitRecord(Base):
    __tablename__ = "rate_limit_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=False, index=True)
    command = Column(String(50), nullable=False)
    count = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (Index('ix_user_rate_limits', 'user_id', 'group_id', 'command'),)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        db.close()

def get_group(group_id: int) -> Optional[Group]:
    try:
        with get_db() as db:
            return db.query(Group).filter(Group.group_id == group_id).first()
    except Exception as e:
        logger.error(f"Failed to get group {group_id}: {e}")
        return None

def get_member(user_id: int, group_id: int) -> Optional[Member]:
    try:
        with get_db() as db:
            return db.query(Member).filter(Member.user_id == user_id, Member.group_id == group_id).first()
    except Exception as e:
        logger.error(f"Failed to get member {user_id} in group {group_id}: {e}")
        return None

def get_group_members(group_id: int, active_only: bool = True) -> List[Member]:
    try:
        with get_db() as db:
            query = db.query(Member).filter(Member.group_id == group_id)
            if active_only:
                query = query.filter(Member.is_active == True)
            return query.all()
    except Exception as e:
        logger.error(f"Failed to get members of group {group_id}: {e}")
        return []

def update_member_last_seen(user_id: int, group_id: int) -> None:
    try:
        with get_db() as db:
            member = db.query(Member).filter(Member.user_id == user_id, Member.group_id == group_id).first()
            if member:
                member.last_seen = datetime.utcnow()
                db.commit()
    except Exception as e:
        logger.error(f"Failed to update last seen for member {user_id}: {e}")

def get_group_stats(group_id: int) -> Dict[str, Any]:
    try:
        with get_db() as db:
            group = db.query(Group).filter(Group.group_id == group_id).first()
            if not group:
                return {}
            
            total_members = db.query(Member).filter(Member.group_id == group_id).count()
            active_members = db.query(Member).filter(Member.group_id == group_id, Member.is_active == True).count()
            admin_members = db.query(Member).filter(Member.group_id == group_id, Member.is_admin == True).count()
            bot_members = db.query(Member).filter(Member.group_id == group_id, Member.is_bot == True).count()
            
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            mentions_today = db.query(MentionLog).filter(MentionLog.group_id == group_id, MentionLog.created_at >= today_start).count()
            total_mentions = db.query(MentionLog).filter(MentionLog.group_id == group_id).count()
            
            last_mention = db.query(MentionLog).filter(MentionLog.group_id == group_id).order_by(MentionLog.created_at.desc()).first()
            
            return {
                "total_members": total_members,
                "active_members": active_members,
                "admin_members": admin_members,
                "bot_members": bot_members,
                "mentions_today": mentions_today,
                "total_mentions": total_mentions,
                "last_mention": last_mention.created_at if last_mention else None,
                "mention_time": f"{group.mention_hour:02d}:{group.mention_minute:02d}",
                "is_active": group.is_active,
                "is_bot_admin": group.is_bot_admin
            }
    except Exception as e:
        logger.error(f"Failed to get group stats for group {group_id}: {e}")
        return {}

def check_rate_limit(user_id: int, group_id: int, command: str) -> bool:
    try:
        with get_db() as db:
            one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
            record = db.query(RateLimitRecord).filter(
                RateLimitRecord.user_id == user_id,
                RateLimitRecord.group_id == group_id,
                RateLimitRecord.command == command,
                RateLimitRecord.last_used >= one_minute_ ago
            ).first()
            
            if record:
                if record.count >= config.RATE_LIMIT_PER_USER:
                    return False
                record.count += 1
                record.last_used = datetime.utcnow()
            else:
                record = RateLimitRecord(
                    user_id=user_id,
                    group_id=group_id,
                    command=command,
                    count=1,
                    last_used=datetime.utcnow()
                )
                db.add(record)
            return True
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True

def log_mention(group_id: int, user_id: int, mention_type: str, mention_count: int, mentioned_members: List[int]) -> None:
    try:
        with get_db() as db:
            mention_log = MentionLog(
                group_id=group_id,
                user_id=user_id,
                mention_type=mention_type,
                mention_count=mention_count,
                mentioned_members=mentioned_members
            )
            db.add(mention_log)
            
            group = db.query(Group).filter(Group.group_id == group_id).first()
            if group:
                if group.last_mention_date.date() != datetime.utcnow().date():
                    group.mention_count_today = 0
                group.increment_mention_count()
            db.commit()
    except Exception as e:
        logger.error(f"Failed to log mention: {e}")

def cleanup_cache() -> None:
    try:
        with get_db() as db:
            db.query(MentionLog).filter(MentionLog.created_at < datetime.utcnow() - timedelta(days=7)).delete()
            db.query(RateLimitRecord).filter(RateLimitRecord.last_used < datetime.utcnow() - timedelta(hours=24)).delete()
            db.commit()
        logger.info("Cache cleaned successfully")
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")

def get_active_members(group_id: int, days: int = 7) -> List[Member]:
    try:
        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            members = db.query(Member).filter(
                Member.group_id == group_id,
                Member.last_seen >= cutoff_date,
                Member.is_active == True,
                Member.is_bot == False
            ).all()
            return members
    except Exception as e:
        logger.error(f"Failed to get active members for group {group_id}: {e}")
        return []