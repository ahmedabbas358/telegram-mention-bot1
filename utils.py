import asyncio
import logging
import cachetools
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from telegram import Bot
from telegram.constants import ChatMemberStatus, ParseMode

from database import get_db, Group, Member
import config

logger = logging.getLogger(__name__)
cache = cachetools.TTLCache(maxsize=100, ttl=config.CACHE_TIMEOUT)

async def is_user_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """التحقق من أن المستخدم هو مشرف في المجموعة"""
    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        return chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logger.error(f"فشل في التحقق من صلاحية المستخدم: {e}")
        return False

async def is_bot_admin(bot: Bot, chat_id: int) -> bool:
    """التحقق من أن البوت هو مشرف في المجموعة"""
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        return bot_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logger.error(f"فشل في التحقق من صلاحية البوت: {e}")
        return False

async def has_bot_permissions(bot: Bot, chat_id: int, permissions: List[str]) -> bool:
    """التحقق من أن البوت لديه الصلاحيات المطلوبة"""
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        
        if bot_member.status == ChatMemberStatus.OWNER:
            return True
        
        for permission in permissions:
            if not getattr(bot_member, permission, False):
                return False
        
        return True
    except Exception as e:
        logger.error(f"فشل في التحقق من صلاحيات البوت: {e}")
        return False

async def get_chat_members_safe(bot: Bot, chat_id: int, force_update: bool = False) -> List[Dict[str, Any]]:
    """جلب أعضاء المجموعة بطريقة آمنة مع التخزين المؤقت"""
    cache_key = f"members_{chat_id}"
    if not force_update and cache_key in cache:
        return cache[cache_key]
    
    members_list = []
    
    try:
        # محاولة جلب المشرفين أولاً
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            user = admin.user
            if not user.is_bot:
                members_list.append({
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_bot": user.is_bot,
                    "is_admin": True
                })
    except Exception as e:
        logger.error(f"فشل في جلب المشرفين: {e}")
    
    # استخدام بيانات قاعدة البيانات كبديل
    if not members_list:
        try:
            with get_db() as db:
                db_members = db.query(Member).filter(
                    Member.group_id == chat_id, 
                    Member.is_bot == False
                ).all()
                
                for member in db_members:
                    members_list.append({
                        "id": member.user_id,
                        "username": member.username,
                        "first_name": member.first_name,
                        "last_name": member.last_name,
                        "is_bot": member.is_bot,
                        "is_admin": member.is_admin
                    })
        except Exception as e:
            logger.error(f"فشل في جلب الأعضاء من قاعدة البيانات: {e}")
    
    cache[cache_key] = members_list
    return members_list

def format_mention_text(custom_message: str, mentions: List[str]) -> str:
    """تنسيق نص الإشارة مع الرسالة المخصصة"""
    if not mentions:
        return custom_message
    
    mentions_text = " ".join(mentions)
    full_text = f"{custom_message}\n\n{mentions_text}"
    
    # تقليل النص إذا تجاوز الحد الأقصى
    if len(full_text) > config.MAX_MESSAGE_LENGTH:
        excess = len(full_text) - config.MAX_MESSAGE_LENGTH
        mentions_text = mentions_text[:-excess-3] + "..."
        full_text = f"{custom_message}\n\n{mentions_text}"
    
    return full_text

async def mention_members_batch(bot: Bot, chat_id: int, members: List[Member], custom_message: str = None) -> int:
    """إرسال منشن لمجموعة من الأعضاء في دفعة واحدة"""
    if not members:
        return 0
    
    if custom_message is None:
        group = get_group(chat_id)
        custom_message = group.custom_message if group else config.DEFAULT_MESSAGE
    
    # تجهيز نصوص الإشارات
    mention_texts = [member.get_mention_text() for member in members]
    message = format_mention_text(custom_message, mention_texts)
    
    try:
        # إرسال الرسالة
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN if config.MENTION_FORMAT == "id" else None
        )
        return len(members)
    except Exception as e:
        logger.error(f"فشل في إرسال الإشارات: {e}")
        return 0

async def mention_all_members(bot: Bot, chat_id: int, members: List[Member] = None) -> Tuple[int, int]:
    """إرسال منشن لجميع الأعضاء على دفعات"""
    if members is None:
        members_data = await get_chat_members_safe(bot, chat_id)
        members = []
        for data in members_data:
            member = Member(
                user_id=data["id"],
                username=data["username"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                is_bot=data["is_bot"],
                is_admin=data["is_admin"]
            )
            members.append(member)
    
    if not members:
        return 0, 0
    
    # تقسيم الأعضاء إلى دفعات
    batch_size = config.DEFAULT_BATCH_SIZE
    batches = [members[i:i + batch_size] for i in range(0, len(members), batch_size)]
    total_mentioned = 0
    successful_batches = 0
    
    for batch in batches:
        try:
            mentioned_count = await mention_members_batch(bot, chat_id, batch)
            total_mentioned += mentioned_count
            successful_batches += 1
            
            # تأخير بين الدفعات
            await asyncio.sleep(config.MENTION_DELAY)
        except Exception as e:
            logger.error(f"فشل في إرسال دفعة الإشارات: {e}")
            continue
    
    return total_mentioned, successful_batches

async def update_member_activity(bot: Bot, user_id: int, chat_id: int, is_admin: bool = False) -> None:
    """تحديث نشاط العضو في قاعدة البيانات"""
    try:
        # الحصول على معلومات المستخدم من Telegram
        chat_member = await bot.get_chat_member(chat_id, user_id)
        user = chat_member.user
        
        with get_db() as db:
            member = db.query(Member).filter(
                Member.user_id == user_id,
                Member.group_id == chat_id
            ).first()
            
            if member:
                member.last_seen = datetime.utcnow()
                member.first_name = user.first_name or member.first_name
                member.last_name = user.last_name or member.last_name
                member.username = user.username or member.username
                member.is_admin = is_admin
            else:
                member = Member(
                    user_id=user_id,
                    group_id=chat_id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    is_bot=user.is_bot,
                    is_admin=is_admin
                )
                db.add(member)
    except Exception as e:
        logger.error(f"فشل في تحديث نشاط العضو: {e}")

async def update_group_info(bot: Bot, chat_id: int) -> Optional[Group]:
    """تحديث معلومات المجموعة في قاعدة البيانات"""
    try:
        chat = await bot.get_chat(chat_id)
        
        with get_db() as db:
            group = db.query(Group).filter(Group.group_id == chat_id).first()
            
            if not group:
                group = Group(
                    group_id=chat_id,
                    group_name=chat.title,
                    group_type=chat.type
                )
                db.add(group)
            else:
                group.group_name = chat.title
                group.group_type = chat.type
                group.updated_at = datetime.utcnow()
            
            # التحقق من صلاحيات البوت
            group.is_bot_admin = await is_bot_admin(bot, chat_id)
            
            return group
    except Exception as e:
        logger.error(f"فشل في تحديث معلومات المجموعة: {e}")
        return None