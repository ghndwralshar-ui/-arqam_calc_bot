import os

# ==========================================
# إعدادات البوت الأساسية (من نسختك القديمة)
# ==========================================
BOT_TOKEN = "8850483932:AAEng210C30m9AEfyeb9lmzWAGKaZ2tkbQo"
ADMIN_ID = 6472852297
SUPPORT_USERNAME = "benti"

# ==========================================
# إعدادات قاعدة البيانات Supabase (الخاصة بقاعدتك القديمة لتستعيد الأرصدة)
# ==========================================
SUPABASE_URL = "https://odsrzvgjwvscsnlbkxgj.supabase.co"
SUPABASE_KEY = "sb_publishable_ylZ_VSULVrr_Lb7PA4G1fg_sy2ko5TJ"

# ==========================================
# إعدادات القنوات والروابط
# ==========================================
FORCED_CHANNEL_USERNAME = "@DigitalHubOrders"
FORCED_CHANNEL_URL = "https://t.me/DigitalHubOrders"
LOG_CHANNEL_ID = -1004374640175  # آيدي قناة السجلات الرقمي الصحيح

# ==========================================
# إعدادات المزودات (HMCARD & 5sim)
# ==========================================
FIVESIM_API_KEY = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MjE3OTQwNDQsImlhdCI6MTc5MDI1ODA0NCwicmF5IjoiZjQ5MGQ2ZDY1ZDk3YWQyYjI5YTZmMmZmMTA3MTE0YjMiLCJzdWIiOjQ1MjI3NTR9.a9hYtNcsLbGzOl-1lYckGNcywKS6K2GbjVvylCVAk6wRN2msqpd4P_iwjiSGhVRhgot5N_SBg7R-_g4WcwMFUQwOowZelELtux7Lc8fw_kMYXcSOtDPKuMY2O_w2kEEGQwITIIR98uUaQkv2r-obwBMvVfnUisJqVp93Qv_gg1f_if-Ogp7H0y9h-CdBBQqMNua-vMwV8-uN9LAJsz6hUkXrmOAG0WjRcdI2e5WiANF9w3wrAbJveP_b2J-JxSJKVs-T_oobDcmsadhlLpQB4hesY2sGyDSzD-KBFp18-PZsHPWVQ8pkNYRe5O4YAqaLACwbP3GOBsd518R7G_JOTA"

HMCARD_API_URL = "https://hmcard.online/api/v2"
HMCARD_API_KEY = "0c13f3ad91dc8c152e7cb01f87f1a271"

# ==========================================
# إعدادات الاتصال والـ Headers
# ==========================================
HEADERS = {
    'Authorization': f'Bearer {FIVESIM_API_KEY}',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
