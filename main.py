import logging
import asyncio
import httpx
from datetime import datetime, timedelta
from supabase import create_client, Client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)

# --- الإعدادات والبيانات الأساسية ---
BOT_TOKEN = "8850483932:AAGlQmf6SfauVpyGY4i7d14IhjPi29tu_fg"
FIVESIM_API_KEY = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MjE3OTQwNDQsImlhdCI6MTc5MDI1ODA0NCwicmF5IjoiZjQ5MGQ2ZDY1ZDk3YWQyYjI5YTZmMmZmMTA3MTE0YjMiLCJzdWIiOjQ1MjI3NTR9.a9hYtNcsLbGzOl-1lYckGNcywKS6K2GbjVvylCVAk6wRN2msqpd4P_iwjiSGhVRhgot5N_SBg7R-_g4WcwMFUQwOowZelELtux7Lc8fw_kMYXcSOtDPKuMY2O_w2kEEGQwITIIR98uUaQkv2r-obwBMvVfnUisJqVp93Qv_gg1f_if-Ogp7H0y9h-CdBBQqMNua-vMwV8-uN9LAJsz6hUkXrmOAG0WjRcdI2e5WiANF9w3wrAbJveP_b2J-JxSJKVs-T_oobDcmsadhlLpQB4hesY2sGyDSzD-KBFp18-PZsHPWVQ8pkNYRe5O4YAqaLACwbP3GOBsd518R7G_JOTA"
ADMIN_ID = 6472852297
SUPPORT_USERNAME = "benti"

LOG_CHANNEL_ID = "@DigitalHubOrders"

HMCARD_API_URL = "https://hmcard.online/api/v2"
HMCARD_API_KEY = "6e568032e93df81068eadaae1175e589"

SUPABASE_URL = "https://odsrzvgjwvscsnlbkxgj.supabase.co"
SUPABASE_KEY = "sb_publishable_ylZ_VSULVrr_Lb7PA4G1fg_sy2ko5TJ"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    'Authorization': f'Bearer {FIVESIM_API_KEY}',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

admin_state = {}

def init_db():
    print("🟢 قاعدة البيانات السحابية (Supabase) متصلة وجاهزة بنجاح!")

def db_get_user(user_id):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        rows = res.data if hasattr(res, 'data') else []
        if not rows:
            all_res = supabase.table("users").select("user_sequence").execute()
            all_u = all_res.data if hasattr(all_res, 'data') else []
            max_seq = max([r.get("user_sequence", 0) for r in all_u]) if all_u else 0
            new_seq = max_seq + 1

            new_data = {
                "user_id": user_id,
                "balance": 0.0,
                "referrals": 0,
                "referred_by": 0,
                "joined_date": now_str,
                "is_banned": 0,
                "user_sequence": new_seq
            }
            supabase.table("users").insert(new_data).execute()
            return {"balance": 0.0, "referrals": 0, "referred_by": 0, "is_banned": 0, "user_sequence": new_seq, "is_really_new": True}
        
        row = rows[0]
        return {
            "balance": float(row.get("balance", 0.0)),
            "referrals": int(row.get("referrals", 0)),
            "referred_by": int(row.get("referred_by", 0)),
            "is_banned": int(row.get("is_banned", 0)),
            "user_sequence": int(row.get("user_sequence", 1)),
            "is_really_new": False
        }
    except Exception as e:
        print(f"db_get_user Error: {e}")
        return {"balance": 0.0, "referrals": 0, "referred_by": 0, "is_banned": 0, "user_sequence": 1, "is_really_new": False}

def db_update_balance(user_id, amount, mode="add"):
    u = db_get_user(user_id)
    current_bal = float(u.get("balance", 0.0))
    if mode == "add":
        new_bal = current_bal + float(amount)
    elif mode == "deduct":
        new_bal = max(0.0, current_bal - float(amount))
    else:
        new_bal = current_bal

    try:
        supabase.table("users").update({"balance": new_bal}).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"db_update_balance Error: {e}")

def db_add_referral_record(new_user_id, referrer_id):
    try:
        res = supabase.table("users").select("referred_by").eq("user_id", new_user_id).execute()
        rows = res.data if hasattr(res, 'data') else []
        if rows and rows[0].get("referred_by", 0) == 0:
            supabase.table("users").update({"referred_by": referrer_id}).eq("user_id", new_user_id).execute()
            ref_info = supabase.table("users").select("referrals").eq("user_id", referrer_id).execute()
            ref_rows = ref_info.data if hasattr(ref_info, 'data') else []
            current_refs = ref_rows[0].get("referrals", 0) if ref_rows else 0
            supabase.table("users").update({"referrals": current_refs + 1}).eq("user_id", referrer_id).execute()
            return True
    except Exception as e:
        print(f"db_add_referral_record Error: {e}")
    return False

def db_get_advanced_stats():
    try:
        res = supabase.table("users").select("*").execute()
        users = res.data if hasattr(res, 'data') else []
        total_users = len(users)
        total_balances = sum(float(u.get("balance", 0.0)) for u in users)
        total_referrals = sum(int(u.get("referrals", 0)) for u in users)

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        new_24h = sum(1 for u in users if u.get("joined_date", "") >= yesterday)

        sorted_users = sorted(users, key=lambda x: x.get("referrals", 0), reverse=True)
        top_refs = [(u["user_id"], u["referrals"]) for u in sorted_users[:5] if u.get("referrals", 0) > 0]

        return {"total_users": total_users, "total_balances": total_balances, "total_referrals": total_referrals, "new_24h": new_24h, "top_refs": top_refs}
    except Exception as e:
        print(f"db_get_advanced_stats Error: {e}")
        return {"total_users": 0, "total_balances": 0, "total_referrals": 0, "new_24h": 0, "top_refs": []}

def db_get_all_users():
    try:
        res = supabase.table("users").select("user_id").eq("is_banned", 0).execute()
        rows = res.data if hasattr(res, 'data') else []
        return [row["user_id"] for row in rows] if rows else []
    except Exception:
        return []

