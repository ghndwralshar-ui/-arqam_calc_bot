import logging
import asyncio
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)
from telegram.request import HTTPXRequest

# استيراد الإعدادات، وقاعدة البيانات، ومعالجات الأزرار والأوامر من الملفات الأخرى
from config import BOT_TOKEN
from database import init_db
from handlers import (
    start, 
    button_handler, 
    handle_text_messages, 
    handle_photo_receipt,  
    pre_checkout_handler, 
    successful_payment_handler
)

# إعدادات التسجيل (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def post_init(application):
    try:
        await application.bot.set_my_commands([BotCommand("start", "بدء استخدام البوت 🚀")])
    except Exception as e:
        print(f"Post init error: {e}")

if __name__ == '__main__':
    print("🟢 جاري تشغيل البوت مع تجاوز قيود الشبكة والمهلات...")
    
    # تهيئة قاعدة البيانات
    init_db()
    
    # إنشاء طلب HTTP مع رفع مهلات الاتصال وقراءة البيانات لمنع أي ReadTimeout نهائياً
    custom_request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=60.0
    )
    
    # بناء تطبيق التليجرام مع الطلب المخصص
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .request(custom_request)
        .get_updates_request(custom_request)
        .post_init(post_init)
        .build()
    )
    
    # إضافة المعالجات (Handlers)
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("🚀 البوت يعمل الآن بقوة وثبات تام بانتظار التحديثات...")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query", "pre_checkout_query"])
