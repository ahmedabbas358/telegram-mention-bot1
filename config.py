import os
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv()

# تحميل المتغيرات الأساسية
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS: List[int] = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
DB_URL = os.getenv("DB_URL", "sqlite:///bot_data.db")

# إعدادات الأداء
DEFAULT_BATCH_SIZE = int(os.getenv("DEFAULT_BATCH_SIZE", "7"))
MENTION_DELAY = float(os.getenv("MENTION_DELAY", "0.5"))
MENTION_FORMAT = os.getenv("MENTION_FORMAT", "username").lower()
MAX_MENTIONS_PER_DAY = int(os.getenv("MAX_MENTIONS_PER_DAY", "0"))

# إعدادات الأمان
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "4000"))
RATE_LIMIT_PER_USER = int(os.getenv("RATE_LIMIT_PER_USER", "3"))
RATE_LIMIT_PER_GROUP = int(os.getenv("RATE_LIMIT_PER_GROUP", "10"))

# إعدادات الجدولة
DEFAULT_MENTION_HOUR = int(os.getenv("DEFAULT_MENTION_HOUR", "9"))
DEFAULT_MENTION_MINUTE = int(os.getenv("DEFAULT_MENTION_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Riyadh")

# إعدادات التخزين المؤقت
CACHE_TIMEOUT = int(os.getenv("CACHE_TIMEOUT", "300"))

# إعدادات التخصيص
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ar")
SUPPORTED_LANGUAGES = ["ar", "en"]

# إعدادات الشبكة
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

# إعدادات السجل والتصحيح
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# إعدادات النسخ الاحتياطي
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "False").lower() == "true"
BACKUP_PATH = os.getenv("BACKUP_PATH", "backups")
BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL", "24"))

# إعدادات إضافية
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
MAX_GROUP_MEMBERS = int(os.getenv("MAX_GROUP_MEMBERS", "200"))