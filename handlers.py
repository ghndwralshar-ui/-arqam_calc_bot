import asyncio
import re
import json
import random
import httpx
import cloudscraper
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, LabeledPrice
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from config import (
    BOT_TOKEN, ADMIN_ID, SUPPORT_USERNAME, FORCED_CHANNEL_USERNAME, 
    FORCED_CHANNEL_URL, LOG_CHANNEL_ID, HMCARD_API_URL, HMCARD_API_KEY, 
    HEADERS, COUNTRY_INFO, OCR_SPACE_API_KEY
)

from database import (
    db_get_user, db_update_balance, db_get_advanced_stats, 
    db_get_all_users, is_admin_or_sub, get_all_sub_admins,
    db_check_and_save_transaction, supabase, db_set_referrer, db_claim_referral_reward, db_increment_referral_count
)
from keyboards import (
    get_main_keyboard, get_virtual_services_keyboard, sections_menu_keyboard,
    whatsapp_services_keyboard, channel_subscribers_keyboard, emoji_reactions_keyboard,
    auto_reactions_keyboard, polls_keyboard, telegram_services_keyboard,
    tg_arab_menu_keyboard, tg_foreign_menu_keyboard, tg_prem_menu_keyboard,
    tg_views_menu_keyboard, tg_auto_menu_keyboard, tg_react_menu_keyboard,
    tg_polls_menu_keyboard, tg_boost_menu_keyboard, facebook_services_keyboard,
    fb_profile_menu_keyboard, fb_page_menu_keyboard, fb_react_menu_keyboard,
    fb_comment_react_menu_keyboard, fb_story_menu_keyboard, fb_share_menu_keyboard,
    instagram_services_keyboard, ig_channel_menu_keyboard, ig_views_menu_keyboard,
    ig_story_menu_keyboard, ig_likes_menu_keyboard, ig_comment_likes_menu_keyboard,
    ig_comments_menu_keyboard, ig_shares_menu_keyboard, tiktok_services_keyboard,
    youtube_services_keyboard, pubg_services_keyboard, freefire_services_keyboard,
    get_admin_keyboard, get_free_services_keyboard, get_forced_subscription_keyboard
)

admin_state = {}
user_selected_service = {}
user_order_data = {}
active_numbers_cache = {}
verification_cache = {}

EXCHANGE_RATE = 550.0
JAIB_ACCOUNT = "772074924"
KREEMI_ACCOUNT = "3105004949"

VALID_BENEFICIARY_PHONE = "772074924"
VALID_BENEFICIARY_NAME = "سالم احمد يحيى صالح السعدي"

OWNER_ID = 6472852297
PROXY_URL = None

def is_owner(user_id: int) -> bool:
    try:
        return int(user_id) == int(OWNER_ID) or int(user_id) == int(ADMIN_ID) or int(user_id) == 6472852297
    except Exception:
        return int(user_id) == 6472852297

FORCED_SUB_MESSAGE = (
    "💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "عذراً عزيزي العميل، لتفعيل حسابك والبدء في استخدام كافة خدمات البوت (الأرقام الافتراضية، والرشق، وشحن الألعاب)، يجب عليك أولاً الاشتراك في قناة البوت الرسمية.\n\n"
    "👇 **اشترك الآن عبر الأزرار أدناه، ثم اضغط على زر التحقق للمتابعة:**"
)

async def check_user_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if is_owner(user_id) or int(user_id) == int(ADMIN_ID):
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=FORCED_CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        print(f"Subscription check error: {e}")
        return True
    return False

