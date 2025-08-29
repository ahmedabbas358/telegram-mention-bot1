import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time
from typing import Dict, Any

from database import get_db, Group, Member, log_mention
from utils import get_chat_members_safe, mention_all_members
import config

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone=config.TIMEZONE)

async def scheduled_mention_all():
    """وظيفة جدولة الذكر التلقائي"""
    try:
        now = datetime.now().time()
        current_time = now.strftime("%H:%M")
        current_weekday = datetime.now().weekday()
        
        with get_db() as db:
            groups = db.query(Group).filter(
                Group.is_active == True,
                Group.mention_time == current_time
            ).all()
        
        for group in groups:
            try:
                # التحقق من أيام الأسبوع المحددة
                if group.mention_days and current_weekday not in group.mention_days:
                    continue
                
                # التحقق من الحد اليومي للإشارات
                if not group.can_mention_today():
                    logger.info(f"تخطي مجموعة {group.group_id} - تجاوز الحد اليومي")
                    continue
                
                # جلب الأعضاء
                members = await get_chat_members_safe(None, group.group_id)
                
                if not members:
                    continue
                
                # إرسال الإشارات
                mentioned_count, successful_batches = await mention_all_members(None, group.group_id, members)
                
                # تسجيل العملية
                mentioned_ids = [member["id"] for member in members[:mentioned_count]]
                await log_mention(
                    group.group_id, 0, "scheduled", "all", 
                    mentioned_count, mentioned_ids, 
                    "ذكر تلقائي"
                )
                
                logger.info(f"تم ذكر {mentioned_count} عضو في المجموعة {group.group_id}")
                
            except Exception as e:
                logger.error(f"فشل في الذكر التلقائي للمجموعة {group.group_id}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"فشل في الذكر التلقائي: {e}")

def setup_scheduler():
    """إعداد الجدولة"""
    try:
        # جدولة الذكر التلقائي كل دقيقة للتحقق من المواعيد
        scheduler.add_job(
            scheduled_mention_all,
            trigger=CronTrigger(minute="*"),
            id="scheduled_mention_all",
            replace_existing=True
        )
        
        # إعادة تعيين العدادات اليومية في منتصف الليل
        scheduler.add_job(
            reset_daily_counters,
            trigger=CronTrigger(hour=0, minute=0),
            id="reset_daily_counters",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("تم بدء خدمة الجدولة")
        
    except Exception as e:
        logger.error(f"فشل في إعداد الجدولة: {e}")

def reset_daily_counters():
    """إعادة تعيين عدادات الإشارات اليومية"""
    try:
        with get_db() as db:
            db.query(Group).update({Group.mention_count_today: 0})
        logger.info("تم إعادة تعيين العدادات اليومية")
    except Exception as e:
        logger.error(f"فشل في إعادة تعيين العدادات: {e}")