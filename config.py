# ==========================================
# 💎 ملف إعدادات بوت ديجيتال هب (Digital Hub) 💎
# ==========================================

# 1. توكن البوت الجديد (محدث ونظيف 100%)
BOT_TOKEN = "8850483932:AAF-ZgsMtCi96OWybPL43ZQS2oeCmF72L68"

# 2. معلومات المشرف الأساسي والمالك
ADMIN_ID = 6542718105  # آيدي المالك الأساسي
SUPPORT_USERNAME = "benti"  # معرف الدعم

# 3. إعدادات القناة الإجبارية (محدثة على قناتك حصرياً)
FORCED_CHANNEL_USERNAME = "@DigitalHubOrders"
FORCED_CHANNEL_URL = "https://t.me/DigitalHubOrders"

# 4. قناة السجلات والطلبات
LOG_CHANNEL_ID = -1002425895743  # آيدي قناة السجلات

# 5. بيانات منصة HMCARD للرشق وشحن الألعاب
HMCARD_API_URL = "https://hmcard.net/api/v2"
HMCARD_API_KEY = "ضع_مفتاح_API_الخاص_بمنصة_hmcard_هنا"

# 6. بيانات ربط قاعدة البيانات السحابية (Supabase)
SUPABASE_URL = "https://your-supabase-url.supabase.co"
SUPABASE_KEY = "ضع_مفتاح_supabase_الخاص_بك_هنا"

# 7. مفتاح ربط خدمة قراءة الإيصالات (OCR)
OCR_SPACE_API_KEY = "K84447385288957"

# 8. إعدادات الاتصال بـ 5sim للأرقام الافتراضية
HEADERS = {
    "Authorization": "Bearer ضع_مفتاح_5sim_هنا",
    "Accept": "application/json"
}

# 9. قاموس الدول ومفاتيحها للأرقام الافتراضية
COUNTRY_INFO = {
    "russia": {"name_ar": "روسيا", "flag": "🇷🇺", "dial": "+7"},
    "usa": {"name_ar": "أمريكا", "flag": "🇺🇸", "dial": "+1"},
    "ukraine": {"name_ar": "أوكرانيا", "flag": "🇺🇦", "dial": "+380"},
    "kazakhstan": {"name_ar": "كازاخستان", "flag": "🇰🇿", "dial": "+7"},
    "indonesia": {"name_ar": "إندونيسيا", "flag": "🇮🇩", "dial": "+62"},
    "philippines": {"name_ar": "الفلبين", "flag": "🇵🇭", "dial": "+63"},
    "malaysia": {"name_ar": "ماليزيا", "flag": "🇲🇾", "dial": "+60"},
    "vietnam": {"name_ar": "فيتنام", "flag": "🇻🇳", "dial": "+84"},
    "kyrgyzstan": {"name_ar": "قيرغيزستان", "flag": "🇰🇬", "dial": "+996"},
    "usa_virtual": {"name_ar": "أمريكا (فوري)", "flag": "🇺🇸", "dial": "+1"},
    "egypt": {"name_ar": "مصر", "flag": "🇪🇬", "dial": "+20"},
    "iraq": {"name_ar": "العراق", "flag": "🇮🇶", "dial": "+964"},
    "morocco": {"name_ar": "المغرب", "flag": "🇲🇦", "dial": "+212"}
}
