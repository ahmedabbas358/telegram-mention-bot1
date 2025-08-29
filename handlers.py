import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ChatType, ChatMemberStatus, ParseMode

from database import get_db, Group, Member, log_activity, log_mention
from utils import update_member_activity, update_group_info, get_chat_members_safe, mention_all_members
from security import admin_required, rate_limit
import config

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء استخدام البوت"""
    user = update.effective_user
    chat = update.effective_chat
    
    # تحديث معلومات المجموعة والعضو
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(context.bot, chat.id)
        is_admin = await is_user_group_admin(context.bot, chat.id, user.id)
        await update_member_activity(context.bot, user.id, chat.id, is_admin)
    
    welcome_text = (
        "مرحباً! 👋 أنا بوت الذكر الجماعي الذكي.\n\n"
        "يمكنني مساعدتك في ذكر أعضاء المجموعة بطرق مختلفة:\n"
        "• ذكر جميع الأعضاء\n"
        "• ذكر المشرفين فقط\n"
        "• ذكر الأعضاء النشطين\n"
        "• ذكر الأعضاء الجدد\n"
        "• ذكر الأعضاء غير النشطين\n\n"
        "استخدم /help لرؤية جميع الأوامر المتاحة."
    )
    
    await update.message.reply_text(welcome_text)
    await log_activity(user.id, chat.id, "start")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رسالة المساعدة"""
    help_text = (
        "🎯 **أوامر البوت المتاحة:**\n\n"
        "👥 **أوامر الذكر:**\n"
        "/mention_all - ذكر جميع الأعضاء\n"
        "/mention_admins - ذكر المشرفين فقط\n"
        "/mention_active - ذكر الأعضاء النشطين\n"
        "/mention_recent - ذكر الأعضاء الجدد\n"
        "/mention_inactive - ذكر الأعضاء غير النشطين\n\n"
        "⚙️ **أوامر الإعدادات:**\n"
        "/settings - عرض إعدادات البوت\n"
        "/set_language [ar/en] - تغيير لغة البوت\n"
        "/set_message [نص] - تعيين رسالة مخصصة\n"
        "/set_time [HH:MM] - تعيين وقت الذكر التلقائي\n\n"
        "📊 **أوامر إدارية:**\n"
        "/stats - إحصائيات المجموعة\n"
        "/admin_list - قائمة المشرفين\n"
        "/activity_log - سجل النشاط\n\n"
        "🛡 **ملاحظات مهمة:**\n"
        "- البوت يحتاج إلى صلاحية المشرف ليعمل بشكل صحيح\n"
        "- بعض الأوامر متاحة فقط لمشرفي المجموعة"
    )
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    await log_activity(update.effective_user.id, update.effective_chat.id, "help")

@admin_required
@rate_limit("user")
async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذكر جميع الأعضاء"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من صلاحيات البوت
    if not await is_bot_admin(context.bot, chat.id):
        await update.message.reply_text("❌ البوت ليس مشرفاً في المجموعة. يرجى ترقيته أولاً.")
        return
    
    # إعلام المستخدم بأن العملية بدأت
    status_message = await update.message.reply_text("⏳ جاري جمع معلومات الأعضاء...")
    
    # جلب الأعضاء
    members = await get_chat_members_safe(context.bot, chat.id)
    
    if not members:
        await status_message.edit_text("❌ لا يمكن العثور على أعضاء في هذه المجموعة.")
        return
    
    # إرسال الإشارات
    mentioned_count, successful_batches = await mention_all_members(context.bot, chat.id)
    
    # تسجيل العملية
    mentioned_ids = [member["id"] for member in members[:mentioned_count]]
    await log_mention(
        chat.id, user.id, "manual", "all", 
        mentioned_count, mentioned_ids, 
        "ذكر جميع الأعضاء"
    )
    
    # إرسال رسالة النجاح
    success_text = f"✅ تم ذكر {mentioned_count} من الأعضاء بنجاح! ({successful_batches} دفعة)"
    await status_message.edit_text(success_text)

@admin_required
@rate_limit("user")
async def mention_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذكر المشرفين فقط"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من صلاحيات البوت
    if not await is_bot_admin(context.bot, chat.id):
        await update.message.reply_text("❌ البوت ليس مشرفاً في المجموعة. يرجى ترقيته أولاً.")
        return
    
    # إعلام المستخدم بأن العملية بدأت
    status_message = await update.message.reply_text("⏳ جاري جمع معلومات المشرفين...")
    
    # جلب المشرفين
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        admin_members = []
        
        for admin in admins:
            user_obj = admin.user
            if not user_obj.is_bot:
                admin_members.append({
                    "id": user_obj.id,
                    "username": user_obj.username,
                    "first_name": user_obj.first_name,
                    "last_name": user_obj.last_name,
                    "is_bot": user_obj.is_bot,
                    "is_admin": True
                })
    except Exception as e:
        logger.error(f"فشل في جلب المشرفين: {e}")
        admin_members = []
    
    if not admin_members:
        await status_message.edit_text("❌ لا يوجد مشرفين للاشارة إليهم.")
        return
    
    # إرسال الإشارات
    mentioned_count, successful_batches = await mention_all_members(context.bot, chat.id, admin_members)
    
    # تسجيل العملية
    mentioned_ids = [member["id"] for member in admin_members[:mentioned_count]]
    await log_mention(
        chat.id, user.id, "manual", "admins", 
        mentioned_count, mentioned_ids, 
        "ذكر المشرفين"
    )
    
    # إرسال رسالة النجاح
    success_text = f"✅ تم ذكر {mentioned_count} من المشرفين بنجاح! ({successful_batches} دفعة)"
    await status_message.edit_text(success_text)

