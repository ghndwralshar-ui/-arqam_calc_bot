import asyncio
import re
import json
import random
import httpx
import cloudscraper
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, LabeledPrice
from telegram.ext import ContextTypes, CommandHandler

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
verification_cache = {}  # 🛡️ لتخزين حالة التحقق المؤقتة

EXCHANGE_RATE = 550.0
JAIB_ACCOUNT = "772074924"
KREEMI_ACCOUNT = "3105004949"

VALID_BENEFICIARY_PHONE = "772074924"
VALID_BENEFICIARY_NAME = "سالم احمد يحيى صالح السعدي"

def is_owner(user_id: int) -> bool:
    return user_id == ADMIN_ID

FORCED_SUB_MESSAGE = (
    "💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "عذراً عزيزي العميل، لتفعيل حسابك والبدء في استخدام كافة خدمات البوت (الأرقام الافتراضية، والرشق، وشحن الألعاب)، يجب عليك أولاً الاشتراك في قناة البوت الرسمية.\n\n"
    "👇 **اشترك الآن عبر الأزرار أدناه، ثم اضغط على زر التحقق للمتابعة:**"
)

def get_subadmin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 الرد على مستخدم عبر الآيدي", callback_data='admin_reply_user')],
        [InlineKeyboardButton("🎁 إرسال هدية لشخص عبر الآيدي", callback_data='admin_send_gift_user')],
        [InlineKeyboardButton("➕ إضافة رصيد (بالدولار)", callback_data='admin_add_balance'), InlineKeyboardButton("➖ خصم رصيد (بالدولار)", callback_data='admin_deduct_balance')],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')]
    ])

