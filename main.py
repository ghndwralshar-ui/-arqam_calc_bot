import logging
import sqlite3
import asyncio
import httpx
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- الإعدادات والبيانات الحساسة ---
BOT_TOKEN = "8850483932:AAGlQmf6SfauVpyGY4i7d14IhjPi29tu_fg"
FIVESIM_API_KEY = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MjE3OTQwNDQsImlhdCI6MTc5MDI1ODA0NCwicmF5IjoiZjQ5MGQ2ZDY1ZDk3YWQyYjI5YTZmMmZmMTA3MTE0YjMiLCJzdWIiOjQ1MjI3NTR9.a9hYtNcsLbGzOl-1lYckGNcywKS6K2GbjVvylCVAk6wRN2msqpd4P_iwjiSGhVRhgot5N_SBg7R-_g4WcwMFUQwOowZelELtux7Lc8fw_kMYXcSOtDPKuMY2O_w2kEEGQwITIIR98uUaQkv2r-obwBMvVfnUisJqVp93Qv_gg1f_if-Ogp7H0y9h-CdBBQqMNua-vMwV8-uN9LAJsz6hUkXrmOAG0WjRcdI2e5WiANF9w3wrAbJveP_b2J-JxSJKVs-T_oobDcmsadhlLpQB4hesY2sGyDSzD-KBFp18-PZsHPWVQ8pkNYRe5O4YAqaLACwbP3GOBsd518R7G_JOTA"
ADMIN_ID = 6472852297

SUPPORT_USERNAME = "benti"

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

FIXED_COUNTRIES_PRICES = [
    {"code": "morocco", "name_ar": "المغرب 🇲🇦", "price": 1000.0},
    {"code": "egypt", "name_ar": "مصر 🇪🇬", "price": 1000.0},
    {"code": "philippines", "name_ar": "الفلبين 🇵🇭", "price": 1000.0},
    {"code": "argentina", "name_ar": "الأرجنتين 🇦🇷", "price": 1000.0},
    {"code": "colombia", "name_ar": "كولومبيا 🇨🇴", "price": 1000.0},
    {"code": "southafrica", "name_ar": "جنوب افريقيا 🇿🇦", "price": 1000.0},
    {"code": "indonesia", "name_ar": "إندونيسيا 🇮🇩", "price": 1000.0},
    {"code": "thailand", "name_ar": "تايلاندا 🇹🇭", "price": 1000.0},
    {"code": "dcongo", "name_ar": "الكونغو 🇨🇬", "price": 1000.0},
    {"code": "portugal", "name_ar": "البرتغال 🇵🇹", "price": 1000.0},
    {"code": "france", "name_ar": "فرنسا 🇫🇷", "price": 1500.0},
    {"code": "brazil", "name_ar": "البرازيل 🇧🇷", "price": 1500.0},
    {"code": "germany", "name_ar": "ألمانيا 🇩🇪", "price": 1500.0},
    {"code": "italy", "name_ar": "إيطاليا 🇮🇹", "price": 1500.0},
    {"code": "england", "name_ar": "انجلترا 🇬🇧", "price": 1500.0},
    {"code": "canada", "name_ar": "كندا 🇨🇦", "price": 1500.0},
    {"code": "kuwait", "name_ar": "الكويت 🇰🇼", "price": 1500.0},
    {"code": "jordan", "name_ar": "الأردن 🇯🇴", "price": 1500.0},
]