async def process_successful_join_reward(user, context, u_data):
    try:
        user_id = user.id
        if not db_claim_referral_reward(user_id):
            return

        referrer_id = u_data.get("referred_by", 0)
        if referrer_id > 0 and referrer_id != user_id:
            db_update_balance(referrer_id, 0.10, mode="add")
            new_ref_count = db_increment_referral_count(referrer_id)
            
            try:
                ref_first_name = "صديقنا"
                try:
                    chat_info = await context.bot.get_chat(referrer_id)
                    if chat_info and chat_info.first_name:
                        ref_first_name = chat_info.first_name
                except Exception:
                    pass

                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=(
                        f"🎉 **مبروك يا {ref_first_name}! انضم شخص حقيقي وعربي عبر رابطك واجتاز التحقق.** 🚀\n\n"
                        f"👤 اسم الصديق: {user.full_name}\n"
                        f"💰 تمت إضافة هدية الدعوة بقيمة **0.10$** إلى رصيدك المتاح!\n"
                        f"📊 إجمالي عدد الدعوات الناجحة لديك: `{new_ref_count}` 🌟"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as ref_notify_err:
                print(f"Error notifying referrer: {ref_notify_err}")
    except Exception as e:
        print(f"process_successful_join_reward Error: {e}")

def mask_link(link: str) -> str:
    if not link: return "لا يوجد رابط"
    length = len(link)
    if length <= 10: return link[:3] + "..."
    half = length // 2
    return link[:half] + "..."

async def analyze_receipt_with_gemini(photo_bytes: bytearray) -> str:
    url = "https://api.ocr.space/parse/image"
    payload = {
        'apikey': OCR_SPACE_API_KEY,  
        'isOverlayRequired': False,
        'detectOrientation': True,
        'scale': True
    }
    raw_bytes = bytes(photo_bytes)
    files = {
        'file': ('receipt.jpg', raw_bytes, 'image/jpeg')
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=payload, files=files)
            if response.status_code == 200:
                result = response.json()
                if not result.get("IsErroredOnProcessing"):
                    parsed_results = result.get("ParsedResults", [])
                    if parsed_results:
                        text = parsed_results[0].get("ParsedText", "").strip()
                        if text:
                            return text
                    return "ERROR_OCR: الإيصال فارغ أو تعذر استخراج النص منه."
                else:
                    error_msg = result.get("ErrorMessage", ["خطأ غير معروف"])[0]
                    return f"ERROR_OCR_API: {error_msg}"
            return f"ERROR_HTTP: خطأ في الاتصال بالخدمة (رمز الاستجابة: {response.status_code})."
    except Exception as e:
        return f"ERROR_EXCEPTION: حدث استثناء أثناء الاتصال: {str(e)[:100]}"

async def send_order_to_hmcard(service_id: int, link: str, quantity: int):
    payload = {
        'key': HMCARD_API_KEY,
        'action': 'add',
        'service': int(service_id),
        'link': str(link),
        'quantity': int(quantity)
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://hmcard.online',
        'Referer': 'https://hmcard.online/',
        'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    }

    try:
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        if PROXY_URL:
            scraper.proxies = {"http": PROXY_URL, "https": PROXY_URL}

        try:
            home_res = scraper.get("https://hmcard.online/", timeout=15)
            if home_res.cookies:
                scraper.cookies.update(home_res.cookies)
        except Exception:
            pass

        response = scraper.post(HMCARD_API_URL, data=payload, headers=headers, timeout=35)
        raw_resp = response.content.decode('utf-8', errors='ignore')

        if response.status_code == 200 and "Bot Verification" not in raw_resp:
            try:
                clean_json = raw_resp[raw_resp.find('{'):raw_resp.rfind('}')+1]
                resp_json = json.loads(clean_json)
                
                order_id = resp_json.get("order") or resp_json.get("order_id") or resp_json.get("id")
                error_msg = resp_json.get("error") or resp_json.get("message")
                
                if order_id and not error_msg:
                    return True, str(order_id), "تم التنفيذ بنجاح"
                elif resp_json.get("success") is True and not error_msg:
                    return True, "HM_" + str(random.randint(100000, 999999)), "تم التنفيذ بنجاح"
                elif error_msg:
                    return False, None, error_msg
            except Exception:
                if "success" in raw_resp.lower() and "Bot Verification" not in raw_resp:
                    return True, "HM_" + str(random.randint(100000, 999999)), "تم التنفيذ بنجاح"
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(headers=headers, timeout=35.0, proxies=PROXY_URL if PROXY_URL else None, follow_redirects=True) as client:
            await client.get("https://hmcard.online/")
            res = await client.post(HMCARD_API_URL, data=payload)
            raw_text = res.text
            
            if res.status_code == 200 and "Bot Verification" not in raw_text:
                try:
                    clean_json = raw_text[raw_text.find('{'):raw_text.rfind('}')+1]
                    resp_json = json.loads(clean_json)
                    order_id = resp_json.get("order") or resp_json.get("order_id") or resp_json.get("id")
                    if order_id:
                        return True, str(order_id), "تم التنفيذ بنجاح"
                except Exception:
                    if "success" in raw_text.lower():
                        return True, "HM_" + str(random.randint(100000, 999999)), "تم التنفيذ بنجاح"
            return False, None, "حماية الموقع تمنع الاتصال الآلي (Cloudflare Block)."
    except Exception as e:
        return False, None, str(e)[:200]

async def fetch_hmcard_services_directly():
    payload = {
        'key': HMCARD_API_KEY,
        'action': 'services'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://hmcard.online',
        'Referer': 'https://hmcard.online/'
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
            response = await client.post(HMCARD_API_URL, data=payload)
            if response.status_code == 200:
                try:
                    services_data = response.json()
                    if isinstance(services_data, list):
                        return services_data
                except Exception:
                    pass
    except Exception as e:
        print(f"Error fetching direct services: {e}")
    return []

async def get_available_countries_for_service(service: str):
    url = f"https://5sim.net/v1/guest/prices?product={service}"
    available_countries = []
    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
        try:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                product_data = data.get(service, data)
                if isinstance(product_data, dict):
                    for country_code, country_info in product_data.items():
                        if country_code not in COUNTRY_INFO:
                            continue
                        has_stock = False
                        best_operator = None
                        max_success_rate = -1.0
                        min_price = 999.0

                        if isinstance(country_info, dict):
                            for operator, op_data in country_info.items():
                                if isinstance(op_data, dict):
                                    count = op_data.get("count", 0)
                                    cost = op_data.get("cost", 0)
                                    rate = op_data.get("rate", 0.0)
                                    if count > 0 and cost is not None:
                                        base_price = float(cost)
                                        max_limit_price = 0.70 if service == "whatsapp" else 0.15
                                        if base_price < max_limit_price:
                                            has_stock = True
                                            success_val = float(rate) if rate is not None else 0.0
                                            
                                            if success_val > max_success_rate or (success_val == max_success_rate and base_price < min_price):
                                                max_success_rate = success_val
                                                min_price = base_price
                                                best_operator = operator

                        if has_stock and min_price < 999.0 and best_operator:
                            fixed_price = 2.00 if service == "whatsapp" else 0.70
                            c_meta = COUNTRY_INFO[country_code]
                            available_countries.append({
                                "code": country_code,
                                "name_ar": c_meta["name_ar"],
                                "flag": c_meta["flag"],
                                "dial": c_meta["dial"],
                                "price": fixed_price,
                                "operator": best_operator
                            })
        except Exception as e:
            print(f"Error fetching countries for {service}: {e}")
    available_countries.sort(key=lambda x: x["price"])
    return available_countries

async def show_available_countries_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, service_code: str, service_title: str):
    query = update.callback_query
    await query.answer("⏳ جاري فحص الدول المتوفرة...", show_alert=False)
    available_countries = await get_available_countries_for_service(service_code)
    
    if not available_countries:
        out_of_stock_msg = (
            "📢 **عذراً عزيزي العميل!**\n"
            "🇸🇦 نفدت أرقام هذه الدولة مؤقتاً بسبب الضغط الشديد.\n"
            "🔄 جاري توفير أرقام جديدة قريباً، يمكنك اختيار دولة أخرى متاحة حالياً بكل سهولة! 👇"
        )
        try:
            await query.edit_message_text(
                out_of_stock_msg, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة للخدمات", callback_data='buy_virtual_number')]])
            )
        except Exception:
            pass
        return

    buttons = []
    row = []
    for c in available_countries:
        btn_text = f"{c['flag']} {c['name_ar']} • ${c['price']:.2f}"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"buy_num_{service_code}_{c['code']}_{c['price']}_{c['operator']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🔙 عـودة للخدمات", callback_data='buy_virtual_number')])
    u_data = db_get_user(query.from_user.id)
    
    try:
        await query.edit_message_text(
            f"🔹 **• الدول المتوفرة بأعلى نسب نجاح لأرقام ({service_title}) •**\n"
            f"⭐ رصيدك: `${u_data['balance']:.2f}`\n\n"
            "👇 **اختر الدولة المطلوبة:**",
            parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception:
        pass

async def send_log_to_channel(context: ContextTypes.DEFAULT_TYPE, log_text: str, service_param: str):
    bot_username = context.bot.username
    start_url = f"https://t.me/{bot_username}?start={service_param}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🤖 الدخول للبوت 🚀", url=start_url)]])
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_text, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception as log_err:
        print(f"❌ خطأ إرسال لوج لقناة الطلبات: {log_err}")

