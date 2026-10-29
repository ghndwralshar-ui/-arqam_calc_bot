from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_keyboard(user_id, is_admin_func):
    buttons = [
        [InlineKeyboardButton("🛒 شــراء رقــم افتـراضـي", callback_data='buy_virtual_number')],
        [InlineKeyboardButton("✈️ عروض Telegram", callback_data='deals_telegram'), InlineKeyboardButton("💬 عروض WhatsApp", callback_data='deals_whatsapp')],
        [InlineKeyboardButton("🎲 • شحـن الرصيـد •", callback_data='deposit_menu'), InlineKeyboardButton("🎳 • الأكثر توفراً •", callback_data='most_available')],
        [InlineKeyboardButton("✨ الخدمات الرقمية وشحن الألعاب ⚡", callback_data='main_rashq')],
        [InlineKeyboardButton("💎 • ربـح الأرصدة مجـانـاً (أكواد وهدايا) •", callback_data='free_points')],
        [InlineKeyboardButton("🔄 • تحويـل الرصيـد •", callback_data='transfer_balance'), InlineKeyboardButton("📞 • الدعم •", url="https://t.me/benti")],
        [InlineKeyboardButton("📖 • تعليمات وطريقة استخدام البوت •", callback_data='bot_instructions')],
        [InlineKeyboardButton("👤 حســابــي", callback_data='user_account')]
    ]
    if is_admin_func(user_id):
        buttons.append([InlineKeyboardButton("⚙️ لـوحـة تحكـم الأدمن الاحترافية", callback_data='admin_panel')])
    return InlineKeyboardMarkup(buttons)

def get_virtual_services_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ WHATSAPP - واتساب", callback_data='service_whatsapp'), InlineKeyboardButton("🎲 TELEGRAM - تليجرام", callback_data='service_telegram')],
        [InlineKeyboardButton("🎳 INSTAGRAM - انستغرام", callback_data='service_instagram'), InlineKeyboardButton("🎯 FACEBOOK - فيسبوك", callback_data='service_facebook')],
        [InlineKeyboardButton("🐤 TWITTER - تويتر", callback_data='service_twitter'), InlineKeyboardButton("🎬 TIKTOK - تيك توك", callback_data='service_tiktok')],
        [InlineKeyboardButton("♣️ SNAPCHAT - سناب شات", callback_data='service_snapchat'), InlineKeyboardButton("💎 IMO - ايمو", callback_data='service_imo')],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')]
    ])

def sections_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 خدمات واتساب", callback_data="sec_whatsapp"), InlineKeyboardButton("🚀 خدمات تليجرام", callback_data="sec_telegram")],
        [InlineKeyboardButton("📘 خدمات فيسبوك", callback_data="sec_facebook"), InlineKeyboardButton("📸 خدمات انستغرام", callback_data="sec_instagram")],
        [InlineKeyboardButton("🎵 خدمات تيك توك", callback_data="sec_tiktok"), InlineKeyboardButton("📺 خدمات يوتيوب", callback_data="sec_youtube")],
        [InlineKeyboardButton("🎮 شحن شدات ببجي موبايل", callback_data="sec_pubg"), InlineKeyboardButton("🔥 شحن فري فاير (Freefire)", callback_data="sec_freefire")],
        [InlineKeyboardButton("🐦 خدمات تويتر (X)", callback_data="sec_twitter"), InlineKeyboardButton("🎬 خدمات كواي", callback_data="sec_kwai")],
        [InlineKeyboardButton("👻 خدمات سناب شات", callback_data="sec_snapchat"), InlineKeyboardButton("💼 خدمات لينكدإن", callback_data="sec_linkedin")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
    ])

def whatsapp_services_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 بروفايل وأعضاء قناة واتساب", callback_data="wa_subscribers")],
        [InlineKeyboardButton("🟢 تفاعلات بروفايل ومنشورات واتساب", callback_data="wa_reactions")],
        [InlineKeyboardButton("🟢 تفاعلات بروفايل تلقائية للمنشورات الجديدة", callback_data="wa_auto_reactions")],
        [InlineKeyboardButton("🟢 تصويتات استطلاع رأي واتساب", callback_data="wa_polls")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="main_rashq")]
    ])