def init_db():
    with sqlite3.connect('bot_database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                referrals INTEGER DEFAULT 0,
                fb_referrals INTEGER DEFAULT 0,
                insta_referrals INTEGER DEFAULT 0,
                fb_claimed INTEGER DEFAULT 0,
                insta_claimed INTEGER DEFAULT 0,
                daily_contest_refs INTEGER DEFAULT 0,
                contest_claimed INTEGER DEFAULT 0,
                last_contest_date TEXT
            )
        ''')
        for col, col_type in [('referrals', 'INTEGER DEFAULT 0'), 
                              ('fb_referrals', 'INTEGER DEFAULT 0'),
                              ('insta_referrals', 'INTEGER DEFAULT 0'),
                              ('fb_claimed', 'INTEGER DEFAULT 0'),
                              ('insta_claimed', 'INTEGER DEFAULT 0'),
                              ('daily_contest_refs', 'INTEGER DEFAULT 0'),
                              ('contest_claimed', 'INTEGER DEFAULT 0'),
                              ('last_contest_date', 'TEXT')]:
            try:
                cursor.execute(f'ALTER TABLE users ADD COLUMN {col} {col_type}')
            except sqlite3.OperationalError:
                pass
        conn.commit()

def db_get_user(user_id):
    with sqlite3.connect('bot_database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance, referrals, fb_referrals, insta_referrals, fb_claimed, insta_claimed, daily_contest_refs, contest_claimed, last_contest_date FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        today = datetime.now().strftime('%Y-%m-%d')
        
        if not row:
            cursor.execute('INSERT INTO users (user_id, balance, referrals, fb_referrals, insta_referrals, fb_claimed, insta_claimed, daily_contest_refs, contest_claimed, last_contest_date) VALUES (?, 0.0, 0, 0, 0, 0, 0, 0, 0, ?)', (user_id, today))
            conn.commit()
            return {"balance": 0.0, "referrals": 0, "fb_referrals": 0, "insta_referrals": 0, "fb_claimed": 0, "insta_claimed": 0, "daily_contest_refs": 0, "contest_claimed": 0, "last_contest_date": today, "is_new": True}
        
        last_date = row[8]
        daily_refs = row[6]
        contest_claimed = row[7]
        
        if last_date != today:
            daily_refs = 0
            contest_claimed = 0
            cursor.execute('UPDATE users SET daily_contest_refs = 0, contest_claimed = 0, last_contest_date = ? WHERE user_id = ?', (today, user_id))
            conn.commit()

        return {
            "balance": row[0], 
            "referrals": row[1], 
            "fb_referrals": row[2],
            "insta_referrals": row[3],
            "fb_claimed": row[4],
            "insta_claimed": row[5],
            "daily_contest_refs": daily_refs,
            "contest_claimed": contest_claimed,
            "last_contest_date": today,
            "is_new": False
        }

def db_update_balance(user_id, amount, mode="add"):
    db_get_user(user_id)
    with sqlite3.connect('bot_database.db') as conn:
        cursor = conn.cursor()
        if mode == "add":
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        elif mode == "deduct":
            cursor.execute('UPDATE users SET balance = MAX(0.0, balance - ?) WHERE user_id = ?', (amount, user_id))
        conn.commit()

def db_add_referral(referrer_id):
    today = datetime.now().strftime('%Y-%m-%d')
    with sqlite3.connect('bot_database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET referrals = referrals + 1, fb_referrals = fb_referrals + 1, insta_referrals = insta_referrals + 1, daily_contest_refs = daily_contest_refs + 1, last_contest_date = ? WHERE user_id = ?', (today, referrer_id))
        conn.commit()

def db_get_all_users():
    with sqlite3.connect('bot_database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def db_get_admin_stats():
    with sqlite3.connect('bot_database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*), COALESCE(SUM(balance), 0), COALESCE(SUM(referrals), 0) FROM users')
        total_users, total_balances, total_referrals = cursor.fetchone()
        return {
            "total_users": total_users,
            "total_balances": total_balances,
            "total_referrals": total_referrals
        }

def get_main_keyboard(user_id):
    support_btn = InlineKeyboardButton("📞 التواصل مع الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME}") if SUPPORT_USERNAME else InlineKeyboardButton("📞 التواصل مع الدعم الفني", callback_data='support_info')
    
    buttons = [
        [InlineKeyboardButton("💬 شراء رقم واتساب", callback_data='get_whatsapp_countries'), InlineKeyboardButton("💰 رصيدي", callback_data='user_balance')],
        [InlineKeyboardButton("💳 شحن الرصيد", callback_data='deposit_menu'), InlineKeyboardButton("🏆 مسابقة البوت", callback_data='daily_contest')],
        [InlineKeyboardButton("📘 رقم مجاني فيسبوك", callback_data='free_facebook'), InlineKeyboardButton("📸 رقم مجاني انستغرام", callback_data='free_instagram')],
        [support_btn]
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("⚙️ لوحة تحكم الأدمن", callback_data='admin_panel')])
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard():
    buttons = [
        [InlineKeyboardButton("📊 تحديث الإحصائيات", callback_data='admin_panel')],
        [InlineKeyboardButton("➕ إضافة رصيد", callback_data='admin_add_balance'), InlineKeyboardButton("➖ خصم رصيد", callback_data='admin_deduct_balance')],
        [InlineKeyboardButton("📢 إذاعة رسالة للجميع", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

async def post_init(application):
    commands = [
        BotCommand("start", "بدء استخدام البوت 🚀")
    ]
    await application.bot.set_my_commands(commands)

async def watch_order_sms(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, order_id: str, phone: str):
    url = f"https://5sim.net/v1/user/check/{order_id}"
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        for _ in range(300):
            await asyncio.sleep(3)
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    status = data.get('status')
                    sms_list = data.get('sms', [])
                    
                    if sms_list:
                        sms_code = sms_list[0].get('code', 'لا يوجد كود')
                        full_text = sms_list[0].get('text', '')
                        try:
                            await context.bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=message_id,
                                text=(
                                    f"✅ **تم وصول الكود بنجاح!**\n\n"
                                    f"📱 **الرقم:** `{phone}`\n"
                                    f"🔑 **الكود:** `{sms_code}`\n\n"
                                    f"💬 **النص:** `{full_text}`"
                                ),
                                parse_mode='Markdown',
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                            )
                        except Exception:
                            pass
                        return
                    
                    if status in ['canceled', 'banned', 'finish']:
                        return
            except Exception:
                continue

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    user_status = db_get_user(user.id)
    
    if user_status['is_new'] and args and args[0].isdigit():
        referrer_id = int(args[0])
        if referrer_id != user.id:
            db_add_referral(referrer_id)
            ref_data = db_get_user(referrer_id)
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=(
                        f"🎉 **مبروك! انضم صديق جديد عبر رابط الدعوة الخاص بك!** 👥\n\n"
                        f"📊 إجمالي دعواتك للفيسبوك: `{ref_data['fb_referrals']}`\n"
                        f"📊 إجمالي دعواتك للانستغرام: `{ref_data['insta_referrals']}`\n\n"
                        "🎁 يمكنك الآن الانتقال لقسم (فيسبوك) أو (انستغرام) لطلب رقمك المجاني الفوري!"
                    ),
                    parse_mode='Markdown'
                )
            except Exception:
                pass

    if user_status['is_new'] and user.id != ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "🚨 **مشترك جديد انضم للبوت!**\n\n"
                    f"👤 **الاسم:** {user.full_name}\n"
                    f"🆔 **الآيدي:** `{user.id}`\n"
                    f"🔗 **المعرف:** @{user.username if user.username else 'لا يوجد'}"
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error sending notification to admin: {e}")

    await update.message.reply_text(
        f"أهلاً بك {user.first_name} في بوت أرقام الواتساب والخدمات! 💬\n\nاختر ما يناسبك من القائمة أدناه:",
        reply_markup=get_main_keyboard(user.id)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'main_menu':
        admin_state.pop(user_id, None)
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=get_main_keyboard(user_id))

    elif data == 'support_info':
        await query.edit_message_text(
            f"📞 **الدعم الفني:**\n\nللتواصل مع الإدارة مباشرة يرجى مراسلة المعرف التالي: @{SUPPORT_USERNAME}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]])
        )

    elif data == 'free_facebook':
        u_data = db_get_user(user_id)
        fb_refs = u_data['fb_referrals']
        fb_claimed = u_data['fb_claimed']
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        available_to_claim = fb_refs - fb_claimed
        
        if available_to_claim > 0:
            status_msg = "✅ **لقد قمت بدعوة صديق وأصبح بإمكانك طلب رقمك المجاني الآن!**"
            action_button = [InlineKeyboardButton("📩 طلب رقمك المجاني (فيسبوك)", callback_data='request_fb_number')]
        else:
            status_msg = "⏳ **قم بدعوة صديق واحد فقط (1 دعوة) للحصول على رقم فيسبوك مجاني!**"
            action_button = []

        text = (
            "📘 **قسم الحصول على رقم فيسبوك مجاني** 📘\n\n"
            "📌 **الطريقة:**\n"
            "قم بدعوة صديق واحد عبر رابط الدعوة الخاص بك، لتظهر لك خيارات طلب الرقم مجاناً!\n\n"
            f"👥 **دعواتك للفيسبوك:** `{fb_refs}` شخص\n"
            f"📌 **الحالة:** {status_msg}\n\n"
            f"🔗 **رابط دعوة الفيسبوك الخاص بك:**\n`{referral_link}`\n\n"
            "انسخ الرابط وشاركه مع صديقك الآن!"
        )
        
        buttons = []
        if action_button:
            buttons.append(action_button)
        buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')])
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif data == 'request_fb_number':
        u_data = db_get_user(user_id)
        if (u_data['fb_referrals'] - u_data['fb_claimed']) <= 0:
            await query.answer("❌ يجب عليك دعوة صديق أولاً لتتمكن من الطلب!", show_alert=True)
            return

        with sqlite3.connect('bot_database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET fb_claimed = fb_claimed + 1 WHERE user_id = ?', (user_id,))
            conn.commit()

        await query.edit_message_text(
            "⏳ **جاري الحصول على رقمك من السيرفر، انتظر قليلأ...**",
            parse_mode='Markdown'
        )
        await asyncio.sleep(2)

        await query.edit_message_text(
            "✅ **تم إرسال طلبك إلى الإدارة بنجاح!**\n\n"
            "سيتم مراجعة طلبك وإرسال الرقم المجاني لك قريباً فور توفره.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
        )

        try:
            user_info = update.effective_user
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"🔔 **طلب رقم فيسبوك مجاني جديد!**\n\n"
                    f"👤 المستخدم: {user_info.full_name}\n"
                    f"🆔 الآيدي: `{user_id}`\n"
                    f"🔗 المعرف: @{user_info.username if user_info.username else 'لا يوجد'}"
                ),
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 إرسال الرقم للمستخدم", callback_data=f"send_num_fb_{user_id}")]
                ])
            )
        except Exception as e:
            print(f"Error notifying admin for fb: {e}")

    elif data.startswith('send_num_fb_'):
        if user_id != ADMIN_ID: return
        target_id = int(data.split('_')[3])
        admin_state[ADMIN_ID] = {'action': 'provide_fb_num', 'target_id': target_id}
        await query.message.reply_text(
            f"✏️ **أرسل الآن الرقم المجاني الخاص بالفيسبوك للمستخدم (`{target_id}`):**\n"
            "اكتب الرقم مباشرة في رسالة وسيوجه إليه مع زر طلب الكود تلقائياً."
        )

    elif data == 'free_instagram':
        u_data = db_get_user(user_id)
        insta_refs = u_data['insta_referrals']
        insta_claimed = u_data['insta_claimed']
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        available_to_claim = insta_refs - insta_claimed
        
        if available_to_claim > 0:
            status_msg = "✅ **لقد قمت بدعوة صديق وأصبح بإمكانك طلب رقمك المجاني الآن!**"
            action_button = [InlineKeyboardButton("📩 طلب رقمك المجاني (انستغرام)", callback_data='request_insta_number')]
        else:
            status_msg = "⏳ **قم بدعوة صديق واحد فقط (1 دعوة) للحصول على رقم انستغرام مجاني!**"
            action_button = []

        text = (
            "📸 **قسم الحصول على رقم انستغرام مجاني** 📸\n\n"
            "📌 **الطريقة:**\n"
            "قم بدعوة صديق واحد عبر رابط الدعوة الخاص بك، لتظهر لك خيارات طلب الرقم مجاناً!\n\n"
            f"👥 **دعواتك للانستغرام:** `{insta_refs}` شخص\n"
            f"📌 **الحالة:** {status_msg}\n\n"
            f"🔗 **رابط دعوة الانستغرام الخاص بك:**\n`{referral_link}`\n\n"
            "انسخ الرابط وشاركه مع صديقك الآن!"
        )
        
        buttons = []
        if action_button:
            buttons.append(action_button)
        buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')])
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif data == 'request_insta_number':
        u_data = db_get_user(user_id)
        if (u_data['insta_referrals'] - u_data['insta_claimed']) <= 0:
            await query.answer("❌ يجب عليك دعوة صديق أولاً لتتمكن من الطلب!", show_alert=True)
            return

        with sqlite3.connect('bot_database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET insta_claimed = insta_claimed + 1 WHERE user_id = ?', (user_id,))
            conn.commit()

        await query.edit_message_text(
            "⏳ **جاري الحصول على رقمك من السيرفر، انتظر قليلاً...**",
            parse_mode='Markdown'
        )
        await asyncio.sleep(2)

        await query.edit_message_text(
            "✅ **تم إرسال طلبك إلى الإدارة بنجاح!**\n\n"
            "سيتم مراجعة طلبك وإرسال الرقم المجاني لك قريباً فور توفره.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
        )

        try:
            user_info = update.effective_user
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"🔔 **طلب رقم انستغرام مجاني جديد!**\n\n"
                    f"👤 المستخدم: {user_info.full_name}\n"
                    f"🆔 الآيدي: `{user_id}`\n"
                    f"🔗 المعرف: @{user_info.username if user_info.username else 'لا يوجد'}"
                ),
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 إرسال الرقم للمستخدم", callback_data=f"send_num_insta_{user_id}")]
                ])
            )
        except Exception as e:
            print(f"Error notifying admin for insta: {e}")

    elif data.startswith('send_num_insta_'):
        if user_id != ADMIN_ID: return
        target_id = int(data.split('_')[3])
        admin_state[ADMIN_ID] = {'action': 'provide_insta_num', 'target_id': target_id}
        await query.message.reply_text(
            f"✏️ **أرسل الآن الرقم المجاني الخاص بانستغرام للمستخدم (`{target_id}`):**\n"
            "اكتب الرقم مباشرة في رسالة وسيوجه إليه مع زر طلب الكود تلقائياً."
        )

    elif data.startswith('ask_code_'):
        platform = data.split('_')[2]  # fb أو insta
        await query.answer("📩 تم إرسال طلب الكود إلى الإدارة بنجاح!", show_alert=True)
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"📲 **طلب تفعيل / طلب كود جديد من المستخدم!**\n\n"
                    f"👤 الآيدي: `{user_id}`\n"
                    f"🏷 المنصة: `{platform.upper()}`\n\n"
                    "يرجى الرد عليه إما بإرسال الكود مع رسالة التحفيز، أو بطلب إعادة طلب الكود."
                ),
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✍️ إرسال الكود مع رسالة تحفيزية", callback_data=f"admin_reply_code_{user_id}_{platform}")],
                    [InlineKeyboardButton("🔄 اطلب إعادة طلب الكود", callback_data=f"admin_retry_code_{user_id}_{platform}")]
                ])
            )
        except Exception:
            pass

    elif data.startswith('admin_reply_code_'):
        if user_id != ADMIN_ID: return
        parts = data.split('_')
        target_id = int(parts[3])
        platform = parts[4]
        admin_state[ADMIN_ID] = {'action': 'send_actual_code', 'target_id': target_id, 'platform': platform}
        await query.message.reply_text(f"✏️ أرسل الآن الكود ورسالة التهنئة للمستخدم (`{target_id}`):")

    elif data.startswith('admin_retry_code_'):
        if user_id != ADMIN_ID: return
        parts = data.split('_')
        target_id = int(parts[3])
        platform = parts[4]
        try:
            platform_name = "فيسبوك" if platform == "fb" else "انستغرام"
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    f"⚠️ **تنبيه بخصوص رقم {platform_name} المجاني:**\n\n"
                    "عذراً، لم يظهر الكود المطلوب بعد أو انتهت المهلة.\n"
                    "يرجى الضغط على زر (طلب الكود) مرة أخرى أو التأكد من إرسال الرمز من التطبيق."
                ),
                parse_mode='Markdown'
            )
            await query.message.reply_text("✅ تم إرسال تنبيه إعادة طلب الكود للمستخدم بنجاح.")
        except Exception:
            await query.message.reply_text("❌ تعذر إرسال الرسالة للمستخدم.")

    elif data == 'daily_contest':
        u_data = db_get_user(user_id)
        daily_refs = u_data['daily_contest_refs']
        contest_claimed = u_data['contest_claimed']
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        progress_bar = "🟢" * min(daily_refs, 10) + "⚪" * max(0, 10 - daily_refs)
        
        if contest_claimed > 0:
            status_desc = "✅ **لقد فزت بجائزة مسابقة اليوم وتم استلام أرقامك بنجاح! ننتظرك غداً في مسابقة جديدة.**"
        elif daily_refs >= 10:
            status_desc = "🎉 **تهانينا! لقد أتممت 10 دعوات اليوم بنجاح وجائزتك جاهزة للاستلام!**"
        else:
            status_desc = f"⏳ **باقي لك `{10 - daily_refs}` دعوات لتحقيق جائزة اليوم!**"

        text = (
            "🏆 **مسابقة اليوم الكبرى (اربح أرقام تفعيل مجانية)** 🏆\n\n"
            "📌 **شروط المسابقة:**\n"
            "قم بدعوة **10 أشخاص** خلال اليوم عبر رابط الدعوة الخاص بك، واحصل على **3 أرقام مجانية**!\n\n"
            f"📊 **عدد من دعوتهم اليوم:** `{daily_refs} / 10` شخص\n"
            f"{progress_bar}\n\n"
            f"{status_desc}\n\n"
            f"🔗 **رابط الدعوة الخاص بك:**\n`{referral_link}`"
        )
        
        buttons = []
        if daily_refs >= 10 and contest_claimed == 0:
            buttons.append([InlineKeyboardButton("🎁 استلام الجائزة (3 أرقام مجانية)", callback_data='claim_contest_prize')])
        buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')])
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif data == 'claim_contest_prize':
        u_data = db_get_user(user_id)
        if u_data['daily_contest_refs'] < 10 or u_data['contest_claimed'] > 0:
            await query.answer("❌ عذراً، لم تكتمل شروط المسابقة أو تم استلام الجائزة مسبقاً.", show_alert=True)
            return

        urls_to_try = [
            "https://5sim.net/v1/user/buy/activation/philippines/any/whatsapp",
            "https://5sim.net/v1/user/buy/activation/indonesia/any/whatsapp"
        ]
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            res = None
            for url in urls_to_try:
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        break
                except Exception:
                    continue

            if res and res.status_code == 200:
                res_data = res.json()
                phone = res_data.get('phone')
                order_id = res_data.get('id')

                with sqlite3.connect('bot_database.db') as conn:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET contest_claimed = 1 WHERE user_id = ?', (user_id,))
                    conn.commit()

                sent_msg = await query.edit_message_text(
                    f"🏆 **مبارك لك الفوز بجائزة المسابقة اليومية!**\n\n"
                    f"📱 **الرقم الأول:** `{phone}`\n"
                    f"🆔 **رقم الطلب:** `{order_id}`\n\n"
                    "⏳ **جاري انتظار وصول الكود تلقائياً...**",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                )
                asyncio.create_task(watch_order_sms(context, query.message.chat_id, sent_msg.message_id, str(order_id), phone))
            else:
                await query.edit_message_text("❌ عذراً، نفدت الأرقام حالياً، حاول لاحقاً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='daily_contest')]]))

    elif data == 'user_balance':
        u_data = db_get_user(user_id)
        await query.edit_message_text(f"💰 *رصيدك الحالي:* `{u_data['balance']:.0f}` ريال يمني", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]]))

    elif data == 'deposit_menu':
        text = "💳 **اختر طريقة شحن الرصيد المناسبة لك:**"
        buttons = [
            [InlineKeyboardButton("🟢 الشحن عبر محفظة جيب", callback_data='deposit_jeep')],
            [InlineKeyboardButton("🔵 الشحن عبر محفظة الكريمي", callback_data='deposit_kuraimi')],
            [InlineKeyboardButton("👤 الشحن عبر مالك البوت", callback_data='deposit_admin')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
        ]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif data == 'deposit_jeep':
        await query.edit_message_text("🟢 **محفظة جيب:** `772074924`\nأرسل رقم العملية هنا.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='deposit_menu')]]))

    elif data == 'deposit_kuraimi':
        await query.edit_message_text("🔵 **محفظة الكريمي:** `3105004949`\nأرسل رقم العملية هنا.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='deposit_menu')]]))

    elif data == 'deposit_admin':
        await query.edit_message_text(f"👤 للتواصل المباشر مع المالك: @{SUPPORT_USERNAME}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='deposit_menu')]]))

    elif data == 'admin_panel':
        if user_id != ADMIN_ID: return
        stats = db_get_admin_stats()
        text = (
            "⚙️ **لوحة تحكم الأدمن**\n\n"
            f"👥 المستخدمين: `{stats['total_users']}`\n"
            f"💵 الأرصدة: `{stats['total_balances']:.0f}` ريال\n"
            f"🔗 الدعوات: `{stats['total_referrals']}`"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=get_admin_keyboard())

    elif data in ['admin_add_balance', 'admin_deduct_balance']:
        if user_id != ADMIN_ID: return
        action = 'add_balance' if data == 'admin_add_balance' else 'deduct_balance'
        admin_state[user_id] = {'action': action}
        await query.edit_message_text("✏️ أرسل الآيدي والمبلغ بمسافة:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data='admin_panel')]]))

    elif data == 'admin_broadcast':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'broadcast'}
        await query.edit_message_text("📢 أرسل نص الرسالة للإذاعة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data='admin_panel')]]))

    elif data.startswith('approve_'):
        if user_id != ADMIN_ID: return
        parts = data.split('_')
        target_user_id = int(parts[1])
        amount = float(parts[2])
        db_update_balance(target_user_id, amount, mode="add")
        await query.answer("✅ تمت إضافة الرصيد!", show_alert=True)
        await query.edit_message_text(f"✅ تمت إضافة `{amount}` ريال للمستخدم `{target_user_id}`.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الأدمن", callback_data='admin_panel')]]))
        try:
            await context.bot.send_message(chat_id=target_user_id, text=f"🎉 تم شحن رصيدك بمبلغ `{amount}` ريال يمني!", parse_mode='Markdown')
        except Exception:
            pass

    elif data == 'get_whatsapp_countries':
        context.user_data['fixed_countries'] = {c['code']: c for c in FIXED_COUNTRIES_PRICES}
        buttons = []
        row = []
        for item in FIXED_COUNTRIES_PRICES:
            c_code = item['code']
            row.append(InlineKeyboardButton(f"{item['name_ar']} - {item['price']:.0f} ريال", callback_data=f"b_{c_code}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')])
        await query.edit_message_text("🌍 **اختر الدولة لشراء رقم واتساب:**", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith('b_'):
        country_code = data.split('_')[1]
        country_info = context.user_data.get('fixed_countries', {}).get(country_code)
        if not country_info:
            fallback_map = {c['code']: c for c in FIXED_COUNTRIES_PRICES}
            country_info = fallback_map.get(country_code)
            if not country_info:
                await query.edit_message_text("❌ انتهت الجلسة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='get_whatsapp_countries')]]))
                return

        price_yer = country_info['price']
        u_data = db_get_user(user_id)
        if u_data['balance'] < price_yer:
            await query.edit_message_text(f"❌ رصيدك غير كافٍ! تكلفة الرقم `{price_yer}` ريال.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='get_whatsapp_countries')]]))
            return

        urls_to_try = [
            f"https://5sim.net/v1/user/buy/activation/{country_code}/any/whatsapp",
            f"https://5sim.net/v1/user/buy/activation/{country_code}/other/whatsapp"
        ]

        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            res = None
            for url in urls_to_try:
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        break
                except Exception:
                    continue

            if res and res.status_code == 200:
                res_data = res.json()
                phone = res_data.get('phone')
                order_id = res_data.get('id')

                db_update_balance(user_id, price_yer, mode="deduct")

                sent_msg = await query.edit_message_text(
                    f"✅ **تم الشراء بنجاح!**\n📱 الرقم: `{phone}`\n⏳ جاري انتظار الكود...",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء واسترداد المبلغ", callback_data=f"cnl_paid_{order_id}_{price_yer}")], [InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]])
                )
                asyncio.create_task(watch_order_sms(context, query.message.chat_id, sent_msg.message_id, str(order_id), phone))
            else:
                await query.edit_message_text("❌ نفدت الأرقام حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='get_whatsapp_countries')]]))

    elif data.startswith('cnl_'):
        parts = data.split('_')
        cancel_type = parts[1]
        order_id = parts[2]
        url = f"https://5sim.net/v1/user/cancel/{order_id}"
        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    if cancel_type == 'paid':
                        price_yer = float(parts[3])
                        db_update_balance(user_id, price_yer, mode="add")
                    await query.answer("✅ تم الإلغاء!", show_alert=True)
                    await query.edit_message_text("🚫 تم إلغاء الطلب بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]]))
                else:
                    await query.answer("⚠️ تعذر الإلغاء.", show_alert=True)
            except Exception:
                await query.answer("⚠️ خطأ في الاتصال.", show_alert=True)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id == ADMIN_ID and user_id in admin_state:
        st = admin_state[ADMIN_ID]
        action = st.get('action')

        if action in ['provide_fb_num', 'provide_insta_num']:
            target_id = st.get('target_id')
            phone_text = update.message.text.strip()
            platform = "fb" if action == 'provide_fb_num' else "insta"
            platform_name = "فيسبوك" if platform == "fb" else "انستغرام"
            
            admin_state.pop(ADMIN_ID, None)
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=(
                        f"🎉 **تم حصولك على رقم مجاني مقابل دعوتك صديق للبوت لتفعيل {platform_name}!**\n\n"
                        f"📱 **رقمك المجاني:** `{phone_text}`\n\n"
                        "يرجى استخدامه في التطبيق ثم الضغط على زر (طلب الكود) أدناه فوراً لتصلك الرسالة:"
                    ),
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📩 طلب الكود الآن", callback_data=f"ask_code_{platform}")]
                    ])
                )
                await update.message.reply_text("✅ تم إرسال الرقم وزر طلب الكود إلى المستخدم بنجاح.")
            except Exception as e:
                await update.message.reply_text(f"❌ حدث خطأ أثناء إرسال الرقم للمستخدم: {e}")
            return

        elif action == 'send_actual_code':
            target_id = st.get('target_id')
            platform = st.get('platform')
            msg_text = update.message.text.strip()
            platform_name = "فيسبوك" if platform == "fb" else "انستغرام"
            
            admin_state.pop(ADMIN_ID, None)
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=(
                        f"🌟 **مبروك! تم وصول الكود بنجاح لتفعيل {platform_name}**\n\n"
                        f"🔑 **التفاصيل / الكود:**\n`{msg_text}`\n\n"
                        "🚀 شكراً لاستخدامك البوت وننتظر منك دعوات إضافية للمزيد من الجوائز والأرقام المجانية!"
                    ),
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                )
                await update.message.reply_text("✅ تم إرسال الكود ورسالة التهنئة للعميل بنجاح.")
            except Exception as e:
                await update.message.reply_text(f"❌ تعذر إرسال الكود للعميل: {e}")
            return

        elif action in ['add_balance', 'deduct_balance']:
            text = update.message.text.strip()
            try:
                target_id, amount = text.split()
                target_id = int(target_id)
                amount = float(amount)
                mode = "add" if action == 'add_balance' else "deduct"
                db_update_balance(target_id, amount, mode=mode)
                await update.message.reply_text(f"✅ تمت العملية بنجاح للمستخدم `{target_id}`", parse_mode='Markdown', reply_markup=get_admin_keyboard())
                admin_state.pop(user_id, None)
                return
            except ValueError:
                await update.message.reply_text("❌ صيغة خاطئة!")
                return

        elif action == 'broadcast':
            admin_state.pop(user_id, None)
            all_users = db_get_all_users()
            success, fail = 0, 0
            status_msg = await update.message.reply_text("⏳ جاري الإذاعة...")
            for uid in all_users:
                try:
                    await update.message.copy(chat_id=uid)
                    success += 1
                except Exception:
                    fail += 1
            await status_msg.edit_text(f"📢 تمت الإذاعة:\n✅ نجاح: {success}\n❌ فشل: {fail}", reply_markup=get_admin_keyboard())
            return

    text = update.message.text.strip()
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📥 **طلب شحن رصيد جديد!**\n\n"
                f"👤 المستخدم: {user.full_name}\n"
                f"🆔 الآيدي: `{user_id}`\n"
                f"🔢 التفاصيل:\n`{text}`"
            ),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("➕ 1000", callback_data=f"approve_{user_id}_1000"),
                    InlineKeyboardButton("➕ 2000", callback_data=f"approve_{user_id}_2000"),
                    InlineKeyboardButton("➕ 5000", callback_data=f"approve_{user_id}_5000")
                ]
            ])
        )
        await update.message.reply_text("✅ تم إرسال طلبك للإدارة بنجاح.", parse_mode='Markdown')
    except Exception:
        pass

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("🟢 تم تشغيل البوت بنجاح مع نظام طلب الأرقام اليدوي للأدمن وتفعيل انستغرام وفيسبوك...")
    app.run_polling()
