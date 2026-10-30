import os

# ==========================================
# إعدادات البوت الأساسية
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "7963283120:AAHq0iVq1B-4QJ4y_YQj9YQj9YQj9YQj9YQ")  # توكن البوت الخاص بك
ADMIN_ID = 7446545229  # آيدي المالك الأساسي للبوت

# ==========================================
# إعدادات القنوات والروابط
# ==========================================
FORCED_CHANNEL_USERNAME = "@DigitalHubOrders"  # معرف القناة للاشتراك الإجباري
FORCED_CHANNEL_URL = "https://t.me/DigitalHubOrders"  # رابط القناة
SUPPORT_USERNAME = "@DigitalHubOrders"  # معرف الدعم الفني

# آيدي قناة السجلات والإكتمالات (الرقمي الصريح الذي يبدأ بـ -100)
LOG_CHANNEL_ID = -1004374640175

# ==========================================
# إعدادات API موقع HMCARD (خدمات الرشق وشحن الألعاب)
# ==========================================
HMCARD_API_URL = "https://hmcard.net/api/v2"
HMCARD_API_KEY = "3aa88e0ab8be2a8c3e8006cdb505963b"  # مفتاح الـ API الخاص بك في موقع HMCARD

# ==========================================
# إعدادات الاتصال العامة و Headers
# ==========================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# ==========================================
# معلومات الدول والأرقام الافتراضية (5sim)
# ==========================================
COUNTRY_INFO = {
    "russia": {"name_ar": "روسيا", "flag": "🇷🇺", "dial": "+7"},
    "kazakhstan": {"name_ar": "كازاخستان", "flag": "🇰🇿", "dial": "+7"},
    "ukraine": {"name_ar": "أوكرانيا", "flag": "🇺🇦", "dial": "+380"},
    "philippines": {"name_ar": "الفلبين", "flag": "🇵🇭", "dial": "+63"},
    "malaysia": {"name_ar": "ماليزيا", "flag": "🇲🇾", "dial": "+60"},
    "indonesia": {"name_ar": "إندونيسيا", "flag": "🇮🇩", "dial": "+62"},
    "vietnam": {"name_ar": "فيتنام", "flag": "🇻🇳", "dial": "+84"},
    "kyrgyzstan": {"name_ar": "قيرغيزستان", "flag": "🇰🇬", "dial": "+996"},
    "usa": {"name_ar": "أمريكا", "flag": "🇺🇸", "dial": "+1"},
    "england": {"name_ar": "بريطانيا", "flag": "🇬🇧", "dial": "+44"},
    "brazil": {"name_ar": "البرازيل", "flag": "🇧🇷", "dial": "+55"},
    "india": {"name_ar": "الهند", "flag": "🇮🇳", "dial": "+91"},
    "egypt": {"name_ar": "مصر", "flag": "🇪🇬", "dial": "+20"},
    "iraq": {"name_ar": "العراق", "flag": "🇮🇶", "dial": "+964"},
    "yemen": {"name_ar": "اليمن", "flag": "🇾🇪", "dial": "+967"},
    "saudi": {"name_ar": "السعودية", "flag": "🇸🇦", "dial": "+966"}
}

STATIC_COUNTRIES = ["russia", "kazakhstan", "usa", "england", "egypt", "iraq"]