def channel_subscribers_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 بروفايل واتساب - أعضاء بدون ضمان", callback_data="sub_no_guarantee")],
        [InlineKeyboardButton("🟢 بروفايل واتساب - ضمان 30 يوم", callback_data="sub_30d")],
        [InlineKeyboardButton("🟢 بروفايل واتساب - ضمان 60 يوم", callback_data="sub_60d")],
        [InlineKeyboardButton("🟢 بروفايل واتساب - ضمان 90 يوم", callback_data="sub_90d")],
        [InlineKeyboardButton("🟢 بروفايل واتساب - عالمي", callback_data="sub_global")],
        [InlineKeyboardButton("🟢 بروفايل واتساب - عربي", callback_data="sub_arabic")],
        [InlineKeyboardButton("🔙 العودة لخدمات واتساب", callback_data="sec_whatsapp")]
    ])

def emoji_reactions_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 تفاعلات بروفايل عشوائية", callback_data="react_random")],
        [InlineKeyboardButton("🟢 تفاعلات بروفايل إعجاب (Like)", callback_data="react_like")],
        [InlineKeyboardButton("🟢 تفاعلات بروفايل حب (Heart)", callback_data="react_heart")],
        [InlineKeyboardButton("🟢 تفاعلات بروفايل ضحك (Haha)", callback_data="react_haha")],
        [InlineKeyboardButton("🟢 تفاعلات بروفايل تعجب (Wow)", callback_data="react_wow")],
        [InlineKeyboardButton("🟢 تفاعلات بروفايل حزن (Sad)", callback_data="react_sad")],
        [InlineKeyboardButton("🟢 تفاعلات بروفايل دعاء (Pray)", callback_data="react_pray")],
        [InlineKeyboardButton("🔙 العودة لخدمات واتساب", callback_data="sec_whatsapp")]
    ])

def auto_reactions_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 ردود فعل بروفايل تلقائية (10 منشورات)", callback_data="auto_10")],
        [InlineKeyboardButton("🟢 ردود فعل بروفايل تلقائية (25 منشوراً)", callback_data="auto_25")],
        [InlineKeyboardButton("🟢 ردود فعل بروفايل تلقائية (50 منشوراً)", callback_data="auto_50")],
        [InlineKeyboardButton("🟢 ردود فعل بروفايل تلقائية (100 منشور)", callback_data="auto_100")],
        [InlineKeyboardButton("🔙 العودة لخدمات واتساب", callback_data="sec_whatsapp")]
    ])

def polls_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 تصويت بروفايل واتساب - الخيار الأول", callback_data="poll_1")],
        [InlineKeyboardButton("🟢 تصويت بروفايل واتساب - الخيار الثاني", callback_data="poll_2")],
        [InlineKeyboardButton("🟢 تصويت بروفايل واتساب - الخيار الثالث", callback_data="poll_3")],
        [InlineKeyboardButton("🟢 تصويت بروفايل واتساب - الخيار الرابع", callback_data="poll_4")],
        [InlineKeyboardButton("🔙 العودة لخدمات واتساب", callback_data="sec_whatsapp")]
    ])

def telegram_services_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 أعضاء تليجرام عرب", callback_data="tg_arab_menu")],
        [InlineKeyboardButton("🌍 أعضاء تليجرام أجانب (Zero Drop)", callback_data="tg_foreign_menu")],
        [InlineKeyboardButton("🥷 أعضاء تليجرام حسابات محذوفة", callback_data="tg_deleted_652")],
        [InlineKeyboardButton("⭐ أعضاء تليجرام بريميوم (Premium)", callback_data="tg_prem_menu")],
        [InlineKeyboardButton("🔍 معرفة رقم هاتفك تليجرام", callback_data="tg_phone_960")],
        [InlineKeyboardButton("👁️ مشاهدات منشورات تليجرام", callback_data="tg_views_menu")],
        [InlineKeyboardButton("⚡ مشاهدات وتفاعلات تلقائية للمنشور الجديد", callback_data="tg_auto_menu")],
        [InlineKeyboardButton("🎯 تفاعلات إيموجي وقصص تليجرام", callback_data="tg_react_menu")],
        [InlineKeyboardButton("🗳️ تصويتات مسابقات تليجرام", callback_data="tg_polls_menu")],
        [InlineKeyboardButton("📊 بوست تصويت استطلاع رأي تليجرام", callback_data="tg_poll_boost_667")],
        [InlineKeyboardButton("🚀 تعزيزات قناة أو مجموعة تليجرام (Boosts)", callback_data="tg_boost_menu")],
        [InlineKeyboardButton("💬 تعليقات مخصصة تليجرام", callback_data="tg_comment_647")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="main_rashq")]
    ])