async def check_user_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id == ADMIN_ID:
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

        if user_id != ADMIN_ID:
            try:
                seq_num = u_data.get('user_sequence', 1)
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(
                        f"🛡️ **مستخدم حقيقي جديد انضم واجتاز التحقق الأمني الذكي!** (رقم {seq_num})\n\n"
                        f"▫️ الاسم: {user.full_name}\n"
                        f"▫️ المعرف: @{user.username if user.username else 'لا يوجد'}\n"
                        f"▫️ الآيدي: `{user_id}`"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as admin_notify_err:
                print(f"Error notifying admin about new user: {admin_notify_err}")

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
                                        if base_price < 0.15:
                                            has_stock = True
                                            success_val = float(rate) if rate is not None else 0.0
                                            
                                            if success_val > max_success_rate or (success_val == max_success_rate and base_price < min_price):
                                                max_success_rate = success_val
                                                min_price = base_price
                                                best_operator = operator

                        if has_stock and min_price < 999.0 and best_operator:
                            fixed_price = 0.70
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
    
    await query.answer("⏳ جاري فحص الدول المتوفرة وأفضل المشغلين بنجاح...", show_alert=False)
    available_countries = await get_available_countries_for_service(service_code)
    
    if not available_countries:
        out_of_stock_msg = (
            "📢 **عذراً عزيزي العميل!**\n"
            "🇸🇦 نفدت أرقام هذه الدولة مؤقتاً بسبب الضغط الشديد.\n"
            "🔄 جاري توفير أرقام جديدة قريباً، يمكنك اختيار دولة أخرى متاحة حالياً بكل سهولة! 👇"
        )
        try:
            await query.edit_message_text(
                out_of_stock_msg,
                parse_mode='Markdown',
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception:
        pass

async def send_log_to_channel(context: ContextTypes.DEFAULT_TYPE, log_text: str, service_param: str):
    bot_username = context.bot.username
    start_url = f"https://t.me/{bot_username}?start={service_param}"
    free_url = f"https://t.me/{bot_username}?start=free_social_number"
    
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎁 احصل على رقمك المجاني الآن ✨", url=free_url),
            InlineKeyboardButton("🤖 الدخول للبوت 🚀", url=start_url)
        ]
    ])
    
    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
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
                            await query.edit_message_text(
                                updated_text, parse_mode='Markdown',
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                            )
                        except Exception:
                            pass
                    else:
                        await query.answer(f"✅ الكود وصل بالفعل: {sms_code}", show_alert=True)
                        
                    if not already_logged:
                        sec_ar = cached.get('sec_name_ar', 'رقم افتراضي')
                        c_ar = cached.get('country_name', 'دولة')
                        phone_num = cached.get('phone', 'رقم')
                        price_num = cached.get('price', 0.0)
                        u_id = cached.get('user_id', query.from_user.id)
                        
                        log_msg = (
                            "📱 **تمت اكتمال خدمة تفعيل رقم افتراضي!** ✅\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 **آيدي العميل:** `{u_id}`\n"
                            f"📦 **القسم:** `{sec_ar}`\n"
                            f"🌍 **الدولة:** {c_ar}\n"
                            f"📞 **الرقم:** `{phone_num}`\n"
                            f"🔑 **الكود الواصل:** `{sms_code}`\n"
                            f"💰 **المبلغ المخصوم:** `${price_num:.2f}`\n"
                            f"🆔 **رقم الطلب:** `{order_id}`\n"
                            f"⭐ **الحالة:** تم وصول الكود بنجاح 🚀"
                        )
                        await send_log_to_channel(context, log_msg, "buy_virtual_number")
                else:
                    await query.answer("❌ لم يصل الكود حتى الآن، يرجى الانتظار قليلاً والمحاولة مجدداً.", show_alert=True)
            else:
                await query.answer("⚠️ تعذر فحص الطلب حالياً من السيرفر.", show_alert=True)
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
                            f"💬 **النص الكامل:** `{full_text}`\n\n"
                            f"💡 *تم وصول الكود بنجاح وخصم المبلغ من رصيدك بعد التأكيد!* 🚀"
                        )
                        try:
                            await context.bot.edit_message_text(
                                chat_id=chat_id, message_id=message_id,
                                text=success_msg, parse_mode='Markdown',
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                            )
                        except Exception:
                            pass

                        if not already_logged:
                            log_msg = (
                                "📱 **تمت اكتمال خدمة تفعيل رقم افتراضي!** ✅\n"
                                "━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"👤 **آيدي العميل:** `{user_id}`\n"
                                f"📦 **القسم:** `{section_name}`\n"
                                f"🌍 **الدولة:** {country_name}\n"
                                f"📞 **الرقم:** `{phone}`\n"
                                f"🔑 **الكود الواصل:** `{sms_code}`\n"
                                f"💰 **المبلغ المخصوم:** `${price:.2f}`\n"
                                f"🆔 **رقم الطلب:** `{order_id}`\n"
                                f"⭐ **الحالة:** تم وصول الكود بنجاح 🚀"
                            )
                            await send_log_to_channel(context, log_msg, "buy_virtual_number")
                        return
                    if data.get('status') in ['canceled', 'banned', 'finish']:
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
        await update.message.reply_text(
            FORCED_SUB_MESSAGE,
            parse_mode='Markdown', reply_markup=get_forced_subscription_keyboard()
        )
        return

    # 🛡️ التحقق الأمني (مسألة جمع فقط)
    v_status = verification_cache.get(user.id, "not_started")
    if v_status != "passed":
        verification_cache[user.id] = "waiting_math"
        n1 = random.randint(1, 9)
        n2 = random.randint(1, 9)
        correct_ans = n1 + n2  # جمع فقط تماماً
        verification_cache[f"{user.id}_ans"] = correct_ans

        await update.message.reply_text(
            f"🛡️ **تحقق أمني ذكي لإثبات أنك بشري ولست روبوت (1/2):**\n\n"
            f"قم بحل المسألة الرياضية التالية لإكمال الدخول:\n"
            f"🔹 كم ناتج: ` {n1} + {n2} = ? `\n\n"
            f"*(أرسل الرقم الناتج في رسالة الآن)*",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
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

    if arg_param == 'buy_virtual_number':
        services_text = (
            "❖ **هنا قائمة التطبيقات والخدمات المتوفرة في البوت** ❖\n"
            "❖ **اختر التطبيق أو الخدمة التي تريدها من الأسفل:**\n\n"
            f"⭐ **رصيدك:** `${u_data['balance']:.2f}`\n"
            "💖 **قناة التفعيلات الرسمية** 💖\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(services_text, parse_mode='Markdown', reply_markup=get_virtual_services_keyboard())
    elif arg_param == 'main_rashq':
        await update.message.reply_text("📂 اختر القسم المطلوب:", reply_markup=sections_menu_keyboard())
    elif arg_param == 'free_social_number':
        update.callback_query = type('obj', (object,), {'from_user': user, 'answer': lambda *a, **k: None, 'edit_message_text': lambda *a, **k: None})()
        await free_social_number_handler(update, context)
        return
    else:
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard(user.id, lambda uid: is_admin_or_sub(uid, ADMIN_ID)))

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


# ==========================================
# 🎁 قسم ربح أرقام فيسبوك أو انستغرام (شرط 7 دعوات + استلام تلقائي بالكامل)
# ==========================================

async def free_social_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    u_data = db_get_user(user_id)
    referrals_count = u_data.get('referrals', 0)
    claimed_free_numbers = u_data.get('claimed_free_numbers', 0)
    current_user_balance = float(u_data.get('balance', 0.0))
    
    total_eligible = referrals_count // 7
    remaining_eligible = max(0, total_eligible - claimed_free_numbers)
    
    total_earned_from_refs = referrals_count * 0.10
    
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    if remaining_eligible == 0:
        next_target = (claimed_free_numbers + 1) * 7
        needed_friends = max(0, next_target - referrals_count)
        
        msg_text = (
            "✨ **﴿ ديجيتال هب | Digital Hub ﴾** ✨\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎁 **اربح رقم فيسبوك أو انستغرام مجاناً عبر دعوة الأصدقاء!** 🚀\n\n"
            "📊 **إحصائياتك وإيرادات دعواتك:**\n"
            f"👥 إجمالي أصدقائك المنضمين: `{referrals_count} شخص`\n"
            f"💰 إجمالي رصيد الدعوات المكتسب: `${total_earned_from_refs:.2f}` *(كل دعوة = 0.10$)*\n"
            f"🎁 الأرقام التي استلمتها سابقاً: `{claimed_free_numbers} رقم`\n"
            f"💳 رصيدك العام الحالي: `${current_user_balance:.2f}`\n"
            f"🎯 المتبقي لدعوتهم للرقم القادم: `{needed_friends} أصدقاء فقط!` *(الشرط: كل 7 دعوات = رقم مجاني)*\n\n"
            "🔗 **رابط الدعوة الخاص بك:**\n"
            f"`{ref_link}`\n\n"
            "*(انسخ الرابط أعلاه وشاركه مع أصدقائك وفي المجموعات)*"
        )
        
        share_text = f"🎁 انضم إلينا في بوت ديجيتال هب واربح أرقام فيسبوك وانستغرام مجاناً! شارك عبر الرابط:\n{ref_link}"
        share_url = f"https://t.me/share/url?url={share_text}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 مشاركة الرابط مع الأصدقاء", url=share_url)],
            [InlineKeyboardButton("🔄 تحديث العداد والرصيد", callback_data="free_social_number")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
        ])
    else:
        msg_text = (
            "🎉 **ألف مبروك يا بطل! لقد أتممت الشروط بنجاح تام!** 🏆\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 لقد قمت بدعوة `{referrals_count}` أصدقاء واجتازوا التحقق بنجاح.\n\n"
            f"🎁 أنت مؤهل للحصول على `{total_eligible}` أرقام مجانية! (كل 7 دعوات = رقم).\n"
            f"📦 الأرقام التي استلمتها: `{claimed_free_numbers} رقم`\n"
            f"⭐ **المتبقي لك للاستلام الآن:** `{remaining_eligible} رقم`\n\n"
            "👇 **اختر المنصة لتفعيل رقمك تلقائياً وبشكل فوري:**"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 الحصول على رقم فيسبوك (تلقائي)", callback_data="get_free_fb_number")],
            [InlineKeyboardButton("📸 الحصول على رقم انستغرام (تلقائي)", callback_data="get_free_ig_number")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
        ])
        
    try:
        if hasattr(query, 'edit_message_text'):
            await query.answer()
            await query.edit_message_text(msg_text, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await context.bot.send_message(chat_id=user_id, text=msg_text, parse_mode='Markdown', reply_markup=keyboard)
    except Exception as e:
        print(f"Error in free_social_number_handler: {e}")
        try:
            await context.bot.send_message(chat_id=user_id, text=msg_text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception:
            pass


async def request_free_social_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    u_data = db_get_user(user_id)
    referrals_count = u_data.get('referrals', 0)
    claimed_free_numbers = u_data.get('claimed_free_numbers', 0)
    
    total_eligible = referrals_count // 7
    if claimed_free_numbers >= total_eligible:
        await query.answer("⚠️ عذراً، لقد استهلكت جميع أرقامك المجانية بناءً على عدد دعواتك (كل 7 دعوات = رقم)!", show_alert=True)
        return
        
    new_claimed = claimed_free_numbers + 1
    
    try:
        supabase.table("users").update({
            "claimed_free_numbers": new_claimed
        }).eq("user_id", user_id).execute()
    except Exception as db_err:
        print(f"Error updating claimed numbers: {db_err}")
    
    if "fb" in data:
        await show_available_countries_menu(update, context, "facebook", "فيسبوك 📘")
    else:
        await show_available_countries_menu(update, context, "instagram", "انستغرام 📸")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == 'get_free_fb_number' or data == 'get_free_ig_number':
        await request_free_social_number(update, context)
        return

    if data == 'check_subscription':
        if await check_user_subscription(user_id, context):
            # 🛡️ إطلاق التحقق الذكي (المسألة الحسابية جمع فقط)
            verification_cache[user_id] = "waiting_math"
            n1 = random.randint(1, 9)
            n2 = random.randint(1, 9)
            correct_ans = n1 + n2
            verification_cache[f"{user_id}_ans"] = correct_ans

            math_text = (
                f"🛡️ **تحقق أمني ذكي لإثبات أنك بشري ولست روبوت (1/2):**\n\n"
                f"قم بحل المسألة الرياضية التالية لإكمال الدخول:\n"
                f"🔹 كم ناتج: ` {n1} + {n2} = ? `\n\n"
                f"*(أرسل الرقم الناتج في رسالة الآن)*"
            )
            try:
                await query.edit_message_text(math_text, parse_mode='Markdown')
            except Exception:
                await context.bot.send_message(chat_id=user_id, text=math_text, parse_mode='Markdown')
        else:
            await query.answer("❌ عذراً، لم تقم بالاشتراك في القناة بعد! يرجى الاشتراك ثم إعادة المحاولة.", show_alert=True)
        return

    if not await check_user_subscription(user_id, context):
        await query.answer("⚠️ يجب عليك الاشتراك في القناة أولاً لاستخدام البوت!", show_alert=True)
        try:
            await query.edit_message_text(
                FORCED_SUB_MESSAGE,
                parse_mode='Markdown', reply_markup=get_forced_subscription_keyboard()
            )
        except Exception:
            pass
        return

    await query.answer()

    if data == 'main_menu':
        u_data = db_get_user(user_id)
        admin_state.pop(user_id, None)
        welcome_text = (
            f"💎 **مرحباً بك عزيزي {query.from_user.first_name} في بوت ﴿ ديجيتال هب | Digital Hub ﴾** 🚀\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **الآيدي:** `{user_id}`\n"
            f"💙 **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌟 بوابتك الأولى والأسرع للخدمات الرقمية المتكاملة، الأرقام الافتراضية، والرشق!\n\n"
            "👇 **اختر ما يناسبك من القائمة أدناه:**"
        )
        try:
            await query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id, lambda uid: is_admin_or_sub(uid, ADMIN_ID)))
        except Exception:
            pass

    elif data == 'free_social_number':
        await free_social_number_handler(update, context)

    elif data == 'buy_virtual_number':
        u_data = db_get_user(user_id)
        services_text = (
            "❖ **هنا قائمة التطبيقات والخدمات المتوفرة في البوت** ❖\n"
            "❖ **اختر التطبيق أو الخدمة التي تريدها من الأسفل:**\n\n"
            f"⭐ **رصيدك:** `${u_data['balance']:.2f}`\n"
            "💖 **قناة التفعيلات الرسمية** 💖\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        try:
            await query.edit_message_text(services_text, parse_mode='Markdown', reply_markup=get_virtual_services_keyboard())
        except Exception:
            pass

    elif data in ['most_available', 'deals_whatsapp', 'service_whatsapp', 'wa_subscribers', 'wa_reactions', 'wa_auto_reactions', 'wa_polls']:
        await query.answer("⚠️ قسم واتساب وعروضه في حالة صيانة الآن. يمكنك طلب رقم لمنصة أخرى بكل سهولة!", show_alert=True)
        try:
            await query.edit_message_text(
                "📢 **عذراً عزيزي العميل!**\n"
                "🛠️ قسم أرقام وعروض **واتساب** في حالة صيانة وتحديث حالياً.\n"
                "✨ **يمكنك طلب رقم لمنصة أخرى (فيسبوك، انستغرام، تليجرام، وغيرها) متاحة وتعمل بكفاءة تامة!** 👇",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة للخدمات", callback_data='buy_virtual_number')]])
            )
        except Exception:
            pass
        return

    elif data == 'deals_telegram':
        await show_available_countries_menu(update, context, "telegram", "تليجرام")

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
                    f"❌ **عذراً، رصيدك غير كافٍ أو صفر لشراء الرقم!**\n⭐ رصيدك الحالي: `${current_balance:.2f}`\n💰 سعر الرقم: `${country_price:.2f}`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 شحن الرصيد", callback_data='deposit_menu'), InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]])
                )
            except Exception:
                pass
            return

        section_names_ar = {
            'whatsapp': 'واتساب', 'telegram': 'تليجرام', 'instagram': 'انستغرام',
            'facebook': 'فيسبوك', 'twitter': 'تويتر', 'tiktok': 'تيك توك',
            'snapchat': 'سناب شات', 'imo': 'إيمو'
        }
        sec_name_ar = section_names_ar.get(service, service.upper())

        c_info = COUNTRY_INFO.get(country_code, {"name_ar": country_code, "dial": "+?"})
        c_name_ar = c_info['name_ar']
        c_dial = c_info['dial']

        out_of_stock_msg = (
            "📢 **عذراً عزيزي العميل!**\n"
            "🇸🇦 نفدت أرقام هذه الدولة مؤقتاً بسبب الضغط الشديد.\n"
            "🔄 جاري توفير أرقام جديدة قريباً، يمكنك اختيار دولة أخرى متاحة حالياً بكل سهولة! 👇"
        )

        await query.answer("🔄 جاري الشراء وتجهيز الرقم من أفضل مشغل...", show_alert=False)
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            try:
                res = await client.get(f"https://5sim.net/v1/user/buy/activation/{country_code}/{operator_name}/{service}")
                if res.status_code == 200:
                    try:
                        res_data = res.json()
                    except Exception:
                        try:
                            await query.edit_message_text(out_of_stock_msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='buy_virtual_number')]]))
                        except Exception:
                            pass
                        return

                    phone, order_id = res_data.get('phone'), res_data.get('id')
                    if not phone or not order_id:
                        try:
                            await query.edit_message_text(out_of_stock_msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='buy_virtual_number')]]))
                        except Exception:
                            pass
                        return

                    active_numbers_cache[str(order_id)] = {
                        'has_sms': False, 
                        'balance_deducted': False,
                        'service': service, 
                        'country_code': country_code, 
                        'price': country_price,
                        'user_id': user_id,
                        'phone': phone,
                        'sec_name_ar': sec_name_ar,
                        'country_name': c_name_ar,
                        'operator': operator_name
                    }

                    success_msg = (
                        f"💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ **تم استخراج الرقم بنجاح تام من أفضل مشغل ({operator_name})!**\n\n"
                        f"📦 **القسم:** `{sec_name_ar}`\n"
                        f"🌍 **الدولة:** {c_name_ar}\n"
                        f"📞 **مفتاح الدولة:** `{c_dial}`\n"
                        f"📱 **الرقم المشتري:** `{phone}`\n"
                        f"⭐ **السعر:** `${country_price:.2f}` *(لا يُخصم الرصيد إلا بعد وصول الكود)*\n\n"
                        f"⏳ **جاري رصد واستقبال الكود تلقائياً...**\n"
                        f"💡 *قم بوضع الرقم في التطبيق واطلب الكود فوراً!* 🚀"
                    )
                    
                    sent_msg = await query.edit_message_text(
                        success_msg,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 طلب الكود", callback_data=f"chk_sms_{order_id}")],
                            [InlineKeyboardButton("🔄 تغيير الرقم", callback_data=f"change_num_{order_id}_{service}_{country_code}_{country_price}_{operator_name}")],
                            [InlineKeyboardButton("❌ إلغاء الرقم", callback_data=f"cnl_paid_{order_id}_{country_price}")]
                        ])
                    )
                    
                    asyncio.create_task(watch_order_sms_auto(context, query.message.chat_id, sent_msg.message_id, str(order_id), phone, country_price, service, user_id, context.bot.username, sec_name_ar, c_name_ar, c_dial))
                else:
                    try:
                        await query.edit_message_text(out_of_stock_msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='buy_virtual_number')]]))
                    except Exception:
                        pass
            except Exception as e:
                try:
                    await query.edit_message_text(f"⚠️ خطأ بالاتصال: `{str(e)[:50]}`", parse_mode='Markdown')
                except Exception:
                    pass

    elif data.startswith('chk_sms_'):
        await check_sms_manual(update, context)
        return

    elif data.startswith('change_num_'):
        parts = data.split('_')
        old_order_id, service, country_code, price_str = parts[2], parts[3], parts[4], float(parts[5])
        operator_name = parts[6] if len(parts) > 6 else "any"
        
        order_status_info = active_numbers_cache.get(old_order_id, {})
        if order_status_info.get('has_sms', False):
            await query.answer("⚠️ عذراً، لا يمكن تغيير الرقم أو إلغاؤه لأنه قد وصل كود التحقق بالفعل!", show_alert=True)
            return

        await query.answer("🔄 جاري إلغاء الرقم الحالي واستخراج رقم جديد بأعلى نسبة نجاح...", show_alert=False)
        
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            try:
                await client.get(f"https://5sim.net/v1/user/cancel/{old_order_id}")

                res = await client.get(f"https://5sim.net/v1/user/buy/activation/{country_code}/{operator_name}/{service}")
                if res.status_code == 200:
                    res_data = res.json()
                    new_phone, new_order_id = res_data.get('phone'), res_data.get('id')
                    
                    if not new_phone or not new_order_id:
                        try:
                            await query.edit_message_text("❌ عذراً، نفدت أرقام هذه الدولة مؤقتاً أثناء التغيير.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]]))
                        except Exception:
                            pass
                        return
                    
                    section_names_ar = {'whatsapp': 'واتساب', 'telegram': 'تليجرام', 'instagram': 'انستغرام', 'facebook': 'فيسبوك'}
                    sec_name_ar = section_names_ar.get(service, service.upper())
                    c_info = COUNTRY_INFO.get(country_code, {"name_ar": country_code, "dial": "+?"})

                    active_numbers_cache[str(new_order_id)] = {
                        'has_sms': False, 
                        'balance_deducted': False,
                        'service': service, 
                        'country_code': country_code, 
                        'price': price_str,
                        'user_id': user_id,
                        'phone': new_phone,
                        'sec_name_ar': sec_name_ar,
                        'country_name': c_info['name_ar'],
                        'operator': operator_name
                    }

                    success_msg = (
                        f"💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ **تم تغيير الرقم واستبداله بنجاح!**\n\n"
                        f"📦 **القسم:** `{sec_name_ar}`\n"
                        f"🌍 **الدولة:** {c_info['name_ar']}\n"
                        f"📞 **مفتاح الدولة:** `{c_info['dial']}`\n"
                        f"📱 **الرقم الجديد:** `{new_phone}`\n"
                        f"⭐ **السعر:** `${price_str:.2f}`\n\n"
                        f"⏳ **جاري رصد الكود تلقائياً للرقم الجديد...** 🚀"
                    )

                    sent_msg = await query.edit_message_text(
                        success_msg,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 طلب الكود", callback_data=f"chk_sms_{new_order_id}")],
                            [InlineKeyboardButton("🔄 تغيير الرقم", callback_data=f"change_num_{new_order_id}_{service}_{country_code}_{price_str}_{operator_name}")],
                            [InlineKeyboardButton("❌ إلغاء الرقم", callback_data=f"cnl_paid_{new_order_id}_{price_str}")]
                        ])
                    )
                    asyncio.create_task(watch_order_sms_auto(context, query.message.chat_id, sent_msg.message_id, str(new_order_id), new_phone, price_str, service, user_id, context.bot.username, sec_name_ar, c_info['name_ar'], c_info['dial']))
                else:
                    try:
                        await query.edit_message_text("❌ عذراً، فشل توفير رقم بديل حالياً.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]]))
                    except Exception:
                        pass
            except Exception as e:
                try:
                    await query.edit_message_text(f"⚠️ خطأ أثناء استبدال الرقم: `{str(e)[:50]}`", parse_mode='Markdown')
                except Exception:
                    pass

    elif data.startswith('cnl_'):
        parts = data.split('_')
        cancel_type, order_id, price = parts[1], parts[2], float(parts[3])
        
        order_status_info = active_numbers_cache.get(order_id, {})
        if order_status_info.get('has_sms', False):
            await query.answer("⚠️ عذراً، لا يمكن إلغاء الرقم لأنه قد وصل كود التحقق بالفعل وتم الخصم!", show_alert=True)
            return

        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
            res = await client.get(f"https://5sim.net/v1/user/cancel/{order_id}")
            if res.status_code == 200 or res.status_code == 400:
                if order_status_info.get('balance_deducted', False):
                    db_update_balance(user_id, price, mode="add")

                await query.answer("✅ تم إلغاء الرقم بنجاح!", show_alert=True)
                try:
                    await query.edit_message_text("🚫 **تم إلغاء الرقم بنجاح.**", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))
                except Exception:
                    pass

    elif data == "main_rashq":
        try:
            await query.edit_message_text("📂 اختر القسم المطلوب:", reply_markup=sections_menu_keyboard())
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
            await query.edit_message_text("⚡ خدمات التفاعل والمشاهدات التلقائية:\nاختر الخدمة المطلوبة:", reply_markup=tg_auto_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_react_menu":
        try:
            await query.edit_message_text("⭐ تفاعلات إيموجي تليجرام:\nاختر نوع التفاعل المطلوب:", reply_markup=tg_react_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_polls_menu":
        try:
            await query.edit_message_text("🗳️ تصويتات واستطلاعات تليجرام:\nاختر نوع التصويت المطلوب:", reply_markup=tg_polls_menu_keyboard())
        except Exception:
            pass

    elif data == "tg_boost_menu":
        try:
            await query.edit_message_text("🚀 تعزيزات قنوات ومجموعات تليجرام (Boosts):\nاختر المدة المطلوبة:", reply_markup=tg_boost_menu_keyboard())
        except Exception:
            pass

    elif data == "sec_whatsapp":
        try:
            await query.edit_message_text("🟢 خدمات واتساب:\nاختر الخدمة المطلوبة:", reply_markup=whatsapp_services_keyboard())
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

    elif data in ["sec_twitter", "sec_kwai", "sec_snapchat", "sec_linkedin"]:
        await query.answer("⚠️ عذراً، لا توجد خدمات متاحة في هذه الفئة حالياً.", show_alert=True)
        return

    elif data == 'free_services_menu':
        free_services_main_text = (
            "💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✨ **قسـم الخـدمـات المجـانيـة والأدوات الاحترافيـة** ✨\n\n"
            "مرحباً بك عزيزي العميل في مركز الخدمات المجانية المتاحة لك بالكامل دون أي رسوم!\n\n"
            "👇 **اختر الأداة أو الخدمة المطلوبة من القائمة أدناه:**"
        )
        try:
            await query.edit_message_text(free_services_main_text, parse_mode='Markdown', reply_markup=get_free_services_keyboard())
        except Exception:
            pass

    elif data == 'fs_url_info':
        admin_state[user_id] = {'action': 'fs_url_info_action'}
        try:
            await query.edit_message_text("🔗 **فحص ومعالجة الروابط:**\nأرسل الآن الرابط المراد فحصه أو التحقق من صحته لتظهر لك تفاصيله بالكامل:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_text_deco':
        admin_state[user_id] = {'action': 'fs_text_deco_action'}
        try:
            await query.edit_message_text("🎨 **زخرفة النصوص والأسماء:**\nأرسل الآن الاسم أو النص المراد زخرفته بأشكال عربية وإنجليزية فخمة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_id_lookup':
        admin_state[user_id] = {'action': 'fs_id_lookup_action'}
        try:
            await query.edit_message_text("🔍 **كشف الآيدي والمعرفات:**\nأرسل معرف (Username) أو قم بتوجيه رسالة (Forward) من أي شخص أو قناة لمعرفة الآيدي الخاص به فوراً:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_password_gen':
        import random, string
        chars = string.ascii_letters + string.digits + "!@#$%&*"
        secure_pass = "".join(random.choice(chars) for _ in range(14))
        pass_text = (
            "📌 **مولد كلمات السر الآمنة:**\n\n"
            f"🔑 كلمة المرور المقترحة:\n`{secure_pass}`\n\n"
            "*(انقر فوق الكود لنسخه واستخدامه لحماية حساباتك)*"
        )
        try:
            await query.edit_message_text(pass_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 توليد كلمة أخرى", callback_data='fs_password_gen'), InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_price_calc':
        try:
            await query.edit_message_text("📊 **حاسبة أسعار الرشق:**\nيمكنك استخدام أقسام الرشق الرئيسية في البوت لمعرفة الأسعار بدقة، أو اختيار الخدمة للاستعلام الفوري.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_url_short':
        admin_state[user_id] = {'action': 'fs_url_short_action'}
        try:
            await query.edit_message_text("✂️ **اختصار الروابط السريع:**\nأرسل الرابط الطويل المراد اختصاره وتوليد رابط نظيف ومختصر له:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_tg_info':
        admin_state[user_id] = {'action': 'fs_tg_info_action'}
        try:
            await query.edit_message_text("📥 **معلومات القنوات العامة:**\nأرسل معرف القناة أو المجموعة العامة (مثال: `@ChannelName`) لجلب معلوماتها الأساسية:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_markdown_fmt':
        admin_state[user_id] = {'action': 'fs_markdown_fmt_action'}
        try:
            await query.edit_message_text("🔤 **منسق النصوص والمخفي:**\nأرسل النص الذي تريد تنسيقه لتجهيزه بصيغة `Markdown` الخاصة بمنشوراتك:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_dial_codes':
        dial_text = (
            "🌐 **دليل مفاتيح الدول الدوليين (أبرز المفاتيح):**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🇸🇦 السعودية: `+966`\n"
            "🇾🇪 اليمن: `+967`\n"
            "🇪 مصر: `+20`\n"
            "🇦🇪 الإمارات: `+971`\n"
            "🇺🇸 أمريكا: `+1`\n"
            "🇹🇷 تركيا: `+90`\n\n"
            "💡 *يمكنك دائماً الاعتماد على هذا الدليل السريع لتفعيل أرقامك.*"
        )
        try:
            await query.edit_message_text(dial_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_tg_post_fmt':
        admin_state[user_id] = {'action': 'fs_tg_post_fmt_action'}
        try:
            await query.edit_message_text("🔤 **تنسيق منشورات تليجرام:**\nأرسل نص المنشور لإضافة التنسيقات الاحترافية المعتمدة لقناتك:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_percent_calc':
        admin_state[user_id] = {'action': 'fs_percent_calc_action'}
        try:
            await query.edit_message_text("🔢 **حاسبة النسب والخصومات:**\nأرسل المبلغ والنسبة المئوية (مثال: `100 15`) لحساب قيمة الخصم أو الربح بسرعة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_word_counter':
        admin_state[user_id] = {'action': 'fs_word_counter_action'}
        try:
            await query.edit_message_text("🔠 **عدّاد الكلمات والحروف:**\nأرسل أي نص طويل ليقوم البوت بحساب عدد الكلمات، الحروف، والأسطر بدقة تامة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_text_cleaner':
        admin_state[user_id] = {'action': 'fs_text_cleaner_action'}
        try:
            await query.edit_message_text("🗑️ **تنظيف النصوص والمسافات:**\nأرسل النص المليء بالمسافات الفارغة لإزالة الزوائد وتنسيقه في ثوانٍ:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
        except Exception:
            pass

    elif data == 'fs_unban_guide':
        unban_guide_text = (
            "🔓 **دليل استئناف وفك الحظر (واتساب وتليجرام)** 🔓\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📱 **1️⃣ فك حظر رقم واتساب:**\n"
            "إذا تم حظر رقمك في واتساب، أرسل رسالة باللغة الإنجليزية عبر البريد إلى `support@whatsapp.com` أو من داخل التطبيق:\n"
            "> *\"My WhatsApp number was banned by mistake. Please review and unban my number. Thank you.\"*\n\n"
            "🚀 **2️⃣ فك تقييد حساب تليجرام:**\n"
            "إذا كان حسابك مقيداً (Spam Bot)، تواصل مع بوت الدعم الرسمي: `@SpamBot` واتبع التعليمات لرفع القيود.\n\n"
            "💡 *هذه الإرشادات الرسمية المعتمدة لتقديم طلبات الاستئناف.*"
        )
        try:
            await query.edit_message_text(unban_guide_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة", callback_data='free_services_menu')]]))
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

    elif data == "ig_f_961":
        user_selected_service[user_id] = {"service_id": 961, "name": "متابعين انستغرام فوري بدون ضمان", "price": 0.78, "min": 10, "max": 100000000, "type": "channel"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data == "ig_f_768":
        user_selected_service[user_id] = {"service_id": 768, "name": "حفظ منشورات انستغرام فوري", "price": 0.40, "min": 10, "max": 100000000, "type": "post"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data == "tik_f_958":
        user_selected_service[user_id] = {"service_id": 958, "name": "متابعين تيك توك فوري بدون ضمان", "price": 2.42, "min": 10, "max": 1000000, "type": "channel"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data == "tik_f_959":
        user_selected_service[user_id] = {"service_id": 959, "name": "متابعين تيك توك فوري - تعويض 30 يوم", "price": 3.38, "min": 10, "max": 1000000, "type": "channel"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data == "yt_f_796":
        user_selected_service[user_id] = {"service_id": 796, "name": "مشتركين يوتيوب فوري بدون ضمان", "price": 0.20, "min": 10, "max": 1000000, "type": "channel"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data.startswith("pubg_f_"):
        pubg_map = {
            "pubg_f_903": (903, "PUBG Mobile - 60 UC", 1.14), "pubg_f_902": (902, "PUBG Mobile - 60 WOW Coins", 1.16),
            "pubg_f_904": (904, "PUBG Mobile - Updatable Firearm Materials Pack", 3.46), "pubg_f_905": (905, "PUBG Mobile - Weekly Mythic Emblem Value Pack", 3.46),
            "pubg_f_906": (906, "PUBG Mobile - Weekly Deal Pack 2", 3.46), "pubg_f_907": (907, "PUBG Mobile - Prime (3 Months)", 3.48),
            "pubg_f_908": (908, "PUBG Mobile - Mythic Emblem Pack", 5.77), "pubg_f_909": (909, "PUBG Mobile - 325 UC", 5.94),
            "pubg_f_910": (910, "PUBG Mobile - 325 WOW Coins", 6.06), "pubg_f_911": (911, "PUBG Mobile - Prime (6 Months)", 6.97),
            "pubg_f_912": (912, "PUBG Mobile - Elite Pass LV1-50", 7.00), "pubg_f_913": (913, "PUBG Mobile - Prime Plus (1 Month)", 11.62),
            "pubg_f_914": (914, "PUBG Mobile - 660 UC", 11.88), "pubg_f_915": (915, "PUBG Mobile - 660 WOW Coins", 12.10),
            "pubg_f_916": (916, "PUBG Mobile - Prime (12 Months)", 13.94), "pubg_f_917": (917, "PUBG Mobile - Elite Pass LV1-100", 14.11),
            "pubg_f_918": (918, "PUBG Mobile - 985 UC", 17.82), "pubg_f_919": (919, "PUBG Mobile - 1320 UC", 23.76),
            "pubg_f_920": (920, "PUBG Mobile - 1800 UC", 29.21), "pubg_f_922": (922, "PUBG Mobile - 1800 WOW Coins", 30.24),
            "pubg_f_923": (923, "PUBG Mobile - Elite Pass Plus LV1-100", 33.95), "pubg_f_924": (924, "PUBG Mobile - Prime Plus (3 Months)", 34.85),
            "pubg_f_925": (925, "PUBG Mobile - 2460 UC", 41.58), "pubg_f_926": (926, "PUBG Mobile - 3850 UC", 56.76),
            "pubg_f_928": (928, "PUBG Mobile - 3850 WOW Coins", 60.49), "pubg_f_929": (929, "PUBG Mobile - Prime Plus (6 Months)", 68.64),
            "pubg_f_930": (930, "PUBG Mobile - 5650 UC", 89.10), "pubg_f_931": (931, "PUBG Mobile - 8100 UC", 112.20),
            "pubg_f_933": (933, "PUBG Mobile - 8100 WOW Coins", 121.00), "pubg_f_935": (935, "PUBG Mobile - 11950 UC", 178.20),
            "pubg_f_936": (936, "PUBG Mobile - 16200 UC", 234.96), "pubg_f_899": (899, "PUBG Mobile - Prime (1 Month)", 1.16),
            "pubg_f_900": (900, "PUBG Mobile - First Purchase Pack", 1.16), "pubg_f_901": (901, "PUBG Mobile - Weekly Deal Pack 1", 1.16)
        }
        s_id, s_name, s_price = pubg_map.get(data, (903, "PUBG Mobile - 60 UC", 1.14))
        user_selected_service[user_id] = {"service_id": s_id, "name": s_name, "fixed_price": s_price, "type": "pubg_id"}
        prompt_user_for_pubg_id(update.effective_message, user_selected_service[user_id], context)

    elif data.startswith("ff_"):
        ff_map = {
            "ff_937": (937, "Freefire Global - 100 Diamonds", 0.22), "ff_938": (938, "Freefire Global - Level Up Level 6", 0.32),
            "ff_939": (939, "Freefire Global - Weekly Lite", 0.43), "ff_940": (940, "Freefire Global - Level Up Level 20", 0.59),
            "ff_941": (941, "Freefire Global - Level Up Level 25", 0.59), "ff_942": (942, "Freefire Global - Level Up Level 10", 0.59),
            "ff_943": (943, "Freefire Global - Level Up Level 15", 0.59), "ff_944": (944, "Freefire Global - Level Up Level 30", 0.85),
            "ff_945": (945, "Freefire Global - 110", 0.89), "ff_946": (946, "Freefire Global - Weekly Membership", 1.76),
            "ff_947": (947, "Freefire Global - 341", 2.70), "ff_948": (948, "Freefire Global - 572", 4.38),
            "ff_949": (949, "Freefire Global - Monthly Membership", 6.33), "ff_950": (950, "Freefire Global - 1166", 8.79),
            "ff_951": (951, "Freefire Global - 2398", 17.59), "ff_952": (952, "Freefire Global - 6160", 44.55)
        }
        s_id, s_name, s_price = ff_map.get(data, (945, "Freefire Global - 110", 0.89))
        user_selected_service[user_id] = {"service_id": s_id, "name": s_name, "fixed_price": s_price, "type": "pubg_id"}
        prompt_user_for_pubg_id(update.effective_message, user_selected_service[user_id], context)

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

    elif data == "fb_group_744":
        user_selected_service[user_id] = {"service_id": 744, "name": "أعضاء مجموعة فيسبوك", "price": 0.72, "min": 10, "max": 100000, "type": "channel"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

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

    elif data.startswith("sub_"):
        service_ids = {"sub_no_guarantee": 729, "sub_30d": 730, "sub_60d": 731, "sub_90d": 732, "sub_global": 805, "sub_arabic": 806}
        prices = {"sub_no_guarantee": 0.39, "sub_30d": 0.70, "sub_60d": 0.80, "sub_90d": 0.80, "sub_global": 0.90, "sub_arabic": 1.0}
        names = {"sub_no_guarantee": "بروفايل واتساب - أعضاء بدون ضمان", "sub_30d": "بروفايل واتساب - ضمان 30 يوم", "sub_60d": "بروفايل واتساب - ضمان 60 يوم", "sub_90d": "بروفايل واتساب - ضمان 90 يوم", "sub_global": "بروفايل واتساب - عالمي", "sub_arabic": "بروفايل واتساب - عربي"}
        user_selected_service[user_id] = {"service_id": service_ids.get(data, 730), "name": names.get(data, "واتساب"), "price": prices.get(data, 1.0), "min": 10, "max": 100000000, "type": "channel"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data.startswith("wa_r_") or data.startswith("wa_a_") or data.startswith("wa_p_") or data.startswith("tg_t_") or data.startswith("fb_f_") or data.startswith("ig_f_") or data.startswith("tg_v_") or data.startswith("tg_a_") or data.startswith("tg_r_") or data.startswith("tg_p_"):
        service_ids = {
            "wa_r_1": 712, "wa_r_2": 713, "wa_r_3": 714, "wa_r_4": 715, "wa_r_5": 716, "wa_r_6": 717,
            "tg_t_653": 653, "tg_t_654": 654, "tg_t_659": 659, "tg_t_660": 660, "tg_t_661": 661, "tg_t_662": 662,
            "tg_t_613": 613, "tg_t_614": 614, "tg_t_646": 646, "tg_t_893": 893, "tg_t_894": 894, "tg_t_895": 895,
            "tg_v_628": 628, "tg_v_668": 668, "tg_v_669": 669, "tg_v_670": 670, "tg_v_671": 671,
            "tg_a_702": 702, "tg_a_703": 703, "tg_a_704": 704, "tg_a_705": 705, "tg_a_706": 706, "tg_a_707": 707, "tg_a_708": 708, "tg_a_709": 709, "tg_a_710": 710, "tg_a_711": 711,
            "tg_r_620": 620, "tg_r_621": 621, "tg_r_622": 622, "tg_r_623": 623, "tg_r_624": 624, "tg_r_625": 625, "tg_r_626": 626, "tg_r_690": 690,
            "tg_p_665": 665, "tg_p_666": 666,
            "fb_f_745": 745, "fb_f_746": 746, "fb_f_747": 747, "fb_f_748": 748, "fb_f_774": 1.02, "fb_f_775": 1.08,
            "fb_f_776": 1.10, "fb_f_777": 1.12, "fb_f_750": 0.28, "fb_f_751": 0.28, "fb_f_752": 0.28, "fb_f_753": 0.28,
            "fb_f_754": 0.28, "fb_f_755": 0.28, "fb_f_756": 0.28, "fb_f_788": 2.80, "fb_f_789": 2.80, "fb_f_790": 2.80,
            "fb_f_791": 2.80, "fb_f_792": 2.80, "fb_f_793": 2.80, "fb_f_794": 2.80, "fb_f_778": 1.81, "fb_f_779": 1.05,
            "fb_f_787": 0.10, "fb_f_795": 1.01, "ig_f_799": 2.06, "ig_f_800": 2.06, "ig_f_801": 2.06, "ig_f_802": 2.06,
            "ig_f_803": 2.06, "ig_f_804": 2.06, "ig_f_757": 0.0054, "ig_f_762": 0.004, "ig_f_766": 1.50, "ig_f_785": 0.30,
            "ig_f_767": 0.50, "ig_f_953": 0.20, "ig_f_954": 0.20, "ig_f_955": 0.20, "ig_f_956": 0.20, "ig_f_957": 0.22,
            "ig_f_724": 724, "ig_f_771": 771, "ig_f_772": 772, "ig_f_773": 773, "ig_f_769": 769, "ig_f_770": 770
        }
        prices = {
            "wa_r_1": 0.50, "wa_r_2": 0.50, "wa_r_3": 0.50, "wa_r_4": 0.50, "wa_r_5": 0.50, "wa_r_6": 0.50,
            "tg_t_653": 2.46, "tg_t_654": 2.80, "tg_t_659": 2.00, "tg_t_660": 5.40, "tg_t_661": 5.60, "tg_t_662": 6.00,
            "tg_t_613": 4.00, "tg_t_614": 8.00, "tg_t_646": 30.00, "tg_t_893": 116.00, "tg_t_894": 196.00, "tg_t_895": 316.00,
            "tg_v_628": 0.04, "tg_v_668": 0.02, "tg_v_669": 0.10, "tg_v_670": 0.60, "tg_v_671": 1.22,
            "tg_a_702": 0.76, "tg_a_703": 1.54, "tg_a_704": 3.84, "tg_a_705": 7.68, "tg_a_706": 0.08, "tg_a_707": 0.28, "tg_a_708": 0.72, "tg_a_709": 1.42, "tg_a_710": 2.86, "tg_a_711": 8.30,
            "tg_r_620": 0.20, "tg_r_621": 0.06, "tg_r_622": 0.06, "tg_r_623": 0.06, "tg_r_624": 0.06, "tg_r_625": 0.06, "tg_r_626": 0.06, "tg_r_690": 0.10,
            "tg_p_665": 4.00, "tg_p_666": 18.00,
            "fb_f_745": 0.55, "fb_f_746": 0.59, "fb_f_747": 0.61, "fb_f_748": 0.62, "fb_f_774": 1.02, "fb_f_775": 1.08,
            "fb_f_776": 1.10, "fb_f_777": 1.12, "fb_f_750": 0.28, "fb_f_751": 0.28, "fb_f_752": 0.28, "fb_f_753": 0.28,
            "fb_f_754": 0.28, "fb_f_755": 0.28, "fb_f_756": 0.28, "fb_f_788": 2.80, "fb_f_789": 2.80, "fb_f_790": 2.80,
            "fb_f_791": 2.80, "fb_f_792": 2.80, "fb_f_793": 2.80, "fb_f_794": 2.80, "fb_f_778": 1.81, "fb_f_779": 1.05,
            "fb_f_787": 0.10, "fb_f_795": 1.01, "ig_f_799": 2.06, "ig_f_800": 2.06, "ig_f_801": 2.06, "ig_f_802": 2.06,
            "ig_f_803": 2.06, "ig_f_804": 2.06, "ig_f_757": 0.0054, "ig_f_762": 0.004, "ig_f_766": 1.50, "ig_f_785": 0.30,
            "ig_f_767": 0.50, "ig_f_953": 0.20, "ig_f_954": 0.20, "ig_f_955": 0.20, "ig_f_956": 0.20, "ig_f_957": 0.22,
            "ig_f_724": 3.40, "ig_f_771": 4.54, "ig_f_772": 1.874, "ig_f_773": 13.36, "ig_f_769": 0.032, "ig_f_770": 0.40
        }
        names = {
            "wa_r_1": "تفاعلات واتساب - إيموجي 1", "wa_r_2": "تفاعلات واتساب - إيموجي 2", "wa_r_3": "تفاعلات واتساب - إيموجي 3",
            "wa_r_4": "تفاعلات واتساب - إيموجي 4", "wa_r_5": "تفاعلات واتساب - إيموجي 5", "wa_r_6": "تفاعلات واتساب - إيموجي 6",
            "tg_t_653": "أعضاء Zero Drop", "tg_t_654": "أعضاء مدى الحياة", "tg_t_659": "أعضاء عرب 10 أيام",
            "tg_t_660": "أعضاء عرب 180 يوم", "tg_t_661": "أعضاء عرب 365 يوم", "tg_t_662": "أعضاء عرب مدى الحياة",
            "tg_t_613": "بريميوم 15 يوم", "tg_t_614": "بريميوم 30 يوم", "tg_t_646": "تعزيزات 2 يوم",
            "tg_t_893": "تعزيزات 7 أيام", "tg_t_894": "تعزيزات 14 يوم", "tg_t_895": "تعزيزات 30 يوم",
            "tg_v_628": "مشاركات ومشاهدات", "tg_v_668": "مشاهدات سريعة 1", "tg_v_669": "مشاهدات سريعة 10", "tg_v_670": "مشاهدات سريعة 50", "tg_v_671": "مشاهدات سريعة 100",
            "tg_a_702": "ردود فعل تليجرام (5)", "tg_a_703": "ردود فعل تليجرام (20)", "tg_a_704": "ردود فعل تليجرام (50)", "tg_a_705": "ردود فعل تليجرام (100)",
            "tg_a_706": "مشاهدات تلقائية (5)", "tg_a_707": "مشاهدات تلقائية (20)", "tg_a_708": "مشاهدات تلقائية (50)", "tg_a_709": "مشاهدات تلقائية (100)", "tg_a_710": "مشاهدات تلقائية (200)", "tg_a_711": "مشاهدات تلقائية (500)",
            "tg_r_620": "تفاعلات تليجرام مختلطة", "tg_r_621": "إعجاب تليجرام", "tg_r_622": "عدم إعجاب", "tg_r_623": "قلب تليجرام", "tg_r_624": "نار تليجرام", "tg_r_625": "عيون قلبية", "tg_r_626": "مذهلة", "tg_r_690": "تفاعلات ومشاهدات",
            "tg_p_665": "تصويت تليجرام عادي", "tg_p_666": "تصويت اشتراك إجباري",
            "fb_f_745": "متابعين فيسبوك 30 يوم", "fb_f_746": "متابعين فيسبوك 90 يوم", "fb_f_747": "متابعين فيسبوك 365 يوم",
            "fb_f_748": "متابعين فيسبوك مدى الحياة", "fb_f_774": "إعجابات صفحة + متابعين", "fb_f_775": "صفحة 90 يوم",
            "fb_f_776": "صفحة 365 يوم", "fb_f_777": "صفحة مدى الحياة", "fb_f_750": "إعجاب فيسبوك", "fb_f_751": "حب فيسبوك",
            "fb_f_752": "عناية فيسبوك", "fb_f_753": "واو فيسبوك", "fb_f_754": "ضحك فيسبوك", "fb_f_755": "حزن فيسبوك",
            "fb_f_756": "غضب فيسبوك", "fb_f_788": "تفاعلات تعليق", "fb_f_789": "ضحك على التعليق", "fb_f_790": "حب على التعليق",
            "fb_f_791": "عناية على التعليق", "fb_f_792": "واو على التعليق", "fb_f_793": "حزن على التعليق", "fb_f_794": "غضب على التعليق",
            "fb_f_778": "مشاهدات قصة فيسبوك", "fb_f_779": "تفاعلات قصة فيسبوك", "fb_f_787": "مشاركة فيسبوك", "fb_f_795": "مشاركة جودة عالية",
            "ig_f_799": "قناة انستغرام - عربي", "ig_f_800": "قناة انستغرام - تركيا", "ig_f_801": "قناة انستغرام - أمريكي",
            "ig_f_802": "قناة انستغرام - فرنسا", "ig_f_803": "قناة انستغرام - باكستان", "ig_f_804": "قناة انستغرام - روسيا",
            "ig_f_757": "مشاهدات فيديو انستغرام", "ig_f_762": "مشاهدات اقتصادية", "ig_f_766": "مشاهدات قصة عرب",
            "ig_f_785": "مشاهدات قصص حقيقية", "ig_f_767": "مشاهدات قصة أجنبية", "ig_f_953": "إعجابات 30 يوم",
            "ig_f_954": "إعجابات 60 يوم", "ig_f_955": "إعجابات 90 يوم", "ig_f_956": "إعجابات 365 يوم",
            "ig_f_957": "إعجابات مدى الحياة", "ig_f_724": "إعجاب تعليق", "ig_f_771": "إعجابات تعليقات اقتصادية",
            "ig_f_772": "تعليقات مخصصة وحقيقية", "ig_f_773": "تعليقات مخصصة مدى الحياة", "ig_f_769": "مشاركة انستغرام", "ig_f_770": "مشاركة مدى الحياة"
        }
        s_id = service_ids.get(data, 712)
        stype = "post"
        if data.startswith("tg_t_") or data in ["ig_f_799", "ig_f_800", "ig_f_801", "ig_f_802", "ig_f_803", "ig_f_804"]: stype = "channel"
        elif data in ["ig_f_724", "ig_f_771"]: stype = "comment"
        elif data in ["ig_f_772", "ig_f_773"]: stype = "comment_text"
        elif data.startswith("tg_p_"): stype = "poll"

        user_selected_service[user_id] = {"service_id": s_id, "name": names.get(data, "خدمة واتساب"), "price": prices.get(data, 0.50), "min": 10, "max": 100000000, "type": stype, "callback_data": data}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data == "confirm_final_order":
        order = user_order_data.get(user_id)
        service = user_selected_service.get(user_id)
        
        if not order or not service:
            await query.answer("⚠️ انتهت صلاحية الطلب أو حدث خطأ، يرجى إعادة محاولة الطلب من جديد.", show_alert=True)
            return

        qty = order.get('count', 1)
        fixed_cost = order.get('fixed_cost', 0.0)
        calc_cost = order.get('calc_cost', 0.0)
        final_cost = fixed_cost if fixed_cost > 0 else calc_cost

        min_limit = service.get('min', 1)
        max_limit = service.get('max', 100000000)
        
        if qty < min_limit or qty > max_limit:
            await query.answer(f"❌ عذراً، الكمية يجب أن تكون بين {min_limit:,} و {max_limit:,}!", show_alert=True)
            return

        u_data = db_get_user(user_id)
        current_balance = float(u_data.get('balance', 0.0))
        if current_balance <= 0 or current_balance < final_cost:
            try:
                await query.edit_message_text(
                    f"❌ **عذراً، رصيدك غير كافٍ أو صفر لإتمام الطلب!**\n⭐ رصيدك الحالي: `${current_balance:.2f}`\n💰 التكلفة المطلوبة: `${final_cost:.2f}`",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 شحن الرصيد", callback_data='deposit_menu'), InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                )
            except Exception:
                pass
            return

        await query.answer("⏳ جاري الاتصال المباشر بالمنصة...", show_alert=False)

        payload = {
            'key': HMCARD_API_KEY,
            'action': 'add',
            'service': int(service['service_id']),
            'link': str(order['link']),
            'quantity': int(qty)
        }

        resp_data = None
        success_request = False
        api_error = "فشل الاتصال بالمنصة"

        custom_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': HMCARD_API_URL
        }

        try:
            scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
            response = scraper.post(HMCARD_API_URL, data=payload, headers=custom_headers, timeout=35)

            if response.status_code == 200:
                try:
                    resp_data = response.json()
                    if isinstance(resp_data, dict):
                        if "order" in resp_data or "order_id" in resp_data or "id" in resp_data:
                            success_request = True
                        elif "error" in resp_data:
                            api_error = resp_data.get("error")
                except json.JSONDecodeError:
                    api_error = "استجابة غير صالحة من السيرفر (ليس JSON)"
            else:
                api_error = f"خطأ HTTP من المنصة: {response.status_code}"
        except Exception as e:
            api_error = str(e)[:100]

        order_id = None
        if success_request and isinstance(resp_data, dict):
            order_id = resp_data.get("order") or resp_data.get("order_id") or resp_data.get("id")

        if success_request and order_id:
            db_update_balance(user_id, final_cost, mode="deduct")
            
            try:
                await query.edit_message_text(
                    f"✅ **تم إرسال طلب الرشق وتأكيده بنجاح!** 🚀✨\n\n"
                    f"🆔 **رقم الطلب في المنصة:** `{order_id}`\n"
                    f"🔗 **الهدف:** `{mask_link(order['link'])}`\n"
                    f"📦 **الكمية:** `{qty:,}`\n"
                    f"⭐ **تم خصم:** `${final_cost:.2f}` من رصيدك.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                )
            except Exception:
                pass
            
            service_name = service.get('name', 'خدمة رقمية')
            cb_param = service.get('callback_data', 'main_rashq')
            log_msg = (
                "🔥 **تم تنفيذ طلب رشق جديد بنجاح!** ✅\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **آيدي العميل:** `{user_id}`\n"
                f"🛍️ **الخدمة:** `{service_name}`\n"
                f"🔗 **الرابط/الآيدي:** `{mask_link(order['link'])}`\n"
                f"📊 **الكمية:** `{qty:,}`\n"
                f"🆔 **رقم الطلب:** `{order_id}`\n"
                f"💰 **المبلغ المخصوم:** `${final_cost:.2f}`\n"
                f"⭐ **الحالة:** تم الإرسال للمنصة بنجاح 🚀"
            )
            await send_log_to_channel(context, log_msg, cb_param)
            return
        else:
            try:
                await query.edit_message_text(
                    f"❌ **عذراً، فشل تنفيذ الطلب من المنصة!**\n\n💬 **السبب:** `{api_error}`\n\n💡 تأكد من صحة رابط الـ API وتوفر الرصيد في حسابك بمنصة HMCARD.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                )
            except Exception:
                pass
            return

    elif data == "cancel_order":
        try:
            await query.edit_message_text("❌ تم إلغاء الطلب بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))
        except Exception:
            pass

    elif data == 'bot_instructions':
        instructions_text = (
            "💎 **دليل استخدام بوت ﴿ ديجيتال هب | Digital Hub ﴾** 🚀\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "مرحباً بك عزيزي العميل في دليلك الكامل لاستخدام خدمات البوت المتطورة من الألف إلى الياء! 🌟\n\n"
            "📱 **1️⃣ قسم الأرقام الافتراضية والتفعيل:**\n"
            "• اختر من القائمة الرئيسية (🛒 شراء رقم افتراضي)، ثم حدد التطبيق (تليجرام، انستغرام، فيسبوك، إلخ).\n"
            "• اختر الدولة المطلوبة ليتم تخصيص الرقم لك فوراً بأعلى نسبة نجاح.\n\n"
            "🔭 **2️⃣ قسم الرشق وشحن الألعاب:**\n"
            "• اضغط على (🔭 قسم الرشق والألعاب)، واختر المنصة المطلوبة.\n\n"
            "💳 **3️⃣ شحن الرصيد التلقائي والآلي:**\n"
            "• يمكنك شحن حسابك عبر محفظة **جيب (Jaib)** أو **بنك الكريمي** بسعر صرف ثابت (1$ = 550 ريال يمني)."
        )
        try:
            await query.edit_message_text(
                instructions_text, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')]])
            )
        except Exception:
            pass

    elif data == 'free_points':
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        u_data = db_get_user(user_id)
        free_text = (
            "💎 **اربح رصيد مجاني في بوت ديجيتال هب!** 🎁\n\n"
            "💬 **قم بدعوة الأصدقاء، وكل شخص ينظم للبوت عن طريقك سوف تحصل على `0.10$` دولار!**\n\n"
            "🔗 **رابط الدعوة الخاص بك:**\n"
            f"`{ref_link}`\n\n"
            "*(انسخ الرابط أعلاه وشاركه مع أصدقائك وفي المجموعات)*\n\n"
            "📊 **أرقامك الحالية:**\n"
            f"👥 عدد الأشخاص الذين دعوتهم: `{u_data['referrals']} شخص`\n"
            f"⭐ إجمالي رصيدك المكتسب: `${u_data['referrals'] * 0.10:.2f}`"
        )
        try:
            await query.edit_message_text(free_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))
        except Exception:
            pass

    elif data == 'transfer_balance':
        admin_state[user_id] = {'action': 'waiting_for_transfer_id'}
        u_data = db_get_user(user_id)
        try:
            await query.edit_message_text(f"🔄 **تحويل الرصيد:**\n⭐ رصيدك الحالي: `${u_data['balance']:.2f}`\n\nأرسل الآن **آيدي (ID)** المستخدم المراد التحويل إليه:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='main_menu')]]))
        except Exception:
            pass

    elif data == 'deposit_menu':
        deposit_text = (
            "💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌟 **بوابة شحن الرصيد الفوري والآمن** 🌟\n\n"
            "أهلاً بك عزيزي العميل. لتعبئة رصيدك بالدولار ($), يرجى اختيار محفظة التحويل المناسبة:\n\n"
            "💱 **سعر الصرف المعتمد (بالعملة القديمة):**\n"
            "• **كل 1 دولار ($) = 550 ريال يمني**\n\n"
            "👇 اختر محفظة الشحن المعتمدة:"
        )
        deposit_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 الشحن عبر محفظة جيب (Jaib)", callback_data='dep_jaib')],
            [InlineKeyboardButton("🏦 الشحن عبر بنك الكريمي (Al-Kuraimi)", callback_data='dep_kreemi')],
            [InlineKeyboardButton("⭐ الشحن الفوري عبر نجوم تليجرام (Stars)", callback_data='dep_telegram_stars')],
            [InlineKeyboardButton("• عودة •", callback_data='main_menu')]
        ])
        try:
            await query.edit_message_text(deposit_text, parse_mode='Markdown', reply_markup=deposit_keyboard)
        except Exception:
            pass

    elif data == 'dep_telegram_stars':
        stars_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ شحن $2 (100 نجمة)", callback_data='pay_stars_100_2')],
            [InlineKeyboardButton("⭐ شحن $10 (500 نجمة)", callback_data='pay_stars_500_10')],
            [InlineKeyboardButton("⭐ شحن $20 (1000 نجمة)", callback_data='pay_stars_1000_20')],
            [InlineKeyboardButton("🔙 عودة", callback_data='deposit_menu')]
        ])
        try:
            await query.edit_message_text("⭐ **اختر الباقة المناسبة لك لشحن رصيدك فوراً:**", parse_mode='Markdown', reply_markup=stars_keyboard)
        except Exception:
            pass

    elif data.startswith('pay_stars_'):
        _, _, stars_count, usd_amount = data.split('_')
        try:
            await context.bot.send_invoice(
                chat_id=user_id, title=f"شحن رصيد بقيمة ${usd_amount}", description="شحن فوري",
                payload=f"deposit_{user_id}_{usd_amount}", provider_token="", currency="XTR", prices=[LabeledPrice("شحن", int(stars_count))]
            )
            await query.answer("✅ تم إرسال فاتورة النجوم في المحادثة.", show_alert=True)
        except Exception:
            await query.answer("⚠️ تعذر إنشاء الفاتورة.", show_alert=True)

    elif data == 'dep_jaib':
        admin_state[user_id] = {'action': 'waiting_for_jaib_deposit'}
        try:
            await query.edit_message_text(
                "💳 **تعليمات الشحن عبر محفظة جيب:**\n\n"
                f"1️⃣ قم بتحويل المبلغ بالريال اليمني إلى حسابنا في جيب:\n"
                f"   📌 رقم الحساب: `{JAIB_ACCOUNT}`\n\n"
                "2️⃣ **قم بإرسال صورة إيصال التحويل (Screenshot) مباشرة هنا في المحادثة.**",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='deposit_menu')]]))
        except Exception:
            pass

    elif data == 'dep_kreemi':
        admin_state[user_id] = {'action': 'waiting_for_kreemi_deposit'}
        try:
            await query.edit_message_text(
                "🏦 **تعليمات الشحن عبر بنك الكريمي:**\n\n"
                "1️⃣ قم بتحويل المبلغ بالريال اليمني إلى حسابنا في الكريمي:\n"
                f"   📌 رقم الحساب : `{KREEMI_ACCOUNT}`\n\n"
                "2️⃣ **قم بإرسال صورة إيصال التحويل (Screenshot) مباشرة هنا في المحادثة.**",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='deposit_menu')]]))
        except Exception:
            pass

    elif data == 'user_account':
        u_data = db_get_user(user_id)
        try:
            await query.edit_message_text(f"👤 **معلومات الحساب:**\n\n🆔 الآيدي: `{user_id}`\n⭐ رصيدك: `${u_data['balance']:.2f}`\n👥 الدعوات: `{u_data['referrals']}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]]))
        except Exception:
            pass

    elif data == 'admin_panel':
        if not is_admin_or_sub(user_id, ADMIN_ID):
            await query.answer("⛔ ليس لديك صلاحيات لوحة التحكم.", show_alert=True)
            return
        
        if user_id == ADMIN_ID:
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
            try:
                await query.edit_message_text(panel_text, parse_mode='Markdown', reply_markup=get_admin_keyboard())
            except Exception:
                pass
        else:
            sub_panel_text = (
                "🛡️ **• لوحة تحكم المشرف المساعد •** 🛡️\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "مرحباً بك يا مشرف! يمكنك استخدام الأزرار أدناه للرد على المستخدمين وإدارة الأرصدة:"
            )
            try:
                await query.edit_message_text(sub_panel_text, parse_mode='Markdown', reply_markup=get_subadmin_keyboard())
            except Exception:
                pass

    elif data == 'admin_top_refs':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        stats = db_get_advanced_stats()
        top_list = stats['top_refs']
        text = "🏆 **قائمة أطراف الإحالات (أعلى 5 أشخاص نشطين):**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        if top_list:
            for idx, (uid, refs) in enumerate(top_list, 1): text += f"{idx}. الآيدي: `{uid}` ⟵ **{refs} دعوة** 🌟\n"
        else: text += "⚠️ لا توجد إحالات مسجلة حتى الآن."
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_create_promo':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_promo_details'}
        try:
            await query.edit_message_text(
                "🎟️ **إنشاء كود هدية جديد:**\n"
                "أرسل التفاصيل بالصيغة التالية:\n"
                "`الكود المبلغ عدد_الاستخدامات`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_reply_user':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_reply_id'}
        try:
            await query.edit_message_text("💬 **الرد على مستخدم:**\nأرسل الآن **آيدي المستخدم** المراد الرد عليه:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_send_gift_user':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_gift_id'}
        try:
            await query.edit_message_text("🎁 **إرسال هدية مالية:**\nأرسل الآن **آيدي المستخدم** المراد إرسال الهدية له:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_add_balance':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_add_bal_id'}
        try:
            await query.edit_message_text("➕ **إضافة رصيد:**\nأرسل الآن **آيدي المستخدم** المراد إضافة الرصيد له:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_deduct_balance':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_deduct_bal_id'}
        try:
            await query.edit_message_text("➖ **خصم رصيد:**\nأرسل الآن **آيدي المستخدم** المراد الخصم من حسابه:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_manage_subadmins':
        if user_id != ADMIN_ID: return
        subs = get_all_sub_admins()
        subs_text = "👥 المشرفون المساعدون:\n" + ("\n".join([f"• `{sid}`" for sid in subs]) if subs else "لا يوجد مشرفين مساعدين.")
        try:
            await query.edit_message_text(subs_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ إضافة", callback_data='admin_add_sub'), InlineKeyboardButton("➖ حذف", callback_data='admin_del_sub')], [InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_add_sub':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_sub_id'}
        try:
            await query.edit_message_text("أرسل آيدي المشرف الجديد:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_del_sub':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_del_sub_id'}
        try:
            await query.edit_message_text("أرسل آيدي المشرف للحذف:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_send_bonus':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_bonus_amount'}
        try:
            await query.edit_message_text("🎁 أرسل المبلغ المراد توزيعه كهدية للجميع (مثال: `0.10`):", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_reset_balances':
        if not is_owner(user_id):
            await query.answer("⛔ عذراً، هذا الإجراء مخصص للمالك الأساسي فقط!", show_alert=True)
            return
        try:
            res = supabase.table("users").select("user_id").execute()
            for u in (res.data if hasattr(res, 'data') else []):
                supabase.table("users").update({"balance": 0.0}).eq("user_id", u["user_id"]).execute()
        except Exception:
            pass
        await query.answer("✅ تمت التصفير بأمان تام بواسطة المالك!", show_alert=True)
        try:
            await query.edit_message_text("🧹 تم تصفير جميع أرصدة المستخدمين بناءً على طلب المالك حصرياً.", reply_markup=get_admin_keyboard())
        except Exception:
            pass

    elif data == 'admin_ban_user':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_ban_id'}
        try:
            await query.edit_message_text("🚫 أرسل آيدي المستخدم للحظر أو فك الحظر:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

    elif data == 'admin_broadcast':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_broadcast'}
        try:
            await query.edit_message_text("📢 **إذاعة شاملة ضخمة:**\nأرسل الآن نص الإذاعة، الصورة، أو أي وسائط تريد إرسالها لجميع المشتركين:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))
        except Exception:
            pass

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("deposit_"): await query.answer(ok=True)
    else: await query.answer(ok=False, error_message="خطأ في الدفع.")

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    if payload.startswith("deposit_"):
        try:
            _, target_user_id, amount_str = payload.split('_')
            target_user_id, amount = int(target_user_id), float(amount_str)
            db_update_balance(target_user_id, amount, mode="add")
            await update.message.reply_text(f"🎉 **تمت عملية الشحن الفوري بنجاح!**\n⭐ تم إضافة: `${amount:.2f}` لحسابك.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))
        except Exception:
            pass

async def handle_photo_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in admin_state and admin_state[user_id].get('action') in ['waiting_for_jaib_deposit', 'waiting_for_kreemi_deposit']:
        action_type = admin_state[user_id].get('action')
        admin_state.pop(user_id, None)
        
        is_jaib = (action_type == 'waiting_for_jaib_deposit')
        wallet_name = "محفظة جيب (Jaib)" if is_jaib else "بنك الكريمي (Al-Kuraimi)"
        target_acc = JAIB_ACCOUNT if is_jaib else KREEMI_ACCOUNT
        
        processing_msg = await update.message.reply_text(
            f"⚡ **جاري فحص وتدقيق إيصال {wallet_name} آلياً واستخراج بيانات العملية...**\n⏳ يرجى الانتظار ثوانٍ معدودة...",
            parse_mode='Markdown'
        )
        
        try:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()

            extracted_text = await analyze_receipt_with_gemini(photo_bytes)

            if extracted_text.startswith("ERROR_"):
                await processing_msg.edit_text(f"❌ **خطأ تقني في قراءة الإيصال:**\n`{extracted_text}`", parse_mode='Markdown')
                return

            clean_text = re.sub(r'[\s\-\_\:\,]', '', extracted_text)
            has_valid_phone = VALID_BENEFICIARY_PHONE in extracted_text or VALID_BENEFICIARY_PHONE in clean_text
            has_valid_name = any(k in extracted_text or k in clean_text for k in ["سالم احمد", "السعدي", "سالم", "يحيى"])

            if not (has_valid_phone and has_valid_name):
                await processing_msg.edit_text("❌ **سبب الخطأ الرئيسي:** الإيصال غير مطابق للبيانات المعتمدة للمستفيد!", parse_mode='Markdown')
                return

            amount_yer = 0.0
            lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
            for line in lines[:4]:
                clean_line = line.replace(',', '').replace(' ', '').replace('•', '')
                if clean_line.isdigit():
                    val = float(clean_line)
                    if 10 <= val <= 10000000 and val != 2026:
                        amount_yer = val
                        break

            if amount_yer <= 0:
                await processing_msg.edit_text("❌ **خطأ:** تعذر تحديد مبلغ التحويل بالريال اليمني بدقة.", parse_mode='Markdown')
                return

            tx_id = None
            tx_id_match = re.search(r'(?:رقم مرجع العملية|مرجع العملية|مرجع|المرجع|Ref|Reference)[:\s#]*([0-9A-Za-z\-]{8,20})', extracted_text, re.IGNORECASE)
            if tx_id_match:
                tx_id = tx_id_match.group(1).strip()

            if not tx_id:
                potential_refs = re.findall(r'\b([0-9]{10,16})\b', extracted_text)
                for ref in potential_refs:
                    if ref != str(target_acc) and ref != str(int(amount_yer)):
                        tx_id = ref
                        break

            if not tx_id:
                await processing_msg.edit_text("❌ **خطأ:** لم يتم العثور على (رقم مرجع العملية) في الإيصال.", parse_mode='Markdown')
                return

            try:
                existing_tx = supabase.table("transactions").select("*").eq("transaction_id", str(tx_id)).execute()
                if existing_tx.data and len(existing_tx.data) > 0:
                    await processing_msg.edit_text("⚠️ **هذا الإيصال مستخدم مسبقاً بالفعل!**", parse_mode='Markdown')
                    return
            except Exception:
                pass

            amount_usd = round(amount_yer / EXCHANGE_RATE, 2)
            saved_success = db_check_and_save_transaction(
                transaction_id=str(tx_id), user_id=user_id, amount_yer=amount_yer, amount_usd=amount_usd, wallet_type=wallet_name
            )

            if not saved_success:
                await processing_msg.edit_text("⚠️ فشل حفظ المعاملة في قاعدة البيانات.", parse_mode='Markdown')
                return

            db_update_balance(user_id, amount_usd, mode="add")
            updated_user = db_get_user(user_id)
            new_balance = float(updated_user.get('balance', 0.0))

            success_reply = (
                f"🎉 **تم التحقق من إيصال العملية وشحن رصيدك بنجاح!** ⚡✨\n\n"
                f"💳 **طريقة الشحن:** {wallet_name}\n"
                f"🆔 **رقم مرجع العملية:** `{tx_id}`\n"
                f"💵 **المبلغ باليمني:** `{amount_yer:,.0f} ريال يمني`\n"
                f"⭐ **المبلغ المضاف:** `${amount_usd:.2f}`\n"
                f"💰 **رصيدك الحالي الجديد:** `${new_balance:.2f}`"
            )

            await processing_msg.edit_text(success_reply, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))

            log_msg = (
                "📥 **عملية شحن رصيد ناجحة وموثقة عبر الإيصال!** ✅\n"
                f"👤 **آيدي العميل:** `{user_id}`\n"
                f"💳 **المحفظة:** {wallet_name}\n"
                f"🆔 **رقم المرجع:** `{tx_id}`\n"
                f"⭐ **المبلغ المضاف:** `${amount_usd:.2f}`"
            )
            await send_log_to_channel(context, log_msg, "deposit_menu")

        except Exception as e:
            await processing_msg.edit_text(f"❌ حدث خطأ غير متوقع: `{str(e)[:100]}`", parse_mode='Markdown')
        return

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_user_subscription(user_id, context):
        await update.message.reply_text(
            FORCED_SUB_MESSAGE,
            parse_mode='Markdown', reply_markup=get_forced_subscription_keyboard()
        )
        return

    text_content = update.message.text.strip() if update.message.text else ""

    # 🛡️ معالجة خطوة التحقق الذكي (مسألة جمع فقط)
    v_status = verification_cache.get(user_id, "not_started")
    if v_status == "waiting_math":
        correct_ans = verification_cache.get(f"{user_id}_ans")
        if text_content.isdigit() and int(text_content) == correct_ans:
            verification_cache[user_id] = "waiting_contact"
            
            contact_button = KeyboardButton("📱 مشاركة جهة الاتصال للتحقق", request_contact=True)
            contact_kb = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
            
            await update.message.reply_text(
                "✅ **إجابة صحيحة يا بطل!** 🧠\n\n"
                "🛡️ **الخطوة الأخيرة للتحقق الأمني (2/2):**\n"
                "يرجى الضغط على الزر أدناه لمشاركة جهة الاتصال الخاصة بك للتحقق من أنك مستخدم عربي حقيقي وليست أداة وهمية:",
                parse_mode='Markdown',
                reply_markup=contact_kb
            )
        else:
            await update.message.reply_text("❌ الإجابة خاطئة! حاول مجدداً، كم ناتج الجمع في المسألة الرياضية السابقة؟")
        return

    # 🛡️ استلام جهة الاتصال، التحقق من كونها عربية، واحتساب الإحالة وإرسال الإشعارات فوراً
    if update.message.contact:
        contact = update.message.contact
        if contact.user_id == user_id:
            phone_num = str(contact.phone_number)
            
            arab_prefixes = ["967", "966", "20", "971", "965", "974", "968", "973", "962", "961", "964", "213", "212", "216", "249", "963", "970"]
            is_arab = any(phone_num.startswith(prefix) or phone_num.replace("+", "").startswith(prefix) for prefix in arab_prefixes)
            
            if is_arab:
                verification_cache[user_id] = "passed"
                u_data = db_get_user(user_id)
                
                # 🎁 هنا يتم احتساب الإحالة وإرسال إشعار للداعي وللأدمن بعد نجاح التحقق بالكامل
                await process_successful_join_reward(update.effective_user, context, u_data)
                u_data = db_get_user(user_id)

                success_welcome = (
                    f"🎉 **تم التحقق بنجاح تام! أهلاً بك يا {update.effective_user.first_name} في عالم ديجيتال هب** 🚀✨\n\n"
                    f"👤 **الآيدي:** `{user_id}`\n"
                    f"💙 **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
                    "🌟 تم تفعيل حسابك بنجاح وأصبحت جاهزاً لاستخدام كافة خدمات الأرقام والرشق!"
                )
                await update.message.reply_text(
                    success_welcome,
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard(user_id, lambda uid: is_admin_or_sub(uid, ADMIN_ID))
                )
                return
            else:
                await update.message.reply_text(
                    "❌ **عذراً، نظام التحقق رصد أن رقم الهاتف غير عربي أو غير مدعوم!**\n"
                    "البوت مخصص للمستخدمين العرب فقط.",
                    reply_markup=ReplyKeyboardRemove()
                )
                return

    u_data = db_get_user(user_id)

    if is_admin_or_sub(user_id, ADMIN_ID) and user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_promo_details':
        admin_state.pop(user_id, None)
        try:
            parts = text_content.split()
            numbers = []
            promo_code = "GIFT"
            for p in parts:
                try:
                    numbers.append(float(p))
                except ValueError:
                    if not any(char.isdigit() for char in p):
                        promo_code = p.upper()

            promo_amount = numbers[0] if len(numbers) > 0 else 0.50
            promo_max = int(numbers[1]) if len(numbers) > 1 else 50

            try:
                supabase.table("promo_codes").insert({
                    "code": promo_code, "amount": promo_amount, "max_uses": promo_max, "current_uses": 0
                }).execute()
            except Exception:
                pass

            bot_username = context.bot.username
            promo_link = f"https://t.me/{bot_username}?start=promo_{promo_code}"
            await update.message.reply_text(f"✅ تم إنشاء كود الهدية `{promo_code}` بقيمة `${promo_amount}` بنجاح!", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ: {e}")
        return

    if is_admin_or_sub(user_id, ADMIN_ID) and user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_broadcast':
        admin_state.pop(user_id, None)
        all_users = db_get_all_users()
        if not all_users:
            await update.message.reply_text("⚠️ لا توجد مستخدمين للإذاعة.")
            return

        status_msg = await update.message.reply_text(f"📢 بدء الإذاعة لـ ({len(all_users)}) مشترك...")
        success_count = 0
        for item in all_users:
            uid = item.get("user_id") if isinstance(item, dict) else item
            if not uid: continue
            try:
                await context.bot.send_message(chat_id=int(uid), text=update.message.text, parse_mode='Markdown')
                success_count += 1
                await asyncio.sleep(0.03)
            except Exception:
                pass
        await status_msg.edit_text(f"✅ اكتملت الإذاعة بنجاح لـ ({success_count}) مشترساً!")
        return

    if user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_rashq_link':
        admin_state[user_id]['link'] = text_content
        admin_state[user_id]['action'] = 'waiting_for_rashq_count'
        await update.message.reply_text("📊 أرسل الآن العدد المطلوب للتمويل (أرقام صحيحة فقط):")
        return

    elif user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_rashq_count':
        if not text_content.isdigit():
            await update.message.reply_text("⚠️ يرجى إرسال أرقام صحيحة فقط للعدد:")
            return
        
        count = int(text_content)
        st_data = admin_state.get(user_id, {})
        service_info = st_data.get('service_info', {"name": "خدمة", "price": 1.0, "min": 10, "max": 100000000})
        
        calc_cost = round((service_info["price"] * count) / 1000.0, 2)
        if calc_cost <= 0: calc_cost = 0.01

        user_order_data[user_id] = {"link": st_data['link'], "count": count, "calc_cost": calc_cost, "fixed_cost": 0.0}
        user_selected_service[user_id] = service_info
        admin_state.pop(user_id, None)

        summary_text = (
            f"📌 ملخص طلبك:\n\n"
            f"🔹 الخدمة: {service_info['name']}\n"
            f"🔗 الرابط: `{mask_link(st_data['link'])}`\n"
            f"📊 العدد: `{count:,}`\n"
            f"💰 التكلفة الإجمالية: `${calc_cost:.2f}$`"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد الطلب", callback_data="confirm_final_order")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_order")]
        ])
        await update.message.reply_text(summary_text, reply_markup=markup, parse_mode="Markdown")
        return

    elif user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_pubg_id':
        player_id = text_content
        st_data = admin_state.get(user_id, {})
        service_info = st_data.get('service_info', {"name": "شدات ببجي", "fixed_price": 1.14})
        fixed_price = service_info.get("fixed_price", 1.14)
        
        user_order_data[user_id] = {"link": player_id, "count": 1, "calc_cost": 0.0, "fixed_cost": fixed_price}
        user_selected_service[user_id] = service_info
        admin_state.pop(user_id, None)

        summary_text = (
            f"🎮 ملخص طلب الشحن (بالآيدي):\n\n"
            f"🔹 الحزمة: {service_info['name']}\n"
            f"🆔 آيدي اللاعب (Player ID): `{player_id}`\n"
            f"💰 السعر الإجمالي الصافي: `${fixed_price:.2f}$`"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد الشحن", callback_data="confirm_final_order")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_order")]
        ])
        await update.message.reply_text(summary_text, reply_markup=markup, parse_mode="Markdown")
        return