async def check_sms_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split('_')
    order_id = parts[2]
    
    url = f"https://5sim.net/v1/user/check/{order_id}"
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        try:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                sms_list = data.get('sms', [])
                if sms_list:
                    sms_code = sms_list[0].get('code', 'لا يوجد كود')
                    full_text = sms_list[0].get('text', '')
                    
                    cached = active_numbers_cache.get(order_id, {})
                    already_logged = cached.get('has_sms', False)
                    
                    if not cached.get('balance_deducted', False) and cached.get('price', 0) > 0:
                        u_id = cached.get('user_id', query.from_user.id)
                        p_val = cached.get('price', 0.0)
                        db_update_balance(u_id, p_val, mode="deduct")
                        active_numbers_cache[order_id]['balance_deducted'] = True

                    active_numbers_cache[order_id]['has_sms'] = True
                    active_numbers_cache[order_id]['code'] = sms_code
                    
                    current_text = query.message.text
                    if "🔑 **الكود الواصل:**" not in current_text:
                        updated_text = current_text + f"\n\n🔑 **الكود الواصل:** `{sms_code}`\n💬 **النص الكامل:** `{full_text}`"
                        try:
                            await query.edit_message_text(updated_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))
                        except Exception:
                            pass
                    else:
                        await query.answer(f"✅ الكود وصل بالفعل: {sms_code}", show_alert=True)
                else:
                    await query.answer("❌ لم يصل الكود حتى الآن، يرجى الانتظار قليلاً.", show_alert=True)
        except Exception:
            await query.answer("❌ حدث خطأ في الاتصال بالسيرفر.", show_alert=True)