def tg_arab_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 أعضاء تليجرام عرب - ضمان 10 أيام", callback_data="tg_t_659")],
        [InlineKeyboardButton("🇸🇦 أعضاء تليجرام عرب - ضمان 180 يوم", callback_data="tg_t_660")],
        [InlineKeyboardButton("🇸🇦 أعضاء تليجرام عرب - ضمان 365 يوم", callback_data="tg_t_661")],
        [InlineKeyboardButton("🇸🇦 أعضاء تليجرام عرب - ضمان مدى الحياة", callback_data="tg_t_662")],
        [InlineKeyboardButton("🔙 العودة لقائمة تليجرام", callback_data="sec_telegram")]
    ])

def tg_foreign_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 أعضاء Zero Drop - ضمان 365 يوم", callback_data="tg_t_653")],
        [InlineKeyboardButton("🌍 أعضاء Zero Drop - ضمان مدى الحياة", callback_data="tg_t_654")],
        [InlineKeyboardButton("🔙 العودة لقائمة تليجرام", callback_data="sec_telegram")]
    ])

def tg_prem_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ أعضاء تليجرام بريميوم - 15 يوم", callback_data="tg_t_613")],
        [InlineKeyboardButton("⭐ أعضاء تليجرام بريميوم - 30 يوم", callback_data="tg_t_614")],
        [InlineKeyboardButton("🔙 العودة لقائمة تليجرام", callback_data="sec_telegram")]
    ])

def tg_views_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁️ مشاركات منشور تليجرام + المشاهدات", callback_data="tg_v_628")],
        [InlineKeyboardButton("👁️ مشاهدات سريعة - آخر منشور 1", callback_data="tg_v_668")],
        [InlineKeyboardButton("👁️ مشاهدات سريعة - آخر 10 منشورات", callback_data="tg_v_669")],
        [InlineKeyboardButton("👁️ مشاهدات سريعة - آخر 50 منشور", callback_data="tg_v_670")],
        [InlineKeyboardButton("👁️ مشاهدات سريعة - آخر 100 منشور", callback_data="tg_v_671")],
        [InlineKeyboardButton("🔙 العودة لقائمة تليجرام", callback_data="sec_telegram")]
    ])

def tg_auto_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ ردود فعل إيجابية تليجرام - 5 منشورات", callback_data="tg_a_702")],
        [InlineKeyboardButton("⚡ ردود فعل إيجابية تليجرام - 20 منشور", callback_data="tg_a_703")],
        [InlineKeyboardButton("⚡ ردود فعل إيجابية تليجرام - 50 منشور", callback_data="tg_a_704")],
        [InlineKeyboardButton("⚡ ردود فعل إيجابية تليجرام - 100 منشور", callback_data="tg_a_705")],
        [InlineKeyboardButton("⚙️ مشاهدات تلقائية تليجرام - 5 منشورات", callback_data="tg_a_706")],
        [InlineKeyboardButton("⚙️ مشاهدات تلقائية تليجرام - 20 منشور", callback_data="tg_a_707")],
        [InlineKeyboardButton("⚙️ مشاهدات تلقائية تليجرام - 50 منشور", callback_data="tg_a_708")],
        [InlineKeyboardButton("⚙️ مشاهدات تلقائية تليجرام - 100 منشور", callback_data="tg_a_709")],
        [InlineKeyboardButton("⚙️ مشاهدات تلقائية تليجرام - 200 منشور", callback_data="tg_a_710")],
        [InlineKeyboardButton("⚙️ مشاهدات تلقائية تليجرام - 500 منشور", callback_data="tg_a_711")],
        [InlineKeyboardButton("🔙 العودة لقائمة تليجرام", callback_data="sec_telegram")]
    ])

