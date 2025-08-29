from functools import wraps
from typing import Callable, Any, Coroutine
from telegram import Update
from telegram.ext import ContextTypes
import logging

from database import check_rate_limit, log_activity
from utils import is_user_group_admin
import config

logger = logging.getLogger(__name__)

def admin_required(func: Callable[[Update, ContextTypes], Coroutine[Any, Any, None]]):
    """ديكوراتور للتحقق من أن المستخدم هو مشرف في المجموعة"""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes, *args, **kwargs):
        if not update.effective_chat or not update.effective_user:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات.")
            return
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # التحقق من أن المستخدم مشرف في المجموعة
        is_admin = await is_user_group_admin(context.bot, chat_id, user_id)
        if not is_admin and user_id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ تحتاج إلى صلاحية المشرف لاستخدام هذا الأمر.")
            await log_activity(user_id, chat_id, func.__name__, {}, False, "ليس مشرفاً")
            return
        
        # تسجيل النشاط
        await log_activity(user_id, chat_id, func.__name__)
        
        return await func(update, context, *args, **kwargs)
    
    return wrapped

def rate_limit(limit_type: str = "user"):
    """ديكوراتور للتحكم في معدل الاستخدام"""
    def decorator(func: Callable[[Update, ContextTypes], Coroutine[Any, Any, None]]):
        @wraps(func)
        async def wrapped(update: Update, context: ContextTypes, *args, **kwargs):
            if not update.effective_chat or not update.effective_user:
                return await func(update, context, *args, **kwargs)
            
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            command_name = func.__name__
            
            # التحقق من معدل الاستخدام
            if limit_type == "user":
                allowed = check_rate_limit(user_id, chat_id, command_name)
                limit = config.RATE_LIMIT_PER_USER
            else:
                allowed = check_rate_limit(0, chat_id, f"group_{command_name}")
                limit = config.RATE_LIMIT_PER_GROUP
            
            if not allowed:
                message = f"❌ لقد تجاوزت الحد المسموح ({limit} في الدقيقة). يرجى الانتظار قليلاً."
                if update.callback_query:
                    await update.callback_query.answer(message, show_alert=True)
                else:
                    await update.message.reply_text(message)
                await log_activity(user_id, chat_id, command_name, {}, False, "تجاوز معدل الاستخدام")
                return
            
            return await func(update, context, *args, **kwargs)
        
        return wrapped
    return decorator