@admin_required
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إعدادات البوت"""
    chat = update.effective_chat
    
    with get_db() as db:
        group = db.query(Group).filter(Group.group_id == chat.id).first()
    
    if not group:
        group = Group(group_id=chat.id)
    
    settings_text = (
        f"⚙️ **إعدادات البوت للمجموعة**\n\n"
        f"• اللغة: {group.group_language}\n"
        f"• وقت الذكر التلقائي: {group.mention_time or 'غير محدد'}\n"
        f"• الرسالة المخصصة: {group.custom_message[:50] + '...' if len(group.custom_message) > 50 else group.custom_message}\n"
        f"• عدد الإشارات اليوم: {group.mention_count_today}/{config.MAX_MENTIONS_PER_DAY if config.MAX_MENTIONS_PER_DAY > 0 else '∞'}\n"
        f"• حالة البوت: {'✅ نشط' if group.is_active else '❌ غير نشط'}\n"
        f"• صلاحية البوت: {'✅ مشرف' if group.is_bot_admin else '❌ ليس مشرف'}"
    )
    
    keyboard = [
        [InlineKeyboardButton("تغيير اللغة", callback_data="set_language")],
        [InlineKeyboardButton("تغيير وقت الذكر", callback_data="set_time")],
        [InlineKeyboardButton("تغيير الرسالة", callback_data="set_message")],
        [InlineKeyboardButton("تفعيل/تعطيل البوت", callback_data="toggle_bot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(settings_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    await log_activity(update.effective_user.id, chat.id, "settings")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استعلامات الأزرار"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    
    # التحقق من أن المستخدم مشرف
    is_admin = await is_user_group_admin(context.bot, chat_id, user_id)
    if not is_admin and user_id not in config.ADMIN_IDS:
        await query.edit_message_text("❌ تحتاج إلى صلاحية المشرف لتغيير الإعدادات.")
        return
    
    if data == "set_language":
        keyboard = [
            [InlineKeyboardButton("العربية", callback_data="lang_ar")],
            [InlineKeyboardButton("English", callback_data="lang_en")],
            [InlineKeyboardButton("Français", callback_data="lang_fr")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("اختر اللغة:", reply_markup=reply_markup)
    
    elif data.startswith("lang_"):
        lang = data.split("_")[1]
        with get_db() as db:
            group = db.query(Group).filter(Group.group_id == chat_id).first()
            if group:
                group.group_language = lang
            else:
                group = Group(group_id=chat_id, group_language=lang)
                db.add(group)
        
        await query.edit_message_text(f"✅ تم تغيير اللغة إلى {lang}")
    
    elif data == "set_time":
        await query.edit_message_text("أرسل وقت الذكر بالتنسيق HH:MM (مثال: 09:30)")
        context.user_data["waiting_for_time"] = True
    
    elif data == "set_message":
        await query.edit_message_text("أرسل الرسالة المخصصة التي تريد استخدامها عند الذكر:")
        context.user_data["waiting_for_message"] = True
    
    elif data == "toggle_bot":
        with get_db() as db:
            group = db.query(Group).filter(Group.group_id == chat_id).first()
            if group:
                group.is_active = not group.is_active
                status = "مفعل" if group.is_active else "معطل"
            else:
                group = Group(group_id=chat_id, is_active=True)
                db.add(group)
                status = "مفعل"
        
        await query.edit_message_text(f"✅ تم {status} البوت بنجاح")
    
    await log_activity(user_id, chat_id, f"callback_{data}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية"""
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text
    
    if "waiting_for_time" in context.user_data:
        # معالجة وقت الذكر
        try:
            time_parts = text.split(":")
            if len(time_parts) != 2:
                raise ValueError
                
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError
                
            time_str = f"{hour:02d}:{minute:02d}"
            
            with get_db() as db:
                group = db.query(Group).filter(Group.group_id == chat.id).first()
                if group:
                    group.mention_time = time_str
                else:
                    group = Group(group_id=chat.id, mention_time=time_str)
                    db.add(group)
            
            await update.message.reply_text(f"✅ تم تعيين وقت الذكر إلى {time_str}")
            del context.user_data["waiting_for_time"]
            
        except ValueError:
            await update.message.reply_text("❌ تنسوق الوقت غير صحيح. يرجى استخدام الصيغة HH:MM (مثال: 09:30)")
    
    elif "waiting_for_message" in context.user_data:
        # معالجة الرسالة المخصصة
        if len(text) > 1000:
            await update.message.reply_text("❌ الرسالة طويلة جداً. الحد الأقصى هو 1000 حرف.")
            return
            
        with get_db() as db:
            group = db.query(Group).filter(Group.group_id == chat.id).first()
            if group:
                group.custom_message = text
            else:
                group = Group(group_id=chat.id, custom_message=text)
                db.add(group)
        
        await update.message.reply_text("✅ تم حفظ الرسالة المخصصة بنجاح")
        del context.user_data["waiting_for_message"]
    
    await log_activity(user.id, chat.id, "message", {"text": text})

def setup_handlers(application):
    """إعداد معالجات الأوامر"""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("mention_all", mention_all))
    application.add_handler(CommandHandler("mention_admins", mention_admins))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application