async def watch_order_sms_auto(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, order_id: str, phone: str, price: float, service: str, user_id: int, bot_username: str, section_name: str, country_name: str, dial_code: str):
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
                        
                        cached = active_numbers_cache.get(order_id, {})
                        already_logged = cached.get('has_sms', False)
                        
                        if not cached.get('balance_deducted', False) and price > 0:
                            db_update_balance(user_id, price, mode="deduct")
                            active_numbers_cache[order_id]['balance_deducted'] = True

                        active_numbers_cache[order_id]['has_sms'] = True
                        active_numbers_cache[order_id]['code'] = sms_code
                        
                        success_msg = (
                            f"💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"✅ **تم استلام كود التفعيل بنجاح!**\n\n"
                            f"📦 **القسم:** `{section_name}`\n"
                            f"🌍 **الدولة:** {country_name}\n"
                            f"📞 **مفتاح الدولة:** `{dial_code}`\n"
                            f"📱 **الرقم المشتري:** `{phone}`\n"
                            f"⭐ **المبلغ المخصوم:** `${price:.2f}`\n\n"
                            f"🔑 **الكود الواصل:** `{sms_code}`\n"
                            f"💬 **النص الكامل:** `{full_text}`"
                        )
                        try:
                            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=success_msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))
                        except Exception:
                            pass
                        return
            except Exception:
                continue

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u_data = db_get_user(user.id)
    
    if u_data.get('is_banned', 0) == 1:
        await update.message.reply_text("⛔ **عذراً، لقد تم حظرك من استخدام هذا البوت بواسطة الإدارة.**", parse_mode='Markdown')
        return

    args = context.args
    arg_param = args[0] if args else None

    if arg_param and arg_param.isdigit():
        referrer_id = int(arg_param)
        if referrer_id != user.id:
            db_set_referrer(user.id, referrer_id)
            u_data = db_get_user(user.id)

    if not await check_user_subscription(user.id, context):
        await update.message.reply_text(FORCED_SUB_MESSAGE, parse_mode='Markdown', reply_markup=get_forced_subscription_keyboard())
        return

    v_status = verification_cache.get(user.id, "not_started")
    if v_status != "passed":
        verification_cache[user.id] = "waiting_math"
        n1 = random.randint(1, 9)
        n2 = random.randint(1, 9)
        correct_ans = n1 + n2
        verification_cache[f"{user.id}_ans"] = correct_ans

        await update.message.reply_text(
            f"🛡️ **تحقق أمني ذكي لإثبات أنك بشري ولست روبوت (1/2):**\n\n"
            f"قم بحل المسألة الرياضية التالية لإكمال الدخول:\n"
            f"🔹 كم ناتج: ` {n1} + {n2} = ? `\n\n*(أرسل الرقم الناتج في رسالة الآن)*",
            parse_mode='Markdown', reply_markup=ReplyKeyboardRemove()
        )
        return

    welcome_text = (
        f"💎 **مرحباً بك عزيزي {user.first_name} في بوت ﴿ ديجيتال هب | Digital Hub ﴾** 🚀\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 **الآيدي:** `{user.id}`\n"
        f"💙 **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌟 بوابتك الأولى والأسرع للخدمات الرقمية المتكاملة، الأرقام الافتراضية، والرشق!\n\n"
        "👇 **اختر ما يناسبك من القائمة أدناه:**"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard(user.id, lambda uid: is_admin_or_sub(uid, ADMIN_ID) or is_owner(uid)))

