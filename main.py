import logging
import sqlite3
import asyncio
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

SUPPORT_USERNAME = "benti"  # معرف الدعم الفني / مالك البوت

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

# القائمة المطلوبة بالأسماء والأعلام والأسعار الثابتة
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
                free_philippines_claimed INTEGER DEFAULT 0
            )
        ''')
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN referrals INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN free_philippines_claimed INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        conn.commit()

def db_get_user(user_id):
    with sqlite3.connect('bot_database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance, referrals, free_philippines_claimed FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute('INSERT INTO users (user_id, balance, referrals, free_philippines_claimed) VALUES (?, 0.0, 0, 0)', (user_id,))
            conn.commit()
            return {"balance": 0.0, "referrals": 0, "free_philippines_claimed": 0, "is_new": True}
        return {"balance": row[0], "referrals": row[1], "free_philippines_claimed": row[2], "is_new": False}

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
    with sqlite3.connect('bot_database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (referrer_id,))
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
    buttons = [
        [InlineKeyboardButton("💬 شراء رقم واتساب", callback_data='get_whatsapp_countries'), InlineKeyboardButton("💰 رصيدي", callback_data='user_balance')],
        [InlineKeyboardButton("💳 شحن الرصيد", callback_data='deposit_menu'), InlineKeyboardButton("🎁 تجميع النقاط", callback_data='points_menu')],
        [InlineKeyboardButton("📞 التواصل مع الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME}")]
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

# نظام المراقبة التلقائية للكود في الخلفية
async def watch_order_sms(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, order_id: str, phone: str, is_free: bool, price_yer: float):
    url = f"https://5sim.net/v1/user/check/{order_id}"
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        # نفحص لمدة 15 دقيقة (300 محاولة × 3 ثوانٍ)
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
                                    f"✅ **وصل كود الواتساب تلقائياً!**\n\n"
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
                    
                    # إذا تم إلغاء الطلب من الموقع مباشرة نتوقف
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
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text="🎉 **مبروك!** قام شخص بالدخول عبر رابط الدعوة الخاص بك وتم احتساب نقطة/إحالة جديدة لك.",
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
        f"أهلاً بك {user.first_name} في بوت أرقام الواتساب! 💬\n\nاختر ما يناسبك من القائمة أدناه:",
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
        text = (
            "🟢 **الشحن عبر محفظة جيب:**\n\n"
            "رقم المحفظة: `772074924`\n\n"
            "📌 *بعد إتمام التحويل، أرسل رقم العملية (إيصال التحويل) هنا في البوت لكي يتم إضافته لرصيدك بعد المراجعة.*"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='deposit_menu')]]))

    elif data == 'deposit_kuraimi':
        text = (
            "🔵 **الشحن عبر محفظة الكريمي:**\n\n"
            "رقم الحساب: `3105004949`\n\n"
            "📌 *بعد إتمام التحويل، أرسل رقم العملية (إيصال التحويل) هنا في البوت لكي يتم إضافته لرصيدك بعد المراجعة.*"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='deposit_menu')]]))

    elif data == 'deposit_admin':
        text = (
            f"👤 **الشحن المباشر عبر مالك البوت:**\n\n"
            f"تواصل مع المالك مباشرة: @{SUPPORT_USERNAME}\n\n"
            "📌 *أرسل له تفاصيل التحويل ليقوم بشحن رصيدك فوراً.*"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='deposit_menu')]]))

    elif data == 'points_menu':
        u_data = db_get_user(user_id)
        referrals = u_data['referrals']
        free_claimed = u_data['free_philippines_claimed']
        
        total_earned_rewards = referrals // 5
        available_rewards = total_earned_rewards - free_claimed
        
        status_text = f"✅ لديك `{available_rewards}` رقم فلبيني مجاني جاهز للاستلام!" if available_rewards > 0 else f"⏳ باقي لك `{5 - (referrals % 5)}` دعوات للحصول على الرقم المجاني القادم."
        
        text = (
            "🎁 **قسم دعوة الأصدقاء وتجميع النقاط**\n\n"
            "📌 *كل 5 دعوات تؤهلك للحصول على رقم فلبيني مجاني!*\n\n"
            f"👥 **إجمالي دعواتك:** `{referrals}` دعوة\n"
            f"🎁 **الأرقام المستحقة:** `{total_earned_rewards}` (تم استلام: `{free_claimed}`)\n"
            f"📌 **الحالة:** {status_text}\n\n"
            "اضغط على زر دعوة الأصدقاء أدناه لمشاركة الرابط الخاص بك."
        )
        
        buttons = [
            [InlineKeyboardButton("👥 دعوة الأصدقاء", callback_data='invite_friends')],
            [InlineKeyboardButton("🇵🇭 طلب رقم فلبيني مجاني", callback_data='claim_free_philippines')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
        ]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif data == 'invite_friends':
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        text = (
            "ادعي أصدقاءك واكسب أرقام وهمية مجانية! (كل 5 دعوات = رقم)\n\n"
            f"رابط الدعوة الخاص بك:\n`{referral_link}`\n\n"
            "انقر على الرابط لنسخه ومشاركته مع أصدقائك!"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='points_menu')]]))

    elif data == 'claim_free_philippines':
        u_data = db_get_user(user_id)
        referrals = u_data['referrals']
        free_claimed = u_data['free_philippines_claimed']
        
        total_earned_rewards = referrals // 5
        available_rewards = total_earned_rewards - free_claimed

        if available_rewards <= 0:
            await query.answer(f"❌ ليس لديك أرقام مجانية مستحقة! لديك {referrals} دعوة (تحتاج إلى {5 - (referrals % 5)} دعوات إضافية).", show_alert=True)
            return

        urls_to_try = [
            "https://5sim.net/v1/user/buy/activation/philippines/any/whatsapp",
            "https://5sim.net/v1/user/buy/activation/philippines/other/whatsapp"
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
                    cursor.execute('UPDATE users SET free_philippines_claimed = free_philippines_claimed + 1 WHERE user_id = ?', (user_id,))
                    conn.commit()

                sent_msg = await query.edit_message_text(
                    f"✅ **تم استخراج الرقم الفلبيني المجاني بنجاح!**\n\n"
                    f"🇵🇭 **الدولة:** `فلبين`\n"
                    f"📱 **الرقم:** `{phone}`\n"
                    f"🆔 **رقم الطلب:** `{order_id}`\n\n"
                    "⏳ **جاري انتظار وصول الكود تلقائياً...**",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ إلغاء واسترجاع الدعوات", callback_data=f"cnl_free_{order_id}")],
                        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
                    ])
                )
                
                # تفعيل فحص الكود تلقائياً في الخلفية
                asyncio.create_task(watch_order_sms(context, query.message.chat_id, sent_msg.message_id, str(order_id), phone, True, 0))
            else:
                await query.edit_message_text("❌ عذراً، الأرقام الفلبينية غير متوفرة حالياً في المنصة، حاول لاحقاً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='points_menu')]]))

    elif data == 'admin_panel':
        if user_id != ADMIN_ID: return
        stats = db_get_admin_stats()
        text = (
            "⚙️ **لوحة تحكم الأدمن**\n\n"
            "📊 **إحصائيات البوت العامة:**\n"
            f"👥 **إجمالي المستخدمين:** `{stats['total_users']}` مستخدم\n"
            f"💵 **مجموع الأرصدة بالبوت:** `{stats['total_balances']:.0f}` ريال يمني\n"
            f"🔗 **إجمالي الدعوات:** `{stats['total_referrals']}` دعوة\n\n"
            "اختر العملية المطلوبة أدناه:"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=get_admin_keyboard())

    elif data in ['admin_add_balance', 'admin_deduct_balance']:
        if user_id != ADMIN_ID: return
        action = 'add_balance' if data == 'admin_add_balance' else 'deduct_balance'
        admin_state[user_id] = {'action': action}
        action_title = "إضافة" if action == 'add_balance' else "خصم"
        await query.edit_message_text(
            f"✏️ **{action_title} رصيد لمستخدم**\n\n"
            "أرسل **آيدي المستخدم** والمبلغ مفصولين بمسافة.\n"
            "📝 *مثال:* `6472852297 5000`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data='admin_panel')]])
        )

    elif data == 'admin_broadcast':
        if user_id != ADMIN_ID: return
        admin_state[user_id] = {'action': 'broadcast'}
        await query.edit_message_text(
            "📢 **إذاعة رسالة لجميع المستخدمين**\n\n"
            "أرسل الآن الرسالة التي تريد إذاعتها (نص، صورة مع نص، إلخ):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data='admin_panel')]])
        )

    elif data.startswith('approve_'):
        if user_id != ADMIN_ID: return
        parts = data.split('_')
        target_user_id = int(parts[1])
        amount = float(parts[2])
        
        db_update_balance(target_user_id, amount, mode="add")
        await query.answer("✅ تمت إضافة الرصيد للمستخدم بنجاح!", show_alert=True)
        await query.edit_message_text(
            f"✅ **تمت الموافقة على عملية الشحن وإضافة `{amount}` ريال للمستخدم `{target_user_id}` بنجاح.**",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الأدمن", callback_data='admin_panel')]])
        )
        try:
            await context.bot.send_message(chat_id=target_user_id, text=f"🎉 **تم شحن رصيدك بنجاح!** تمت إضافة `{amount}` ريال يمني إلى حسابك.", parse_mode='Markdown')
        except Exception:
            pass

    elif data == 'get_whatsapp_countries':
        context.user_data['fixed_countries'] = {c['code']: c for c in FIXED_COUNTRIES_PRICES}

        buttons = []
        row = []
        for item in FIXED_COUNTRIES_PRICES:
            c_code = item['code']
            btn_text = f"{item['name_ar']} - {item['price']:.0f} ريال"
            callback = f"b_{c_code}"
            row.append(InlineKeyboardButton(btn_text, callback_data=callback))
            
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')])

        text = (
            "🌍 *قائمة أسعار الأرقام الدولية الجاهزة للتفعيل* 🌍\n\n"
            "🇲🇦 المغرب - 1000 ريال\n"
            "🇪🇬 مصر - 1000 ريال\n"
            "🇵🇭 الفلبين - 1000 ريال\n"
            "🇦🇷 الأرجنتين - 1000 ريال\n"
            "🇨🇴 كولومبيا - 1000 ريال\n"
            "🇿🇦 جنوب افريقيا - 1000 ريال\n"
            "🇮🇩 اندونيسيا - 1000 ريال\n"
            "🇹🇭 تايلاندا - 1000 ريال\n"
            "🇨🇬 الكونغو - 1000 ريال\n"
            "🇵🇹 البرتغال - 1000 ريال\n\n"
            "🇫🇷 فرنسا - 1500 ريال\n"
            "🇧🇷 البرازيل - 1500 ريال\n"
            "🇩🇪 ألمانيا - 1500 ريال\n"
            "🇮🇹 إيطاليا - 1500 ريال\n"
            "🇬🇧 انجلترا - 1500 ريال\n"
            "🇨🇦 كندا - 1500 ريال\n"
            "🇰🇼 الكويت - 1500 ريال\n"
            "🇯🇴 الأردن - 1500 ريال\n\n"
            "⚡️ *جميع الأرقام جاهزة مع الكود - تفعيل فوري ومضمون*\n\n"
            "👇 *اختر الدولة أدناه للشراء مباشرة:*"
        )

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith('b_'):
        country_code = data.split('_')[1]
        country_info = context.user_data.get('fixed_countries', {}).get(country_code)
        if not country_info:
            fallback_map = {c['code']: c for c in FIXED_COUNTRIES_PRICES}
            country_info = fallback_map.get(country_code)
            if not country_info:
                await query.edit_message_text("❌ انتهت جلسة الشراء، يرجى إعادة فتح قائمة الدول.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='get_whatsapp_countries')]]))
                return

        price_yer = country_info['price']

        u_data = db_get_user(user_id)
        if u_data['balance'] < price_yer:
            await query.edit_message_text(
                f"❌ **رصيدك غير كافٍ للشراء!**\n\n"
                f"💰 **تكلفة الرقم:** `{price_yer}` ريال\n"
                f"💵 **رصيدك الحالي:** `{u_data['balance']:.0f}` ريال",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='get_whatsapp_countries')]]))
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
                    f"✅ *تم شراء رقم الواتساب بنجاح!*\n\n"
                    f"🌍 **الدولة:** `{country_info['name_ar']}`\n"
                    f"📱 **الرقم:** `{phone}`\n"
                    f"🆔 **رقم الطلب:** `{order_id}`\n\n"
                    "⏳ **جاري انتظار وصول الكود تلقائياً...**",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ إلغاء واسترجاع المبلغ", callback_data=f"cnl_paid_{order_id}_{price_yer}")],
                        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
                    ])
                )
                
                # تفعيل فحص الكود تلقائياً في الخلفية للأرقام المدفوعة
                asyncio.create_task(watch_order_sms(context, query.message.chat_id, sent_msg.message_id, str(order_id), phone, False, price_yer))
            else:
                err_msg = res.text if res and res.text else "نفدت الأرقام لهذه الدولة حالياً."
                await query.edit_message_text(f"❌ تعذر الشراء: {err_msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='get_whatsapp_countries')]]))

    elif data.startswith('cnl_'):
        parts = data.split('_')
        cancel_type = parts[1]
        order_id = parts[2]
        
        url = f"https://5sim.net/v1/user/cancel/{order_id}"
        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    if cancel_type == 'free':
                        with sqlite3.connect('bot_database.db') as conn:
                            cursor = conn.cursor()
                            cursor.execute('UPDATE users SET free_philippines_claimed = MAX(0, free_philippines_claimed - 1) WHERE user_id = ?', (user_id,))
                            conn.commit()
                        await query.answer("✅ تم إلغاء الرقم واسترجاع استحقاق الدعوات بنجاح!", show_alert=True)
                        await query.edit_message_text(
                            "🚫 **تم إلغاء الطلب المجاني بنجاح واسترجاع الدعوات.**",
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                        )
                    else:
                        price_yer = float(parts[3])
                        db_update_balance(user_id, price_yer, mode="add")
                        await query.answer("✅ تم إلغاء الرقم وإعادة المبلغ لرصيدك!", show_alert=True)
                        await query.edit_message_text(
                            "🚫 **تم إلغاء الطلب بنجاح واسترجاع المبلغ.**",
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]])
                        )
                else:
                    await query.answer("⚠️ تعذر الإلغاء (قد تكون استلمت الكود أو انتهت المهلة).", show_alert=True)
            except Exception:
                await query.answer("⚠️ خطأ أثناء إرسال طلب الإلغاء.", show_alert=True)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id == ADMIN_ID and user_id in admin_state:
        action = admin_state[user_id].get('action')
        
        if action in ['add_balance', 'deduct_balance']:
            text = update.message.text.strip()
            try:
                target_id, amount = text.split()
                target_id = int(target_id)
                amount = float(amount)

                mode = "add" if action == 'add_balance' else "deduct"
                db_update_balance(target_id, amount, mode=mode)
                
                txt_action = "إضافة" if mode == "add" else "خصم"
                await update.message.reply_text(
                    f"✅ **تمت عملية {txt_action} الرصيد بنجاح!**\n\n"
                    f"👤 **المستخدم:** `{target_id}`\n"
                    f"💵 **المبلغ:** `{amount}` ريال",
                    parse_mode='Markdown',
                    reply_markup=get_admin_keyboard()
                )
                admin_state.pop(user_id, None)
                return
            except ValueError:
                await update.message.reply_text("❌ **صيغة خاطئة!** أرسل الآيدي والمبلغ بمسافة بينهما.\nمثال: `6472852297 1000`", parse_mode='Markdown')
                return

        elif action == 'broadcast':
            admin_state.pop(user_id, None)
            all_users = db_get_all_users()
            success_count = 0
            fail_count = 0

            status_msg = await update.message.reply_text("⏳ جاري بدء إذاعة الرسالة لجميع المستخدمين...")

            for uid in all_users:
                try:
                    await update.message.copy(chat_id=uid)
                    success_count += 1
                except Exception:
                    fail_count += 1

            await status_msg.edit_text(
                "📢 **تم الانتهاء من الإذاعة بنجاح!**\n\n"
                f"✅ **تم الإرسال إلى:** `{success_count}` مستخدم\n"
                f"❌ **فشل (مستخدم حظر البوت):** `{fail_count}` مستخدم",
                parse_mode='Markdown',
                reply_markup=get_admin_keyboard()
            )
            return

    text = update.message.text.strip()
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "📥 **طلب شحن رصيد جديد!**\n\n"
                f"👤 **المستخدم:** {user.full_name}\n"
                f"🆔 **الآيدي:** `{user_id}`\n"
                f"🔗 **المعرف:** @{user.username if user.username else 'لا يوجد'}\n"
                f"🔢 **رقم العملية / التفاصيل:**\n`{text}`"
            ),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("➕ إضافة 1000", callback_data=f"approve_{user_id}_1000"),
                    InlineKeyboardButton("➕ إضافة 2000", callback_data=f"approve_{user_id}_2000"),
                    InlineKeyboardButton("➕ إضافة 5000", callback_data=f"approve_{user_id}_5000")
                ]
            ])
        )
        await update.message.reply_text(
            "✅ **تم إرسال رقم العملية إلى الإدارة بنجاح!**\n"
            "سيتم مراجعة الإيداع وإضافة الرصيد إلى حسابك في أقرب وقت.",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Error forwarding deposit to admin: {e}")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("🟢 تم تشغيل البوت بنجاح ويقوم بالاستماع الآن...")
    app.run_polling(drop_pending_updates=True)
