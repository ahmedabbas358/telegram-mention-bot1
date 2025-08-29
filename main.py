import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from database import init_db
from handlers import setup_handlers
from scheduler import setup_scheduler
from utils import update_member_activity, update_group_info

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL),
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def post_init(application):
    """وظيفة ما بعد التهيئة"""
    # تهيئة قاعدة البيانات
    init_db()
    
    # بدء خدمة الجدولة
    setup_scheduler()
    
    logger.info("تم تهيئة البوت بنجاح")

async def post_stop(application):
    """وظيفة ما بعد التوقف"""
    logger.info("إيقاف البوت...")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأخطاء العام"""
    logger.error(f"حدث خطأ أثناء معالجة التحديث: {context.error}")
    
    if update and update.effective_chat:
        try:
            await update.effective_chat.send_message(
                "❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى لاحقاً."
            )
        except Exception:
            pass

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # إنشاء تطبيق البوت
    application = ApplicationBuilder() \
        .token(Config.BOT_TOKEN) \
        .post_init(post_init) \
        .post_stop(post_stop) \
        .build()
    
    # إعداد معالجات الأوامر
    application = setup_handlers(application)
    
    # إعداد معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # بدء تشغيل البوت
    logger.info("بدأ تشغيل البوت...")
    application.run_polling()

if __name__ == "__main__":
    main()