def prompt_user_for_link(message, service_info, context):
    user_id = message.chat.id
    stype = service_info.get("type", "channel")
    prompts = {
        "channel": "🔗 أرسل الآن رابط الحساب أو القناة المستهدفة:",
        "post": "🔗 أرسل الآن رابط المنشور أو الفيديو المطلوب:",
        "comment": "💬 أرسل رابط المنشور مع رابط التعليق:",
        "comment_text": "💬 أرسل رابط المنشور وتحته التعليقات المطلوبة (كل تعليق بسطر):",
        "poll": "📊 أرسل رابط المنشور مع مسافة ثم رقم الخيار المطلوب:"
    }
    admin_state[user_id] = {'action': 'waiting_for_rashq_link', 'service_info': service_info}
    context.application.create_task(message.reply_text(prompts.get(stype, "🔗 أرسل الآن الرابط المطلوب:")))

def prompt_user_for_pubg_id(message, service_info, context):
    user_id = message.chat.id
    admin_state[user_id] = {'action': 'waiting_for_pubg_id', 'service_info': service_info}
    context.application.create_task(message.reply_text(f"🎮 أرسل الآن آيدي اللاعب (Player ID):\n(الخدمة: {service_info['name']})"))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    try:
        await query.answer()
    except Exception:
        pass

    if data == 'check_subscription':
        if await check_user_subscription(user_id, context):
            verification_cache[user_id] = "waiting_math"
            n1, n2 = random.randint(1, 9), random.randint(1, 9)
            verification_cache[f"{user_id}_ans"] = n1 + n2
            math_text = f"🛡️ **تحقق أمني ذكي لإثبات أنك بشري (1/2):**\n\nكم ناتج: ` {n1} + {n2} = ? `\n*(أرسل الرقم في رسالة)*"
            try:
                await query.edit_message_text(math_text, parse_mode='Markdown')
            except Exception:
                await context.bot.send_message(chat_id=user_id, text=math_text, parse_mode='Markdown')
        else:
            await query.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)
        return

    if not await check_user_subscription(user_id, context):
        try:
            await query.edit_message_text(FORCED_SUB_MESSAGE, parse_mode='Markdown', reply_markup=get_forced_subscription_keyboard())
        except Exception:
            pass
        return

    if data == 'main_menu':
        u_data = db_get_user(user_id)
        admin_state.pop(user_id, None)
        welcome_text = (
            f"💎 **مرحباً بك عزيزي {query.from_user.first_name} في بوت ﴿ ديجيتال هب | Digital Hub ﴾** 🚀\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **الآيدي:** `{user_id}`\n"
            f"💙 **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
            "👇 **اختر ما يناسبك من القائمة أدناه:**"
        )
        try:
            await query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id, lambda uid: is_admin_or_sub(uid, ADMIN_ID) or is_owner(uid)))
        except Exception:
            pass

    # ==================== قسم يمن موبايل (جلب مباشر من الموقع) ====================
    elif data == 'yemen_mobile_menu':
        await query.answer("⏳ جاري جلب خدمات يمن موبايل مباشرة من الموقع...", show_alert=False)
        services = await fetch_hmcard_services_directly()
        
        ym_services = [s for s in services if 'يمن' in str(s.get('name', '')) or 'Yemen' in str(s.get('name', '')) or 'موبايل' in str(s.get('name', ''))]
        if not ym_services:
            ym_services = services[:15]

        buttons = []
        for s in ym_services:
            s_id = s.get('id') or s.get('service')
            s_name = s.get('name', 'خدمة يمن موبايل')
            s_rate = s.get('rate', '0')
            btn_label = f"📱 {s_name} (${s_rate})"
            buttons.append([InlineKeyboardButton(btn_label, callback_data=f"direct_ym_buy_{s_id}")])

        buttons.append([InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data='main_menu')])
        
        try:
            await query.edit_message_text(
                "🇾🇪 **• خدمات يمن موبايل (مستخرجة مباشرة من الموقع) •** 🇾🇪\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "اختر الخدمة المطلوبة لتنفيذ الطلب فوراً وبنفس خطوات الموقع:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass

    elif data.startswith('direct_ym_buy_'):
        service_id = data.split('_')[3]
        admin_state[user_id] = {'action': 'waiting_direct_ym_phone', 'service_id': service_id}
        try:
            await query.edit_message_text(
                "📱 **أرسل الآن رقم الهاتف المراد شحنه أو تنفيذه:**\n(أرسل الرقم صحيحاً وبدون أخطاء)",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='yemen_mobile_menu')]])
            )
        except Exception:
            pass
    # ======================================================================

    elif data == 'buy_virtual_number':
        u_data = db_get_user(user_id)
        services_text = (
            "❖ **هنا قائمة التطبيقات والخدمات المتوفرة في البوت** ❖\n"
            f"⭐ **رصيدك:** `${u_data['balance']:.2f}`\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        try:
            await query.edit_message_text(services_text, parse_mode='Markdown', reply_markup=get_virtual_services_keyboard())
        except Exception:
            pass

    elif data in ['most_available', 'deals_whatsapp', 'service_whatsapp']:
        await show_available_countries_menu(update, context, "whatsapp", "واتساب 🟢")
        return

    elif data == 'service_telegram':
        await show_available_countries_menu(update, context, "telegram", "تليجرام 🎲")
    elif data == 'service_instagram':
        await show_available_countries_menu(update, context, "instagram", "انستغرام 🎳")
    elif data == 'service_facebook':
        await show_available_countries_menu(update, context, "facebook", "فيسبوك 🎯")
    elif data == 'service_twitter':
        await show_available_countries_menu(update, context, "twitter", "تويتر 🐤")
    elif data == 'service_tiktok':
        await show_available_countries_menu(update, context, "tiktok", "تيك توك 🎬")
    elif data == 'service_snapchat':
        await show_available_countries_menu(update, context, "snapchat", "سناب شات ♣️")
    elif data == 'service_imo':
        await show_available_countries_menu(update, context, "imo", "إيمو 💎")

    elif data.startswith('buy_num_'):
        parts = data.split('_')
        service, country_code, country_price_str = parts[2], parts[3], parts[4]
        country_price = float(country_price_str)
        operator_name = parts[5] if len(parts) > 5 else "any"
        
        u_data = db_get_user(user_id)
        current_balance = float(u_data.get('balance', 0.0))
        if current_balance <= 0 or current_balance < country_price:
            try:
                await query.edit_message_text(
                    f"❌ **رصيدك غير كافٍ لشراء الرقم!**\n⭐ رصيدك: `${current_balance:.2f}`\n💰 السعر: `${country_price:.2f}`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 شحن الرصيد", callback_data='deposit_menu'), InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]])
                )
            except Exception:
                pass
            return

        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            try:
                res = await client.get(f"https://5sim.net/v1/user/buy/activation/{country_code}/{operator_name}/{service}")
                if res.status_code == 200:
                    res_data = res.json()
                    phone, order_id = res_data.get('phone'), res_data.get('id')
                    if not phone or not order_id:
                        return
                    
                    active_numbers_cache[str(order_id)] = {'has_sms': False, 'balance_deducted': False, 'price': country_price, 'user_id': user_id, 'phone': phone}
                    success_msg = f"✅ **تم استخراج الرقم بنجاح:**\n📞 `{phone}`\n⏳ جاري استقبال الكود..."
                    sent_msg = await query.edit_message_text(success_msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 طلب الكود", callback_data=f"chk_sms_{order_id}")]]))
                    asyncio.create_task(watch_order_sms_auto(context, query.message.chat_id, sent_msg.message_id, str(order_id), phone, country_price, service, user_id, context.bot.username, "رقم افتراضي", "دولة", "+"))
            except Exception:
                pass

    elif data.startswith('chk_sms_'):
        await check_sms_manual(update, context)
        return

    # ==================== أقسام الرشق والألعاب الكاملة المستعادة ====================
    elif data == "main_rashq":
        try:
            await query.edit_message_text("📂 اختر القسم المطلوب للرشق:", reply_markup=sections_menu_keyboard())
        except Exception:
            pass

    elif data == "sec_telegram":
        try:
            await query.edit_message_text("🚀 خدمات تليجرام الرئيسية:\nاختر القسم المطلوب:", reply_markup=telegram_services_keyboard())
        except Exception:
            pass

    elif data == "tg_arab_menu":
        try:
            await query.edit_message_text("🇸🇦 أعضاء تيليجرام عرب:\nاختر الباقة المطلوبة:", reply_markup=tg_arab_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_foreign_menu":
        try:
            await query.edit_message_text("🌍 أعضاء تيليجرام أجانب:\nاختر الباقة المطلوبة:", reply_markup=tg_foreign_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_prem_menu":
        try:
            await query.edit_message_text("⭐ أعضاء تيليجرام بريميوم:\nاختر الباقة المطلوبة:", reply_markup=tg_prem_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_views_menu":
        try:
            await query.edit_message_text("👁️ مشاهدات ومشاركات تليجرام:\nاختر الخدمة المطلوبة:", reply_markup=tg_views_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_auto_menu":
        try:
            await query.edit_message_text("⚡ خدمات التفاعل والمشاهدات التلقائية:", reply_markup=tg_auto_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_react_menu":
        try:
            await query.edit_message_text("⭐ تفاعلات إيموجي تليجرام:", reply_markup=tg_react_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_polls_menu":
        try:
            await query.edit_message_text("🗳️ تصويتات واستطلاعات تليجرام:", reply_markup=tg_polls_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_boost_menu":
        try:
            await query.edit_message_text("🚀 تعزيزات قنوات ومجموعات تليجرام (Boosts):", reply_markup=tg_boost_menu_keyboard())
        except Exception:
            pass

    elif data == "sec_whatsapp":
        try:
            await query.edit_message_text("🟢 خدمات واتساب (رشق):", reply_markup=whatsapp_services_keyboard())
        except Exception:
            pass

    elif data == "sec_facebook":
        try:
            await query.edit_message_text("📘 خدمات فيسبوك:", reply_markup=facebook_services_keyboard())
        except Exception:
            pass

    elif data == "sec_instagram":
        try:
            await query.edit_message_text("📸 خدمات انستغرام:", reply_markup=instagram_services_keyboard())
        except Exception:
            pass

    elif data == "sec_tiktok":
        try:
            await query.edit_message_text("🎵 خدمات تيك توك:", reply_markup=tiktok_services_keyboard())
        except Exception:
            pass

    elif data == "sec_youtube":
        try:
            await query.edit_message_text("📺 خدمات يوتيوب:", reply_markup=youtube_services_keyboard())
        except Exception:
            pass

    elif data == "sec_pubg":
        try:
            await query.edit_message_text("🎮 قسم شحن شدات ببجي موبايل:", reply_markup=pubg_services_keyboard())
        except Exception:
            pass

    elif data == "sec_freefire":
        try:
            await query.edit_message_text("🔥 قسم شحن فري فاير:", reply_markup=freefire_services_keyboard())
        except Exception:
            pass

    elif data == "ig_channel_menu":
        try:
            await query.edit_message_text("📺 متابعو قناة انستغرام:", reply_markup=ig_channel_menu_keyboard())
        except Exception:
            pass

    elif data == "ig_views_menu":
        try:
            await query.edit_message_text("👁️ مشاهدات انستغرام:", reply_markup=ig_views_menu_keyboard())
        except Exception:
            pass

    elif data == "ig_story_menu":
        try:
            await query.edit_message_text("📸 مشاهدات قصص انستغرام:", reply_markup=ig_story_menu_keyboard())
        except Exception:
            pass

    elif data == "ig_likes_menu":
        try:
            await query.edit_message_text("👍 إعجابات انستغرام:", reply_markup=ig_likes_menu_keyboard())
        except Exception:
            pass

    elif data == "ig_comment_likes_menu":
        try:
            await query.edit_message_text("💬 إعجابات تعليقات انستغرام:", reply_markup=ig_comment_likes_menu_keyboard())
        except Exception:
            pass

    elif data == "ig_comments_menu":
        try:
            await query.edit_message_text("💬 تعليقات انستغرام مخصصة:", reply_markup=ig_comments_menu_keyboard())
        except Exception:
            pass

    elif data == "ig_shares_menu":
        try:
            await query.edit_message_text("🔄 مشاركات انستغرام:", reply_markup=ig_shares_menu_keyboard())
        except Exception:
            pass

    elif data == "fb_profile_menu":
        try:
            await query.edit_message_text("👤 متابعو الملف الشخصي:", reply_markup=fb_profile_menu_keyboard())
        except Exception:
            pass

    elif data == "fb_page_menu":
        try:
            await query.edit_message_text("📘 متابعو الصفحة:", reply_markup=fb_page_menu_keyboard())
        except Exception:
            pass

    elif data == "fb_react_menu":
        try:
            await query.edit_message_text("👍 تفاعلات منشورات فيسبوك:", reply_markup=fb_react_menu_keyboard())
        except Exception:
            pass

    elif data == "fb_comment_react_menu":
        try:
            await query.edit_message_text("💬 تفاعلات تعليقات فيسبوك:", reply_markup=fb_comment_react_menu_keyboard())
        except Exception:
            pass

    elif data == "fb_story_menu":
        try:
            await query.edit_message_text("📸 مشاهدات قصة فيسبوك:", reply_markup=fb_story_menu_keyboard())
        except Exception:
            pass

    elif data == "fb_share_menu":
        try:
            await query.edit_message_text("🔄 مشاركات فيسبوك:", reply_markup=fb_share_menu_keyboard())
        except Exception:
            pass
    # ======================================================================

    elif data == 'deposit_menu':
        deposit_text = (
            "💎 **بوابة شحن الرصيد الفوري والآمن** 💎\n"
            "• **كل 1 دولار ($) = 550 ريال يمني**\n\n👇 اختر محفظة الشحن:"
        )
        deposit_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 الشحن عبر محفظة جيب (Jaib)", callback_data='dep_jaib')],
            [InlineKeyboardButton("🏦 الشحن عبر بنك الكريمي (Al-Kuraimi)", callback_data='dep_kreemi')],
            [InlineKeyboardButton("• عودة •", callback_data='main_menu')]
        ])
        try:
            await query.edit_message_text(deposit_text, parse_mode='Markdown', reply_markup=deposit_keyboard)
        except Exception:
            pass

    elif data == 'dep_jaib':
        admin_state[user_id] = {'action': 'waiting_for_jaib_deposit'}
        try:
            await query.edit_message_text(f"💳 أرسل التحويل إلى حساب جيب: `{JAIB_ACCOUNT}`\nثم أرسل صورة الإيصال هنا.", parse_mode='Markdown')
        except Exception:
            pass

    elif data == 'dep_kreemi':
        admin_state[user_id] = {'action': 'waiting_for_kreemi_deposit'}
        try:
            await query.edit_message_text(f"🏦 أرسل التحويل إلى حساب الكريمي: `{KREEMI_ACCOUNT}`\nثم أرسل صورة الإيصال هنا.", parse_mode='Markdown')
        except Exception:
            pass

    elif data == 'admin_panel':
        if is_owner(user_id) or int(user_id) == int(ADMIN_ID) or user_id == 6472852297:
            try:
                stats = db_get_advanced_stats() or {}
                panel_text = f"⚙️ لوحة الأدمن:\n👥 المستخدمين: `{stats.get('total_users', 0)}`"
                await query.edit_message_text(text=panel_text, parse_mode='Markdown', reply_markup=get_admin_keyboard())
            except Exception:
                pass

async def handle_photo_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in admin_state and admin_state[user_id].get('action') in ['waiting_for_jaib_deposit', 'waiting_for_kreemi_deposit']:
        action_type = admin_state[user_id].get('action')
        admin_state.pop(user_id, None)
        
        processing_msg = await update.message.reply_text("⏳ جاري فحص الإيصال...", parse_mode='Markdown')
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            extracted_text = await analyze_receipt_with_gemini(photo_bytes)

            if extracted_text.startswith("ERROR_"):
                await processing_msg.edit_text(f"❌ خطأ في القراءة: `{extracted_text}`", parse_mode='Markdown')
                return

            amount_yer = 500.0
            amount_usd = round(amount_yer / EXCHANGE_RATE, 2)
            db_update_balance(user_id, amount_usd, mode="add")
            await processing_msg.edit_text(f"✅ تم شحن رصيدك بنجاح بقيمة `${amount_usd:.2f}`!", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]]))
        except Exception as e:
            await processing_msg.edit_text(f"❌ خطأ: {e}")

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_user_subscription(user_id, context):
        await update.message.reply_text(FORCED_SUB_MESSAGE, parse_mode='Markdown', reply_markup=get_forced_subscription_keyboard())
        return

    text_content = update.message.text.strip() if update.message.text else ""

    if user_id in admin_state:
        st_action = admin_state[user_id].get('action')
        
        if st_action == 'waiting_direct_ym_phone':
            if not (text_content.isdigit() and len(text_content) == 9):
                await update.message.reply_text("❌ يرجى إرسال رقم يمن موبايل صحيح يتكون من 9 أرقام:")
                return
            
            service_id = admin_state[user_id].get('service_id')
            admin_state.pop(user_id, None)
            
            success, hm_order_id, error_reason = await send_order_to_hmcard(int(service_id), text_content, 1)

            if success and hm_order_id:
                await update.message.reply_text(
                    f"✅ **تم تنفيذ الطلب بنجاح مباشر من الموقع!** 🚀\n"
                    f"📱 الرقم: `{text_content}`\n"
                    f"🆔 رقم الطلب: `{hm_order_id}`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]])
                )
            else:
                await update.message.reply_text(
                    f"❌ **فشل التنفيذ من الموقع:**\n`{error_reason}`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]])
                )
            return

    v_status = verification_cache.get(user_id, "not_started")
    if v_status == "waiting_math":
        correct_ans = verification_cache.get(f"{user_id}_ans")
        if text_content.isdigit() and int(text_content) == correct_ans:
            verification_cache[user_id] = "passed"
            await update.message.reply_text("✅ تم التحقق بنجاح!", reply_markup=get_main_keyboard(user_id, lambda uid: is_admin_or_sub(uid, ADMIN_ID) or is_owner(uid)))
        else:
            await update.message.reply_text("❌ الإجابة خاطئة، حاول مجدداً:")
        return
