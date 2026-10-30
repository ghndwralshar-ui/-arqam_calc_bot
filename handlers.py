import logging
import asyncio
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes

from config import (
    BOT_TOKEN, ADMIN_ID, SUPPORT_USERNAME, FORCED_CHANNEL_USERNAME, 
    FORCED_CHANNEL_URL, LOG_CHANNEL_ID, HMCARD_API_URL, HMCARD_API_KEY, 
    HEADERS, COUNTRY_INFO, STATIC_COUNTRIES
)
from database import (
    db_get_user, db_update_balance, db_get_advanced_stats, 
    db_get_all_users, is_admin_or_sub, get_all_sub_admins
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
    get_admin_keyboard
)

admin_state = {}
user_selected_service = {}
user_order_data = {}

# سعر الصرف الثابت (كل 1 دولار = 550 ريال يمني بالعملة القديمة)
EXCHANGE_RATE = 550.0

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

async def get_forced_subscription_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 اضغط هنا للانضمام إلى القناة", url=FORCED_CHANNEL_URL)],
        [InlineKeyboardButton("✅ اشتركت، تحقق من الاشتراك 🔄", callback_data="check_subscription")]
    ])

async def process_successful_join_reward(user, context, u_data):
    try:
        if u_data.get("reward_claimed", 0) == 1:
            return
        from database import supabase
        supabase.table("users").update({"reward_claimed": 1}).eq("user_id", user.id).execute()

        if user.id != ADMIN_ID:
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
            except Exception as admin_notify_err:
                print(f"Error notifying admin about new user: {admin_notify_err}")

        referrer_id = u_data.get("referred_by", 0)
        if referrer_id > 0 and referrer_id != user.id:
            db_update_balance(referrer_id, 0.10, mode="add")
            ref_info = db_get_user(referrer_id)
            new_ref_count = ref_info["referrals"] + 1
            supabase.table("users").update({"referrals": new_ref_count}).eq("user_id", referrer_id).execute()
            
            try:
                updated_ref_info = db_get_user(referrer_id)
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=(
                        "🎉🔥 **تهانينا القلبية لك يا بطل!** 🔥🎉\n"
                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                        "🌟 انضم مستخدم جديد عبر رابط الإحالة الخاص بك!\n\n"
                        "🎁 **تمت إضافة:** `$0.10` إلى رصيدك كمكافأة دعوة.\n"
                        f"💰 **رصيدك الحالي:** `${updated_ref_info['balance']:.2f}`\n"
                        f"👥 **إجمالي دعواتك:** `{updated_ref_info['referrals']} شخص`\n\n"
                        "🚀 *واصل مشاركة رابطك واربح المزيد من الأرباح فوراً!*"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as ref_msg_err:
                print(f"Error sending ref msg: {ref_msg_err}")
    except Exception as e:
        print(f"process_successful_join_reward Error: {e}")

def mask_link(link: str) -> str:
    if not link: return "لا يوجد رابط"
    length = len(link)
    if length <= 10: return link[:3] + "..."
    half = length // 2
    return link[:half] + "..."

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
                        min_price = 999.0
                        if isinstance(country_info, dict):
                            for operator, op_data in country_info.items():
                                if isinstance(op_data, dict):
                                    count = op_data.get("count", 0)
                                    cost = op_data.get("cost", 0)
                                    if count > 0 and cost is not None:
                                        has_stock = True
                                        base_price = float(cost)
                                        if base_price < min_price:
                                            min_price = base_price
                        if has_stock and min_price < 999.0:
                            doubled_price = round(min_price * 2.0, 2)
                            c_meta = COUNTRY_INFO[country_code]
                            available_countries.append({
                                "code": country_code,
                                "name_ar": c_meta["name_ar"],
                                "flag": c_meta["flag"],
                                "dial": c_meta["dial"],
                                "price": doubled_price
                            })
        except Exception as e:
            print(f"Error fetching countries for {service}: {e}")
    available_countries.sort(key=lambda x: x["price"])
    return available_countries

async def show_available_countries_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, service_code: str, service_title: str):
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer("⏳ جاري فحص الدول المتوفرة والأسعار المحدثة...", show_alert=False)
    available_countries = await get_available_countries_for_service(service_code)
    
    if not available_countries:
        out_of_stock_msg = (
            "📢 **عذراً عزيزي العميل!**\n"
            "🇸🇦 نفدت أرقام هذه الدولة مؤقتاً بسبب الضغط الشديد.\n"
            "🔄 جاري توفير أرقام جديدة قريباً، يمكنك اختيار دولة أخرى متاحة حالياً بكل سهولة! 👇"
        )
        await query.edit_message_text(
            out_of_stock_msg,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عـودة للخدمات", callback_data='buy_virtual_number')]])
        )
        return

    buttons = []
    row = []
    for c in available_countries:
        btn_text = f"{c['flag']} {c['name_ar']} • ${c['price']:.2f}"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"buy_num_{service_code}_{c['code']}_{c['price']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🔙 عـودة للخدمات", callback_data='buy_virtual_number')])
    u_data = db_get_user(user_id)
    
    await query.edit_message_text(
        f"🔹 **• الدول المتوفرة حالياً لأرقام ({service_title}) •**\n"
        f"⭐ رصيدك: `${u_data['balance']:.2f}`\n\n"
        "👇 **اختر الدولة المطلوبة:**",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def check_sms_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 جاري فحص وصول الكود...", show_alert=False)
    
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
                    current_text = query.message.text
                    
                    updated_text = current_text + f"\n\n🔑 **الكود:** `{sms_code}`\n💬 **النص:** `{full_text}`"
                    await query.edit_message_text(
                        updated_text, parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                    )
                else:
                    await query.answer("⏳ لم يتم استلام الكود بعد، انتظر قليلاً واضغط مجدداً.", show_alert=True)
            else:
                await query.answer("⚠️ تعذر فحص الطلب حالياً.", show_alert=True)
        except Exception:
            await query.answer("❌ خطأ في الاتصال بالسيرفر.", show_alert=True)

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
                        
                        success_msg = (
                            f"💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"✅ **تم شراء الرقم بنجاح تام!**\n\n"
                            f"📦 **القسم:** `{section_name}`\n"
                            f"🌍 **الدولة:** {country_name}\n"
                            f"📞 **مفتاح الدولة:** `{dial_code}`\n"
                            f"📱 **الرقم المشتري:** `{phone}`\n"
                            f"⭐ **المبلغ المخصوم:** `${price:.2f}`\n\n"
                            f"🔑 **الكود الواصل:** `{sms_code}`\n"
                            f"💬 **النص الكامل:** `{full_text}`\n\n"
                            f"💡 *قم بوضع الرقم في التطبيق واطلب الكود فوراً!* 🚀"
                        )
                        
                        try:
                            await context.bot.edit_message_text(
                                chat_id=chat_id, message_id=message_id,
                                text=success_msg, parse_mode='Markdown',
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                            )
                        except Exception:
                            pass
                        
                        try:
                            masked_ph = phone[:4] + "***" + phone[-3:]
                            service_deeplink = f"https://t.me/{bot_username}?start=buy_virtual_number"
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
                                    f"🛍️ **القسم:** `{section_name}`\n"
                                    f"📱 **الرقم:** `{masked_ph}`\n"
                                    f"🔑 **الكود:** `{sms_code}`\n"
                                    f"⭐ **الحالة:** مكتمل ومنجز بنجاح 🚀"
                                ),
                                parse_mode='Markdown', reply_markup=channel_buttons
                            )
                        except Exception as log_err:
                            print(f"Log error: {log_err}")
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

    if not await check_user_subscription(user.id, context):
        await update.message.reply_text(
            f"💎 ديجيتال هب | Digital Hub:\n🚀 To use this bot, you must join our channel {FORCED_CHANNEL_URL}",
            parse_mode='Markdown', reply_markup=await get_forced_subscription_keyboard()
        )
        return

    args = context.args
    arg_param = args[0] if args else None

    if arg_param and arg_param.isdigit():
        referrer_id = int(arg_param)
        if referrer_id != user.id:
            if u_data.get('referred_by', 0) == 0:
                from database import supabase
                supabase.table("users").update({"referred_by": referrer_id}).eq("user_id", user.id).execute()
                u_data['referred_by'] = referrer_id

    await process_successful_join_reward(user, context, u_data)

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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == 'check_subscription':
        if await check_user_subscription(user_id, context):
            await query.answer("✅ تم التحقق من اشتراكك بنجاح! أهلاً بك.", show_alert=True)
            u_data = db_get_user(user_id)
            await process_successful_join_reward(query.from_user, context, u_data)
            welcome_text = (
                f"💎 **مرحباً بك عزيزي {query.from_user.first_name} في بوت ﴿ ديجيتال هب | Digital Hub ﴾** 🚀\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 **الآيدي:** `{user_id}`\n"
                f"💙 **رصيدك الحالي:** `${u_data['balance']:.2f}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🌟 بوابتك الأولى والأسرع للخدمات الرقمية المتكاملة، الأرقام الافتراضية، والرشق!\n\n"
                "👇 **اختر ما يناسبك من القائمة أدناه:**"
            )
            await query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id, lambda uid: is_admin_or_sub(uid, ADMIN_ID)))
        else:
            await query.answer("❌ عذراً، لم تقم بالاشتراك في القناة بعد! يرجى الاشتراك ثم إعادة المحاولة.", show_alert=True)
        return

    if not await check_user_subscription(user_id, context):
        await query.answer("⚠️ يجب عليك الاشتراك في القناة أولاً لاستخدام البوت!", show_alert=True)
        try:
            await query.edit_message_text(
                f"💎 ديجيتال هب | Digital Hub:\n🚀 To use this bot, you must join our channel {FORCED_CHANNEL_URL}",
                parse_mode='Markdown', reply_markup=await get_forced_subscription_keyboard()
            )
        except Exception:
            pass
        return

    await query.answer()

    if data == 'main_menu':
        u_data = db_get_user(user_id)
        await process_successful_join_reward(query.from_user, context, u_data)
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
        await query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id, lambda uid: is_admin_or_sub(uid, ADMIN_ID)))

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

    elif data == 'most_available':
        await show_available_countries_menu(update, context, "whatsapp", "واتساب")

    elif data == 'deals_whatsapp':
        await show_available_countries_menu(update, context, "whatsapp", "واتساب")

    elif data == 'deals_telegram':
        await show_available_countries_menu(update, context, "telegram", "تليجرام")

    elif data == 'service_whatsapp':
        await show_available_countries_menu(update, context, "whatsapp", "واتساب 🛍️")
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
        
        u_data = db_get_user(user_id)
        current_balance = float(u_data.get('balance', 0.0))
        if current_balance <= 0 or current_balance < country_price:
            await query.edit_message_text(
                f"❌ **عذراً، رصيدك غير كافٍ أو صفر لشراء الرقم!**\n⭐ رصيدك الحالي: `${current_balance:.2f}`\n💰 سعر الرقم: `${country_price:.2f}`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 شحن الرصيد", callback_data='deposit_menu'), InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]])
            )
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

        await query.answer("🔄 جاري الشراء وتجهيز الرقم...", show_alert=False)
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            try:
                res = await client.get(f"https://5sim.net/v1/user/buy/activation/{country_code}/any/{service}")
                if res.status_code == 200:
                    try:
                        res_data = res.json()
                    except Exception:
                        await query.edit_message_text(out_of_stock_msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='buy_virtual_number')]]))
                        return

                    phone, order_id = res_data.get('phone'), res_data.get('id')
                    if not phone or not order_id:
                        await query.edit_message_text(out_of_stock_msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='buy_virtual_number')]]))
                        return

                    db_update_balance(user_id, country_price, mode="deduct")
                    
                    success_msg = (
                        f"💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ **تم شراء الرقم بنجاح تام!**\n\n"
                        f"📦 **القسم:** `{sec_name_ar}`\n"
                        f"🌍 **الدولة:** {c_name_ar}\n"
                        f"📞 **مفتاح الدولة:** `{c_dial}`\n"
                        f"📱 **الرقم المشتري:** `{phone}`\n"
                        f"⭐ **المبلغ المخصوم:** `${country_price:.2f}`\n\n"
                        f"⏳ **جاري رصد واستقبال الكود تلقائياً...**\n"
                        f"💡 *قم بوضع الرقم في التطبيق واطلب الكود فوراً!* 🚀"
                    )
                    
                    sent_msg = await query.edit_message_text(
                        success_msg,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 طلب الكود", callback_data=f"chk_sms_{order_id}")],
                            [InlineKeyboardButton("❌ إلغاء الرقم واسترداد الرصيد", callback_data=f"cnl_paid_{order_id}_{country_price}")]
                        ])
                    )
                    
                    asyncio.create_task(watch_order_sms_auto(context, query.message.chat_id, sent_msg.message_id, str(order_id), phone, country_price, service, user_id, context.bot.username, sec_name_ar, c_name_ar, c_dial))
                else:
                    await query.edit_message_text(out_of_stock_msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='buy_virtual_number')]]))
            except Exception as e:
                await query.edit_message_text(f"⚠️ خطأ بالاتصال: `{str(e)[:50]}`", parse_mode='Markdown')

    elif data.startswith('chk_sms_'):
        await check_sms_manual(update, context)
        return

    elif data.startswith('cnl_'):
        parts = data.split('_')
        cancel_type, order_id, price = parts[1], parts[2], float(parts[3])
        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
            res = await client.get(f"https://5sim.net/v1/user/cancel/{order_id}")
            if res.status_code == 200 or res.status_code == 400:
                if cancel_type == 'paid': db_update_balance(user_id, price, mode="add")
                await query.answer("✅ تم إلغاء الرقم واسترداد الرصيد بنجاح!", show_alert=True)
                await query.edit_message_text("🚫 **تم إلغاء الرقم واسترداد مبلغ الرصيد إلى محفظتك بنجاح.**", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))

    elif data == "main_rashq":
        await query.edit_message_text("📂 اختر القسم المطلوب:", reply_markup=sections_menu_keyboard())

    elif data == "sec_whatsapp":
        await query.edit_message_text("🟢 خدمات واتساب:\nاختر الخدمة المطلوبة:", reply_markup=whatsapp_services_keyboard())

    elif data == "sec_telegram":
        await query.edit_message_text("🚀 خدمات تليجرام:\nاختر القسم الفرعي المطلوب:", reply_markup=telegram_services_keyboard())

    elif data == "sec_facebook":
        await query.edit_message_text("📘 خدمات فيسبوك:", reply_markup=facebook_services_keyboard())

    elif data == "sec_instagram":
        await query.edit_message_text("📸 خدمات انستغرام:", reply_markup=instagram_services_keyboard())

    elif data == "sec_tiktok":
        await query.edit_message_text("🎵 خدمات تيك توك:", reply_markup=tiktok_services_keyboard())

    elif data == "sec_youtube":
        await query.edit_message_text("📺 خدمات يوتيوب:", reply_markup=youtube_services_keyboard())

    elif data == "sec_pubg":
        await query.edit_message_text("🎮 قسم شحن شدات ببجي موبايل:", reply_markup=pubg_services_keyboard())

    elif data == "sec_freefire":
        await query.edit_message_text("🔥 قسم شحن فري فاير:", reply_markup=freefire_services_keyboard())

    elif data in ["sec_twitter", "sec_kwai", "sec_snapchat", "sec_linkedin"]:
        await query.answer("⚠️ عذراً، لا توجد خدمات متاحة في هذه الفئة حالياً.", show_alert=True)
        return

    elif data == "ig_channel_menu":
        await query.edit_message_text("📺 متابعو قناة انستغرام:", reply_markup=ig_channel_menu_keyboard())

    elif data == "ig_views_menu":
        await query.edit_message_text("👁️ مشاهدات انستغرام:", reply_markup=ig_views_menu_keyboard())

    elif data == "ig_story_menu":
        await query.edit_message_text("📸 مشاهدات قصص انستغرام:", reply_markup=ig_story_menu_keyboard())

    elif data == "ig_likes_menu":
        await query.edit_message_text("👍 إعجابات انستغرام:", reply_markup=ig_likes_menu_keyboard())

    elif data == "ig_comment_likes_menu":
        await query.edit_message_text("💬 إعجابات تعليقات انستغرام:", reply_markup=ig_comment_likes_menu_keyboard())

    elif data == "ig_comments_menu":
        await query.edit_message_text("💬 تعليقات انستغرام مخصصة:", reply_markup=ig_comments_menu_keyboard())

    elif data == "ig_shares_menu":
        await query.edit_message_text("🔄 مشاركات انستغرام:", reply_markup=ig_shares_menu_keyboard())

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
        await query.edit_message_text("👤 متابعو الملف الشخصي:", reply_markup=fb_profile_menu_keyboard())

    elif data == "fb_page_menu":
        await query.edit_message_text("📘 متابعو الصفحة:", reply_markup=fb_page_menu_keyboard())

    elif data == "fb_group_744":
        user_selected_service[user_id] = {"service_id": 744, "name": "أعضاء مجموعة فيسبوك", "price": 0.72, "min": 10, "max": 100000, "type": "channel"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data == "fb_react_menu":
        await query.edit_message_text("👍 تفاعلات منشورات فيسبوك:", reply_markup=fb_react_menu_keyboard())

    elif data == "fb_comment_react_menu":
        await query.edit_message_text("💬 تفاعلات تعليقات فيسبوك:", reply_markup=fb_comment_react_menu_keyboard())

    elif data == "fb_story_menu":
        await query.edit_message_text("📸 مشاهدات قصة فيسبوك:", reply_markup=fb_story_menu_keyboard())

    elif data == "fb_share_menu":
        await query.edit_message_text("🔄 مشاركات فيسبوك:", reply_markup=fb_share_menu_keyboard())

    elif data == "wa_subscribers":
        await query.edit_message_text("🟢 بروفايل وأعضاء واتساب:", reply_markup=channel_subscribers_keyboard())

    elif data == "wa_reactions":
        await query.edit_message_text("🟢 تفاعلات واتساب:", reply_markup=emoji_reactions_keyboard())

    elif data == "wa_auto_reactions":
        await query.edit_message_text("🟢 تفاعلات تلقائية واتساب:", reply_markup=auto_reactions_keyboard())

    elif data == "wa_polls":
        await query.edit_message_text("🟢 تصويتات واتساب:", reply_markup=polls_keyboard())

    elif data.startswith("sub_"):
        service_ids = {"sub_no_guarantee": 729, "sub_30d": 730, "sub_60d": 731, "sub_90d": 732, "sub_global": 805, "sub_arabic": 806}
        prices = {"sub_no_guarantee": 0.39, "sub_30d": 0.70, "sub_60d": 0.80, "sub_90d": 0.80, "sub_global": 0.90, "sub_arabic": 1.0}
        names = {"sub_no_guarantee": "بروفايل واتساب - أعضاء بدون ضمان", "sub_30d": "بروفايل واتساب - ضمان 30 يوم", "sub_60d": "بروفايل واتساب - ضمان 60 يوم", "sub_90d": "بروفايل واتساب - ضمان 90 يوم", "sub_global": "بروفايل واتساب - عالمي", "sub_arabic": "بروفايل واتساب - عربي"}
        user_selected_service[user_id] = {"service_id": service_ids.get(data, 730), "name": names.get(data, "واتساب"), "price": prices.get(data, 1.0), "min": 10, "max": 100000000, "type": "channel"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data.startswith("tg_t_") or data.startswith("fb_f_") or data.startswith("ig_f_"):
        service_ids = {
            "tg_t_653": 653, "tg_t_654": 654, "tg_t_659": 659, "tg_t_660": 660, "tg_t_661": 661, "tg_t_662": 662,
            "tg_t_613": 613, "tg_t_614": 614, "tg_t_646": 646, "tg_t_893": 893, "tg_t_894": 894, "tg_t_895": 895,
            "fb_f_745": 745, "fb_f_746": 746, "fb_f_747": 747, "fb_f_748": 748, "fb_f_774": 774, "fb_f_775": 775,
            "fb_f_776": 776, "fb_f_777": 777, "fb_f_750": 750, "fb_f_751": 751, "fb_f_752": 752, "fb_f_753": 753,
            "fb_f_754": 754, "fb_f_755": 755, "fb_f_756": 756, "fb_f_788": 788, "fb_f_789": 789, "fb_f_790": 790,
            "fb_f_791": 791, "fb_f_792": 792, "fb_f_793": 793, "fb_f_794": 794, "fb_f_778": 778, "fb_f_779": 779,
            "fb_f_787": 787, "fb_f_795": 795, "ig_f_799": 799, "ig_f_800": 800, "ig_f_801": 801, "ig_f_802": 802,
            "ig_f_803": 803, "ig_f_804": 804, "ig_f_757": 757, "ig_f_762": 762, "ig_f_766": 766, "ig_f_785": 785,
            "ig_f_767": 767, "ig_f_953": 953, "ig_f_954": 954, "ig_f_955": 955, "ig_f_956": 956, "ig_f_957": 957,
            "ig_f_724": 724, "ig_f_771": 771, "ig_f_772": 772, "ig_f_773": 773, "ig_f_769": 769, "ig_f_770": 770
        }
        prices = {
            "tg_t_653": 2.46, "tg_t_654": 2.80, "tg_t_659": 2.00, "tg_t_660": 5.40, "tg_t_661": 5.60, "tg_t_662": 6.00,
            "tg_t_613": 4.00, "tg_t_614": 8.00, "tg_t_646": 30.00, "tg_t_893": 116.00, "tg_t_894": 196.00, "tg_t_895": 316.00,
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
            "tg_t_653": "أعضاء Zero Drop", "tg_t_654": "أعضاء مدى الحياة", "tg_t_659": "أعضاء عرب 10 أيام",
            "tg_t_660": "أعضاء عرب 180 يوم", "tg_t_661": "أعضاء عرب 365 يوم", "tg_t_662": "أعضاء عرب مدى الحياة",
            "tg_t_613": "بريميوم 15 يوم", "tg_t_614": "بريميوم 30 يوم", "tg_t_646": "تعزيزات 2 يوم",
            "tg_t_893": "تعزيزات 7 أيام", "tg_t_894": "تعزيزات 14 يوم", "tg_t_895": "تعزيزات 30 يوم",
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
        s_id = service_ids.get(data, 730)
        stype = "post"
        if data in ["ig_f_799", "ig_f_800", "ig_f_801", "ig_f_802", "ig_f_803", "ig_f_804"]: stype = "channel"
        elif data in ["ig_f_724", "ig_f_771"]: stype = "comment"
        elif data in ["ig_f_772", "ig_f_773"]: stype = "comment_text"

        user_selected_service[user_id] = {"service_id": s_id, "name": names.get(data, "خدمة"), "price": prices.get(data, 1.0), "min": 10, "max": 100000000, "type": stype}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data.startswith("react_") or data.startswith("tg_r_"):
        service_ids = {
            "react_random": 733, "react_like": 814, "react_heart": 815, "react_haha": 736, "react_wow": 737, "react_sad": 738, "react_pray": 739,
            "tg_r_620": 620, "tg_r_621": 621, "tg_r_622": 622, "tg_r_623": 623, "tg_r_624": 624, "tg_r_625": 625, "tg_r_626": 626, "tg_r_690": 690
        }
        names = {
            "react_random": "تفاعلات عشوائية", "react_like": "إعجاب", "react_heart": "حب", "react_haha": "ضحك", "react_wow": "واو", "react_sad": "حزن", "react_pray": "دعاء",
            "tg_r_620": "تفاعلات تليجرام مختلطة", "tg_r_621": "إعجاب تليجرام", "tg_r_622": "عدم إعجاب", "tg_r_623": "قلب تليجرام", "tg_r_624": "نار تليجرام", "tg_r_625": "عيون قلبية", "tg_r_626": "مذهلة", "tg_r_690": "تفاعلات ومشاهدات"
        }
        s_id = service_ids.get(data, 733)
        price = 0.20 if s_id in range(733, 740) else 0.06
        user_selected_service[user_id] = {"service_id": s_id, "name": names.get(data, "تفاعلات"), "price": price, "min": 10, "max": 100000, "type": "post"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data.startswith("auto_") or data.startswith("tg_a_"):
        service_ids = {
            "auto_10": 712, "auto_25": 713, "auto_50": 714, "auto_100": 715,
            "tg_a_702": 702, "tg_a_703": 703, "tg_a_704": 704, "tg_a_705": 705,
            "tg_a_706": 706, "tg_a_707": 707, "tg_a_708": 708, "tg_a_709": 709, "tg_a_710": 710, "tg_a_711": 711
        }
        prices = {
            "auto_10": 15.44, "auto_25": 30.88, "auto_50": 61.74, "auto_100": 123.50,
            "tg_a_702": 0.76, "tg_a_703": 1.54, "tg_a_704": 3.84, "tg_a_705": 7.68,
            "tg_a_706": 0.08, "tg_a_707": 0.28, "tg_a_708": 0.72, "tg_a_709": 1.42, "tg_a_710": 2.86, "tg_a_711": 8.30
        }
        names = {
            "auto_10": "تفاعلات تلقائية (10)", "auto_25": "تفاعلات تلقائية (25)", "auto_50": "تفاعلات تلقائية (50)", "auto_100": "تفاعلات تلقائية (100)",
            "tg_a_702": "ردود فعل تليجرام (5)", "tg_a_703": "ردود فعل تليجرام (20)", "tg_a_704": "ردود فعل تليجرام (50)", "tg_a_705": "ردود فعل تليجرام (100)",
            "tg_a_706": "مشاهدات تلقائية (5)", "tg_a_707": "مشاهدات تلقائية (20)", "tg_a_708": "مشاهدات تلقائية (50)", "tg_a_709": "مشاهدات تلقائية (100)", "tg_a_710": "مشاهدات تلقائية (200)", "tg_a_711": "مشاهدات تلقائية (500)"
        }
        user_selected_service[user_id] = {"service_id": service_ids.get(data, 712), "name": names.get(data, "تلقائي"), "price": prices.get(data, 1.0), "min": 10, "max": 100000, "type": "channel"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data.startswith("poll_") or data.startswith("tg_p_"):
        service_ids = {"poll_1": 725, "poll_2": 726, "poll_3": 727, "poll_4": 728, "tg_p_665": 665, "tg_p_666": 666}
        prices = {"poll_1": 4.00, "poll_2": 4.00, "poll_3": 4.00, "poll_4": 4.00, "tg_p_665": 4.00, "tg_p_666": 18.00}
        names = {"poll_1": "تصويت 1", "poll_2": "تصويت 2", "poll_3": "تصويت 3", "poll_4": "تصويت 4", "tg_p_665": "تصويت تليجرام عادي", "tg_p_666": "تصويت اشتراك إجباري"}
        user_selected_service[user_id] = {"service_id": service_ids.get(data, 725), "name": names.get(data, "تصويت"), "price": prices.get(data, 4.00), "min": 10, "max": 100000, "type": "poll"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data.startswith("tg_v_"):
        service_ids = {"tg_v_628": 628, "tg_v_668": 668, "tg_v_669": 669, "tg_v_670": 670, "tg_v_671": 671}
        prices = {"tg_v_628": 0.04, "tg_v_668": 0.02, "tg_v_669": 0.10, "tg_v_670": 0.60, "tg_v_671": 1.22}
        names = {"tg_v_628": "مشاركات ومشاهدات", "tg_v_668": "مشاهدات سريعة 1", "tg_v_669": "مشاهدات سريعة 10", "tg_v_670": "مشاهدات سريعة 50", "tg_v_671": "مشاهدات سريعة 100"}
        user_selected_service[user_id] = {"service_id": service_ids.get(data, 628), "name": names.get(data, "مشاهدات"), "price": prices.get(data, 0.05), "min": 10, "max": 100000000, "type": "post"}
        prompt_user_for_link(update.effective_message, user_selected_service[user_id], context)

    elif data == "confirm_final_order":
        order = user_order_data.get(user_id)
        service = user_selected_service.get(user_id)
        if order and service:
            qty = order.get('count', 1)
            fixed_cost = order.get('fixed_cost', 0.0)
            calc_cost = order.get('calc_cost', 0.0)
            final_cost = fixed_cost if fixed_cost > 0 else calc_cost

            u_data = db_get_user(user_id)
            current_balance = float(u_data.get('balance', 0.0))
            if current_balance <= 0 or current_balance < final_cost:
                await query.edit_message_text(
                    f"❌ **عذراً، رصيدك غير كافٍ أو صفر لإتمام الطلب!**\n⭐ رصيدك الحالي: `${current_balance:.2f}`\n💰 التكلفة المطلوبة: `${final_cost:.2f}`",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 شحن الرصيد", callback_data='deposit_menu'), InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                )
                return

            async with httpx.AsyncClient(headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}, timeout=20.0) as client:
                payload = {
                    'key': HMCARD_API_KEY,
                    'action': 'add',
                    'service': service['service_id'],
                    'link': order['link'],
                    'quantity': qty
                }
                try:
                    res = await client.post(HMCARD_API_URL, data=payload)
                    if res.status_code == 200:
                        try:
                            resp_data = res.json()
                        except Exception:
                            text_resp = res.text
                            await query.edit_message_text(
                                f"❌ **عذراً، موقع الرشق يرسل صفحة حماية أو خطأ.**\n🔍 الرد: `{text_resp[:150]}`",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]])
                            )
                            return

                        if isinstance(resp_data, dict) and "order" in resp_data:
                            order_id = resp_data["order"]
                            db_update_balance(user_id, final_cost, mode="deduct")
                            
                            await query.edit_message_text(
                                f"✅ **تم إرسال طلب الرشق وتأكيده بنجاح!** 🚀✨\n\n"
                                f"🆔 **رقم الطلب في المنصة:** `{order_id}`\n"
                                f"🔗 **الهدف:** `{mask_link(order['link'])}`\n"
                                f"📦 **الكمية:** `{qty:,}`\n"
                                f"⭐ **تم خصم:** `${final_cost:.2f}` من رصيدك.",
                                parse_mode='Markdown',
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                            )
                            
                            try:
                                service_name = service.get('name', 'خدمة رقمية')
                                await context.bot.send_message(
                                    chat_id=LOG_CHANNEL_ID,
                                    text=(
                                        "🔥 **تم تنفيذ طلب رشق جديد بنجاح!** ✅\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"👤 **آيدي العميل:** `{user_id}`\n"
                                        f"🛍️ **الخدمة:** `{service_name}`\n"
                                        f"🔗 **الرابط/الآيدي:** `{mask_link(order['link'])}`\n"
                                        f"📊 **الكمية:** `{qty:,}`\n"
                                        f"🆔 **رقم الطلب:** `{order_id}`\n"
                                        f"💰 **المبلغ المخصوم:** `${final_cost:.2f}`\n"
                                        f"⭐ **الحالة:** تم الإرسال للمنصة بنجاح 🚀"
                                    ),
                                    parse_mode='Markdown'
                                )
                            except Exception as log_err:
                                print(f"❌ خطأ إرسال لوج الرشق للقناة: {log_err}")
                            return
                        else:
                            api_error = resp_data.get("error", resp_data.get("message", "خطأ غير معروف"))
                            await query.edit_message_text(
                                f"❌ **عذراً، رفض موقع الرشق تنفيذ الطلب!**\n\n💬 **السبب:** `{api_error}`",
                                parse_mode='Markdown',
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                            )
                            return
                except Exception as api_err:
                    await query.edit_message_text(f"❌ **استثناء أثناء الاتصال:** `{str(api_err)[:100]}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]]))

    elif data == "cancel_order":
        await query.edit_message_text("❌ تم إلغاء الطلب بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))

    elif data == 'bot_instructions':
        instructions_text = (
            "💎 **دليل استخدام بوت ﴿ ديجيتال هب | Digital Hub ﴾** 🚀\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "بوابتك الأولى والأسرع للخدمات الرقمية المتكاملة في مكان واحد وبأفضل الأسعار! 🌟\n\n"
            "📱 **1️⃣ قسم الأرقام الافتراضية:**\n"
            "• احصل فوراً على أرقام لتفعيل (واتساب، تليجرام، انستغرام، فيسبوك، وغيرها) من مختلف دول العالم.\n\n"
            "🔭 **2️⃣ قسم الرشق وشحن الألعاب:**\n"
            "• اطلب خدمات زيادة المتابعين والتفاعلات لجميع المنصات بكل سهولة.\n\n"
            "> 💡 *انقر على الزر أدناه للعودة للقائمة الرئيسية واستكشاف خدماتنا فوراً!* 👇"
        )
        await query.edit_message_text(
            instructions_text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')]])
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
            "إذا كان لديك كود هدية، **قم بإرساله مباشرة في هذه المحادثة**!"
        )
        await query.edit_message_text(free_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))

    elif data == 'transfer_balance':
        admin_state[user_id] = {'action': 'waiting_for_transfer_id'}
        u_data = db_get_user(user_id)
        await query.edit_message_text(f"🔄 **تحويل الرصيد:**\n⭐ رصيدك الحالي: `${u_data['balance']:.2f}`\n\nأرسل الآن **آيدي (ID)** المستخدم المراد التحويل إليه:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='main_menu')]]))

    elif data == 'deposit_menu':
        deposit_text = (
            "💎 **﴿ ديجيتال هب | Digital Hub ﴾** 💎\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌟 **بوابة شحن الرصيد الفوري والآمن** 🌟\n\n"
            "أهلاً بك عزيزي العميل. لتعبئة رصيدك في البوت بالدولار ($)، يمكنك التحويل بالريال اليمني عبر محفظة جيب أو الكريمي:\n\n"
            "📌 **رقم الحساب/المحفظة المعتمد:** `772074924`\n\n"
            "💱 **سعر الصرف المعتمد (بالعملة القديمة):**\n"
            "• **كل 1 دولار ($) = 550 ريال يمني**\n"
            "  *(البوت يقوم آلياً بحساب وتحويل أي مبلغ يمني ترسله إلى ما يعادله بالدولار وإضافته لرصيدك)*\n\n"
            "📲 **خطوات الشحن:**\n"
            "1️⃣ قم بتحويل المبلغ بالريال اليمني إلى الرقم أعلاه.\n"
            "2️⃣ **قم بإرسال صورة إيصال التحويل (Screenshot) الأصلية** تماماً كما تم حفظها من تطبيق جيب أو الكريمي بدون أي تعديل.\n\n"
            "👇 اختر طريقة الإرسال أو الشحن المتاحة:"
        )
        deposit_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ الشحن الفوري عبر نجوم تليجرام (Stars)", callback_data='dep_telegram_stars')],
            [InlineKeyboardButton("📲 إرسال إيصال التحويل (جيب / الكريمي)", callback_data='dep_jaib')],
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
        await query.edit_message_text("⭐ **اختر الباقة المناسبة لك لشحن رصيدك فوراً:**", parse_mode='Markdown', reply_markup=stars_keyboard)

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
        admin_state[user_id] = {'action': 'waiting_for_deposit'}
        await query.edit_message_text(
            "📲 **تعليمات شحن الرصيد الآلي عبر الإيصال:**\n\n"
            "1️⃣ قم بتحويل المبلغ بالريال اليمني إلى رقم الحساب المعتمد:\n"
            "   📌 `772074924`\n"
            "   *(سعر الصرف: 1 دولار = 550 ريال يمني بالعملة القديمة)*\n\n"
            "2️⃣ **قم بإرسال صورة إيصال التحويل (Screenshot) الأصلية** تماماً كما تم حفظها من محفظة جيب أو الكريمي.\n"
            "⚠️ *تنبيه:* أي صورة يُشتبه في تعديلها أو قصها سيتم رفضها تلقائياً وتنبيهك.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• عودة •", callback_data='deposit_menu')]])
        )

    elif data.startswith('approve_deposit_'):
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        _, _, target_user_id, yer_amount = data.split('_', 3)
        target_user_id, yer_amount = int(target_user_id), float(yer_amount)
        
        # آلة حاسبة الصرف: تحويل الريال اليمني إلى دولار بناءً على سعر الصرف 550
        usd_amount = round(yer_amount / EXCHANGE_RATE, 2)
        
        db_update_balance(target_user_id, usd_amount, mode="add")
        try:
            await context.bot.send_message(
                chat_id=target_user_id, 
                text=f"🎉 **مبروك! تمت إضافة الرصيد بنجاح بعد تحويل الحوالة:**\n💵 المبلغ المحول: `{yer_amount:,.0f} ريال يمني`\n⭐ رصيدك المضاف: `${usd_amount:.2f}`", 
                parse_mode='Markdown'
            )
        except Exception:
            pass
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ تم الاعتماد بنجاح للمستخدم `{target_user_id}` بمبلغ `${usd_amount:.2f}` (يعادل {yer_amount:,.0f} ريال)", parse_mode='Markdown')

    elif data.startswith('approve_custom_yer_'):
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        _, _, _, target_user_id = data.split('_', 3)
        admin_state[user_id] = {'action': 'waiting_for_yer_amount_input', 'target_user_id': int(target_user_id)}
        await query.message.reply_text("🔢 أرسل الآن **المبلغ بالريال اليمني** الذي تحوله المستخدم (مثلاً: `5500` أو `11000`) لكي يحسبه البوت آلياً ويضيفه بالدولار:", parse_mode='Markdown')
        return

    elif data.startswith('reject_deposit_'):
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        _, _, target_user_id = data.split('_', 2)
        target_user_id = int(target_user_id)
        try:
            await context.bot.send_message(
                chat_id=target_user_id, 
                text="❌ **عذراً، الصورة غير واضحة أو تبدو معدلة!**\nيرجى إرسال الصورة **بدون أي تعديل** وإرسالها كما تم حفظها من محفظة جيب أو الكريمي لكي يتم اعتماد الرصيد وتحويله آلياً.", 
                parse_mode='Markdown'
            )
        except Exception:
            pass
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"❌ تم رفض الطلب وإرسال تنبيه الصورة للمستخدم `{target_user_id}`", parse_mode='Markdown')

    elif data == 'user_account':
        u_data = db_get_user(user_id)
        await query.edit_message_text(f"👤 **معلومات الحساب:**\n\n🆔 الآيدي: `{user_id}`\n⭐ رصيدك: `${u_data['balance']:.2f}`\n👥 الدعوات: `{u_data['referrals']}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]]))

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
            await query.edit_message_text(panel_text, parse_mode='Markdown', reply_markup=get_admin_keyboard())
        else:
            sub_panel_text = (
                "🛡️ **• لوحة تحكم المشرف المساعد •** 🛡️\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "مرحباً بك يا مشرف! يمكنك استخدام الأزرار أدناه للرد على المستخدمين وإدارة الأرصدة:"
            )
            await query.edit_message_text(sub_panel_text, parse_mode='Markdown', reply_markup=get_subadmin_keyboard())

    elif data == 'admin_top_refs':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        stats = db_get_advanced_stats()
        top_list = stats['top_refs']
        text = "🏆 **قائمة أطراف الإحالات (أعلى 5 أشخاص نشطين):**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        if top_list:
            for idx, (uid, refs) in enumerate(top_list, 1): text += f"{idx}. الآيدي: `{uid}` ⟵ **{refs} دعوة** 🌟\n"
        else: text += "⚠️ لا توجد إحالات مسجلة حتى الآن."
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للوحة", callback_data='admin_panel')]]))

    elif data == 'admin_create_promo':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_promo_details'}
        await query.edit_message_text("🎟️ **إنشاء كود هدية جديد:**\nأرسل الكود والمبلغ وعدد المرات بمسافات:\n*(مثال: `WELCOME 0.50 100`)*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_reply_user':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_reply_id'}
        await query.edit_message_text("💬 **الرد على مستخدم:**\nأرسل الآن **آيدي المستخدم** المراد الرد عليه:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_send_gift_user':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_gift_id'}
        await query.edit_message_text("🎁 **إرسال هدية مالية:**\nأرسل الآن **آيدي المستخدم** المراد إرسال الهدية له:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_add_balance':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_add_bal_id'}
        await query.edit_message_text("➕ **إضافة رصيد:**\nأرسل الآن **آيدي المستخدم** المراد إضافة الرصيد له:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_deduct_balance':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_deduct_bal_id'}
        await query.edit_message_text("➖ **خصم رصيد:**\nأرسل الآن **آيدي المستخدم** المراد الخصم من حسابه:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_manage_subadmins':
        if user_id != ADMIN_ID: return
        subs = get_all_sub_admins()
        subs_text = "👥 المشرفون المساعدون:\n" + ("\n".join([f"• `{sid}`" for sid in subs]) if subs else "لا يوجد مشرفين مساعدين.")
        await query.edit_message_text(subs_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ إضافة", callback_data='admin_add_sub'), InlineKeyboardButton("➖ حذف", callback_data='admin_del_sub')], [InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_add_sub':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_sub_id'}
        await query.edit_message_text("أرسل آيدي المشرف الجديد:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_del_sub':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_del_sub_id'}
        await query.edit_message_text("أرسل آيدي المشرف للحذف:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_send_bonus':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'waiting_for_bonus_amount'}
        await query.edit_message_text("🎁 أرسل المبلغ المراد توزيعه كهدية للجميع (مثال: `0.10`):", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_reset_balances':
        if user_id != ADMIN_ID: return
        try:
            from database import supabase
            res = supabase.table("users").select("user_id").execute()
            for u in (res.data if hasattr(res, 'data') else []):
                supabase.table("users").update({"balance": 0.0}).eq("user_id", u["user_id"]).execute()
        except Exception:
            pass
        await query.answer("✅ تمت التصفير بنجاح!", show_alert=True)
        await query.edit_message_text("🧹 تم تصفير جميع أرصدة المستخدمين بنجاح.", reply_markup=get_admin_keyboard())

    elif data == 'admin_ban_user':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_ban_id'}
        await query.edit_message_text("🚫 أرسل آيدي المستخدم للحظر أو فك الحظر:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

    elif data == 'admin_broadcast':
        if not is_admin_or_sub(user_id, ADMIN_ID): return
        admin_state[user_id] = {'action': 'waiting_for_broadcast'}
        await query.edit_message_text("📢 أرسل الآن رسالة الإذاعة الشاملة (نص، صورة، أو وسائط):", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='admin_panel')]]))

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
    
    if not await check_user_subscription(user_id, context):
        return

    if user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_deposit':
        admin_state.pop(user_id, None)
        
        receipt_caption = update.message.caption or "إيصال شحن بدون تعليق"
        processing_msg = await update.message.reply_text("🔄 **جاري فحص إيصال التحويل وحساب الصرف (550 ريال = 1$)...** انتظر لحظة ⏳", parse_mode='Markdown')
        
        admin_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ اعتماد 1,100 ر.ي ($2)", callback_data=f"approve_deposit_{user_id}_1100"), InlineKeyboardButton("➕ اعتماد 2,750 ر.ي ($5)", callback_data=f"approve_deposit_{user_id}_2750")],
            [InlineKeyboardButton("➕ اعتماد 5,500 ر.ي ($10)", callback_data=f"approve_deposit_{user_id}_5500"), InlineKeyboardButton("➕ اعتماد مبلغ مخصص (يدوي)", callback_data=f"approve_custom_yer_{user_id}")],
            [InlineKeyboardButton("❌ رفض (صورة معدلة)", callback_data=f"reject_deposit_{user_id}")]
        ])
        
        for adm_id in set([ADMIN_ID] + get_all_sub_admins()):
            try:
                await context.bot.send_photo(
                    chat_id=adm_id,
                    photo=update.message.photo[-1].file_id,
                    caption=f"📥 **إيصال شحن جديد (صورة)!**\n🆔 الآيدي: `{user_id}`\n💬 الوصف: {receipt_caption}\n\n💱 *اختر المبلغ بالريال اليمني ليقوم البوت بصرفه آلياً بالدولار ($):*",
                    parse_mode='Markdown',
                    reply_markup=admin_markup
                )
            except Exception:
                pass
        
        await processing_msg.edit_text(
            "✅ **تم استلام صورة الإيصال بنجاح!**\n"
            "جاري مراجعة الحوالة بواسطة الآلة الحاسبة الذكية للبوت واعتمادها بالدولار ($)، انتظر لحظات.", 
            parse_mode='Markdown', 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
        )
        return

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_user_subscription(user_id, context):
        await update.message.reply_text(
            f"💎 ديجيتال هب | Digital Hub:\n🚀 To use this bot, you must join our channel {FORCED_CHANNEL_URL}",
            parse_mode='Markdown', reply_markup=await get_forced_subscription_keyboard()
        )
        return

    u_data = db_get_user(user_id)
    await process_successful_join_reward(update.effective_user, context, u_data)

    text_content = update.message.text.strip() if update.message.text else ""

    if is_admin_or_sub(user_id, ADMIN_ID) and user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_yer_amount_input':
        try:
            yer_val = float(text_content)
            st_data = admin_state.pop(user_id)
            target_id = st_data['target_user_id']
            
            usd_val = round(yer_val / EXCHANGE_RATE, 2)
            db_update_balance(target_id, usd_val, mode="add")
            
            admin_markup = get_admin_keyboard() if user_id == ADMIN_ID else get_subadmin_keyboard()
            await update.message.reply_text(
                f"✅ **تمت عملية الصرف والحساب الآلي بنجاح!**\n"
                f"👤 المستخدم: `{target_id}`\n"
                f"💵 المبلغ اليمني: `{yer_val:,.0f} ريال`\n"
                f"⭐ الرصيد المضاف: `${usd_val:.2f}` (حسب سعر 550)",
                parse_mode='Markdown',
                reply_markup=admin_markup
            )
            try:
                await context.bot.send_message(
                    chat_id=target_id, 
                    text=f"🎉 **مبروك! تمت إضافة الرصيد بنجاح:**\n💵 المبلغ: `{yer_val:,.0f} ريال يمني`\n⭐ رصيدك المضاف: `${usd_val:.2f}`",
                    parse_mode='Markdown'
                )
            except Exception:
                pass
            return
        except ValueError:
            await update.message.reply_text("❌ مبلغ غير صالح! أرسل أرقاماً صحيحة فقط للمبلغ اليمني:")
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
        
        if count < service_info.get("min", 10) or count > service_info.get("max", 100000000):
            await update.message.reply_text(f"⚠️ العدد يجب أن يكون بين {service_info.get('min', 10):,} و {service_info.get('max', 100000000):,}. أرسل العدد الصحيح:")
            return

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
            f"💰 السعر الإجمالي الصافي: `{fixed_price:.2f}$`"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد الشحن", callback_data="confirm_final_order")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_order")]
        ])
        await update.message.reply_text(summary_text, reply_markup=markup, parse_mode="Markdown")
        return

    if user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_transfer_id':
        try:
            target_id = int(text_content)
            admin_state[user_id] = {'action': 'waiting_for_transfer_amount', 'target_id': target_id}
            await update.message.reply_text("💰 أرسل الآن المبلغ المراد تحويله بالدولار ($):", parse_mode='Markdown')
        except ValueError:
            await update.message.reply_text("❌ الآيدي غير صالح! يرجى إرسال أرقام صحيحة للآيدي:")
        return

    elif user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_transfer_amount':
        try:
            amount = float(text_content)
            st_data = admin_state.pop(user_id)
            target_id = st_data['target_id']
            if u_data['balance'] < amount or amount <= 0:
                await update.message.reply_text("❌ رصيدك غير كافٍ أو المبلغ غير صالح للتحويل!")
                return
            db_update_balance(user_id, amount, mode="deduct")
            db_update_balance(target_id, amount, mode="add")
            await update.message.reply_text(f"✅ تم تحويل مبلغ `${amount:.2f}` بنجاح!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]]))
            try:
                await context.bot.send_message(chat_id=target_id, text=f"🎁 وصلت حوالة بقيمة `${amount:.2f}`!", parse_mode='Markdown')
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("❌ مبلغ غير صالح! أرسل أرقام صحيحة:")
        return

    if text_content and not (is_admin_or_sub(user_id, ADMIN_ID) and user_id in admin_state):
        try:
            from database import supabase
            res = supabase.table("promo_codes").select("*").eq("code", text_content).execute()
            rows = res.data if hasattr(res, 'data') else []
            if rows:
                promo = rows[0]
                amount, max_uses, used_count = float(promo["amount"]), int(promo["max_uses"]), int(promo["used_count"])
                if used_count >= max_uses:
                    await update.message.reply_text("❌ **عذراً، هذا الكود استنفد الحد الأقصى.**")
                    return
                used_check = supabase.table("user_promo_uses").select("*").eq("user_id", user_id).eq("code", text_content).execute()
                if used_check.data:
                    await update.message.reply_text("⚠️ **لقد قمت باستخدام هذا الكود مسبقاً.**")
                    return
                db_update_balance(user_id, amount, mode="add")
                supabase.table("promo_codes").update({"used_count": used_count + 1}).eq("code", text_content).execute()
                supabase.table("user_promo_uses").insert({"user_id": user_id, "code": text_content}).execute()
                await update.message.reply_text(f"🎉 **تهانينا! تم تفعيل كود الهدية وإضافة `${amount:.2f}` إلى رصيدك.**", parse_mode='Markdown')
                return
        except Exception:
            pass

    if is_admin_or_sub(user_id, ADMIN_ID) and user_id in admin_state:
        action = admin_state[user_id].get('action')
        admin_markup = get_admin_keyboard() if user_id == ADMIN_ID else get_subadmin_keyboard()
        
        if action == 'waiting_for_promo_details':
            if user_id != ADMIN_ID: return
            try:
                parts = text_content.split()
                code_str = parts[0]
                amt = float(parts[1])
                uses = int(parts[2])
                from database import supabase
                supabase.table("promo_codes").upsert({"code": code_str, "amount": amt, "max_uses": uses, "used_count": 0}).execute()
                admin_state.pop(user_id, None)
                await update.message.reply_text("✅ تم إنشاء وتفعيل كود الهدية بنجاح!", reply_markup=admin_markup)
                return
            except Exception:
                await update.message.reply_text("❌ صيغة خاطئة! أرسل هكذا: `CODE 0.50 100`")
                return

        elif action == 'waiting_for_broadcast':
            if user_id != ADMIN_ID: return
            admin_state.pop(user_id, None)
            all_users = db_get_all_users()
            status_msg = await update.message.reply_text("🚀 جاري إرسال الإذاعة الشاملة لجميع المشتركين...")
            c = 0
            for uid in all_users:
                try:
                    await update.message.copy(chat_id=uid)
                    c += 1
                    await asyncio.sleep(0.03)
                except Exception:
                    pass
            await status_msg.edit_text(f"✅ تمت الإذاعة بنجاح إلى `{c}` مشترك.", reply_markup=admin_markup)
            return

        elif action == 'waiting_for_reply_id':
            try:
                target_id = int(text_content)
                admin_state[user_id] = {'action': 'waiting_for_reply_text', 'target_id': target_id}
                await update.message.reply_text("💬 أرسل الآن **نص الرد** المراد إرساله للمستخدم:", parse_mode='Markdown')
                return
            except ValueError:
                await update.message.reply_text("❌ الآيدي غير صالح! أرسل أرقاماً فقط:")
                return

        elif action == 'waiting_for_reply_text':
            st_data = admin_state.pop(user_id)
            target_id = st_data['target_id']
            try:
                await context.bot.send_message(chat_id=target_id, text=f"💬 **رد من الإدارة:**\n\n{text_content}", parse_mode='Markdown')
                await update.message.reply_text("✅ تم إرسال الرد للمستخدم بنجاح!", reply_markup=admin_markup)
                
                if user_id != ADMIN_ID:
                    try:
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"🔔 **تنبيه إداري:** قام المشرف (`{user_id}`) بالرد على المستخدم (`{target_id}`).\n💬 **النص:** {text_content}"
                        )
                    except Exception:
                        pass
                return
            except Exception as e:
                await update.message.reply_text(f"❌ تعذر إرسال الرد للمستخدم: {e}", reply_markup=admin_markup)
                return

        elif action == 'waiting_for_gift_id':
            try:
                target_id = int(text_content)
                admin_state[user_id] = {'action': 'waiting_for_gift_amount', 'target_id': target_id}
                await update.message.reply_text("🎁 أرسل الآن **المبلغ** المراد إهداؤه بالدولار ($):", parse_mode='Markdown')
                return
            except ValueError:
                await update.message.reply_text("❌ الآيدي غير صالح! أرسل أرقاماً فقط:")
                return

        elif action == 'waiting_for_gift_amount':
            try:
                gift_amt = float(text_content)
                st_data = admin_state.pop(user_id)
                target_id = st_data['target_id']
                db_update_balance(target_id, gift_amt, mode="add")
                await update.message.reply_text(f"✅ تم إرسال الهدية بقيمة `${gift_amt:.2f}` للمستخدم `{target_id}` بنجاح!", reply_markup=admin_markup)
                try:
                    await context.bot.send_message(chat_id=target_id, text=f"🎁 **مبروك! وصلت لك هدية مالية من الإدارة بقيمة:** `${gift_amt:.2f}`", parse_mode='Markdown')
                except Exception:
                    pass
                
                if user_id != ADMIN_ID:
                    try:
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"🔔 **تنبيه إداري:** قام المشرف (`{user_id}`) بإرسال هدية مالية بقيمة `${gift_amt:.2f}` للمستخدم (`{target_id}`)."
                        )
                    except Exception:
                        pass
                return
            except ValueError:
                await update.message.reply_text("❌ مبلغ غير صالح! أرسل رقماً صحيحاً:")
                return

        elif action == 'waiting_for_add_bal_id':
            try:
                target_id = int(text_content)
                admin_state[user_id] = {'action': 'waiting_for_add_bal_amount', 'target_id': target_id}
                await update.message.reply_text("➕ أرسل الآن **المبلغ** المراد إضافته للحساب بالدولار ($):", parse_mode='Markdown')
                return
            except ValueError:
                await update.message.reply_text("❌ الآيدي غير صالح! أرسل أرقاماً فقط:")
                return

        elif action == 'waiting_for_add_bal_amount':
            try:
                bal_amt = float(text_content)
                st_data = admin_state.pop(user_id)
                target_id = st_data['target_id']
                db_update_balance(target_id, bal_amt, mode="add")
                await update.message.reply_text(f"✅ تمت إضافة `${bal_amt:.2f}` لحساب المستخدم `{target_id}` بنجاح!", reply_markup=admin_markup)
                try:
                    await context.bot.send_message(chat_id=target_id, text=f"💳 **تمت إضافة رصيد لحسابك بواسطة الإدارة بقيمة:** `${bal_amt:.2f}`", parse_mode='Markdown')
                except Exception:
                    pass
                
                if user_id != ADMIN_ID:
                    try:
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"🔔 **تنبيه إداري:** قام المشرف (`{user_id}`) بإضافة رصيد بقيمة `${bal_amt:.2f}` للمستخدم (`{target_id}`)."
                        )
                    except Exception:
                        pass
                return
            except ValueError:
                await update.message.reply_text("❌ مبلغ غير صالح! أرسل رقماً صحيحاً:")
                return

        elif action == 'waiting_for_deduct_bal_id':
            try:
                target_id = int(text_content)
                admin_state[user_id] = {'action': 'waiting_for_deduct_bal_amount', 'target_id': target_id}
                await update.message.reply_text("➖ أرسل الآن **المبلغ** المراد خصمه من الحساب بالدولار ($):", parse_mode='Markdown')
                return
            except ValueError:
                await update.message.reply_text("❌ الآيدي غير صالح! أرسل أرقاماً فقط:")
                return

        elif action == 'waiting_for_deduct_bal_amount':
            try:
                bal_amt = float(text_content)
                st_data = admin_state.pop(user_id)
                target_id = st_data['target_id']
                db_update_balance(target_id, bal_amt, mode="deduct")
                await update.message.reply_text(f"✅ تم خصم `${bal_amt:.2f}` من حساب المستخدم `{target_id}` بنجاح!", reply_markup=admin_markup)
                
                if user_id != ADMIN_ID:
                    try:
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"🔔 **تنبيه إداري:** قام المشرف (`{user_id}`) بخصم رصيد بقيمة `${bal_amt:.2f}` من المستخدم (`{target_id}`)."
                        )
                    except Exception:
                        pass
                return
            except ValueError:
                await update.message.reply_text("❌ مبلغ غير صالح! أرسل رقماً صحيحاً:")
                return

        elif action == 'waiting_for_sub_id':
            if user_id != ADMIN_ID: return
            try:
                clean_text = text_content.strip()
                if not clean_text.isdigit():
                    await update.message.reply_text("❌ الآيدي غير صالح! يرجى إرسال أرقام صحيحة فقط للآيدي:")
                    return
                
                new_sub_id = int(clean_text)
                from database import supabase
                supabase.table("sub_admins").upsert({"admin_id": new_sub_id}).execute()
                admin_state.pop(user_id, None)
                await update.message.reply_text(f"✅ تمت إضافة المشرف المساعد (الآيدي: `{new_sub_id}`) بنجاح!", parse_mode='Markdown', reply_markup=admin_markup)
                return
            except Exception as e:
                await update.message.reply_text(f"❌ حدث خطأ أثناء إضافة المشرف: {e}")
                return

        elif action == 'waiting_for_del_sub_id':
            if user_id != ADMIN_ID: return
            try:
                clean_text = text_content.strip()
                if not clean_text.isdigit():
                    await update.message.reply_text("❌ الآيدي غير صالح! أرسل أرقاماً صحيحة فقط:")
                    return
                del_sub_id = int(clean_text)
                from database import supabase
                supabase.table("sub_admins").delete().eq("admin_id", del_sub_id).execute()
                admin_state.pop(user_id, None)
                await update.message.reply_text("✅ تم حذف المشرف المساعد بنجاح!", reply_markup=admin_markup)
                return
            except Exception:
                await update.message.reply_text("❌ حدث خطأ!")
                return

        elif action == 'waiting_for_bonus_amount':
            if user_id != ADMIN_ID: return
            try:
                bonus_amt = float(text_content)
                admin_state.pop(user_id, None)
                all_users = db_get_all_users()
                for uid in all_users:
                    db_update_balance(uid, bonus_amt, mode="add")
                await update.message.reply_text(f"✅ تم توزيع الهدية المالية بقيمة `${bonus_amt:.2f}` على جميع المشتركين بنجاح!", reply_markup=admin_markup)
                return
            except Exception:
                await update.message.reply_text("❌ مبلغ غير صالح!")
                return

        elif action == 'waiting_for_ban_id':
            if user_id != ADMIN_ID: return
            try:
                clean_text = text_content.strip()
                if not clean_text.isdigit():
                    await update.message.reply_text("❌ الآيدي غير صالح! أرسل أرقاماً صحيحة فقط:")
                    return
                target_id = int(clean_text)
                u_info = db_get_user(target_id)
                new_ban = 1 if u_info.get('is_banned', 0) == 0 else 0
                from database import supabase
                supabase.table("users").update({"is_banned": new_ban}).eq("user_id", target_id).execute()
                admin_state.pop(user_id, None)
                status_str = "حظر" if new_ban == 1 else "فك حظر"
                await update.message.reply_text(f"✅ تم تنفيذ عملية ({status_str}) للمستخدم `{target_id}` بنجاح.", reply_markup=admin_markup)
                return
            except Exception:
                await update.message.reply_text("❌ الآيدي غير صالح!")
                return

    if user_id in admin_state and admin_state[user_id].get('action') == 'waiting_for_deposit':
        admin_state.pop(user_id, None)
        admin_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ اعتماد 1,100 ر.ي ($2)", callback_data=f"approve_deposit_{user_id}_1100"), InlineKeyboardButton("➕ اعتماد 2,750 ر.ي ($5)", callback_data=f"approve_deposit_{user_id}_2750")],
            [InlineKeyboardButton("➕ اعتماد مبلغ مخصص", callback_data=f"approve_custom_yer_{user_id}")],
            [InlineKeyboardButton("❌ رفض (صورة معدلة)", callback_data=f"reject_deposit_{user_id}")]
        ])
        for adm_id in set([ADMIN_ID] + get_all_sub_admins()):
            try:
                await context.bot.send_message(chat_id=adm_id, text=f"📥 **طلب شحن جديد!**\n🆔 الآيدي: `{user_id}`\nالتفاصيل: `{text_content}`", parse_mode='Markdown', reply_markup=admin_markup)
            except Exception:
                pass
        await update.message.reply_text("✅ تم إرسال إيصالك للإدارة بنجاح، انتظر المراجعة وحساب الصرف الآلي.")
        return