def tg_react_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥷 تفاعلات تليجرام إيجابية مختلطة", callback_data="tg_r_620")],
        [InlineKeyboardButton("👍 تفاعلات إعجاب (Thumbs Up)", callback_data="tg_r_621")],
        [InlineKeyboardButton("👎 تفاعلات عدم إعجاب (Thumbs Down)", callback_data="tg_r_622")],
        [InlineKeyboardButton("❤️ تفاعلات قلب (Heart)", callback_data="tg_r_623")],
        [InlineKeyboardButton("🔥 تفاعلات نار (Fire)", callback_data="tg_r_624")],
        [InlineKeyboardButton("😍 تفاعلات عيون قلبية", callback_data="tg_r_625")],
        [InlineKeyboardButton("🤩 تفاعلات مذهلة", callback_data="tg_r_626")],
        [InlineKeyboardButton("✨ تفاعلات + مشاهدات", callback_data="tg_r_690")],
        [InlineKeyboardButton("🔙 العودة لقائمة تليجرام", callback_data="sec_telegram")]
    ])

def tg_polls_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗳️ تصويت تليجرام عادي", callback_data="tg_p_665")],
        [InlineKeyboardButton("🔥 تصويت اشتراك إجباري", callback_data="tg_p_666")],
        [InlineKeyboardButton("🔙 العودة لقائمة تليجرام", callback_data="sec_telegram")]
    ])

def tg_boost_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 تعزيزات تليجرام - 2 يوم", callback_data="tg_t_646")],
        [InlineKeyboardButton("🚀 تعزيزات تليجرام - 7 أيام", callback_data="tg_t_893")],
        [InlineKeyboardButton("🚀 تعزيزات تليجرام - 14 يوم", callback_data="tg_t_894")],
        [InlineKeyboardButton("🚀 تعزيزات تليجرام - 30 يوم", callback_data="tg_t_895")],
        [InlineKeyboardButton("🔙 العودة لقائمة تليجرام", callback_data="sec_telegram")]
    ])

def facebook_services_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 متابعو الملف الشخصي أو الصفحة", callback_data="fb_profile_menu")],
        [InlineKeyboardButton("📘 متابعون وإعجابات صفحة فيسبوك", callback_data="fb_page_menu")],
        [InlineKeyboardButton("👥 أعضاء مجموعة فيسبوك", callback_data="fb_group_744")],
        [InlineKeyboardButton("👍 لايكات وتفاعلات منشورات فيسبوك", callback_data="fb_react_menu")],
        [InlineKeyboardButton("💬 إعجابات وتفاعلات على التعليقات", callback_data="fb_comment_react_menu")],
        [InlineKeyboardButton("📸 مشاهدات وتفاعلات قصص فيسبوك (استوري)", callback_data="fb_story_menu")],
        [InlineKeyboardButton("🔄 مشاركات فيسبوك", callback_data="fb_share_menu")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="main_rashq")]
    ])

def fb_profile_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 متابعو فيسبوك - ضمان 30 يوم", callback_data="fb_f_745")],
        [InlineKeyboardButton("👤 متابعو فيسبوك - ضمان 90 يوم", callback_data="fb_f_746")],
        [InlineKeyboardButton("👤 متابعو فيسبوك - ضمان 365 يوم", callback_data="fb_f_747")],
        [InlineKeyboardButton("👤 متابعو فيسبوك - ضمان مدى الحياة", callback_data="fb_f_748")],
        [InlineKeyboardButton("🔙 العودة لقائمة فيسبوك", callback_data="sec_facebook")]
    ])

def fb_page_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📘 إعجابات صفحة فيسبوك + 1000 متابع", callback_data="fb_f_774")],
        [InlineKeyboardButton("📘 متابعين وإعجابات صفحة - ضمان 90 يوم", callback_data="fb_f_775")],
        [InlineKeyboardButton("📘 متابعين وإعجابات صفحة - ضمان 365 يوم", callback_data="fb_f_776")],
        [InlineKeyboardButton("📘 إعجابات صفحة ومتابعين - مدى الحياة", callback_data="fb_f_777")],
        [InlineKeyboardButton("🔙 العودة لقائمة فيسبوك", callback_data="sec_facebook")]
    ])

