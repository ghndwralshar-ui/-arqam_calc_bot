import os

# --- الإعدادات والبيانات الأساسية ---
BOT_TOKEN = "8850483932:AAEng210C30m9AEfyeb9lmzWAGKaZ2tkbQo"
FIVESIM_API_KEY = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MjE3OTQwNDQsImlhdCI6MTc5MDI1ODA0NCwicmF5IjoiZjQ5MGQ2ZDY1ZDk3YWQyYjI5YTZmMmZmMTA3MTE0YjMiLCJzdWIiOjQ1MjI3NTR9.a9hYtNcsLbGzOl-1lYckGNcywKS6K2GbjVvylCVAk6wRN2msqpd4P_iwjiSGhVRhgot5N_SBg7R-_g4WcwMFUQwOowZelELtux7Lc8fw_kMYXcSOtDPKuMY2O_w2kEEGQwITIIR98uUaQkv2r-obwBMvVfnUisJqVp93Qv_gg1f_if-Ogp7H0y9h-CdBBQqMNua-vMwV8-uN9LAJsz6hUkXrmOAG0WjRcdI2e5WiANF9w3wrAbJveP_b2J-JxSJKVs-T_oobDcmsadhlLpQB4hesY2sGyDSzD-KBFp18-PZsHPWVQ8pkNYRe5O4YAqaLACwbP3GOBsd518R7G_JOTA"
ADMIN_ID = 6472852297
SUPPORT_USERNAME = "benti"

FORCED_CHANNEL_USERNAME = "@DigitalHubOrders"
FORCED_CHANNEL_URL = "https://t.me/DigitalHubOrders"
LOG_CHANNEL_ID = "@DigitalHubOrders"

HMCARD_API_URL = "https://hmcard.online/api/v2"
HMCARD_API_KEY = "0c13f3ad91dc8c152e7cb01f87f1a271"

SUPABASE_URL = "https://odsrzvgjwvscsnlbkxgj.supabase.co"
SUPABASE_KEY = "sb_publishable_ylZ_VSULVrr_Lb7PA4G1fg_sy2ko5TJ"

HEADERS = {
    'Authorization': f'Bearer {FIVESIM_API_KEY}',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# قاموس الدول المعتمدة
COUNTRY_INFO = {
    "russia": {"name_ar": "روسيا", "flag": "🇷🇺", "dial": "+7"},
    "usa": {"name_ar": "أمريكا", "flag": "🇺🇸", "dial": "+1"},
    "uk": {"name_ar": "بريطانيا", "flag": "🇬🇧", "dial": "+44"},
    "india": {"name_ar": "الهند", "flag": "🇮🇳", "dial": "+91"},
    "indonesia": {"name_ar": "إندونيسيا", "flag": "🇮🇩", "dial": "+62"},
    "brazil": {"name_ar": "البرازيل", "flag": "🇧🇷", "dial": "+55"},
    "germany": {"name_ar": "ألمانيا", "flag": "🇩🇪", "dial": "+49"},
    "turkey": {"name_ar": "تركيا", "flag": "🇹🇷", "dial": "+90"},
    "ukraine": {"name_ar": "أوكرانيا", "flag": "🇺🇦", "dial": "+380"},
    "kazakhstan": {"name_ar": "كازاخستان", "flag": "🇰🇿", "dial": "+7"},
    "vietnam": {"name_ar": "فيتنام", "flag": "🇻🇳", "dial": "+84"},
    "philippines": {"name_ar": "الفلبين", "flag": "🇵🇭", "dial": "+63"},
    "poland": {"name_ar": "بولندا", "flag": "🇵🇱", "dial": "+48"},
    "colombia": {"name_ar": "كولومبيا", "flag": "🇨🇴", "dial": "+57"},
    "egypt": {"name_ar": "مصر", "flag": "🇪🇬", "dial": "+20"},
    "nigeria": {"name_ar": "نيجيريا", "flag": "🇳🇬", "dial": "+234"},
    "kenya": {"name_ar": "كينيا", "flag": "🇰🇪", "dial": "+254"},
    "southafrica": {"name_ar": "جنوب أفريقيا", "flag": "🇿🇦", "dial": "+27"},
    "myanmar": {"name_ar": "ميانمار", "flag": "🇲🇲", "dial": "+95"},
    "cambodia": {"name_ar": "كمبوديا", "flag": "🇰🇭", "dial": "+855"},
    "bangladesh": {"name_ar": "بنغلاديش", "flag": "🇧🇩", "dial": "+880"},
    "pakistan": {"name_ar": "باكستان", "flag": "🇵🇰", "dial": "+92"},
    "malaysia": {"name_ar": "ماليزيا", "flag": "🇲🇾", "dial": "+60"},
    "thailand": {"name_ar": "تايلاند", "flag": "🇹🇭", "dial": "+66"},
    "mexico": {"name_ar": "المكسيك", "flag": "🇲🇽", "dial": "+52"},
    "spain": {"name_ar": "إسبانيا", "flag": "🇪🇸", "dial": "+34"},
    "france": {"name_ar": "فرنسا", "flag": "🇫🇷", "dial": "+33"},
    "italy": {"name_ar": "إيطاليا", "flag": "🇮🇹", "dial": "+39"},
    "canada": {"name_ar": "كندا", "flag": "🇨🇦", "dial": "+1"},
    "yemen": {"name_ar": "اليمن", "flag": "🇾🇪", "dial": "+967"}
}

STATIC_COUNTRIES = [{"code": k, **v} for k, v in COUNTRY_INFO
