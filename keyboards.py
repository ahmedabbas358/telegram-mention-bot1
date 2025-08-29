Lfrom telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    keyboard = [
        [InlineKeyboardButton("👥 ذكر الجميع", callback_data="mention_all")],
        [InlineKeyboardButton("⏰ جدولة الذكر", callback_data="scheduling")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

def scheduling_menu():
    keyboard = [
        [InlineKeyboardButton("🕒 تعيين وقت الذكر", callback_data="set_time")],
        [InlineKeyboardButton("🔔 تفعيل/تعطيل الجدولة", callback_data="toggle_scheduling")],
        [InlineKeyboardButton("↩️ العودة", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def settings_menu():
    keyboard = [
        [InlineKeyboardButton("📝 تخصيص الرسالة", callback_data="custom_message")],
        [InlineKeyboardButton("🛡 صلاحيات البوت", callback_data="check_permissions")],
        [InlineKeyboardButton("↩️ العودة", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def time_selection_menu(selected_hour=None, selected_minute=None):
    keyboard = []
    row = []
    
    if selected_hour is None:
        for h in range(0, 24):
            emoji = "🌙" if h < 6 else "☀️" if h < 12 else "🌞" if h < 18 else "🌜"
            row.append(InlineKeyboardButton(f"{emoji}{h:02d}", callback_data=f"hour_{h}")))
            if len(row) == 4:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("↩️ إلغاء", callback_data="scheduling")])
    elif selected_minute is None:
        for m in range(0, 60, 5):
            row.append(InlineKeyboardButton(f"{m:02d}", callback_data=f"minute_{selected_hour}_{m}")))
            if len(row) == 6:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("↩️ رجوع", callback_data="set_time")])
    else:
        keyboard = [
            [InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_time_{selected_hour}_{selected_minute}")],
            [InlineKeyboardButton("↩️ إعادة تعيين", callback_data="set_time")]
        ]
    return InlineKeyboardMarkup(keyboard)

def back_button_menu(target="main_menu"):
    keyboard = [[InlineKeyboardButton("↩️ العودة", callback_data=target)]]
    return InlineKeyboardMarkup(keyboard)

def group_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛡 تحقق من الصلاحيات", callback_data="check_permissions")],
        [InlineKeyboardButton("📊 تحديث معلومات المجموعة", callback_data="update_group_info")],
        [InlineKeyboardButton("↩️ القائمة الرئيسية", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def member_settings_menu():
    keyboard = [
        [InlineKeyboardButton("📝 تعديل بيانات العضو", callback_data="edit_member")],
        [InlineKeyboardButton("🛡 صلاحيات العضو", callback_data="check_member_permissions")],
        [InlineKeyboardButton("↩️ العودة", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def days_selection_menu(selected_days=None):
    keyboard = []
    row = []
    for d in range(1, 31):
        row.append(InlineKeyboardButton(f"{d} يوم", callback_data=f"day_{d}"))
        if len(row) == 6:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("↩️ رجوع", callback_data="scheduling")])
    return InlineKeyboardMarkup(keyboard)

def language_selection_menu():
    keyboard = [
        [InlineKeyboardButton("العربية", callback_data="set_lang_ar")],
        [InlineKeyboardButton("English", callback_data="set_lang_en")]
    ]
    return InlineKeyboardMarkup(keyboard)