def fb_react_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👍 إعجاب فيسبوك (Like)", callback_data="fb_f_750")],
        [InlineKeyboardButton("❤️ حب فيسبوك (Love)", callback_data="fb_f_751")],
        [InlineKeyboardButton("🤗 عناية فيسبوك (Care)", callback_data="fb_f_752")],
        [InlineKeyboardButton("😮 واو فيسبوك (Wow)", callback_data="fb_f_753")],
        [InlineKeyboardButton("😄 ضحك فيسبوك (Haha)", callback_data="fb_f_754")],
        [InlineKeyboardButton("😢 حزن فيسبوك (Sad)", callback_data="fb_f_755")],
        [InlineKeyboardButton("😡 غضب فيسبوك (Angry)", callback_data="fb_f_756")],
        [InlineKeyboardButton("🔙 العودة لقائمة فيسبوك", callback_data="sec_facebook")]
    ])

def fb_comment_react_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👍 تفاعلات تعليق - ضمان 30 يوم", callback_data="fb_f_788")],
        [InlineKeyboardButton("😂 تفاعلات ضحك على التعليق", callback_data="fb_f_789")],
        [InlineKeyboardButton("❤️ تفاعلات حب على التعليق", callback_data="fb_f_790")],
        [InlineKeyboardButton("🤗 تفاعلات عناية على التعليق", callback_data="fb_f_791")],
        [InlineKeyboardButton("😮 تفاعلات واو على التعليق", callback_data="fb_f_792")],
        [InlineKeyboardButton("😢 تفاعلات حزن على التعليق", callback_data="fb_f_793")],
        [InlineKeyboardButton("😡 تفاعلات غضب على التعليق", callback_data="fb_f_794")],
        [InlineKeyboardButton("🔙 العودة لقائمة فيسبوك", callback_data="sec_facebook")]
    ])

def fb_story_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 مشاهدات قصة فيسبوك فورية", callback_data="fb_f_778")],
        [InlineKeyboardButton("⭐ تفاعلات قصة فيسبوك", callback_data="fb_f_779")],
        [InlineKeyboardButton("🔙 العودة لقائمة فيسبوك", callback_data="sec_facebook")]
    ])

def fb_share_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 مشاركة منشور فيسبوك (صور/فيديو)", callback_data="fb_f_787")],
        [InlineKeyboardButton("🚀 مشاركة فيسبوك بجودة عالية", callback_data="fb_f_795")],
        [InlineKeyboardButton("🔙 العودة لقائمة فيسبوك", callback_data="sec_facebook")]
    ])

def instagram_services_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 متابعو انستغرام (فوري وبدون ضمان)", callback_data="ig_f_961")],
        [InlineKeyboardButton("📺 متابعو قناة انستغرام (عربي وعالمي)", callback_data="ig_channel_menu")],
        [InlineKeyboardButton("👁️ مشاهدات انستغرام (فيديو وفوري)", callback_data="ig_views_menu")],
        [InlineKeyboardButton("📸 مشاهدات قصص / استوري انستغرام", callback_data="ig_story_menu")],
        [InlineKeyboardButton("👍 إعجابات انستغرام (لايكات بضمانات)", callback_data="ig_likes_menu")],
        [InlineKeyboardButton("💬 إعجابات على تعليقات انستغرام", callback_data="ig_comment_likes_menu")],
        [InlineKeyboardButton("💬 تعليقات انستغرام مخصصة وحقيقية", callback_data="ig_comments_menu")],
        [InlineKeyboardButton("🔄 مشاركات منشورات انستغرام", callback_data="ig_shares_menu")],
        [InlineKeyboardButton("📌 حفظ منشورات انستغرام فوري", callback_data="ig_f_768")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="main_rashq")]
    ])

