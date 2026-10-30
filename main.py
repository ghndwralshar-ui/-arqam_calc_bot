import logging
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

# استيراد الإعدادات، وقاعدة البيانات، ومعالجات الأزرار والأوامر من الملفات الأخرى
from config import BOT_TOKEN
from database import init_db
from handlers import (
    start, 
    button_handler, 
    handle_text_messages, 
    handle_photo_receipt,  # الدالة الخاصة بمعالجة وفحص صور الإيصالات
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
    print("🟢 جاري تشغيل البوت المقسم بنجاح...")
    
    # تهيئة قاعدة البيانات
    init_db()
    
    # بناء تطبيق التليجرام
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    # إضافة المعالجات (Handlers)
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # معالج صور الإيصالات (يستقبل الصور ويوجهها لدالة معالجة الإيصالات)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_receipt))
    
    # معالج الرسائل النصية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("🚀 البوت يعمل الآن بكامل قوائمه بنجاح واستقرار تام!")
    app.run_polling(drop_pending_updates=True)