def is_admin_or_sub(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        res = supabase.table("sub_admins").select("admin_id").eq("admin_id", user_id).execute()
        rows = res.data if hasattr(res, 'data') else []
        return len(rows) > 0
    except Exception:
        return False

def get_all_sub_admins():
    try:
        res = supabase.table("sub_admins").select("admin_id").execute()
        rows = res.data if hasattr(res, 'data') else []
        return [row["admin_id"] for row in rows] if rows else []
    except Exception:
        return []

def get_forced_channels():
    try:
        res = supabase.table("forced_channels").select("channel_username, channel_title").execute()
        rows = res.data if hasattr(res, 'data') else []
        return [(row["channel_username"], row["channel_title"]) for row in rows] if rows else []
    except Exception:
        return []

async def check_forced_subscription(user_id, bot):
    channels = get_forced_channels()
    if not channels:
        return True, []
    
    not_subscribed = []
    for ch_username, ch_title in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_username, user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append((ch_username, ch_title))
        except Exception:
            not_subscribed.append((ch_username, ch_title or ch_username))
            
    if not_subscribed:
        return False, not_subscribed
    return True, []

def mult_price(price: float) -> float:
    return round(price * 3.0, 2)

def mask_link(link: str) -> str:
    if not link:
        return "لا يوجد رابط"
    length = len(link)
    if length <= 10:
        return link[:3] + "..."
    half = length // 2
    return link[:half] + "..."

WHATSAPP_DEALS = [
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": mult_price(0.50)},
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": mult_price(0.50)},
    {"code": "pakistan", "name_ar": "باكستان 🇵🇰", "price": mult_price(0.55)},
    {"code": "bangladesh", "name_ar": "بنغلاديش 🇧🇩", "price": mult_price(0.55)},
    {"code": "india", "name_ar": "الهند 🇮🇳", "price": mult_price(0.60)},
    {"code": "vietnam", "name_ar": "فيتنام 🇻🇳", "price": mult_price(0.60)},
    {"code": "ethiopia", "name_ar": "إثيوبيا 🇪🇹", "price": mult_price(0.60)},
    {"code": "egypt", "name_ar": "مصر 🇪🇬", "price": mult_price(0.70)}
]

TELEGRAM_DEALS = [
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": mult_price(0.65)},
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": mult_price(0.65)},
    {"code": "pakistan", "name_ar": "باكستان 🇵🇰", "price": mult_price(0.70)},
    {"code": "bangladesh", "name_ar": "بنغلاديش 🇧🇩", "price": mult_price(0.70)},
    {"code": "india", "name_ar": "الهند 🇮🇳", "price": mult_price(0.75)},
    {"code": "russia", "name_ar": "روسيا 🇷🇺", "price": mult_price(0.80)},
    {"code": "ethiopia", "name_ar": "إثيوبيا 🇪🇹", "price": mult_price(0.75)},
    {"code": "vietnam", "name_ar": "فيتنام 🇻🇳", "price": mult_price(0.75)}
]

ARAB_COUNTRIES = [
    {"code": "yemen", "name_ar": "اليمن 🇾🇪", "price": mult_price(1.00)},
    {"code": "saudiarabia", "name_ar": "السعودية 🇸🇦", "price": mult_price(1.80)},
    {"code": "uae", "name_ar": "الإمارات 🇦🇪", "price": mult_price(1.80)},
    {"code": "qatar", "name_ar": "قطر 🇶🇦", "price": mult_price(1.80)},
    {"code": "kuwait", "name_ar": "الكويت 🇰🇼", "price": mult_price(1.80)},
    {"code": "bahrain", "name_ar": "البحرين 🇧🇭", "price": mult_price(1.40)},
    {"code": "oman", "name_ar": "عمان 🇴🇲", "price": mult_price(1.40)},
    {"code": "iraq", "name_ar": "العراق 🇮🇶", "price": mult_price(1.40)},
    {"code": "syria", "name_ar": "سوريا 🇸🇾", "price": mult_price(1.30)},
    {"code": "lebanon", "name_ar": "لبنان 🇱🇧", "price": mult_price(1.40)},
    {"code": "jordan", "name_ar": "الأردن 🇯🇴", "price": mult_price(1.30)},
    {"code": "palestine", "name_ar": "فلسطين 🇵🇸", "price": mult_price(1.40)},
    {"code": "egypt", "name_ar": "مصر 🇪🇬", "price": mult_price(0.90)},
    {"code": "sudan", "name_ar": "السودان 🇸🇩", "price": mult_price(1.10)},
    {"code": "libya", "name_ar": "ليبيا 🇱🇾", "price": mult_price(1.30)},
    {"code": "tunisia", "name_ar": "تونس 🇹🇳", "price": mult_price(1.20)},
    {"code": "algeria", "name_ar": "الجزائر 🇩🇿", "price": mult_price(1.10)},
    {"code": "morocco", "name_ar": "المغرب 🇲🇦", "price": mult_price(0.90)},
    {"code": "mauritania", "name_ar": "موريتانيا 🇲🇷", "price": mult_price(1.10)},
    {"code": "somalia", "name_ar": "الصومال 🇸🇴", "price": mult_price(1.10)},
    {"code": "djibouti", "name_ar": "جيبوتي 🇩🇯", "price": mult_price(1.10)},
    {"code": "comoros", "name_ar": "جزر القمر 🇰🇲", "price": mult_price(1.10)}
]

WHATSAPP_FOREIGN = [
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": mult_price(0.70)},
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": mult_price(0.70)},
    {"code": "pakistan", "name_ar": "باكستان 🇵🇰", "price": mult_price(0.70)},
    {"code": "bangladesh", "name_ar": "بنغلاديش 🇧🇩", "price": mult_price(0.70)},
    {"code": "ethiopia", "name_ar": "إثيوبيا 🇪🇹", "price": mult_price(0.80)},
    {"code": "india", "name_ar": "الهند 🇮🇳", "price": mult_price(0.80)},
    {"code": "thailand", "name_ar": "تايلاند 🇹🇭", "price": mult_price(0.80)},
    {"code": "vietnam", "name_ar": "فيتنام 🇻🇳", "price": mult_price(0.80)},
    {"code": "brazil", "name_ar": "البرازيل 🇧🇷", "price": mult_price(0.90)},
    {"code": "russia", "name_ar": "روسيا 🇷🇺", "price": mult_price(0.90)},
    {"code": "nigeria", "name_ar": "نيجيريا 🇳🇬", "price": mult_price(0.90)},
    {"code": "peru", "name_ar": "بيرو 🇵🇪", "price": mult_price(0.90)},
    {"code": "colombia", "name_ar": "كولومبيا 🇨🇴", "price": mult_price(0.85)},
    {"code": "argentina", "name_ar": "الأرجنتين 🇦🇷", "price": mult_price(0.85)},
    {"code": "kenya", "name_ar": "كينيا 🇰🇪", "price": mult_price(0.95)},
    {"code": "tanzania", "name_ar": "تنزانيا 🇹🇿", "price": mult_price(0.95)},
    {"code": "uganda", "name_ar": "أوغندا 🇺🇬", "price": mult_price(0.95)},
    {"code": "ghana", "name_ar": "غانا 🇬🇭", "price": mult_price(0.95)},
    {"code": "ukraine", "name_ar": "أوكرانيا 🇺🇦", "price": mult_price(1.00)},
    {"code": "kazakhstan", "name_ar": "كازاخستان 🇰🇿", "price": mult_price(0.95)},
    {"code": "kyrgyzstan", "name_ar": "قرغيزستان 🇰🇬", "price": mult_price(0.95)},
    {"code": "uzbekistan", "name_ar": "أوزبكستان 🇺🇿", "price": mult_price(0.95)},
    {"code": "malaysia", "name_ar": "ماليزيا 🇲🇾", "price": mult_price(1.10)},
    {"code": "china", "name_ar": "الصين 🇨🇳", "price": mult_price(1.20)},
    {"code": "turkey", "name_ar": "تركيا 🇹🇷", "price": mult_price(1.40)},
    {"code": "germany", "name_ar": "ألمانيا 🇩🇪", "price": mult_price(1.60)},
    {"code": "france", "name_ar": "فرنسا 🇫🇷", "price": mult_price(1.60)},
    {"code": "italy", "name_ar": "إيطاليا 🇮🇹", "price": mult_price(1.50)},
    {"code": "spain", "name_ar": "إسبانيا 🇪🇸", "price": mult_price(1.50)},
    {"code": "uk", "name_ar": "بريطانيا 🇬🇧", "price": mult_price(1.70)},
    {"code": "canada", "name_ar": "كندا 🇨🇦", "price": mult_price(1.60)},
    {"code": "usa", "name_ar": "أمريكا 🇺🇸", "price": mult_price(1.80)}
]

TELEGRAM_COUNTRIES = [
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": mult_price(0.95)},
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": mult_price(0.95)},
    {"code": "russia", "name_ar": "روسيا 🇷🇺", "price": mult_price(1.10)},
    {"code": "india", "name_ar": "الهند 🇮🇳", "price": mult_price(1.00)},
    {"code": "pakistan", "name_ar": "باكستان 🇵🇰", "price": mult_price(0.90)},
    {"code": "bangladesh", "name_ar": "بنغلاديش 🇧🇩", "price": mult_price(0.90)},
    {"code": "ethiopia", "name_ar": "إثيوبيا 🇪🇹", "price": mult_price(0.95)},
    {"code": "vietnam", "name_ar": "فيتنام 🇻🇳", "price": mult_price(0.95)},
    {"code": "egypt", "name_ar": "مصر 🇪🇬", "price": mult_price(1.10)},
    {"code": "brazil", "name_ar": "البرازيل 🇧🇷", "price": mult_price(1.20)},
    {"code": "nigeria", "name_ar": "نيجيريا 🇳🇬", "price": mult_price(1.10)},
    {"code": "peru", "name_ar": "بيرو 🇵🇪", "price": mult_price(1.10)},
    {"code": "colombia", "name_ar": "كولومبيا 🇨🇴", "price": mult_price(1.05)},
    {"code": "argentina", "name_ar": "الأرجنتين 🇦🇷", "price": mult_price(1.05)},
    {"code": "kenya", "name_ar": "كينيا 🇰🇪", "price": mult_price(1.15)},
    {"code": "tanzania", "name_ar": "تنزانيا 🇹🇿", "price": mult_price(1.15)},
    {"code": "uganda", "name_ar": "أوغندا 🇺🇬", "price": mult_price(1.15)},
    {"code": "ghana", "name_ar": "غانا 🇬🇭", "price": mult_price(1.15)},
    {"code": "ukraine", "name_ar": "أوكرانيا 🇺🇦", "price": mult_price(1.25)},
    {"code": "kazakhstan", "name_ar": "كازاخستان 🇰🇿", "price": mult_price(1.20)},
    {"code": "kyrgyzstan", "name_ar": "قرغيزستان 🇰🇬", "price": mult_price(1.20)},
    {"code": "uzbekistan", "name_ar": "أوزبكستان 🇺🇿", "price": mult_price(1.20)},
    {"code": "malaysia", "name_ar": "ماليزيا 🇲🇾", "price": mult_price(1.35)},
    {"code": "china", "name_ar": "الصين 🇨🇳", "price": mult_price(1.45)},
    {"code": "turkey", "name_ar": "تركيا 🇹🇷", "price": mult_price(1.60)},
    {"code": "germany", "name_ar": "ألمانيا 🇩🇪", "price": mult_price(1.90)},
    {"code": "france", "name_ar": "فرنسا 🇫🇷", "price": mult_price(1.90)},
    {"code": "italy", "name_ar": "إيطاليا 🇮🇹", "price": mult_price(1.80)},
    {"code": "spain", "name_ar": "إسبانيا 🇪🇸", "price": mult_price(1.80)},
    {"code": "uk", "name_ar": "بريطانيا 🇬🇧", "price": mult_price(2.00)},
    {"code": "canada", "name_ar": "كندا 🇨🇦", "price": mult_price(1.90)},
    {"code": "usa", "name_ar": "أمريكا 🇺🇸", "price": mult_price(2.20)}
]

INSTAGRAM_COUNTRIES = [
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": mult_price(0.60)},
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": mult_price(0.60)},
    {"code": "pakistan", "name_ar": "باكستان 🇵🇰", "price": mult_price(0.60)},
    {"code": "bangladesh", "name_ar": "بنغلاديش 🇧🇩", "price": mult_price(0.60)},
    {"code": "ethiopia", "name_ar": "إثيوبيا 🇪🇹", "price": mult_price(0.65)},
    {"code": "india", "name_ar": "الهند 🇮🇳", "price": mult_price(0.70)},
    {"code": "thailand", "name_ar": "تايلاند 🇹🇭", "price": mult_price(0.70)},
    {"code": "vietnam", "name_ar": "فيتنام 🇻🇳", "price": mult_price(0.70)},
    {"code": "russia", "name_ar": "روسيا 🇷🇺", "price": mult_price(0.75)},
    {"code": "egypt", "name_ar": "مصر 🇪🇬", "price": mult_price(0.75)},
    {"code": "brazil", "name_ar": "البرازيل 🇧🇷", "price": mult_price(0.80)},
    {"code": "nigeria", "name_ar": "نيجيريا 🇳🇬", "price": mult_price(0.75)},
    {"code": "peru", "name_ar": "بيرو 🇵🇪", "price": mult_price(0.75)},
    {"code": "colombia", "name_ar": "كولومبيا 🇨🇴", "price": mult_price(0.70)},
    {"code": "argentina", "name_ar": "الأرجنتين 🇦🇷", "price": mult_price(0.70)},
    {"code": "kenya", "name_ar": "كينيا 🇰🇪", "price": mult_price(0.80)},
    {"code": "tanzania", "name_ar": "تنزانيا 🇹🇿", "price": mult_price(0.80)},
    {"code": "uganda", "name_ar": "أوغندا 🇺🇬", "price": mult_price(0.80)},
    {"code": "ghana", "name_ar": "غانا 🇬🇭", "price": mult_price(0.80)},
    {"code": "ukraine", "name_ar": "أوكرانيا 🇺🇦", "price": mult_price(0.85)},
    {"code": "kazakhstan", "name_ar": "كازاخستان 🇰🇿", "price": mult_price(0.80)},
    {"code": "kyrgyzstan", "name_ar": "قرغيزستان 🇰🇬", "price": mult_price(0.80)},
    {"code": "uzbekistan", "name_ar": "أوزبكستان 🇺🇿", "price": mult_price(0.80)},
    {"code": "malaysia", "name_ar": "ماليزيا 🇲🇾", "price": mult_price(0.95)},
    {"code": "china", "name_ar": "الصين 🇨🇳", "price": mult_price(1.00)},
    {"code": "turkey", "name_ar": "تركيا 🇹🇷", "price": mult_price(1.10)},
    {"code": "germany", "name_ar": "ألمانيا 🇩🇪", "price": mult_price(1.30)},
    {"code": "france", "name_ar": "فرنسا 🇫🇷", "price": mult_price(1.30)},
    {"code": "italy", "name_ar": "إيطاليا 🇮🇹", "price": mult_price(1.20)},
    {"code": "spain", "name_ar": "إسبانيا 🇪🇸", "price": mult_price(1.20)},
    {"code": "uk", "name_ar": "بريطانيا 🇬🇧", "price": mult_price(1.40)},
    {"code": "usa", "name_ar": "أمريكا 🇺🇸", "price": mult_price(1.50)}
]

FACEBOOK_COUNTRIES = [
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": mult_price(0.65)},
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": mult_price(0.65)},
    {"code": "pakistan", "name_ar": "باكستان 🇵🇰", "price": mult_price(0.65)},
    {"code": "bangladesh", "name_ar": "بنغلاديش 🇧🇩", "price": mult_price(0.65)},
    {"code": "ethiopia", "name_ar": "إثيوبيا 🇪🇹", "price": mult_price(0.70)},
    {"code": "india", "name_ar": "الهند 🇮🇳", "price": mult_price(0.75)},
    {"code": "thailand", "name_ar": "تايلاند 🇹🇭", "price": mult_price(0.75)},
    {"code": "vietnam", "name_ar": "فيتنام 🇻🇳", "price": mult_price(0.75)},
    {"code": "russia", "name_ar": "روسيا 🇷🇺", "price": mult_price(0.80)},
    {"code": "egypt", "name_ar": "مصر 🇪🇬", "price": mult_price(0.75)},
    {"code": "brazil", "name_ar": "البرازيل 🇧🇷", "price": mult_price(0.85)},
    {"code": "nigeria", "name_ar": "نيجيريا 🇳🇬", "price": mult_price(0.80)},
    {"code": "peru", "name_ar": "بيرو 🇵🇪", "price": mult_price(0.80)},
    {"code": "colombia", "name_ar": "كولومبيا 🇨🇴", "price": mult_price(0.75)},
    {"code": "argentina", "name_ar": "الأرجنتين 🇦🇷", "price": mult_price(0.75)},
    {"code": "kenya", "name_ar": "كينيا 🇰🇪", "price": mult_price(0.85)},
    {"code": "tanzania", "name_ar": "تنزانيا 🇹🇿", "price": mult_price(0.85)},
    {"code": "uganda", "name_ar": "أوغندا 🇺🇬", "price": mult_price(0.85)},
    {"code": "ghana", "name_ar": "غانا 🇬🇭", "price": mult_price(0.85)},
    {"code": "ukraine", "name_ar": "أوكرانيا 🇺🇦", "price": mult_price(0.90)},
    {"code": "kazakhstan", "name_ar": "كازاخستان 🇰🇿", "price": mult_price(0.85)},
    {"code": "kyrgyzstan", "name_ar": "قرغيزستان 🇰🇬", "price": mult_price(0.85)},
    {"code": "uzbekistan", "name_ar": "أوزبكستان 🇺🇿", "price": mult_price(0.85)},
    {"code": "malaysia", "name_ar": "ماليزيا 🇲🇾", "price": mult_price(1.00)},
    {"code": "china", "name_ar": "الصين 🇨🇳", "price": mult_price(1.10)},
    {"code": "turkey", "name_ar": "تركيا 🇹🇷", "price": mult_price(1.20)},
    {"code": "germany", "name_ar": "ألمانيا 🇩🇪", "price": mult_price(1.40)},
    {"code": "france", "name_ar": "فرنسا 🇫🇷", "price": mult_price(1.40)},
    {"code": "italy", "name_ar": "إيطاليا 🇮🇹", "price": mult_price(1.30)},
    {"code": "spain", "name_ar": "إسبانيا 🇪🇸", "price": mult_price(1.30)},
    {"code": "uk", "name_ar": "بريطانيا 🇬🇧", "price": mult_price(1.50)},
    {"code": "usa", "name_ar": "أمريكا 🇺🇸", "price": mult_price(1.60)}
]

TWITTER_COUNTRIES = [
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": mult_price(0.80)},
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": mult_price(0.80)},
    {"code": "pakistan", "name_ar": "باكستان 🇵🇰", "price": mult_price(0.80)},
    {"code": "bangladesh", "name_ar": "بنغلاديش 🇧🇩", "price": mult_price(0.80)},
    {"code": "ethiopia", "name_ar": "إثيوبيا 🇪🇹", "price": mult_price(0.85)},
    {"code": "india", "name_ar": "الهند 🇮🇳", "price": mult_price(0.90)},
    {"code": "thailand", "name_ar": "تايلاند 🇹🇭", "price": mult_price(0.90)},
    {"code": "vietnam", "name_ar": "فيتنام 🇻🇳", "price": mult_price(0.90)},
    {"code": "russia", "name_ar": "روسيا 🇷🇺", "price": mult_price(0.95)},
    {"code": "egypt", "name_ar": "مصر 🇪🇬", "price": mult_price(0.95)},
    {"code": "brazil", "name_ar": "البرازيل 🇧🇷", "price": mult_price(1.00)},
    {"code": "nigeria", "name_ar": "نيجيريا 🇳🇬", "price": mult_price(0.95)},
    {"code": "peru", "name_ar": "بيرو 🇵🇪", "price": mult_price(0.95)},
    {"code": "colombia", "name_ar": "كولومبيا 🇨🇴", "price": mult_price(0.90)},
    {"code": "argentina", "name_ar": "الأرجنتين 🇦🇷", "price": mult_price(0.90)},
    {"code": "kenya", "name_ar": "كينيا 🇰🇪", "price": mult_price(1.00)},
    {"code": "tanzania", "name_ar": "تنزانيا 🇹🇿", "price": mult_price(1.00)},
    {"code": "uganda", "name_ar": "أوغندا 🇺🇬", "price": mult_price(1.00)},
    {"code": "ghana", "name_ar": "غانا 🇬🇭", "price": mult_price(1.00)},
    {"code": "ukraine", "name_ar": "أوكرانيا 🇺🇦", "price": mult_price(1.10)},
    {"code": "kazakhstan", "name_ar": "كازاخستان 🇰🇿", "price": mult_price(1.05)},
    {"code": "kyrgyzstan", "name_ar": "قرغيزستان 🇰🇬", "price": mult_price(1.05)},
    {"code": "uzbekistan", "name_ar": "أوزبكستان 🇺🇿", "price": mult_price(1.05)},
    {"code": "malaysia", "name_ar": "ماليزيا 🇲🇾", "price": mult_price(1.20)},
    {"code": "china", "name_ar": "الصين 🇨🇳", "price": mult_price(1.30)},
    {"code": "turkey", "name_ar": "تركيا 🇹🇷", "price": mult_price(1.40)},
    {"code": "germany", "name_ar": "ألمانيا 🇩🇪", "price": mult_price(1.60)},
    {"code": "france", "name_ar": "فرنسا 🇫🇷", "price": mult_price(1.60)},
    {"code": "italy", "name_ar": "إيطاليا 🇮🇹", "price": mult_price(1.50)},
    {"code": "spain", "name_ar": "إسبانيا 🇪🇸", "price": mult_price(1.50)},
    {"code": "uk", "name_ar": "بريطانيا 🇬🇧", "price": mult_price(1.70)},
    {"code": "usa", "name_ar": "أمريكا 🇺🇸", "price": mult_price(1.90)}
]

TIKTOK_COUNTRIES = [
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": mult_price(0.70)},
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": mult_price(0.70)},
    {"code": "pakistan", "name_ar": "باكستان 🇵🇰", "price": mult_price(0.70)},
    {"code": "bangladesh", "name_ar": "بنغلاديش 🇧🇩", "price": mult_price(0.70)},
    {"code": "ethiopia", "name_ar": "إثيوبيا 🇪🇹", "price": mult_price(0.75)},
    {"code": "india", "name_ar": "الهند 🇮🇳", "price": mult_price(0.80)},
    {"code": "thailand", "name_ar": "تايلاند 🇹🇭", "price": mult_price(0.80)},
    {"code": "vietnam", "name_ar": "فيتنام 🇻🇳", "price": mult_price(0.80)},
    {"code": "russia", "name_ar": "روسيا 🇷🇺", "price": mult_price(0.85)},
    {"code": "egypt", "name_ar": "مصر 🇪🇬", "price": mult_price(0.85)},
    {"code": "brazil", "name_ar": "البرازيل 🇧🇷", "price": mult_price(0.90)},
    {"code": "nigeria", "name_ar": "نيجيريا 🇳🇬", "price": mult_price(0.85)},
    {"code": "peru", "name_ar": "بيرو 🇵🇪", "price": mult_price(0.85)},
    {"code": "colombia", "name_ar": "كولومبيا 🇨🇴", "price": mult_price(0.80)},
    {"code": "argentina", "name_ar": "الأرجنتين 🇦🇷", "price": mult_price(0.80)},
    {"code": "kenya", "name_ar": "كينيا 🇰🇪", "price": mult_price(0.90)},
    {"code": "tanzania", "name_ar": "تنزانيا 🇹🇿", "price": mult_price(0.90)},
    {"code": "uganda", "name_ar": "أوغندا 🇺🇬", "price": mult_price(0.90)},
    {"code": "ghana", "name_ar": "غانا 🇬🇭", "price": mult_price(0.90)},
    {"code": "ukraine", "name_ar": "أوكرانيا 🇺🇦", "price": mult_price(0.95)},
    {"code": "kazakhstan", "name_ar": "كازاخستان 🇰🇿", "price": mult_price(0.90)},
    {"code": "kyrgyzstan", "name_ar": "قرغيزستان 🇰🇬", "price": mult_price(0.90)},
    {"code": "uzbekistan", "name_ar": "أوزبكستان 🇺🇿", "price": mult_price(0.90)},
    {"code": "malaysia", "name_ar": "ماليزيا 🇲🇾", "price": mult_price(1.05)},
    {"code": "china", "name_ar": "الصين 🇨🇳", "price": mult_price(1.15)},
    {"code": "turkey", "name_ar": "تركيا 🇹🇷", "price": mult_price(1.25)},
    {"code": "germany", "name_ar": "ألمانيا 🇩🇪", "price": mult_price(1.45)},
    {"code": "france", "name_ar": "فرنسا 🇫🇷", "price": mult_price(1.45)},
    {"code": "italy", "name_ar": "إيطاليا 🇮🇹", "price": mult_price(1.35)},
    {"code": "spain", "name_ar": "إسبانيا 🇪🇸", "price": mult_price(1.35)},
    {"code": "uk", "name_ar": "بريطانيا 🇬🇧", "price": mult_price(1.55)},
    {"code": "usa", "name_ar": "أمريكا 🇺🇸", "price": mult_price(1.60)}
]

SNAP_IMO_COUNTRIES = [
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": mult_price(0.85)},
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": mult_price(0.85)},
    {"code": "pakistan", "name_ar": "باكستان 🇵🇰", "price": mult_price(0.85)},
    {"code": "bangladesh", "name_ar": "بنغلاديش 🇧🇩", "price": mult_price(0.85)},
    {"code": "ethiopia", "name_ar": "إثيوبيا 🇪🇹", "price": mult_price(0.90)},
    {"code": "india", "name_ar": "الهند 🇮🇳", "price": mult_price(0.95)},
    {"code": "thailand", "name_ar": "تايلاند 🇹🇭", "price": mult_price(0.95)},
    {"code": "vietnam", "name_ar": "فيتنام 🇻🇳", "price": mult_price(0.95)},
    {"code": "russia", "name_ar": "روسيا 🇷🇺", "price": mult_price(1.00)},
    {"code": "egypt", "name_ar": "مصر 🇪🇬", "price": mult_price(1.00)},
    {"code": "brazil", "name_ar": "البرازيل 🇧🇷", "price": mult_price(1.10)},
    {"code": "nigeria", "name_ar": "نيجيريا 🇳🇬", "price": mult_price(1.05)},
    {"code": "peru", "name_ar": "بيرو 🇵🇪", "price": mult_price(1.05)},
    {"code": "colombia", "name_ar": "كولومبيا 🇨🇴", "price": mult_price(1.00)},
    {"code": "argentina", "name_ar": "الأرجنتين 🇦🇷", "price": mult_price(1.00)},
    {"code": "kenya", "name_ar": "كينيا 🇰🇪", "price": mult_price(1.10)},
    {"code": "tanzania", "name_ar": "تنزانيا 🇹🇿", "price": mult_price(1.10)},
    {"code": "uganda", "name_ar": "أوغندا 🇺🇬", "price": mult_price(1.10)},
    {"code": "ghana", "name_ar": "غانا 🇬🇭", "price": mult_price(1.10)},
    {"code": "ukraine", "name_ar": "أوكرانيا 🇺🇦", "price": mult_price(1.20)},
    {"code": "kazakhstan", "name_ar": "كازاخستان 🇰🇿", "price": mult_price(1.15)},
    {"code": "kyrgyzstan", "name_ar": "قرغيزستان 🇰🇬", "price": mult_price(1.15)},
    {"code": "uzbekistan", "name_ar": "أوزبكستان 🇺🇿", "price": mult_price(1.15)},
    {"code": "malaysia", "name_ar": "ماليزيا 🇲🇾", "price": mult_price(1.30)},
    {"code": "china", "name_ar": "الصين 🇨🇳", "price": mult_price(1.40)},
    {"code": "turkey", "name_ar": "تركيا 🇹🇷", "price": mult_price(1.50)},
    {"code": "germany", "name_ar": "ألمانيا 🇩🇪", "price": mult_price(1.70)},
    {"code": "france", "name_ar": "فرنسا 🇫🇷", "price": mult_price(1.70)},
    {"code": "italy", "name_ar": "إيطاليا 🇮🇹", "price": mult_price(1.60)},
    {"code": "spain", "name_ar": "إسبانيا 🇪🇸", "price": mult_price(1.60)},
    {"code": "uk", "name_ar": "بريطانيا 🇬🇧", "price": mult_price(1.80)},
    {"code": "usa", "name_ar": "أمريكا 🇺🇸", "price": mult_price(2.00)}
]

def get_main_keyboard(user_id):
    buttons = [
        [InlineKeyboardButton("🛒 شــراء رقــم افتـراضـي", callback_data='buy_virtual_number')],
        [InlineKeyboardButton("✈️ عروض Telegram", callback_data='deals_telegram'), InlineKeyboardButton("💬 عروض WhatsApp", callback_data='deals_whatsapp')],
        [InlineKeyboardButton("🎲 • شحـن الرصيـد •", callback_data='deposit_menu'), InlineKeyboardButton("🎳 • الأكثر توفراً •", callback_data='most_available')],
        [InlineKeyboardButton("🔭 • الرشـق وشحـن الألعـاب والبرامـج •", callback_data='boosting_services')],
        [InlineKeyboardButton("💎 • ربـح الأرصدة مجـانـاً (أكواد وهدايا) •", callback_data='free_points')],
        [InlineKeyboardButton("🔄 • تحويـل الرصيـد •", callback_data='transfer_balance'), InlineKeyboardButton("📞 • الدعم •", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("📖 • تعليمات وطريقة استخدام البوت •", callback_data='bot_instructions')],
        [InlineKeyboardButton("👤 حســابــي", callback_data='user_account')]
    ]
    if is_admin_or_sub(user_id):
        buttons.append([InlineKeyboardButton("⚙️ لـوحـة تحكـم الأدمن الاحترافية", callback_data='admin_panel')])
    return InlineKeyboardMarkup(buttons)

def get_virtual_services_keyboard():
    buttons = [
        [InlineKeyboardButton("🛍️ WHATSAPP - واتساب", callback_data='service_whatsapp'), InlineKeyboardButton("🎲 TELEGRAM - تليجرام", callback_data='cat_telegram')],
        [InlineKeyboardButton("🎳 INSTAGRAM - انستغرام", callback_data='service_instagram'), InlineKeyboardButton("🎯 FACEBOOK - فيسبوك", callback_data='service_facebook')],
        [InlineKeyboardButton("🐤 TWITTER - تويتر", callback_data='service_twitter'), InlineKeyboardButton("🎬 TIKTOK - تيك توك", callback_data='service_tiktok')],
        [InlineKeyboardButton("♣️ SNAPCHAT - سناب شات", callback_data='service_snapchat'), InlineKeyboardButton("💎 IMO - ايمو", callback_data='service_imo')],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

def get_whatsapp_sections_keyboard():
    buttons = [
        [InlineKeyboardButton("🌐 • الـدول العـربيـة •", callback_data='wa_arab_countries')],
        [InlineKeyboardButton("🌍 • الـدول الأجنبيـة والعـالميـة •", callback_data='wa_foreign_countries')],
        [InlineKeyboardButton("🔙 • عـودة لقـائمـة الخـدمـات •", callback_data='buy_virtual_number')]
    ]
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 تحديث الإحصائيات الشاملة", callback_data='admin_panel')],
        [InlineKeyboardButton("🏆 قائمة أطراف الإحالات (Top 5)", callback_data='admin_top_refs')],
        [InlineKeyboardButton("🎟️ إضافـة كود هدية (Promo Code)", callback_data='admin_create_promo')],
        [InlineKeyboardButton("💬 الرد على مستخدم عبر الآيدي", callback_data='admin_reply_user')],
        [InlineKeyboardButton("🎁 إرسال هدية لشخص عبر الآيدي", callback_data='admin_send_gift_user')],
        [InlineKeyboardButton("➕ إضافة رصيد (بالدولار)", callback_data='admin_add_balance'), InlineKeyboardButton("➖ خصم رصيد (بالدولار)", callback_data='admin_deduct_balance')],
        [InlineKeyboardButton("👥 إدارة المشرفين (إضافة / حذف)", callback_data='admin_manage_subadmins')],
        [InlineKeyboardButton("📢 إدارة الاشتراك الإجباري (إضافة / حذف)", callback_data='admin_manage_forced')],
        [InlineKeyboardButton("🎁 إرسال هدية مالية (Bonus) للجميع", callback_data='admin_send_bonus')],
        [InlineKeyboardButton("🧹 تصفير جميع أرصدة المستخدمين", callback_data='admin_reset_balances')],
        [InlineKeyboardButton("🚫 حظر / إلغاء حظر مستخدم", callback_data='admin_ban_user')],
        [InlineKeyboardButton("📢 إذاعة شاملة ضخمة", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')]
    ])

async def post_init(application):
    try:
        await application.bot.set_my_commands([BotCommand("start", "بدء استخدام البوت 🚀")])
    except Exception as e:
        print(f"Post init error: {e}")

async def watch_order_sms(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, order_id: str, phone: str, price: float, service: str, user_id: int, bot_username: str):
    url = f"https://5sim.net/v1/user/check/{order_id}"
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        for _ in range(300):
            await asyncio.sleep(3)
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    sms_list = data.get('sms', [])
                    if sms_list:
                        sms_code = sms_list[0].get('code', 'لا يوجد كود')
                        full_text = sms_list[0].get('text', '')
                        
                        await context.bot.edit_message_text(
                            chat_id=chat_id, message_id=message_id,
                            text=f"✅ **تم وصول الكود بنجاح!**\n\n📱 **الرقم:** `{phone}`\n🔑 **الكود:** `{sms_code}`\n\n💬 **النص:** `{full_text}`",
                            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                        )
                        
                        try:
                            masked_ph = phone[:4] + "***" + phone[-3:]
                            service_deeplink = f"https://t.me/{bot_username}?start=buy_virtual_number"
                            s_lower = service.lower()
                            if s_lower == 'whatsapp':
                                service_deeplink = f"https://t.me/{bot_username}?start=service_whatsapp"
                            elif s_lower == 'telegram':
                                service_deeplink = f"https://t.me/{bot_username}?start=cat_telegram"
                            elif s_lower == 'instagram':
                                service_deeplink = f"https://t.me/{bot_username}?start=service_instagram"
                            elif s_lower == 'facebook':
                                service_deeplink = f"https://t.me/{bot_username}?start=service_facebook"
                            elif s_lower == 'twitter':
                                service_deeplink = f"https://t.me/{bot_username}?start=service_twitter"
                            elif s_lower == 'tiktok':
                                service_deeplink = f"https://t.me/{bot_username}?start=service_tiktok"
                            elif s_lower == 'snapchat':
                                service_deeplink = f"https://t.me/{bot_username}?start=service_snapchat"
                            elif s_lower == 'imo':
                                service_deeplink = f"https://t.me/{bot_username}?start=service_imo"

                            channel_buttons = InlineKeyboardMarkup([
                                [
                                    InlineKeyboardButton("🛒 شراء من نفس الخدمة", url=service_deeplink),
                                    InlineKeyboardButton("🤖 الدخول إلى البوت", url=f"https://t.me/{bot_username}?start=main_menu")
                                ]
                            ])
                            await context.bot.send_message(
                                chat_id=LOG_CHANNEL_ID,
                                text=(
                                    "🔥 **تم اكتمال تفعيل رقم جديد بنجاح!** ✅\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"👤 **آيدي الشخص:** `{user_id}`\n"
                                    f"🛍️ **الخدمة:** `{service.upper()}`\n"
                                    f"📱 **الرقم:** `{masked_ph}`\n"
                                    f"🔑 **الكود:** `{sms_code}`\n"
                                    f"⭐ **الحالة:** مكتمل ومنجز بنجاح 🚀"
                                ),
                                parse_mode='Markdown',
                                reply_markup=channel_buttons
                            )
                        except Exception as log_err:
                            print(f"خطأ في إرسال سجل الأرقام للقناة: {log_err}")

                        return
                    if data.get('status') in ['canceled', 'banned', 'finish']:
                        return
            except Exception:
                continue

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    is_subbed, not_subbed_list = await check_forced_subscription(user.id, context.bot)
    if not is_subbed:
        sub_buttons = []
        for ch_username, ch_title in not_subbed_list:
            clean_ch = ch_username.replace("@", "")
            sub_buttons.append([InlineKeyboardButton(f"📢 انضم إلى قناة {ch_title}", url=f"https://t.me/{clean_ch}")])
        sub_buttons.append([InlineKeyboardButton("🔄 • تحققت من الاشتراكات •", callback_data='main_menu')])
        
        await update.message.reply_text(
            "📬| لطفاً عليك الاشتراك في قنوات البوت أولاً اشترك ثم اضغط على  /start للتحقق ✅:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(sub_buttons)
        )
        return

    u_data = db_get_user(user.id)
    
    if u_data.get('is_banned', 0) == 1:
        await update.message.reply_text("⛔ **عذراً، لقد تم حظرك من استخدام هذا البوت بواسطة الإدارة.**", parse_mode='Markdown')
        return
    
    if u_data.get('is_really_new', False) and user.id != ADMIN_ID:
        try:
            seq_num = u_data.get('user_sequence', 1)
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"👤 **مستخدم جديد انضم إلى البوت! (رقم {seq_num})**\n\n"
                    f"▫️ الاسم: {user.full_name}\n"
                    f"▫️ المعرف: @{user.username if user.username else 'لا يوجد'}\n"
                    f"▫️ الآيدي: `{user.id}`"
                ),
                parse_mode='Markdown'
            )
        except Exception:
            pass

    args = context.args
    arg_param = args[0] if args else None

    if arg_param and arg_param.isdigit():
        referrer_id = int(arg_param)
        if referrer_id != user.id:
            added = db_add_referral_record(user.id, referrer_id)
            if added:
                db_update_balance(referrer_id, 0.10, mode="add")
                try:
                    u_info = db_get_user(referrer_id)
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=(
                            "🎉🔥 **تهانينا القلبية لك يا بطل!** 🔥🎉\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            "🌟 انضم مستخدم جديد إلى البوت عبر رابط الإحالة الخاص بك بنجاح تام!\n\n"
                            "🎁 **تمت إضافة:** `$0.10` إلى رصيدك كمكافأة دعوة.\n"
                            f"💰 **رصيدك الحالي:** `${u_info['balance']:.2f}`\n"
                            f"👥 **إجمالي دعواتك:** `{u_info['referrals']} شخص`\n\n"
                            "🚀 *واصل مشاركة رابطك واربح المزيد من الأرباح فوراً!*"
                        ),
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

    welcome_text = (
        f"💎 **مرحباً بك عزيزي {user.first_name} في بوت ﴿ ديجيتال هب | Digital Hub ﴾** 🚀\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 **الآيدي:** `{user.id}`\n"
        f"💙 **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌟 بوابتك الأولى والأسرع للخدمات الرقمية المتكاملة، الأرقام الافتراضية، والرشق!\n\n"
        "👇 **اختر ما يناسبك من القائمة أدناه:**"
    )

    if arg_param == 'boosting_services':
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {'key': HMCARD_API_KEY, 'action': 'services'}
                res = await client.post(HMCARD_API_URL, data=payload)
                if res.status_code == 200:
                    services = res.json()
                    if isinstance(services, list) and len(services) > 0:
                        categories = {}
                        cat_mapping = {}
                        for serv in services:
                            if not isinstance(serv, dict): continue
                            cat = serv.get('category', 'أخرى') or 'أخرى'
                            if cat not in categories:
                                categories[cat] = []
                                cat_mapping[str(len(cat_mapping) + 1)] = cat
                            categories[cat].append(serv)
                        
                        if user.id not in admin_state:
                            admin_state[user.id] = {}
                        admin_state[user.id]['hm_services'] = services
                        admin_state[user.id]['hm_categories'] = cat_mapping
                        
                        buttons = []
                        for cat_id, cat_name in cat_mapping.items():
                            buttons.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"hm_cat_{cat_id}")])
                        buttons.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')])
                        
                        await update.message.reply_text(
                            f"🔭 **• قسم الرشـق وشحـن الألعـاب والبرامـج •**\n\n⭐ **رصيدك:** `${u_data['balance']:.2f}`\nاختر القسم المطلوب:",
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup(buttons)
                        )
                        return
        except Exception:
            pass
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard(user.id))

    elif arg_param == 'buy_virtual_number':
        services_text = (
            "❖ **هنا قائمة التطبيقات والخدمات المتوفرة في البوت** ❖\n"
            "❖ **اختر التطبيق أو الخدمة التي تريدها من الأسفل:**\n\n"
            f"⭐ **رصيدك:** `${u_data['balance']:.2f}`\n"
            "💖 **قناة التفعيلات الرسمية** 💖\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(services_text, parse_mode='Markdown', reply_markup=get_virtual_services_keyboard())

    elif arg_param == 'service_whatsapp':
        services_text = (
            f"🛍️ **قسم أرقام واتساب الرسمية**\n\n⭐ **رصيدك:** `${u_data['balance']:.2f}`\n\nاختر القسم المطلوب:"
        )
        await update.message.reply_text(services_text, parse_mode='Markdown', reply_markup=get_whatsapp_sections_keyboard())

    elif arg_param == 'cat_telegram':
        buttons = []
        row = []
        for item in TELEGRAM_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_telegram_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        await update.message.reply_text(f"🎲 **• أرقام تليجرام الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif arg_param == 'service_instagram':
        buttons = []
        row = []
        for item in INSTAGRAM_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_instagram_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        await update.message.reply_text(f"🎳 **• أرقام انستغرام الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif arg_param == 'service_facebook':
        buttons = []
        row = []
        for item in FACEBOOK_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_facebook_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        await update.message.reply_text(f"🎯 **• أرقام فيسبوك الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif arg_param == 'service_twitter':
        buttons = []
        row = []
        for item in TWITTER_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_twitter_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        await update.message.reply_text(f"🐤 **• أرقام تويتر الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif arg_param == 'service_tiktok':
        buttons = []
        row = []
        for item in TIKTOK_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_tiktok_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        await update.message.reply_text(f"🎬 **• أرقام تيك توك الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif arg_param in ['service_snapchat', 'service_imo']:
        serv_title = "سناب شات ♣️" if arg_param == 'service_snapchat' else "إيمو 💎"
        serv_code = "snapchat" if arg_param == 'service_snapchat' else "imo"
        buttons = []
        row = []
        for item in SNAP_IMO_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_{serv_code}_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        await update.message.reply_text(f"🔹 **• أرقام خدمة {serv_title} ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    else:
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard(user.id))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_first_name = query.from_user.first_name
    data = query.data

    is_subbed, not_subbed_list = await check_forced_subscription(user_id, context.bot)
    if not is_subbed and data != 'main_menu':
        sub_buttons = []
        for ch_username, ch_title in not_subbed_list:
            clean_ch = ch_username.replace("@", "")
            sub_buttons.append([InlineKeyboardButton(f"📢 انضم إلى قناة {ch_title}", url=f"https://t.me/{clean_ch}")])
        sub_buttons.append([InlineKeyboardButton("🔄 • تحققت من الاشتراكات •", callback_data='main_menu')])
        
        await query.edit_message_text(
            "📬| لطفاً عليك الاشتراك في قنوات البوت أولاً اشترك ثم اضغط على  /start للتحقق ✅:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(sub_buttons)
        )
        return

    if data == 'main_menu':
        admin_state.pop(user_id, None)
        u_data = db_get_user(user_id)
        welcome_text = (
            f"💎 **مرحباً بك عزيزي {user_first_name} في بوت ﴿ ديجيتال هب | Digital Hub ﴾** 🚀\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **الآيدي:** `{user_id}`\n"
            f"💙 **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌟 بوابتك الأولى والأسرع للخدمات الرقمية المتكاملة، الأرقام الافتراضية، والرشق!\n\n"
            "👇 **اختر ما يناسبك من القائمة أدناه:**"
        )
        await query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))

    elif data == 'bot_instructions':
        instructions_text = (
            "💎 **دليل استخدام بوت ﴿ ديجيتال هب | Digital Hub ﴾** 🚀\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "بوابتك الأولى والأسرع للخدمات الرقمية المتكاملة في مكان واحد وبأفضل الأسعار! 🌟\n\n"
            "📱 **1️⃣ قسم الأرقام الافتراضية:**\n"
            "• احصل فوراً على أرقام لتفعيل (واتساب، تليجرام، انستغرام، فيسبوك، وغيرها) من مختلف دول العالم.\n"
            "• النظام يتحقق من وصول الكود ويعرسلك مباشرة داخل البوت مع إمكانية إلغاء الرقم واسترداد رصيدك في حال لم يصل الكود.\n\n"
            "🔭 **2️⃣ قسم الرشق وشحن الألعاب:**\n"
            "• اطلب خدمات زيادة المتابعين والتفاعلات لجميع منصات التواصل الاجتماعي بكل سهولة.\n"
            "• الأسعار تنافسية ومضبوطة بعناية لتوفير أفضل تجربة لك.\n\n"
            "🎲 **3️⃣ شحن الرصيد الفوري واليدوي:**\n"
            "• ⭐️ نجوم تليجرام (Telegram Stars): شحن فوري تلقائي (كل 100 نجمة = 2$ دولار).\n"
            "• 💙 محفظة جيب (Jaib): تحويل إلى الحساب المعتمد (1$ = 550 ريال يمني قديم).\n"
            "• 🏦 بنك الكريمي (Alkurimi): تحويل مباشر (1$ = 550 ريال يمني قديم).\n"
            "• 📞 للدعم والمساعدة: @benti\n\n"
            "💎 **4️⃣ ربح الأرصدة مجاناً وإدخال الاكواد:**\n"
            "• شارك رابط الإحالة الخاص بك أو **أرسل كود الهدية (Promo Code)** في المحادثة مباشرة لشحن رصيدك مجاناً!\n\n"
            "🔄 **5️⃣ تحويل الرصيد:**\n"
            "• يمكنك تحويل أي مبلغ من رصيدك لأي مستخدم آخر داخل البوت بكل سهولة عبر آيدي المستخدم.\n\n"
            "> 💡 *انقر على الزر أدناه للعودة للقائمة الرئيسية واستكشاف خدماتنا فوراً!* 👇"
        )
        await query.edit_message_text(
            instructions_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')]])
        )

    elif data == 'buy_virtual_number':
        u_data = db_get_user(user_id)
        services_text = (
            "❖ **هنا قائمة التطبيقات والخدمات المتوفرة في البوت** ❖\n"
            "❖ **اختر التطبيق أو الخدمة التي تريدها من الأسفل:**\n\n"
            f"⭐ **رصيدك:** `${u_data['balance']:.2f}`\n"
            "💖 **قناة التفعيلات الرسمية** 💖\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(services_text, parse_mode='Markdown', reply_markup=get_virtual_services_keyboard())

    elif data == 'boosting_services':
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            "⏳ جاري جلب قائمة خدمات الرشق وشحن الألعاب من المنصة...",
            parse_mode='Markdown'
        )
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                services = None
                payload = {'key': HMCARD_API_KEY, 'action': 'services'}
                res = await client.post(HMCARD_API_URL, data=payload)
                
                if res.status_code == 200:
                    try:
                        data_json = res.json()
                        if isinstance(data_json, list):
                            services = data_json
                        elif isinstance(data_json, dict):
                            err_text = data_json.get('error', 'استجابة غير صالحة من المنصة')
                            await query.edit_message_text(f"⚠️ **رد المنصة:**\n`{err_text}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]]))
                            return
                    except Exception:
                        raw_text = res.text[:200] if res.text else "استجابة فارغة"
                        await query.edit_message_text(f"⚠️ استجابة غير متوقعة من المنصة:\n`{raw_text}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]]))
                        return

                if services and isinstance(services, list) and len(services) > 0:
                    categories = {}
                    cat_mapping = {}
                    for serv in services:
                        if not isinstance(serv, dict):
                            continue
                        cat = serv.get('category', 'أخرى')
                        if not cat:
                            cat = 'أخرى'
                        if cat not in categories:
                            categories[cat] = []
                            cat_mapping[str(len(cat_mapping) + 1)] = cat
                        categories[cat].append(serv)
                    
                    if user_id not in admin_state:
                        admin_state[user_id] = {}
                    admin_state[user_id]['hm_services'] = services
                    admin_state[user_id]['hm_categories'] = cat_mapping
                    
                    buttons = []
                    for cat_id, cat_name in cat_mapping.items():
                        buttons.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"hm_cat_{cat_id}")])
                    buttons.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')])
                    
                    await query.edit_message_text(
                        f"🔭 **• قسم الرشـق وشحـن الألعـاب والبرامـج •**\n\n⭐ **رصيدك:** `${u_data['balance']:.2f}`\nاختر القسم المطلوب:",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    await query.edit_message_text("⚠️ لم يتم جلب أي خدمات. تأكد من صحة مفتاح الـ API الخاص بـ HM Card أو وجود رصيد في حسابك.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]]))
        except Exception as e:
            await query.edit_message_text(f"⚠️ حدث خطأ أثناء الاتصال: {str(e)[:50]}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]]))

    elif data.startswith('hm_cat_'):
        cat_id = data.replace('hm_cat_', '')
        user_state_data = admin_state.get(user_id, {})
        cat_mapping = user_state_data.get('hm_categories', {})
        services = user_state_data.get('hm_services', [])
        
        cat_name = cat_mapping.get(cat_id)
        if not cat_name:
            await query.edit_message_text("⚠️ انتهت صلاحية الجلسة، يرجى إعادة فتح قسم الرشق.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='boosting_services')]]))
            return

        buttons = []
        for serv in services:
            if isinstance(serv, dict) and serv.get('category') == cat_name:
                s_id = serv.get('service')
                s_name = str(serv.get('name', ''))
                try:
                    orig_rate = float(serv.get('rate', '0.00'))
                except ValueError:
                    orig_rate = 0.00
                
                multiplied_rate = round(orig_rate * 3.0, 2)
                button_title = f"{s_name} | ${multiplied_rate:.2f}"
                buttons.append([InlineKeyboardButton(button_title, callback_data=f"hm_serv_{s_id}")])
        
        buttons.append([InlineKeyboardButton("🔙 عودة للأقسام", callback_data='boosting_services')])
        await query.edit_message_text(
            "🔭 **اختر الخدمة المطلوبة من القائمة أدناه:**",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith('hm_serv_'):
        serv_id = data.replace('hm_serv_', '')
        if user_id not in admin_state:
            admin_state[user_id] = {}
        
        selected_serv_text = "خدمة غير معروفة"
        service_rate = 0.00
        min_qty = 100
        max_qty = 10000
        
        for serv in admin_state.get(user_id, {}).get('hm_services', []):
            if str(serv.get('service')) == str(serv_id):
                selected_serv_text = str(serv.get('name', ''))
                try:
                    orig_rate = float(serv.get('rate', '0.00'))
                except ValueError:
                    orig_rate = 0.00
                service_rate = round(orig_rate * 3.0, 2)
                try:
                    min_qty = int(serv.get('min', 100))
                except (ValueError, TypeError):
                    min_qty = 100
                try:
                    max_qty = int(serv.get('max', 10000))
                except (ValueError, TypeError):
                    max_qty = 10000
                break

        admin_state[user_id].update({
            'action': 'waiting_for_hm_link',
            'service_id': serv_id,
            'service_name': selected_serv_text,
            'service_rate': service_rate,
            'min_qty': min_qty,
            'max_qty': max_qty
        })
        
        details_text = (
            f"🔹 **اسم الخدمة:**\n`{selected_serv_text}`\n\n"
            f"💵 **السعر:** `${service_rate:.2f}`\n"
            f"📉 **أقل كمية للطلب:** `{min_qty}`\n"
            f"📈 **أكبر كمية للطلب:** `{max_qty}`\n\n"
            "🔗 الخطوة الأولى للطلب الخدمة :\n"
            "أرسل الآن رابط الطلب (رابط الحساب، القناة، المنشور، أو الآيدي حسب الخدمة):"
        )
        
        await query.edit_message_text(
            details_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 • طلب الخدمة •", callback_data=f"hm_order_step2_{serv_id}")],
                [InlineKeyboardButton("• عودة •", callback_data='boosting_services')]
            ])
        )

    elif data.startswith('hm_order_step2_'):
        serv_id = data.replace('hm_order_step2_', '')
        if user_id not in admin_state:
            admin_state[user_id] = {}
        admin_state[user_id].update({'action': 'waiting_for_hm_link', 'service_id': serv_id})
        
        step_text = (
            "🔗 الخطوة الأولى للطلب الخدمة :\n"
            "أرسل الآن رابط الطلب (رابط الحساب، القناة، المنشور، أو الآيدي حسب الخدمة):"
        )
        await query.edit_message_text(
            step_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='boosting_services')]])
        )

    elif data == 'confirm_hm_order':
        st_data = admin_state.get(user_id, {})
        service_id = st_data.get('service_id')
        link = st_data.get('link')
        quantity = st_data.get('quantity')
        cost = st_data.get('cost')
        service_name = st_data.get('service_name', 'خدمة رشق')

        if not service_id or not link or not quantity or not cost:
            await query.answer("⚠️ انتهت صلاحية الطلب، يرجى إعادة البدء.", show_alert=True)
            return

        u_data = db_get_user(user_id)
        if u_data['balance'] < cost:
            not_enough_text = (
                "❌ **عذراً، رصيد محفظتك غير كافٍ لإتمام عملية الشراء!**\n\n"
                f"⭐ **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
                "💡 يرجى شحن رصيدك لتتمكن من إتمام الطلب بنجاح."
            )
            not_enough_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 يرجى شحن رصيدك", callback_data='deposit_menu')],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
            ])
            await query.edit_message_text(not_enough_text, parse_mode='Markdown', reply_markup=not_enough_markup)
            return

        await query.answer("🔄 جاري إرسال الطلب للموقع...", show_alert=False)

        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {
                'key': HMCARD_API_KEY,
                'action': 'add',
                'service': service_id,
                'link': link,
                'quantity': quantity
            }
            res = await client.post(HMCARD_API_URL, data=payload)
            if res.status_code == 200:
                resp_data = res.json()
                if isinstance(resp_data, dict) and 'order' in resp_data:
                    order_id = resp_data['order']
                    db_update_balance(user_id, cost, mode="deduct")
                    admin_state.pop(user_id, None)
                    
                    await query.edit_message_text(
                        f"✅ **تم إرسال طلب الرشق وتأكيده بنجاح!**\n\n"
                        f"🆔 **رقم الطلب في المنصة:** `{order_id}`\n"
                        f"🔗 **الرابط:** `{link}`\n"
                        f"📦 **الكمية:** `{quantity}`\n"
                        f"⭐ **تم خصم:** `${cost:.2f}` من رصيدك.",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                    )
                    
                    try:
                        masked_l = mask_link(link)
                        bot_username = context.bot.username
                        channel_buttons = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("🛒 شراء من نفس الخدمة", url=f"https://t.me/{bot_username}?start=boosting_services"),
                                InlineKeyboardButton("🤖 الدخول إلى البوت", url=f"https://t.me/{bot_username}?start=main_menu")
                            ]
                        ])
                        await context.bot.send_message(
                            chat_id=LOG_CHANNEL_ID,
                            text=(
                                "🔥 **تم قبول وتنفيذ طلب رشق جديد بنجاح!** ✅\n"
                                "━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"👤 **آيدي الشخص:** `{user_id}`\n"
                                f"🔭 **الخدمة:** `{service_name}`\n"
                                f"🆔 **رقم الطلب:** `{order_id}`\n"
                                f"📦 **الكمية:** `{quantity}`\n"
                                f"🔗 **الرابط:** `{masked_l}`\n"
                                f"💰 **المبلغ المخصوم:** `${cost:.2f}`\n"
                                f"⭐ **الحالة:** مكتمل ومُرسل للمنصة 🚀"
                            ),
                            parse_mode='Markdown',
                            reply_markup=channel_buttons
                        )
                    except Exception as log_err:
                        print(f"خطأ في إرسال سجل الرشق للقناة: {log_err}")
                else:
                    err_msg = resp_data.get('error', 'خطأ غير معروف من المنصة') if isinstance(resp_data, dict) else 'استجابة غير صالحة من المنصة'
                    await query.edit_message_text(f"❌ **فشل الطلب من المنصة:**\n`{err_msg}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='boosting_services')]]))
            else:
                await query.edit_message_text("❌ تعذر الاتصال بموقع الخدمات حالياً.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='boosting_services')]]))

    elif data == 'cancel_hm_order':
        admin_state.pop(user_id, None)
        await query.edit_message_text(
            "❌ **تم إلغاء الطلب بنجاح.**",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
        )

    elif data == 'free_points':
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        u_data = db_get_user(user_id)
        
        free_text = (
            "💎 **قسم ربح الأرصدة مجاناً وأكواد الهدية:**\n\n"
            "1️⃣ **رابط الإحالة الخاص بك:**\n"
            f"`{ref_link}`\n"
            f"👥 عدد الدعوات: `{u_data['referrals']} شخص` | ⭐ الأرباح: `${u_data['referrals'] * 0.10:.2f}`\n\n"
            "2️⃣ **شحن عبر كود هدية (Promo Code):**\n"
            "إذا كان لديك كود هدية أو قسيمة شحن، **قم بإرسال الكود مباشرة في هذه المحادثة** وسيتولى البوت شحن رصيدك فوراً!"
        )
        await query.edit_message_text(
            free_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
        )

    elif data == 'transfer_balance':
        admin_state[user_id] = {'action': 'waiting_for_transfer_id'}
        u_data = db_get_user(user_id)
        transfer_text = (
            "🔄 **• نظام تحويل الرصيد بين المستخدمين •**\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"⭐ **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
            "👤 **الخطوة الأولى:**\n"
            "أرسل الآن **آيدي (ID)** المستخدم المراد التحويل إليه في رسالة هنا:"
        )
        await query.edit_message_text(
            transfer_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='main_menu')]])
        )

    elif data == 'deposit_menu':
        deposit_text = (
            "🌐 **طرق الدفع والشحن المتوفرة ✓**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "✅ يمكنك شحن حسابك في البوت بشكل فوري عبر **نجوم تليجرام (Telegram Stars)** (كل 100 نجمة = 2$ دولار داخل البوت) أو عبر الطرق اليدوية أدناه:"
        )
        deposit_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ شحن الرصيد عبر نجوم تليجرام (Stars)", callback_data='dep_telegram_stars')],
            [InlineKeyboardButton("الدفع عبر محفظة جيب", callback_data='dep_jaib')],
            [InlineKeyboardButton("الدفع عبر بنك الكريمي", callback_data='dep_alkurimi')],
            [InlineKeyboardButton("• هل لديك طريقة دفع أخرى؟ •", callback_data='dep_other_support')],
            [InlineKeyboardButton("• عودة •", callback_data='main_menu')]
        ])
        await query.edit_message_text(deposit_text, parse_mode='Markdown', reply_markup=deposit_keyboard)

    elif data == 'dep_telegram_stars':
        stars_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ شحن $2 (100 نجمة)", callback_data='pay_stars_100_2')],
            [InlineKeyboardButton("⭐ شحن $10 (500 نجمة)", callback_data='pay_stars_500_10')],
            [InlineKeyboardButton("⭐ شحن $20 (1000 نجمة)", callback_data='pay_stars_1000_20')],
            [InlineKeyboardButton("🔙 عودة", callback_data='deposit_menu')]
        ])
        await query.edit_message_text(
            "⭐ **قسم الشحن الفوري عبر نجوم تليجرام:**\n\n"
            "💡 **ملاحظة:** كل 100 نجمة = 2$ دولار داخل البوت.\n\n"
            "اختر الباقة المناسبة لك لشحن رصيدك فوراً في البوت:",
            parse_mode='Markdown',
            reply_markup=stars_keyboard
        )

    elif data.startswith('pay_stars_'):
        _, _, stars_count, usd_amount = data.split('_')
        stars_count = int(stars_count)
        usd_amount = float(usd_amount)
        
        title = f"شحن رصيد بقيمة ${usd_amount}"
        description = f"إضافة رصيد بقيمة ${usd_amount} إلى حسابك في بوت الأرقام والخدمات."
        payload = f"deposit_{user_id}_{usd_amount}"
        currency = "XTR"
        prices = [LabeledPrice("شحن رصيد بوت", stars_count)]
        
        try:
            await context.bot.send_invoice(
                chat_id=user_id, title=title, description=description,
                payload=payload, provider_token="", currency=currency, prices=prices
            )
            await query.answer("✅ تم إرسال فاتورة النجوم في المحادثة، قم بإتمام الدفع.", show_alert=True)
        except Exception as e:
            await query.answer(f"⚠️ تعذر إنشاء الفاتورة: {str(e)[:40]}", show_alert=True)

    elif data == 'dep_other_support':
        support_msg = (
            "📞 **طرق الشحن عبر الدعم الفني**\n\n"
            f"إذا كانت لديك طريقة دفع مختلفة، يمكنك التواصل مباشرة مع الإدارة عبر معرف الدعم المعتمد:\n"
            f"👉 @{SUPPORT_USERNAME}"
        )
        await query.edit_message_text(
            support_msg,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='deposit_menu')]])
        )

    elif data == 'dep_jaib':
        admin_state[user_id] = {'action': 'waiting_for_deposit'}
        jaib_text = (
            "أهلاً بك عزيزي في قسم الشحن عبر محفظة جيب 💙\n\n"
            "💰 طريقة الشحن : كل 1 دولار = 550 ريال يمني قديم\n\n"
            "اقل مبلغ للشحن 1$\n\n"
            "📲 خطوات الشحن:\n\n"
            "1- قم بتحويل المبلغ الذي تريده إلى هذا الرقم عبر تطبيق جيب:\n"
            "`78132392`\n\n"
            "2- بعد التحويل مباشرة، انسخ رقم العملية أو رسالة التأكيد من تطبيق جيب والصقها هنا في المحادثة\n\n"
            "3- سيتم مراجعة الطلب وإضافة الرصيد إلى حسابك فوراً ✅"
        )
        await query.edit_message_text(jaib_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='deposit_menu')]]))

    elif data == 'dep_alkurimi':
        admin_state[user_id] = {'action': 'waiting_for_deposit'}
        alkurimi_text = (
            "أهلاً بك عزيزي في قسم الشحن عبر بنك الكريمي 💙\n\n"
            "💰 طريقة الشحن : كل 1 دولار = 550 ريال يمني قديم\n\n"
            "اقل مبلغ للشحن 1$\n\n"
            "📲 خطوات الشحن:\n\n"
            "1- قم بتحويل المبلغ إلى رقم حسابنا عبر تطبيق الكريمي أو الصراف:\n"
            "`3105004949`\n\n"
            "2- بعد التحويل مباشرة، انسخ رقم العملية أو الحوالة والصقها هنا في المحادثة\n\n"
            "3- سيتم مراجعة الطلب وإضافة الرصيد إلى حسابك فوراً ✅"
        )
        await query.edit_message_text(alkurimi_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='deposit_menu')]]))

    elif data.startswith('approve_deposit_'):
        if not is_admin_or_sub(user_id): return
        _, _, target_user_id, amount = data.split('_', 3)
        target_user_id = int(target_user_id)
        amount = float(amount)

        db_update_balance(target_user_id, amount, mode="add")
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 **مبروك! تم قبول طلب الشحن وإضافة الرصيد بنجاح.**\n⭐ تم إضافة: `${amount:.2f}` لحسابك.",
                parse_mode='Markdown'
            )
        except Exception:
            pass

        try:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"✅ **تم اعتماد شحن الرصيد بنجاح بواسطة المشرف!**\n👤 للمستخدم: `{target_user_id}`\n⭐ المبلغ المضاف: `${amount:.2f}`", parse_mode='Markdown')
        except Exception:
            pass

    elif data.startswith('reject_deposit_'):
        if not is_admin_or_sub(user_id): return
        _, _, target_user_id = data.split('_', 2)
        target_user_id = int(target_user_id)

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="❌ **عذراً، تم رفض طلب الشحن الخاص بك بسبب عدم صحة رقم العملية أو عدم توفر رصيد مقابل له.** يرجى التأكد والمحاولة مرة أخرى أو التواصل مع الدعم.",
                parse_mode='Markdown'
            )
        except Exception:
            pass

        try:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"❌ **تم رفض طلب الشحن وإلغاؤه بنجاح.**\n👤 للمستخدم: `{target_user_id}`", parse_mode='Markdown')
        except Exception:
            pass

    elif data.startswith('custom_deposit_'):
        if not is_admin_or_sub(user_id): return
        _, _, target_user_id = data.split('_', 2)
        target_user_id = int(target_user_id)
        
        admin_state[user_id] = {
            'action': 'waiting_for_custom_deposit_amount',
            'target_user_id': target_user_id,
            'message_to_edit': query.message
        }
        await query.message.reply_text(
            f"✍️ **أدخل المبلغ المراد إضافته للمستخدم (`{target_user_id}`) بالدولار:**\n*(مثال: 0.75 أو 3)*",
            parse_mode='Markdown'
        )

    elif data == 'deals_whatsapp':
        buttons = []
        row = []
        for item in WHATSAPP_DEALS:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_whatsapp_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة للقائمـة الرئيسيـة", callback_data='main_menu')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🔥 **• عروض أرقام واتساب ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == 'deals_telegram':
        buttons = []
        row = []
        for item in TELEGRAM_DEALS:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_telegram_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة للقائمـة الرئيسيـة", callback_data='main_menu')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🔥 **• عروض أرقام تليجرام ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == 'service_whatsapp':
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🛍️ **قسم أرقام واتساب الرسمية**\n\n⭐ **رصيدك:** `${u_data['balance']:.2f}`\n\nاختر القسم المطلوب:",
            parse_mode='Markdown', reply_markup=get_whatsapp_sections_keyboard()
        )

    elif data == 'wa_arab_countries':
        buttons = []
        row = []
        for item in ARAB_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_whatsapp_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لأقسـام الواتساب", callback_data='service_whatsapp')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🌐 **• الدول العربية الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == 'wa_foreign_countries':
        buttons = []
        row = []
        for item in WHATSAPP_FOREIGN:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_whatsapp_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لأقسـام الواتساب", callback_data='service_whatsapp')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🌍 **• الدول الأجنبية والعالمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == 'cat_telegram':
        buttons = []
        row = []
        for item in TELEGRAM_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_telegram_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🎲 **• أرقام تليجرام الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == 'service_instagram':
        buttons = []
        row = []
        for item in INSTAGRAM_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_instagram_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🎳 **• أرقام انستغرام الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == 'service_facebook':
        buttons = []
        row = []
        for item in FACEBOOK_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_facebook_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🎯 **• أرقام فيسبوك الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == 'service_twitter':
        buttons = []
        row = []
        for item in TWITTER_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_twitter_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🐤 **• أرقام تويتر الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == 'service_tiktok':
        buttons = []
        row = []
        for item in TIKTOK_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_tiktok_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🎬 **• أرقام تيك توك الرسمية ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data in ['service_snapchat', 'service_imo']:
        serv_title = "سناب شات ♣️" if data == 'service_snapchat' else "إيمو 💎"
        serv_code = "snapchat" if data == 'service_snapchat' else "imo"
        
        buttons = []
        row = []
        for item in SNAP_IMO_COUNTRIES:
            row.append(InlineKeyboardButton(f"{item['name_ar']} • ${item['price']:.2f}", callback_data=f"buy_num_{serv_code}_{item['code']}_{item['price']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 عـودة لقـائمـة الخـدمـات", callback_data='buy_virtual_number')])
        
        u_data = db_get_user(user_id)
        await query.edit_message_text(
            f"🔹 **• أرقام خدمة {serv_title} ($) •**\n⭐ رصيدك: `${u_data['balance']:.2f}`\n\nاختر الدولة المطلوبة:",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith('buy_num_'):
        parts = data.split('_')
        service = parts[2]
        country_code = parts[3]
        country_price = float(parts[4])
        u_data = db_get_user(user_id)
        
        if u_data['balance'] < country_price:
            not_enough_text = (
                "❌ **عذراً، رصيد محفظتك غير كافٍ لإتمام عملية الشراء!**\n\n"
                f"⭐ **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
                "💡 يرجى شحن رصيدك لتتمكن من إتمام الطلب بنجاح."
            )
            not_enough_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 يرجى شحن رصيدك", callback_data='deposit_menu')],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
            ])
            await query.edit_message_text(not_enough_text, parse_mode='Markdown', reply_markup=not_enough_markup)
            return

        await query.answer("🔄 جاري الشراء...", show_alert=False)
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            try:
                res = await client.get(f"https://5sim.net/v1/user/buy/activation/{country_code}/any/{service}")
                if res.status_code == 200:
                    res_data = res.json()
                    phone = res_data.get('phone')
                    order_id = res_data.get('id')
                    
                    if not phone or not order_id:
                        await query.edit_message_text(
                            "⚠️ **عذراً، نفدت الأرقام لهذه الدولة حالياً في الموقع.**\nيرجى تجربة دولة أخرى أو محاولة الشراء لاحقاً.",
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للقائمة", callback_data='buy_virtual_number')]])
                        )
                        return

                    db_update_balance(user_id, country_price, mode="deduct")
                    
                    sent_msg = await query.edit_message_text(
                        f"✅ **تم الشراء بنجاح!**\n📱 الرقم: `{phone}`\n⭐ تم خصم: `${country_price:.2f}`\n⏳ جاري انتظار الكود...",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("❌ إلغاء واسترداد الرصيد", callback_data=f"cnl_paid_{order_id}_{country_price}")],
                            [InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]
                        ])
                    )
                    asyncio.create_task(watch_order_sms(context, query.message.chat_id, sent_msg.message_id, str(order_id), phone, country_price, service, user_id, context.bot.username))
                else:
                    await query.edit_message_text(
                        "❌ **عذراً، الأرقام غير متوفرة حالياً لهذه الدولة أو رصيد الموقع نفد.**\nجرب دولة أخرى أو تأكد من رصيد الحساب.",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للقائمة", callback_data='buy_virtual_number')]])
                    )
            except Exception as e:
                await query.edit_message_text(
                    f"⚠️ حدث خطأ أثناء الاتصال:\n`{str(e)[:60]}`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للقائمة", callback_data='buy_virtual_number')]])
                )

    elif data.startswith('cnl_'):
        _, cancel_type, order_id, price = data.split('_', 3)
        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
            res = await client.get(f"https://5sim.net/v1/user/cancel/{order_id}")
            if res.status_code == 200:
                if cancel_type == 'paid':
                    db_update_balance(user_id, float(price), mode="add")
                await query.answer("✅ تم الإلغاء واسترداد الرصيد بنجاح!", show_alert=True)
                await query.edit_message_text("🚫 تم إلغاء الطلب بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))
            else:
                await query.answer("⚠️ تعذر إلغاء الطلب.", show_alert=True)

    elif data == 'user_account':
        u_data = db_get_user(user_id)
        text = f"👤 **معلومات الحساب:**\n\n🆔 الآيدي: `{user_id}`\n⭐ رصيدك: `${u_data['balance']:.2f}`\n👥 الدعوات: `{u_data['referrals']}`"
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]]))

    elif data == 'admin_panel':
        if not is_admin_or_sub(user_id): return
        stats = db_get_advanced_stats()
        panel_text = (
            "⚙️ **• لوحة تحكم الأدمن الاحترافية المتقدمة •** ⚙️\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 **إجمالي المستخدمين:** `{stats['total_users']} مشترك`\n"
            f"🆕 **المستخدمين الجدد (آخر 24 ساعة):** `{stats['new_24h']} مشترك جديد` 📈\n"
            f"💰 **إجمالي أرصدة المحافظ:** `${stats['total_balances']:.2f}`\n"
            f"🔗 **إجمالي الإحالات الكلية:** `{stats['total_referrals']} دعوة`\n\n"
            "👇 **اختر الإجراء المطلـوب من الأزرار أدناه:**"
        )
        await query.edit_message_text(panel_text, parse_mode='Markdown', reply_markup=get_admin_keyboard())

    elif data == 'admin_top_refs':
        if not is_admin_or_sub(user_id): return
        stats = db_get_advanced_stats()
        top_list = stats['top_refs']
        
        text = "🏆 **قائمة أطراف الإحالات (أعلى 5 أشخاص نشطين):**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        if top_list:
            for idx, (uid, refs) in enumerate(top_list, 1):
                text += f"{idx}. الآيدي: `{uid}` ⟵ **{refs} دعوة** 🌟\n"
        else:
            text += "⚠️ لا توجد إحالات مسجلة حتى الآن."
            
        await query.edit_message_text(
            text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]])
        )

    elif data == 'admin_create_promo':
        if not is_admin_or_sub(user_id): return
        admin_state[user_id] = {'action': 'waiting_for_promo_details'}
        await query.edit_message_text(
            "🎟️ **إنشاء كود هدية جديد (Promo Code):**\n\n"
            "أرسل الآن **(الكود)** و **(المبلغ بالدولار)** و **(عدد مرات الاستخدام)** بمسافات بينها.\n"
            "*(مثال: `WELCOME 0.50 100`)*\n"
            "*(تعني: كود بقيمة 0.50$ ومتاح لـ 100 شخص)*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]])
        )

    elif data == 'admin_reply_user':
        if not is_admin_or_sub(user_id): return
        admin_state[user_id] = {'action': 'waiting_for_reply_id'}
        await query.edit_message_text(
            "💬 **الرد على مستخدم عبر الآيدي:**\n\n"
            "أرسل الآن رسالتك بالصيغة التالية (الآيدي مسافة نص الرسالة):\n"
            "مثال: `6472852297 أهلاً بك عزيزي، تم حل مشكلتك بنجاح.`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]])
        )

    elif data == 'admin_send_gift_user':
        if not is_admin_or_sub(user_id): return
        admin_state[user_id] = {'action': 'waiting_for_gift_id'}
        await query.edit_message_text(
            "🎁 **إرسال هدية لشخص عبر الآيدي:**\n\n"
            "أرسل الآن **(آيدي المستخدم)** في رسالة وحدها:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]])
        )

    elif data == 'admin_add_balance':
        if not is_admin_or_sub(user_id): return
        admin_state[user_id] = {'action': 'waiting_for_add_bal_id'}
        await query.edit_message_text(
            "➕ **إضافة رصيد بالدولار ($):**\n\n"
            "أرسل الآن **(آيدي المستخدم)** في رسالة وحدها:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]])
        )

    elif data == 'admin_deduct_balance':
        if not is_admin_or_sub(user_id): return
        admin_state[user_id] = {'action': 'waiting_for_deduct_bal_id'}
        await query.edit_message_text(
            "➖ **خصم رصيد بالدولار ($):**\n\n"
            "أرسل الآن **(آيدي المستخدم)** في رسالة وحدها:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]])
        )

    elif data == 'admin_manage_subadmins':
        if user_id != ADMIN_ID:
            await query.answer("❌ هذا الأمر مخصص للمسؤول الأساسي فقط!", show_alert=True)
            return
        subs = get_all_sub_admins()
        subs_text = "👥 **قائمة المشرفين المساعدين الحاليين:**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        if subs:
            for idx, sid in enumerate(subs, 1):
                subs_text += f"{idx}. الآيدي: `{sid}`\n"
        else:
            subs_text += "⚠️ لا يوجد مشرفون مساعدون حالياً.\n"
            
        subs_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ إضافة مشرف جديد", callback_data='admin_add_sub')],
            [InlineKeyboardButton("➖ حذف مشرف حالي", callback_data='admin_del_sub')],
            [InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]
        ])
        await query.edit_message_text(subs_text, parse_mode='Markdown', reply_markup=subs_markup)

    elif data == 'admin_add_sub':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_sub_id'}
        await query.edit_message_text(
            "➕ **إضافة مشرف مساعد جديد:**\n\nأرسل الآن **آيدي (ID)** المستخدم لتفعيله كمشرف مساعد:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_manage_subadmins')]])
        )

    elif data == 'admin_del_sub':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_del_sub_id'}
        await query.edit_message_text(
            "➖ **حذف مشرف مساعد:**\n\nأرسل الآن **آيدي (ID)** المشرف المراد إزالته من الإدارة:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_manage_subadmins')]])
        )

    elif data == 'admin_manage_forced':
        if user_id != ADMIN_ID:
            await query.answer("❌ هذا الأمر مخصص للمسؤول الأساسي فقط!", show_alert=True)
            return
        channels = get_forced_channels()
        ch_text = "📢 **قنوات الاشتراك الإجباري الحالية:**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        if channels:
            for idx, (username, title) in enumerate(channels, 1):
                ch_text += f"{idx}. العنوان: {title} ⟵ المعرف: `{username}`\n"
        else:
            ch_text += "⚠️ لا توجد قنوات اشتراك إجباري مفعلة حالياً.\n"
            
        ch_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ إضافة قناة اشتراك إجباري", callback_data='admin_add_forced')],
            [InlineKeyboardButton("➖ حذف قناة اشتراك إجباري", callback_data='admin_del_forced')],
            [InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]
        ])
        await query.edit_message_text(ch_text, parse_mode='Markdown', reply_markup=ch_markup)

    elif data == 'admin_add_forced':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_forced_add'}
        await query.edit_message_text(
            "➕ **إضافة قناة اشتراك إجباري جديدة:**\n\n"
            "أرسل (معرف القناة مع @).\n"
            "مثال: `@DigitalHubOrders`\n"
            "*(سيتم قبولها فوراً وبدون تعقيد!)*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_manage_forced')]])
        )

    elif data == 'admin_del_forced':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_forced_del'}
        await query.edit_message_text(
            "➖ **حذف قناة اشتراك إجباري:**\n\nأرسل الآن **معرف القناة (يبدأ بـ @)** المراد حذفها:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_manage_forced')]])
        )

    elif data == 'admin_send_bonus':
        if user_id != ADMIN_ID:
            await query.answer("❌ هذا الأمر مخصص للمسؤول الأساسي فقط!", show_alert=True)
            return
        admin_state[user_id] = {'action': 'waiting_for_bonus_amount'}
        await query.edit_message_text(
            "🎁 **إرسال هدية مالية (Bonus) لجميع المستخدمين:**\n\n"
            "أرسل الآن **المبلغ بالدولار ($)** الذي تريد إضافته لكل مشترك في البوت دفعة واحدة:\n"
            "*(مثال: `0.05` أو `0.10`)*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]])
        )

    elif data == 'admin_reset_balances':
        if user_id != ADMIN_ID:
            await query.answer("❌ هذا الأمر مخصص للمسؤول الأساسي فقط!", show_alert=True)
            return
        
        try:
            res = supabase.table("users").select("user_id").execute()
            users = res.data if hasattr(res, 'data') else []
            for u in users:
                supabase.table("users").update({"balance": 0.0}).eq("user_id", u["user_id"]).execute()
        except Exception:
            pass
            
        await query.answer("✅ تمت عملية التصفير بنجاح تام وبصمت!", show_alert=True)
        await query.edit_message_text(
            "🧹 **تم تصفير جميع أرصدة المستخدمين في البوت بنجاح!**\n\n"
            "⭐ أصبحت جميع الأرصدة الآن `0.00$` وبدون إزعاج المستخدمين.",
            parse_mode='Markdown',
            reply_markup=get_admin_keyboard()
        )

    elif data == 'admin_ban_user':
        if not is_admin_or_sub(user_id): return
        admin_state[user_id] = {'action': 'waiting_for_ban_id'}
        await query.edit_message_text(
            "🚫 **حظر / إلغاء حظر مستخدم:**\n\n"
            "أرسل الآن **آيدي (ID)** المستخدم لتبديل حالته (إذا كان محظوراً يتم فك حظره، وإذا كان نشطاً يتم حظره):",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]])
        )

    elif data == 'admin_broadcast':
        if not is_admin_or_sub(user_id): return
        admin_state[user_id] = {'action': 'waiting_for_broadcast'}
        await query.edit_message_text(
            "📢 **قسم الإذاعة الشاملة الضخمة:**\n\n"
            "أرسل الآن **الرسالة، الصورة، الفيديو، أو المنشور** الذي تريد إذاعته لجميع مستخدمي البوت النشطين.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]])
        )

    else:
        await query.edit_message_text(
            "🛠 **هذا القسم قيد التجهيز والتطوير البرمجي حالياً...**",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
        )

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("deposit_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="حدث خطأ في عملية الدفع، يرجى المحاولة لاحقاً.")

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    
    if payload.startswith("deposit_"):
        try:
            _, target_user_id, amount_str = payload.split('_')
            target_user_id = int(target_user_id)
            amount = float(amount_str)
            
            db_update_balance(target_user_id, amount, mode="add")
            
            await update.message.reply_text(
                f"🎉 **تمت عملية الدفع بنجاح الشحن الفوري بالنجوم!**\n\n"
                f"⭐ تم إضافه رصيد بقيمة: **`${amount:.2f}`** إلى حسابك.\n"
                f"🚀 يمكنك الآن استخدام رصيدك في شراء الأرقام والخدمات فوراً!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
            )
        except Exception:
            pass

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_subbed, not_subbed_list = await check_forced_subscription(user_id, context.bot)
    if not is_subbed:
        sub_buttons = []
        for ch_username, ch_title in not_subbed_list:
            clean_ch = ch_username.replace("@", "")
            sub_buttons.append([InlineKeyboardButton(f"📢 انضم إلى قناة {ch_title}", url=f"https://t.me/{clean_ch}")])
        sub_buttons.append([InlineKeyboardButton("🔄 • تحققت من الاشتراكات •", callback_data='main_menu')])
        
        await update.message.reply_text(
            "📬| لطفاً عليك الاشتراك في قنوات البوت أولاً اشترك ثم اضغط على  /start للتحقق ✅:",
            reply_markup=InlineKeyboardMarkup(sub_buttons)
        )
        return

    text_content = update.message.text.strip() if update.message.text else ""

    if text_content and not (is_admin_or_sub(user_id) and user_id in admin_state):
        try:
            res = supabase.table("promo_codes").select("*").eq("code", text_content).execute()
            rows = res.data if hasattr(res, 'data') else []
            if rows:
                promo = rows[0]
                amount, max_uses, used_count = float(promo["amount"]), int(promo["max_uses"]), int(promo["used_count"])
                
                if used_count >= max_uses:
                    await update.message.reply_text("❌ **عذراً، هذا الكود استنفد الحد الأقصى لعدد مرات الاستخدام وانتهت صلاحيته.**")
                    return
                
                used_check = supabase.table("user_promo_uses").select("*").eq("user_id", user_id).eq("code", text_content).execute()
                used_rows = used_check.data if hasattr(used_check, 'data') else []
                if used_rows:
                    await update.message.reply_text("⚠️ **عذراً، لقد قمت باستخدام هذا الكود مسبقاً ولا يمكنك استخدامه مرة أخرى.**")
                    return
                
                db_update_balance(user_id, amount, mode="add")
                supabase.table("promo_codes").update({"used_count": used_count + 1}).eq("code", text_content).execute()
                supabase.table("user_promo_uses").insert({"user_id": user_id, "code": text_content}).execute()
                
                u_data = db_get_user(user_id)
                await update.message.reply_text(
                    f"🎉 **تهانينا! تم تفعيل كود الهدية بنجاح.** 🎁\n\n"
                    f"💰 **تمت إضافة:** `${amount:.2f}` إلى رصيدك.\n"
                    f"⭐ **رصيدك الحالي:** `${u_data['balance']:.2f}`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                )
                return
        except Exception as promo_err:
            print(f"Promo error: {promo_err}")

    if is_admin_or_sub(user_id) and user_id in admin_state:
        action = admin_state[user_id].get('action')
        
        if action == 'waiting_for_promo_details':
            try:
                parts = text_content.split()
                if len(parts) < 3:
                    raise ValueError()
                
                code_str = parts[0]
                amount_val = float(parts[1])
                max_uses_val = int(parts[2])
                
                if amount_val <= 0 or max_uses_val <= 0:
                    raise ValueError()
                
                supabase.table("promo_codes").upsert({"code": code_str, "amount": amount_val, "max_uses": max_uses_val, "used_count": 0}).execute()
                
                admin_state.pop(user_id, None)
                await update.message.reply_text(
                    f"✅ **تم إنشاء كود الهدية بنجاح تام!** 🎟️\n\n"
                    f"▫️ الكود: `{code_str}`\n"
                    f"▫️ القيمة: `${amount_val:.2f}`\n"
                    f"▫️ عدد المستخدمين المسموح: `{max_uses_val} شخص`",
                    parse_mode='Markdown',
                    reply_markup=get_admin_keyboard()
                )
                return
            except Exception:
                await update.message.reply_text("❌ الصيغة خاطئة! أرسل (الكود والمبلغ وعدد المرات) بمسافات صحيحة.\nمثال: `WELCOME 0.50 100`")
                return

        elif action == 'waiting_for_gift_id':
            try:
                target_id = int(text_content)
                admin_state[user_id] = {'action': 'waiting_for_gift_amount', 'target_user_id': target_id}
                await update.message.reply_text(
                    f"👤 **تم استقبال الآيدي:** `{target_id}`\n\n💰 **الخطوة الثانية:** أرسل الآن **المبلغ بالدولار ($)** المراد إرساله هدية:",
                    parse_mode='Markdown'
                )
                return
            except ValueError:
                await update.message.reply_text("❌ الآيدي يجب أن يكون أرقام صحيحة فقط. أعد إرسال الآيدي:")
                return

        elif action == 'waiting_for_gift_amount':
            try:
                gift_amount = float(text_content)
                if gift_amount <= 0:
                    raise ValueError()
                
                st_data = admin_state.pop(user_id)
                target_id = st_data['target_user_id']
                
                db_update_balance(target_id, gift_amount, mode="add")
                
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"🎁 **تهانينا القلبية! وصلتك هدية مالية خاصة من الإدارة بقيمة `${gift_amount:.2f}`** 🚀✨",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

                await update.message.reply_text(
                    f"✅ **تم إرسال الهدية المالية بنجاح تام!**\n\n👤 للمستخدم: `{target_id}`\n🎁 مبلغ الهدية: `${gift_amount:.2f}`",
                    parse_mode='Markdown',
                    reply_markup=get_admin_keyboard()
                )
                return
            except ValueError:
                await update.message.reply_text("❌ مبلغ غير صالح! أرسل رقماً صحيحاً أو عشرياً (مثل 1.50).")
                return

        elif action == 'waiting_for_add_bal_id':
            try:
                target_id = int(text_content)
                admin_state[user_id] = {'action': 'waiting_for_add_bal_amount', 'target_user_id': target_id}
                await update.message.reply_text(
                    f"👤 **تم استقبال الآيدي:** `{target_id}`\n\n💰 **الخطوة الثانية:** أرسل الآن **المبلغ بالدولار ($)** المراد إضافته:",
                    parse_mode='Markdown'
                )
                return
            except ValueError:
                await update.message.reply_text("❌ الآيدي يجب أن يكون أرقام صحيحة فقط. أعد إرسال الآيدي:")
                return

        elif action == 'waiting_for_add_bal_amount':
            try:
                amount = float(text_content)
                if amount <= 0:
                    raise ValueError()
                
                st_data = admin_state.pop(user_id)
                target_id = st_data['target_user_id']
                
                db_update_balance(target_id, amount, mode="add")
                
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"🎉 **تمت إضافة مبلغ `${amount:.2f}` إلى رصيدك من قبل الإدارة!**",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

                await update.message.reply_text(
                    f"✅ **تمت إضافة الرصيد بنجاح!**\n\n👤 للمستخدم: `{target_id}`\n⭐ المبلغ المضاف: `${amount:.2f}`",
                    parse_mode='Markdown',
                    reply_markup=get_admin_keyboard()
                )
                return
            except ValueError:
                await update.message.reply_text("❌ مبلغ غير صالح! أرسل رقماً صحيحاً أو عشرياً (مثل 0.10).")
                return

        elif action == 'waiting_for_deduct_bal_id':
            try:
                target_id = int(text_content)
                admin_state[user_id] = {'action': 'waiting_for_deduct_bal_amount', 'target_user_id': target_id}
                await update.message.reply_text(
                    f"👤 **تم استقبال الآيدي:** `{target_id}`\n\n💰 **الخطوة الثانية:** أرسل الآن **المبلغ بالدولار ($)** المراد خصمه:",
                    parse_mode='Markdown'
                )
                return
            except ValueError:
                await update.message.reply_text("❌ الآيدي يجب أن يكون أرقام صحيحة فقط. أعد إرسال الآيدي:")
                return

        elif action == 'waiting_for_deduct_bal_amount':
            try:
                amount = float(text_content)
                if amount <= 0:
                    raise ValueError()
                
                st_data = admin_state.pop(user_id)
                target_id = st_data['target_user_id']
                
                db_update_balance(target_id, amount, mode="deduct")
                
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"⚠️ **تم خصم مبلغ `${amount:.2f}` من رصيدك بواسطة الإدارة.**",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

                await update.message.reply_text(
                    f"✅ **تم خصم الرصيد بنجاح!**\n\n👤 للمستخدم: `{target_id}`\n⭐ المبلغ المخصوم: `${amount:.2f}`",
                    parse_mode='Markdown',
                    reply_markup=get_admin_keyboard()
                )
                return
            except ValueError:
                await update.message.reply_text("❌ مبلغ غير صالح! أرسل رقماً صحيحاً أو عشرياً (مثل 0.50).")
                return

        elif action == 'waiting_for_reply_id':
            try:
                space_idx = text_content.find(' ')
                if space_idx == -1:
                    raise ValueError()
                target_id = int(text_content[:space_idx].strip())
                reply_msg = text_content[space_idx:].strip()
                
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"💬 **رسالة جديدة من إدارة البوت:**\n\n{reply_msg}",
                    parse_mode='Markdown'
                )
                await update.message.reply_text("✅ تم إرسال الرد إلى المستخدم بنجاح!", reply_markup=get_admin_keyboard())
                admin_state.pop(user_id, None)
                return
            except Exception:
                await update.message.reply_text("❌ صيغة خاطئة! أرسل الآيدي أولاً ثم مسافة ثم نص الرسالة.")
                return

        elif action == 'waiting_for_bonus_amount':
            try:
                bonus_amount = float(text_content)
                all_users = db_get_all_users()
                
                status_msg = await update.message.reply_text(f"🎁 **جاري توزيع هدية بقيمة `${bonus_amount:.2f}` لجميع المشتركين...**", parse_mode='Markdown')
                count = 0
                for uid in all_users:
                    db_update_balance(uid, bonus_amount, mode="add")
                    count += 1
                    try:
                        await context.bot.send_message(
                            chat_id=uid,
                            text=f"🎁 **تهانينا! وصلتك هدية مالية من الإدارة بقيمة `${bonus_amount:.2f}`** 🚀",
                            parse_mode='Markdown'
                        )
                        await asyncio.sleep(0.03)
                    except Exception:
                        pass
                
                await status_msg.edit_text(
                    f"✅ **تم توزيع الهدية بنجاح تام!**\n\n💰 المبلغ المضاف لكل فرد: `${bonus_amount:.2f}`\n👥 عدد المستفيدين: `{count} مشترك`",
                    parse_mode='Markdown',
                    reply_markup=get_admin_keyboard()
                )
                admin_state.pop(user_id, None)
                return
            except Exception:
                await update.message.reply_text("❌ مبلغ غير صالح! أرسل رقماً صحيحاً أو عشرياً (مثل 0.05).")
                return

        elif action == 'waiting_for_sub_id':
            try:
                sub_id = int(text_content)
                supabase.table("sub_admins").upsert({"admin_id": sub_id, "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}).execute()
                
                await update.message.reply_text(f"✅ تم تعيين المستخدم `{sub_id}` كـ **مشرف مساعد** بنجاح!", parse_mode='Markdown', reply_markup=get_admin_keyboard())
                try:
                    await context.bot.send_message(chat_id=sub_id, text="🌟 **مبروك! تم ترقيتك لتكون مشرفاً مساعداً في البوت.** أرسل /start لتظهر لك لوحة التحكم.", parse_mode='Markdown')
                except Exception:
                    pass
                admin_state.pop(user_id, None)
                return
            except Exception:
                await update.message.reply_text("❌ آيدي غير صالح!")
                return

        elif action == 'waiting_for_del_sub_id':
            try:
                sub_id = int(text_content)
                supabase.table("sub_admins").delete().eq("admin_id", sub_id).execute()
                
                await update.message.reply_text(f"✅ تم إزالة المشرف `{sub_id}` من قائمة الإدارة بنجاح.", parse_mode='Markdown', reply_markup=get_admin_keyboard())
                admin_state.pop(user_id, None)
                return
            except Exception:
                await update.message.reply_text("❌ آيدي غير صالح!")
                return

        elif action == 'waiting_for_forced_add':
            try:
                clean_text = text_content.strip()
                if not clean_text.startswith('@'):
                    await update.message.reply_text("❌ يجب أن تبدأ القناة بـ @ (مثال: `@DigitalHubOrders`)")
                    return
                
                parts = clean_text.split(maxsplit=1)
                ch_uname = parts[0]
                ch_ttl = parts[1] if len(parts) > 1 else "قناة الإشراك الإجباري"
                
                supabase.table("forced_channels").upsert({"channel_username": ch_uname, "channel_title": ch_ttl}).execute()
                
                await update.message.reply_text(f"✅ تم إضافة القناة `{ch_uname}` للاشتراك الإجباري بنجاح!", parse_mode='Markdown', reply_markup=get_admin_keyboard())
                admin_state.pop(user_id, None)
                return
            except Exception as e:
                await update.message.reply_text(f"❌ حدث خطأ أثناء الحفظ: {e}")
                return

        elif action == 'waiting_for_forced_del':
            try:
                ch_uname = text_content.strip()
                supabase.table("forced_channels").delete().eq("channel_username", ch_uname).execute()
                
                await update.message.reply_text(f"✅ تم حذف القناة `{ch_uname}` من الاشتراك الإجباري بنجاح.", parse_mode='Markdown', reply_markup=get_admin_keyboard())
                admin_state.pop(user_id, None)
                return
            except Exception:
                await update.message.reply_text("❌ خطأ، تأكد من كتابة معرف القناة الصحيح.")
                return

        elif action == 'waiting_for_ban_id':
            try:
                target_id = int(text_content)
                u_info = db_get_user(target_id)
                new_ban_status = 1 if u_info['is_banned'] == 0 else 0
                
                supabase.table("users").update({"is_banned": new_ban_status}).eq("user_id", target_id).execute()
                
                status_text = "حظر المستخدم بنجاح 🚫" if new_ban_status == 1 else "فك حظر المستخدم بنجاح ✅"
                await update.message.reply_text(f"✅ **{status_text}**\n🆔 الآيدي: `{target_id}`", parse_mode='Markdown', reply_markup=get_admin_keyboard())
                admin_state.pop(user_id, None)
                return
            except Exception:
                await update.message.reply_text("❌ آيدي غير صالح! أرسل أرقام الآيدي الصحيحة.")
                return

        elif action == 'waiting_for_broadcast':
            admin_state.pop(user_id, None)
            all_users = db_get_all_users()
            status_msg = await update.message.reply_text("🚀 **جاري بدء عملية الإذاعة الشاملة لجميع المستخدمين النشطين...**", parse_mode='Markdown')
            
            success_count = 0
            fail_count = 0
            for uid in all_users:
                try:
                    await update.message.copy(chat_id=uid)
                    success_count += 1
                    await asyncio.sleep(0.04)
                except Exception:
                    fail_count += 1

            await status_msg.edit_text(
                f"📊 **تقرير الإذاعة الشاملة والضخمة:**\n\n"
                f"✅ **تمت الإذاعة بنجاح إلى:** `{success_count} مشترك`\n"
                f"❌ **فشل (حظروا البوت أو توقفت حساباتهم):** `{fail_count} مشترك`\n"
                f"👥 **إجمالي المستهدفين:** `{len(all_users)} مشترك`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ عودة لوحة الأدمن", callback_data='admin_panel')]])
            )
            return

    if user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_hm_link':
        link_text = text_content
        admin_state[user_id]['link'] = link_text
        admin_state[user_id]['action'] = 'waiting_for_hm_quantity'
        
        await update.message.reply_text(
            "📦 **الخطوة الثانية للطلب:**\nأرسل الآن **الكمية المطلوبة** (أرقام صحيحة فقط):",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='boosting_services')]])
        )
        return

    elif user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_hm_quantity':
        qty_text = text_content
        try:
            quantity = int(qty_text)
            st_data = admin_state.get(user_id, {})
            min_q = int(st_data.get('min_qty', 100))
            max_q = int(st_data.get('max_qty', 1000000))

            if quantity < min_q or quantity > max_q:
                await update.message.reply_text(
                    f"❌ **الكمية غير مطابقة لشروط الخدمة!**\nيجب أن تكون بين `{min_q}` و `{max_q}`.\nأرسل الكمية الصحيحة:",
                    parse_mode='Markdown'
                )
                return

            service_id = st_data.get('service_id')
            link = st_data.get('link')
            service_name = st_data.get('service_name', 'خدمة رشق')
            
            serv_rate = st_data.get('service_rate', 0.0)
            if serv_rate <= 0:
                for s in st_data.get('hm_services', []):
                    if str(s.get('service')) == str(service_id):
                        try:
                            orig_rate = float(s.get('rate', 0.0))
                        except ValueError:
                            orig_rate = 0.0
                        serv_rate = round(orig_rate * 3.0, 2)
                        break

            cost = round((float(quantity) / 1000.0) * serv_rate, 2)
            if cost <= 0:
                cost = 0.01

            admin_state[user_id]['quantity'] = quantity
            admin_state[user_id]['cost'] = cost

            u_data = db_get_user(user_id)

            confirm_text = (
                "📋 **تأكيد تفاصيل الطلب:**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔹 **اسم الخدمة:** `{service_name}`\n"
                f"🔗 **الرابط:** `{mask_link(link)}`\n"
                f"📦 **الكمية المطلوبة:** `{quantity}`\n"
                f"💰 **التكلفة الإجمالية:** `${cost:.2f}`\n\n"
                f"⭐ **رصيدك الحالي:** `${u_data['balance']:.2f}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "👇 انقر على زر التأكيد أدناه لإتمام الطلب:"
            )

            confirm_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ تأكيد وإتمام الطلب", callback_data='confirm_hm_order')],
                [InlineKeyboardButton("❌ إلغاء الطلب", callback_data='cancel_hm_order')]
            ])

            await update.message.reply_text(confirm_text, parse_mode='Markdown', reply_markup=confirm_keyboard)
        except ValueError:
            await update.message.reply_text("❌ الرجاء إدخال رقم صحيح وموجب للكمية:", parse_mode='Markdown')
        return

    if user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_transfer_id':
        try:
            target_id = int(text_content)
            if target_id == user_id:
                await update.message.reply_text("❌ لا يمكنك التحويل إلى نفس حسابك! أرسل آيدي صحيح:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='main_menu')]]))
                return
            
            target_data = db_get_user(target_id)
            admin_state[user_id] = {'action': 'waiting_for_transfer_amount', 'target_id': target_id}
            
            await update.message.reply_text(
                f"👤 **تم العثور على المستخدم بنجاح!**\n🆔 آيدي المستلم: `{target_id}`\n\n💰 **الخطوة الثانية:**\nأرسل الآن **المبلغ بالدولار ($)** المراد تحويله في رسالة:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='main_menu')]])
            )
        except ValueError:
            await update.message.reply_text("❌ الآيدي يجب أن يكون أرقام صحيحة فقط. أعد إرسال الآيدي:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='main_menu')]]))
        return

    elif user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_transfer_amount':
        try:
            amount = float(text_content)
            if amount <= 0:
                raise ValueError()
            
            st_data = admin_state.pop(user_id)
            target_id = st_data['target_id']
            sender_data = db_get_user(user_id)
            
            if sender_data['balance'] < amount:
                await update.message.reply_text(
                    f"❌ **رصيدك غير كافٍ لإتمام التحويل!**\n⭐ رصيدك الحالي: `${sender_data['balance']:.2f}`\n\nأرسل مبلغاً أقل أو اشحن رصيدك:",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                )
                return
            
            db_update_balance(user_id, amount, mode="deduct")
            db_update_balance(target_id, amount, mode="add")
            
            await update.message.reply_text(
                f"✅ **تم تحويل الرصيد بنجاح!**\n\n"
                f"👤 إلى الآيدي: `{target_id}`\n"
                f"⭐ المبلغ المحول: `${amount:.2f}`\n"
                f"💎 رصيدك الجديد: `${db_get_user(user_id)['balance']:.2f}`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
            )
            
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"🎁 **لقد استلمت حوالة رصيد جديدة!**\n\n⭐ المبلغ المستلم: `${amount:.2f}`\n👤 من المستخدم: `{user_id}`",
                    parse_mode='Markdown'
                )
            except Exception:
                pass
            return
        except ValueError:
            await update.message.reply_text("❌ الرجاء إدخال رقم صحيح وموجب للمبلغ بالدولار:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='main_menu')]]))
            return

    if user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_deposit':
        admin_state.pop(user_id, None)
        text = update.message.text or update.message.caption or "إيصال مرسل (صورة)"
        
        await update.message.reply_text(
            "🔄 **جاري التحقق من رقم العملية يرجى الإنتظار...**",
            parse_mode='Markdown'
        )

        admin_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ اعتماد $1", callback_data=f"approve_deposit_{user_id}_1.0"),
                InlineKeyboardButton("➕ اعتماد $5", callback_data=f"approve_deposit_{user_id}_5.0")
            ],
            [
                InlineKeyboardButton("➕ اعتماد $10", callback_data=f"approve_deposit_{user_id}_10.0"),
                InlineKeyboardButton("✍️ إرسال مبلغ مخصص", callback_data=f"custom_deposit_{user_id}")
            ],
            [
                InlineKeyboardButton("❌ رفض (لا يوجد رصيد)", callback_data=f"reject_deposit_{user_id}")
            ]
        ])
        
        all_admins = [ADMIN_ID] + get_all_sub_admins()
        for adm_id in set(all_admins):
            try:
                await context.bot.send_message(
                    chat_id=adm_id,
                    text=(
                        f"📥 **طلب شحن رصيد جديد بانتظار التحقق والإشراف!**\n\n"
                        f"👤 المستخدم: {update.effective_user.full_name}\n"
                        f"🆔 الآيدي: `{user_id}`\n"
                        f"💬 تفاصيل العملية أو رقمها:\n`{text}`"
                    ),
                    parse_mode='Markdown',
                    reply_markup=admin_markup
                )
            except Exception:
                pass
        return

    text = text_content
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📥 **رسالة جديدة من مستخدم:**\n\n👤 المستخدم: {update.effective_user.full_name}\n🆔 الآيدي: `{user_id}`\n🔢 النص:\n`{text}`",
            parse_mode='Markdown'
        )
    except Exception:
        pass

if __name__ == '__main__':
    try:
        print("🟡 جاري تهيئة الاتصال السحابي وبدء تشغيل البوت...")
        init_db()
        app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
        
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
        app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
        
        print("🟢 البوت يعمل بكامل طاقته على قاعدة البيانات السحابية Supabase بدلاً من الملفات المحلية!")
        app.run_polling()
    except Exception as e:
        print(f"❌ حدث خطأ أدى لتوقف البوت: {e}")