def ig_channel_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 متابعو قناة انستغرام - عربي", callback_data="ig_f_799")],
        [InlineKeyboardButton("🇹🇷 متابعو قناة انستغرام - تركيا", callback_data="ig_f_800")],
        [InlineKeyboardButton("🇺🇸 متابعو قناة انستغرام - أمريكي", callback_data="ig_f_801")],
        [InlineKeyboardButton("🇫🇷 متابعو قناة انستغرام - فرنسا", callback_data="ig_f_802")],
        [InlineKeyboardButton("🇵🇰 متابعو قناة انستغرام - باكستان", callback_data="ig_f_803")],
        [InlineKeyboardButton("🇷🇺 متابعو قناة انستغرام - روسيا", callback_data="ig_f_804")],
        [InlineKeyboardButton("🔙 العودة لقائمة انستغرام", callback_data="sec_instagram")]
    ])

def ig_views_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁️ مشاهدات فيديو انستغرام فورية", callback_data="ig_f_757")],
        [InlineKeyboardButton("🔥 مشاهدات انستغرام اقتصادية فورية", callback_data="ig_f_762")],
        [InlineKeyboardButton("🔙 العودة لقائمة انستغرام", callback_data="sec_instagram")]
    ])

def ig_story_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 مشاهدات قصة انستغرام عرب فورية", callback_data="ig_f_766")],
        [InlineKeyboardButton("⭐ مشاهدات قصص حسابات حقيقية", callback_data="ig_f_785")],
        [InlineKeyboardButton("🌍 مشاهدات قصة انستغرام أجنبية", callback_data="ig_f_767")],
        [InlineKeyboardButton("🔙 العودة لقائمة انستغرام", callback_data="sec_instagram")]
    ])

def ig_likes_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👍 إعجابات انستغرام - ضمان 30 يوم", callback_data="ig_f_953")],
        [InlineKeyboardButton("👍 إعجابات انستغرام - ضمان 60 يوم", callback_data="ig_f_954")],
        [InlineKeyboardButton("👍 إعجابات انستغرام - ضمان 90 يوم", callback_data="ig_f_955")],
        [InlineKeyboardButton("👍 إعجابات انستغرام - ضمان 365 يوم", callback_data="ig_f_956")],
        [InlineKeyboardButton("⭐ إعجابات انستغرام - ضمان مدى الحياة", callback_data="ig_f_957")],
        [InlineKeyboardButton("🔙 العودة لقائمة انستغرام", callback_data="sec_instagram")]
    ])

def ig_comment_likes_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ إعجاب تعليق انستغرام", callback_data="ig_f_724")],
        [InlineKeyboardButton("🔥 إعجابات تعليقات انستغرام اقتصادية", callback_data="ig_f_771")],
        [InlineKeyboardButton("🔙 العودة لقائمة انستغرام", callback_data="sec_instagram")]
    ])

def ig_comments_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 تعليقات انستغرام مخصصة وحقيقية", callback_data="ig_f_772")],
        [InlineKeyboardButton("⭐ تعليقات انستغرام مخصصة - مدى الحياة", callback_data="ig_f_773")],
        [InlineKeyboardButton("🔙 العودة لقائمة انستغرام", callback_data="sec_instagram")]
    ])

def ig_shares_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 مشاركة منشور انستغرام", callback_data="ig_f_769")],
        [InlineKeyboardButton("🚀 مشاركة منشور انستغرام - مدى الحياة", callback_data="ig_f_770")],
        [InlineKeyboardButton("🔙 العودة لقائمة انستغرام", callback_data="sec_instagram")]
    ])

def tiktok_services_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 متابعين تيك توك فوري - بدون ضمان", callback_data="tik_f_958")],
        [InlineKeyboardButton("♻️ متابعين تيك توك فوري - تعويض 30 يوم", callback_data="tik_f_959")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="main_rashq")]
    ])

def youtube_services_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📺 مشتركين يوتيوب فوري - بدون ضمان", callback_data="yt_f_796")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="main_rashq")]
    ])

