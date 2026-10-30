import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

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

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

if __name__ == '__main__':
    print("🟢 جاري تشغيل البوت...")
    init_db()
    
    # بناء التطبيق بالبساطة المطلقة لضمان عدم حدوث أي Timeout
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    print("🚀 البوت يعمل الآن بنجاح تام!")
    app.run_polling(drop_pending_updates=True)