def pubg_services_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 PUBG Mobile - 60 UC — 1.14$", callback_data="pubg_f_903")],
        [InlineKeyboardButton("🪙 PUBG Mobile - 60 WOW Coins — 1.16$", callback_data="pubg_f_902")],
        [InlineKeyboardButton("📦 PUBG Mobile - Updatable Firearm Materials Pack — 3.46$", callback_data="pubg_f_904")],
        [InlineKeyboardButton("🎁 PUBG Mobile - Weekly Mythic Emblem Value Pack — 3.46$", callback_data="pubg_f_905")],
        [InlineKeyboardButton("⚡ PUBG Mobile - Weekly Deal Pack 2 — 3.46$", callback_data="pubg_f_906")],
        [InlineKeyboardButton("👑 PUBG Mobile - Prime (3 Months) — 3.48$", callback_data="pubg_f_907")],
        [InlineKeyboardButton("🏆 PUBG Mobile - Mythic Emblem Pack — 5.77$", callback_data="pubg_f_908")],
        [InlineKeyboardButton("💎 PUBG Mobile - 325 UC — 5.94$", callback_data="pubg_f_909")],
        [InlineKeyboardButton("🪙 PUBG Mobile - 325 WOW Coins — 6.06$", callback_data="pubg_f_910")],
        [InlineKeyboardButton("👑 PUBG Mobile - Prime (6 Months) — 6.97$", callback_data="pubg_f_911")],
        [InlineKeyboardButton("🎖️ PUBG Mobile - Elite Pass LV1-50 — 7.00$", callback_data="pubg_f_912")],
        [InlineKeyboardButton("⭐ PUBG Mobile - Prime Plus (1 Month) — 11.62$", callback_data="pubg_f_913")],
        [InlineKeyboardButton("💎 PUBG Mobile - 660 UC — 11.88$", callback_data="pubg_f_914")],
        [InlineKeyboardButton("🪙 PUBG Mobile - 660 WOW Coins — 12.10$", callback_data="pubg_f_915")],
        [InlineKeyboardButton("👑 PUBG Mobile - Prime (12 Months) — 13.94$", callback_data="pubg_f_916")],
        [InlineKeyboardButton("🎖️ PUBG Mobile - Elite Pass LV1-100 — 14.11$", callback_data="pubg_f_917")],
        [InlineKeyboardButton("💎 PUBG Mobile - 985 UC — 17.82$", callback_data="pubg_f_918")],
        [InlineKeyboardButton("💎 PUBG Mobile - 1320 UC — 23.76$", callback_data="pubg_f_919")],
        [InlineKeyboardButton("🔥 PUBG Mobile - 1800 UC (discounted) — 29.21$", callback_data="pubg_f_920")],
        [InlineKeyboardButton("🪙 PUBG Mobile - 1800 WOW Coins — 30.24$", callback_data="pubg_f_922")],
        [InlineKeyboardButton("🎖️ PUBG Mobile - Elite Pass Plus LV1-100 — 33.95$", callback_data="pubg_f_923")],
        [InlineKeyboardButton("⭐ PUBG Mobile - Prime Plus (3 Months) — 34.85$", callback_data="pubg_f_924")],
        [InlineKeyboardButton("💎 PUBG Mobile - 2460 UC — 41.58$", callback_data="pubg_f_925")],
        [InlineKeyboardButton("🔥 PUBG Mobile - 3850 UC (discounted) — 56.76$", callback_data="pubg_f_926")],
        [InlineKeyboardButton("🪙 PUBG Mobile - 3850 WOW Coins — 60.49$", callback_data="pubg_f_928")],
        [InlineKeyboardButton("⭐ PUBG Mobile - Prime Plus (6 Months) — 68.64$", callback_data="pubg_f_929")],
        [InlineKeyboardButton("💎 PUBG Mobile - 5650 UC — 89.10$", callback_data="pubg_f_930")],
        [InlineKeyboardButton("🔥 PUBG Mobile - 8100 UC (discounted) — 112.20$", callback_data="pubg_f_931")],
        [InlineKeyboardButton("🪙 PUBG Mobile - 8100 WOW Coins — 121.00$", callback_data="pubg_f_933")],
        [InlineKeyboardButton("💎 PUBG Mobile - 11950 UC — 178.20$", callback_data="pubg_f_935")],
        [InlineKeyboardButton("💎 PUBG Mobile - 16200 UC — 234.96$", callback_data="pubg_f_936")],
        [InlineKeyboardButton("👑 PUBG Mobile - Prime (1 Month) — 1.16$", callback_data="pubg_f_899")],
        [InlineKeyboardButton("🎁 PUBG Mobile - First Purchase Pack — 1.16$", callback_data="pubg_f_900")],
        [InlineKeyboardButton("⚡ PUBG Mobile - Weekly Deal Pack 1 — 1.16$", callback_data="pubg_f_901")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="main_rashq")]
    ])

def freefire_services_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Freefire Global - 100 Diamonds Package - Newbie Offer 1 — 0.22$", callback_data="ff_937")],
        [InlineKeyboardButton("🎯 Freefire Global - Level Up Package - Level 6 — 0.32$", callback_data="ff_938")],
        [InlineKeyboardButton("⭐ Freefire Global - Weekly Lite — 0.43$", callback_data="ff_939")],
        [InlineKeyboardButton("🎯 Freefire Global - Level Up Package - Level 20 — 0.59$", callback_data="ff_940")],
        [InlineKeyboardButton("🎯 Freefire Global - Level Up Package - Level 25 — 0.59$", callback_data="ff_941")],
        [InlineKeyboardButton("🎯 Freefire Global - Level Up Package - Level 10 — 0.59$", callback_data="ff_942")],
        [InlineKeyboardButton("🎯 Freefire Global - Level Up Package - Level 15 — 0.59$", callback_data="ff_943")],
        [InlineKeyboardButton("🎯 Freefire Global - Level Up Package - Level 30 — 0.85$", callback_data="ff_944")],
        [InlineKeyboardButton("💎 Freefire Global - 110 — 0.89$", callback_data="ff_945")],
        [InlineKeyboardButton("👑 Freefire Global - Weekly Membership — 1.76$", callback_data="ff_946")],
        [InlineKeyboardButton("💎 Freefire Global - 341 — 2.70$", callback_data="ff_947")],
        [InlineKeyboardButton("💎 Freefire Global - 572 — 4.38$", callback_data="ff_948")],
        [InlineKeyboardButton("👑 Freefire Global - Monthly Membership — 6.33$", callback_data="ff_949")],
        [InlineKeyboardButton("💎 Freefire Global - 1166 — 8.79$", callback_data="ff_950")],
        [InlineKeyboardButton("💎 Freefire Global - 2398 — 17.59$", callback_data="ff_951")],
        [InlineKeyboardButton("🔥 Freefire Global - 6160 — 44.55$", callback_data="ff_952")],
        [InlineKeyboardButton("🔙 العودة للأقسام", callback_data="main_rashq")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 تحديث الإحصائيات الشاملة", callback_data='admin_panel')],
        [InlineKeyboardButton("🏆 قائمة أطراف الإحالات (Top 5)", callback_data='admin_top_refs')],
        [InlineKeyboardButton("🎟️ إضافـة كود هدية (Promo Code)", callback_data='admin_create_promo')],
        [InlineKeyboardButton("💬 الرد على مستخدم عبر الآيدي", callback_data='admin_reply_user')],
        [InlineKeyboardButton("🎁 إرسال هدية لشخص عبر الآيدي", callback_data='admin_send_gift_user')],
        [InlineKeyboardButton("➕ إضافة رصيد (بالدولار)", callback_data='admin_add_balance'), InlineKeyboardButton("➖ خصم رصيد (بالدولار)", callback_data='admin_deduct_balance')],
        [InlineKeyboardButton("👥 إدارة المشرفين (إضافة / حذف)", callback_data='admin_manage_subadmins')],
        [InlineKeyboardButton("🎁 إرسال هدية مالية (Bonus) للجميع", callback_data='admin_send_bonus')],
        [InlineKeyboardButton("🧹 تصفير جميع أرصدة المستخدمين", callback_data='admin_reset_balances')],
        [InlineKeyboardButton("🚫 حظر / إلغاء حظر مستخدم", callback_data='admin_ban_user')],
        [InlineKeyboardButton("📢 إذاعة شاملة ضخمة", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu')]
    ])
