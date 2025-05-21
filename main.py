from dotenv import load_dotenv
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
from aiogram.types import FSInputFile, URLInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler  # Webhook uchun importlar
from aiohttp import web  # Webhook server uchun import

load_dotenv()

# Sozlamalar
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # .env faylidan WEBHOOK_URL o'qiladi
WEB_SERVER_HOST = "0.0.0.0"  # Render uchun host
WEB_SERVER_PORT = int(os.getenv("PORT", 8000))  # Render beradigan port (odatda $PORT)

# Bot va dispatcher obyektlarini yaratish
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()


# Holatlar klassini aniqlash
class Form(StatesGroup):
    CHOOSE_GENDER = State()
    VILOYAT = State()
    TUMAN = State()
    AGE_FEMALE = State()
    FEMALE_CHOICE = State()
    POSE_WOMAN = State()
    MJM_EXPERIENCE = State()  # Umumiy MJM tajribasi (Oila uchun)
    MJM_EXPERIENCE_FEMALE = State()  # Ayol uchun MJM tajribasi (Alohida state)
    JMJ_AGE = State()
    JMJ_DETAILS = State()
    FAMILY_HUSBAND_AGE = State()
    FAMILY_WIFE_AGE = State()
    FAMILY_AUTHOR = State()
    FAMILY_HUSBAND_CHOICE = State()
    FAMILY_WIFE_AGREEMENT = State()  # Oila, Erkak yozmoqda, Erkak tanlovi (MJM/Erkak) dan keyin
    FAMILY_WIFE_CHOICE = State()
    FAMILY_HUSBAND_AGREEMENT = State()  # Oila, Ayol yozmoqda, Ayol tanlovi (MJM erim bilan) dan keyin
    ABOUT = State()  # Qo'shimcha ma'lumot so'raladigan oxirgi bosqima


# New state for admin's reply context
class AdminState(StatesGroup):
    REPLYING_TO_USER = State()


# Viloyatlar ro'yxati
VILOYATLAR = [
    "Andijon", "Buxoro", "Farg'ona", "Jizzax", "Qashqadaryo", "Navoiy", "Namangan",
    "Samarqand", "Sirdaryo", "Surxondaryo", "Toshkent", "Toshkent shahar", "Xorazm",
    "Qoraqalpog'iston Respublikasi",
]

# Tumanlar lug'ati (viloyatlarga bog'langan)
TUMANLAR = {
    "Andijon": ["Andijon shahar", "Asaka", "Baliqchi", "Bo‘ston", "Izboskan", "Qo‘rg‘ontepa", "Shahrixon", "Ulug‘nor",
                "Xo‘jaobod", "Yuzboshilar", "Hokim"],
    "Buxoro": ["Buxoro shahar", "Buxoro tumani", "G‘ijduvon", "Jondor", "Kogon", "Qorako‘l", "Olot", "Peshku",
               "Romitan", "Shofirkon", "Vobkent"],
    "Farg'ona": ["Farg'ona shahar", "Farg'ona tumani", "Beshariq", "Bog‘dod", "Buvayda", "Dang‘ara", "Qo‘qon", "Quva",
                 "Rishton", "Rishton tumani", "Toshloq", "Oltiariq", "Quvasoy shahar"],
    "Jizzax": ["Jizzax shahar", "Arnasoy", "Baxmal", "Dashtobod", "Forish", "G‘allaorol", "Zarbdor", "Zomin",
               "Mirzacho‘l", "Paxtakor", "Sharof Rashidov"],
    "Qashqadaryo": ["Qarshi shahar", "Chiroqchi", "G‘uzor", "Dehqonobod", "Koson", "Kitob", "Mirishkor", "Muborak",
                    "Nishon", "Qarshi tumani", "Shahrisabz", "Yakkabog‘"],
    "Navoiy": ["Navoiy shahar", "Karmana", "Konimex", "Navbahor", "Nurota", "Tomdi", "Uchquduq", "Xatirchi"],
    "Namangan": ["Namangan shahar", "Chust", "Kosonsoy", "Mingbuloq", "Namangan tumani", "Pop", "To‘raqo‘rg‘on",
                 "Uychi", "Yangiqo‘rg‘on"],
    "Samarqand": ["Samarqand shahar", "Bulung‘ur", "Jomboy", "Kattaqo‘rg‘on", "Narpay", "Nurobod", "Oqdaryo", "Payariq",
                  "Pastdarg‘om", "Paxtachi", "Qo‘shrabot", "Samarqand tumani", "Toyloq"],
    "Sirdaryo": ["Guliston shahar", "Boyovut", "Guliston tumani", "Mirzaobod", "Oqoltin", "Sayxunobod", "Sardoba",
                 "Sirdaryo tumani", "Xovos"],
    "Surxondaryo": ["Termiz shahar", "Angor", "Boysun", "Denov", "Jarqo‘rg‘on", "Muzrabot", "Sariosiyo", "Sherobod",
                    "Sho‘rchi", "Termiz tumani"],
    "Toshkent": ["Bekobod", "Bo‘ka", "Ohangaron", "Oqqo‘rg‘on", "Chinoz", "Qibray", "Quyichirchiq", "Toshkent tumani",
                 "Yangiyo‘l", "Zangiota", "Bekobod shahar", "Ohangaron shahar", "Yangiyo‘l shahar"],
    "Toshkent shahar": ["Mirzo Ulug‘bek", "Mirobod", "Sergeli", "Olmazor", "Shayxontohur", "Chilonzor", "Yunusobod",
                        "Uchtepa", "Yashnobod"],
    "Xorazm": ["Urganch shahar", "Bog‘ot", "Gurlan", "Xiva shahar", "Qo‘shko‘pir", "Shovot", "Urganch tumani", "Xonqa",
               "Yangiariq"],
    "Qoraqalpog'iston Respublikasi": ["Nukus shahar", "Amudaryo", "Beruniy", "Bo‘zatov", "Kegayli", "Qonliko‘l",
                                      "Qo‘ng‘irot",
                                      "Qorao‘zak", "Shumanay", "Taxtako‘pir", "To‘rtko‘l", "Xo‘jayli",
                                      "Chimboy", "Mo‘ynoq", "Ellikqal‘a"],
}

# Ayollar uchun pozitsiyalar ro'yxati
POSES_WOMAN = [
    "Rakom", "Chavandoz(Ustizda sakrab)", "Oyolarimni yelkezga qo'yib", "Romantik/Erkalab",
    "BSDM / Qiynab", "Hamma pozada", "Kunillingus / Minet / 69 / Lazzatli seks", "Anal/Romantik"
]

# MJM tajribasi variantlari (Oila uchun)
MJM_EXPERIENCE_OPTIONS = [
    "Hali bo'lmagan",
    "1-marta bo'lgan",
    "2-3 marta bo'lgan",
    "5 martadan ko'p (MJMni sevamiz)"
]

# MJM tajribasi variantlari (Ayol uchun)
MJM_EXPERIENCE_FEMALE_OPTIONS = [
    "Hali bo'lmagan",
    "1-marta bo'lgan",
    "2-3 marta bo'lgan",
    "5 martadan ko'p (MJMni sevaman)"
]

# Suhbat rejimida bo'lgan foydalanuvchilar IDsi
# DIQQAT: Bot o'chib yonganda bu ro'yxat tozalanadi. Doimiy saqlash uchun DB ishlatish kerak.
chat_mode_users = set()


# Umumiy navigatsiya tugmalarini qo'shish funksiyasi (Vertical)
def add_navigation_buttons(builder: InlineKeyboardBuilder, back_state: str):
    builder.row(
        types.InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"back_{back_state}"),
        types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )


# Jinsni tanlash klaviaturasi (Vertical)
def gender_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👨 Erkak", callback_data="gender_male"))
    builder.row(types.InlineKeyboardButton(text="👩 Ayol", callback_data="gender_female"))
    builder.row(types.InlineKeyboardButton(text="👨‍👩‍👧 Oilaman", callback_data="gender_family"))
    builder.row(
        types.InlineKeyboardButton(text="ℹ️ Bot haqida", callback_data="about_bot"))  # Bot haqida tugmasi qo'shildi
    add_navigation_buttons(builder, "start")
    return builder.as_markup()


# Viloyatlar klaviaturasi (Vertical)
def viloyat_keyboard():
    builder = InlineKeyboardBuilder()
    for vil in VILOYATLAR:
        builder.row(types.InlineKeyboardButton(text=vil, callback_data=f"vil_{vil}"))
    add_navigation_buttons(builder, "gender")
    return builder.as_markup()


# Tumanlar klaviaturasi (Vertical)
def tuman_keyboard(viloyat):
    builder = InlineKeyboardBuilder()
    for tuman in TUMANLAR.get(viloyat, []):
        builder.row(types.InlineKeyboardButton(text=tuman, callback_data=f"tum_{tuman}"))
    add_navigation_buttons(builder, "viloyat")
    return builder.as_markup()


# Ayolning yoshini tanlash klaviaturasi (Vertical)
def age_female_keyboard():
    builder = InlineKeyboardBuilder()
    ranges = ["18-25", "26-35", "36-45", "45+"]
    for r in ranges:
        builder.row(types.InlineKeyboardButton(text=r, callback_data=f"age_{r}"))
    add_navigation_buttons(builder, "tuman")
    return builder.as_markup()


# Ayolning tanlov klaviaturasi (Vertical)
def female_choice_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👨 Erkak bilan", callback_data="choice_1"))
    builder.row(types.InlineKeyboardButton(text="👥 MJM (2ta erkak)", callback_data="choice_2"))
    builder.row(types.InlineKeyboardButton(text="👭 JMJ (Dugonam bor)", callback_data="choice_3"))
    add_navigation_buttons(builder, "age_female")
    return builder.as_markup()


# Ayollar uchun pozitsiyalar klaviaturasi (Vertical)
def poses_keyboard():
    builder = InlineKeyboardBuilder()
    for idx, pose in enumerate(POSES_WOMAN, 1):
        builder.row(types.InlineKeyboardButton(text=f"{idx}. {pose}", callback_data=f"pose_{idx}"))
    add_navigation_buttons(builder, "female_choice")
    return builder.as_markup()


# MJM tajribasini tanlash klaviaturasi (Vertical)
def mjm_experience_keyboard(is_female=False):
    builder = InlineKeyboardBuilder()
    options = MJM_EXPERIENCE_FEMALE_OPTIONS if is_female else MJM_EXPERIENCE_OPTIONS

    for idx, option in enumerate(options):
        # Changed callback_data to use index for robustness
        callback_prefix = "mjm_exp_female_" if is_female else "mjm_exp_family_"
        builder.row(types.InlineKeyboardButton(text=option, callback_data=f"{callback_prefix}{idx}"))

    # Back button logic remains the same, handled by add_navigation_buttons
    if is_female:
        add_navigation_buttons(builder, "female_choice")  # Back to Female Choice
    else:  # Family
        add_navigation_buttons(builder, "family_husband_choice")  # Back to Family Husband Choice

    return builder.as_markup()


# Oila: Kim yozmoqda klaviaturasi (Vertical)
def family_author_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👨 Erkak yozmoqda", callback_data="author_husband"))
    builder.row(types.InlineKeyboardButton(text="👩 Ayol yozmoqda", callback_data="author_wife"))
    add_navigation_buttons(builder, "family_wife_age")  # Oila uchun kim yozmoqdadan oldingi state
    return builder.as_markup()


# Oila: Erkakning tanlovi klaviaturasi (Vertical)
def family_husband_choice_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👥 MJM", callback_data="h_choice_mjm"))
    builder.row(types.InlineKeyboardButton(text="👨 Erkak (ayolim uchun)", callback_data="h_choice_erkak"))
    add_navigation_buttons(builder, "family_author")  # Erkak tanlovidan oldingi state
    return builder.as_markup()


# Oila: Ayolning roziligi klaviaturasi (Erkak tanlovidan keyin) (Vertical)
def family_wife_agreement_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Ha rozi", callback_data="wife_agree_yes"))
    builder.row(
        types.InlineKeyboardButton(text="🔄 Yo'q, lekin men istayman (kondiraman)", callback_data="wife_agree_convince"))
    builder.row(
        types.InlineKeyboardButton(text="❓ Bilmayman, hali aytib ko'rmadim", callback_data="wife_agree_unknown"))
    # This state is reached after Family Husband Choice (either MJM or Erkak)
    add_navigation_buttons(builder, "family_husband_choice")  # Back to Family Husband Choice
    return builder.as_markup()


# Oila: Ayolning tanlovi klaviaturasi (Vertical)
def family_wife_choice_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👥 MJM (erim bilan)", callback_data="w_choice_mjm_husband"))
    builder.row(types.InlineKeyboardButton(text="👥 MJM (begona 2 erkak bilan)", callback_data="w_choice_mjm_strangers"))
    builder.row(types.InlineKeyboardButton(text="👨 Erkak (erimdan qoniqmayapman)", callback_data="w_choice_erkak"))
    add_navigation_buttons(builder, "family_author")  # Ayol tanlovidan oldingi state
    return builder.as_markup()


# Oila: Erkakning roziligi klaviaturasi (Ayol tanlovidan keyin) (Vertical)
def family_husband_agreement_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Ha rozi", callback_data="husband_agree_yes"))
    builder.row(types.InlineKeyboardButton(text="🔄 Yo'q, lekin men istayman (kondiraman)",
                                           callback_data="husband_agree_convince"))
    builder.row(
        types.InlineKeyboardButton(text="❓ Bilmayman, hali aytib ko'rmadim", callback_data="husband_agree_unknown"))
    # This state is reached after Family Wife Choice (MJM erim bilan)
    add_navigation_buttons(builder, "family_wife_choice")  # Back to Family Wife Choice
    return builder.as_markup()


# Admin panelga va kanalga ma'lumotlarni yuborish funksiyasi (Uch manzilga)
async def send_application_to_destinations(data: dict, user: types.User):
    # Admin chatlari uchun to'liq ma'lumot
    admin_message_text = (
        f"📊 **Yangi ariza qabul qilindi**\n\n"
        f"👤 **Foydalanuvchi:** "
    )
    if user.username:
        admin_message_text += f"[@{user.username}](tg://user?id={user.id}) (ID: `{user.id}`)\n"
    else:
        admin_message_text += f"[{user.full_name}](tg://user?id={user.id}) (ID: `{user.id}`)\n"

    admin_message_text += (
        f"📝 **Ism:** {user.full_name}\n"
        f"🚻 **Jins:** {data.get('gender', 'None1')}\n"
        f"🗺️ **Viloyat:** {data.get('viloyat', 'None1')}\n"
        f"🏘️ **Tuman:** {data.get('tuman', 'None1')}\n"
    )

    # Jinsga qarab qo'shimcha ma'lumotlarni formatlash (Admin uchun)
    if data.get('gender') == 'female':
        admin_message_text += (
            f"🎂 **Yosh:** {data.get('age', 'None1')}\n"
            f"🤝 **Tanlov:** {'Erkak bilan' if data.get('choice') == '1' else ('👥 MJM (2ta erkak)' if data.get('choice') == '2' else ('👭 JMJ (Dugonam bor)' if data.get('choice') == '3' else 'None1'))}\n"
        )
        if data.get('choice') == '1':  # Erkak bilan
            admin_message_text += f"🤸 **Pozitsiya:** {data.get('pose', 'None1')}\n"
        elif data.get('choice') == '2':  # Ayol MJM
            admin_message_text += f"👥 **MJM tajriba:** {data.get('mjm_experience_female', 'None1')}\n"  # Use female specific experience
        elif data.get('choice') == '3':  # Ayol JMJ
            admin_message_text += (
                f"🎂 **Dugona yoshi:** {data.get('jmj_age', 'None1')}\n"
                f"ℹ️ **Dugona haqida:** {data.get('jmj_details', 'None1')}\n"
            )

    elif data.get('gender') == 'family':
        admin_message_text += (
            f"👨 **Erkak yoshi:** {data.get('husband_age', 'None1')}\n"
            f"👩 **Ayol yoshi:** {data.get('wife_age', 'None1')}\n"
            f"✍️ **Yozmoqda:** {'Erkak' if data.get('author') == 'husband' else ('Ayol' if data.get('author') == 'wife' else 'None1')}\n"
        )
        if data.get('author') == 'husband':
            h_choice_text = {'mjm': '👥 MJM', 'erkak': '👨 Erkak (ayoli uchun)'}.get(data.get('h_choice'), 'None1')
            admin_message_text += f"🎯 **Erkak tanlovi:** {h_choice_text}\n"
            if data.get('h_choice') == 'mjm':
                admin_message_text += f"👥 **MJM tajriba:** {data.get('mjm_experience', 'None1')}\n"  # Use general MJM experience
            admin_message_text += f"👩‍⚕️ **Ayol roziligi:** {data.get('wife_agreement', 'None1')}\n"

        elif data.get('author') == 'wife':
            w_choice_text = {'mjm_husband': '👥 MJM (erim bilan)', 'mjm_strangers': '👥 MJM (begona 2 erkak bilan)',
                             'erkak': '👨 Erkak (erimdan qoniqmayapman)'}.get(data.get('w_choice'), 'None1')
            admin_message_text += f"🎯 **Ayol tanlovi:** {w_choice_text}\n"
            if data.get('w_choice') == 'mjm_husband':
                admin_message_text += f"👨‍⚕️ **Erkak roziligi:** {data.get('husband_agreement', 'None1')}\n"

    # Qo'shimcha ma'lumot 'about' (Admin uchun)
    if data.get('about'):
        admin_message_text += f"ℹ️ **Qo'shimcha / Kutilayotgan natija:** {data.get('about', 'None1')}\n"

    # "Javob yozish" tugmasi
    builder = InlineKeyboardBuilder()
    builder.button(text="✉️ Javob yozish", callback_data=f"admin_initiate_reply_{user.id}")
    reply_markup = builder.as_markup()

    # !!! ADMIN USERGA YUBORISH !!!
    try:
        await bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=admin_message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logging.info(f"Application sent to admin user {ADMIN_USER_ID} for user {user.id}")
    except Exception as e:
        logging.error(f"Failed to send application to admin user {ADMIN_USER_ID} for user {user.id}: {e}")
        try:
            await bot.send_message(ADMIN_USER_ID,
                                   f"⚠️ Ogohlantirish: Foydalanuvchi `{user.id}` arizasini shaxsiy admin chatga yuborishda xatolik: {e}",
                                   parse_mode="Markdown")
        except Exception as e_admin:
            logging.error(f"Failed to send error notification to admin user: {e_admin}")

    # !!! ADMIN GURUHIGA YUBORISH !!!
    try:
        await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logging.info(f"Application sent to admin group {ADMIN_GROUP_ID} for user {user.id}")
    except Exception as e:
        logging.error(f"Failed to send application to admin group {ADMIN_GROUP_ID} for user {user.id}: {e}")
        try:
            await bot.send_message(ADMIN_USER_ID,
                                   f"⚠️ Ogohlantirish: Foydalanuvchi `{user.id}` arizasini admin guruhiga yuborishda xatolik: {e}",
                                   parse_mode="Markdown")
        except Exception as e_admin:
            logging.error(f"Failed to send error notification to admin user about group error: {e_admin}")

    # !!! KANALGA YUBORISH (ID va username yashirin holda) !!!
    channel_text = f"📊 **Yangi ariza**\n\n📝 **Ism:** {user.full_name}\n"  # Faqat ism ko'rinadi

    # Jinsga qarab qo'shimcha ma'lumotlarni formatlash (Kanal uchun)
    if data.get('gender'):
        channel_text += f"🚻 **Jins:** {data['gender']}\n"
    if data.get('viloyat'):
        channel_text += f"🗺️ **Viloyat:** {data['viloyat']}\n"
    if data.get('tuman'):
        channel_text += f"🏘️ **Tuman:** {data['tuman']}\n"
    if data.get('gender') == 'female':
        if data.get('age'):
            channel_text += f"🎂 **Yosh:** {data['age']}\n"
        if data.get('choice'):
            choice_text = {'1': 'Erkak bilan', '2': '👥 MJM (2ta erkak)', '3': '👭 JMJ (Dugonam bor)'}.get(data['choice'],
                                                                                                         'None1')
            channel_text += f"🤝 **Tanlov:** {choice_text}\n"
        if data.get('pose'):
            channel_text += f"🤸 **Pozitsiya:** {data['pose']}\n"
        if data.get('mjm_experience_female') and data.get('choice') == '2':  # Use female specific experience
            channel_text += f"👥 **MJM tajriba:** {data['mjm_experience_female']}\n"
        if data.get('jmj_age') and data.get('choice') == '3':
            channel_text += f"🎂 **Dugona yoshi:** {data['jmj_age']}\n"
        if data.get('jmj_details') and data.get('choice') == '3':
            channel_text += f"ℹ️ **Dugona haqida:** {data['jmj_details']}\n"
    elif data.get('gender') == 'family':
        if data.get('husband_age'):
            channel_text += f"👨 **Erkak yoshi:** {data['husband_age']}\n"
        if data.get('wife_age'):
            channel_text += f"👩 **Ayol yoshi:** {data['wife_age']}\n"
        if data.get('author'):
            author_text = {'husband': 'Erkak', 'wife': 'Ayol'}.get(data['author'], 'None1')
            channel_text += f"✍️ **Yozmoqda:** {author_text}\n"
        if data.get('h_choice') and data.get('author') == 'husband':
            h_choice_text = {'mjm': '👥 MJM', 'erkak': '👨 Erkak (ayoli uchun)'}.get(data['h_choice'], 'None1')
            channel_text += f"🎯 **Erkak tanlovi:** {h_choice_text}\n"
        if data.get('mjm_experience') and data.get('author') == 'husband' and data.get(
                'h_choice') == 'mjm':  # Use general MJM experience
            channel_text += f"👥 **MJM tajriba:** {data['mjm_experience']}\n"
        if data.get('wife_agreement') and data.get('author') == 'husband':
            wife_agree_text = {'yes': '✅ Ha rozi', 'convince': '🔄 Yo\'q, lekin men istayman',
                               'unknown': '❓ Bilmayman, hali aytmadim'}.get(data['wife_agreement'], 'None1')
            channel_text += f"👩‍⚕️ **Ayol roziligi:** {wife_agree_text}\n"
        if data.get('w_choice') and data.get('author') == 'wife':
            w_choice_text = {'mjm_husband': '👥 MJM (erim bilan)', 'mjm_strangers': '👥 MJM (begona 2 erkak bilan)',
                             'erkak': '👨 Erkak (erimdan qoniqmayapman)'}.get(data['w_choice'], 'None1')
            channel_text += f"🎯 **Ayol tanlovi:** {w_choice_text}\n"
        if data.get('husband_agreement') and data.get('author') == 'wife' and data.get('w_choice') == 'mjm_husband':
            husband_agree_text = {'yes': '✅ Ha rozi', 'convince': '🔄 Yo\'q, lekin men istayman',
                                  'unknown': '❓ Bilmayman', 'unknown': '❓ Bilmayman, hali aytmadim'}.get(
                data['husband_agreement'], 'None1')  # Corrected typo here
            channel_text += f"👨‍⚕️ **Erkak roziligi:** {husband_agree_text}\n"

    # Qo'shimcha ma'lumot 'about' (Kanal uchun)
    if data.get('about'):
        channel_text += f"ℹ️ **Qo'shimcha / Kutilayotgan natija:** {data['about']}\n"

    channel_text += "\n---\nBu ariza kanalga avtomatik joylandi."

    try:
        await bot.send_message(
            CHANNEL_ID,
            channel_text,
            parse_mode="Markdown"
        )
        logging.info(f"Application sent to channel {CHANNEL_ID} for user {user.id}")
    except Exception as e:
        logging.error(f"Failed to send application to channel {CHANNEL_ID} for user {user.id}: {e}")
        try:
            await bot.send_message(ADMIN_USER_ID,
                                   f"⚠️ Ogohlantirish: Foydalanuvchi `{user.id}` arizasini kanalga yuborishda xatolik: {e}",
                                   parse_mode="Markdown")
        except Exception as e_admin:
            logging.error(f"Failed to send error notification to admin user about channel error: {e_admin}")


# /start komandasini handleri
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    # Agar foydalanuvchi suhbat rejimida bo'lsa, start ni boshqacha handle qilish
    if message.from_user.id in chat_mode_users:
        await message.answer("Siz suhbat rejimidasiz. Suhbatni tugatish uchun /endchat buyrug'ini bosing. \n\n"
                             "Agar suhbat tugasa admin sizga yoza olmaydi.\n\n"
                             "Istasangiz suhbatni tugatishdan oldin siz bilan bog'lanish uchun\n\n"
                             " raqam yoki username qoldiring ")
        return

    await state.clear()
    await message.answer("Salom! Iltimos, jinsingizni tanlang:", reply_markup=gender_keyboard())
    await state.set_state(Form.CHOOSE_GENDER)
    logging.info(f"User {message.from_user.id} started the bot.")


# Bekor qilish handleri
@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    # Agar foydalanuvchi suhbat rejimida bo'lsa, bekor qilish tugmasi ishlamasligi kerak
    if callback.from_user.id in chat_mode_users:
        await callback.answer("Siz suhbat rejimidasiz. Suhbatni tugatish uchun /endchat ni bosing.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("Suhbat bekor qilindi. Yangidan boshlash uchun /start ni bosing.")
    await callback.answer()
    logging.info(f"User {callback.from_user.id} cancelled the form.")


# Bot haqida ma'lumot handleri
@dp.callback_query(F.data == "about_bot")
async def about_bot_handler(callback: types.CallbackQuery):
    about_text = (
        "Bu bot orqali siz o'zingizga mos juftlikni topishingiz mumkin.\n"
        "Anonimlik kafolatlanadi.\n"
        "Qoidalar:\n"
        "- Faqat 18+ foydalanuvchilar uchun.\n"
        "- Haqiqiy ma'lumotlarni kiriting.\n"
        "- Hurmat doirasidan chiqmaslik.\n"
        "Qayta boshlash uchun /start buyrug'ini bosing."
    )
    await callback.message.edit_text(about_text, reply_markup=InlineKeyboardBuilder().button(text="◀️ Orqaga",
                                                                                             callback_data="back_start").as_markup())
    await callback.answer()


# Orqaga qaytish handleri
@dp.callback_query(F.data.startswith("back_"))
async def back_handler(callback: types.CallbackQuery, state: FSMContext):
    # Agar foydalanuvchi suhbat rejimida bo'lsa, orqaga tugmasi ishlamasligi kerak
    if callback.from_user.id in chat_mode_users:
        await callback.answer("Siz suhbat rejimidasiz. Suhbatni tugatish uchun /endchat buyrug'ini bosing. \n\n"
                              "Agar suhbat tugasa admin sizga yoza olmaydi.\n\n"
                              "Istasangiz suhbatni tugatishdan oldin siz bilan bog'lanish uchun\n\n"
                              " raqam yoki username qoldiring ", show_alert=True)
        return

    target_state_name = callback.data.split("_")[1]
    data = await state.get_data()  # Get current state data to determine flow

    logging.info(f"User {callback.from_user.id} going back to {target_state_name}")
    logging.info(f"Current state data: {data}")

    # Orqaga qaytish logikasini state'ga qarab aniqlash
    if target_state_name == "start":
        await start_handler(callback.message, state)
    elif target_state_name == "gender":
        await state.set_state(Form.CHOOSE_GENDER)
        await callback.message.edit_text("Iltimos, jinsingizni tanlang:", reply_markup=gender_keyboard())
    elif target_state_name == "viloyat":
        await state.set_state(Form.VILOYAT)
        await callback.message.edit_text("Viloyatingizni tanlang:", reply_markup=viloyat_keyboard())
    elif target_state_name == "tuman":
        viloyat = data.get('viloyat')
        if viloyat:
            await state.set_state(Form.TUMAN)
            await callback.message.edit_text("Tumaningizni tanlang:", reply_markup=tuman_keyboard(viloyat))
        else:
            await state.set_state(Form.VILOYAT)
            await callback.message.edit_text("Viloyatingizni tanlang:", reply_markup=viloyat_keyboard())
    elif target_state_name == "age_female":
        await state.set_state(Form.AGE_FEMALE)
        await callback.message.edit_text("Yoshingizni tanlang:", reply_markup=age_female_keyboard())
    elif target_state_name == "female_choice":
        await state.set_state(Form.FEMALE_CHOICE)
        await callback.message.edit_text("Tanlang:", reply_markup=female_choice_keyboard())
    elif target_state_name == "pose_woman":  # Ayol -> Erkak bilan -> Pozitsiya
        await state.set_state(Form.POSE_WOMAN)
        await callback.message.edit_text("Iltimos, pozitsiyalardan birini tanlang:", reply_markup=poses_keyboard())
    # --- UPDATED BACK LOGIC FOR MJM EXPERIENCE (REMOVED REDUNDANT add_navigation_buttons CALLS) ---
    elif target_state_name == "mjm_experience":  # Back to MJM Experience (from ABOUT) - Family flow
        # mjm_experience_keyboard already adds navigation buttons internally
        await callback.message.edit_text("MJM tajribangizni tanlang:",
                                         reply_markup=mjm_experience_keyboard(is_female=False))
        await state.set_state(Form.MJM_EXPERIENCE)
    elif target_state_name == "mjm_experience_female":
        # mjm_experience_keyboard already adds navigation buttons internally
        await callback.message.edit_text("MJM tajribangizni tanlang:",
                                         reply_markup=mjm_experience_keyboard(is_female=True))
        await state.set_state(Form.MJM_EXPERIENCE_FEMALE)
    # ---------------------------------------------
    elif target_state_name == "jmj_age":  # Ayol -> JMJ -> Dugona yoshini kiritish
        await state.set_state(Form.JMJ_AGE)
        await callback.message.edit_text("Dugonangizning yoshini kiriting:")
    elif target_state_name == "jmj_details":  # Ayol -> JMJ -> Dugona haqida kiritish
        await state.set_state(Form.JMJ_DETAILS)
        await callback.message.edit_text("Dugonangiz haqida qo'shimcha ma'lumot kiriting:")
    elif target_state_name == "family_husband_age":  # Oila -> Erkak yoshini kiritish
        await state.set_state(Form.FAMILY_HUSBAND_AGE)
        await callback.message.edit_text("Erkakning yoshini kiriting:")
    elif target_state_name == "family_wife_age":  # Oila -> Ayol yoshini kiritish
        await state.set_state(Form.FAMILY_WIFE_AGE)
        await callback.message.edit_text("Ayolning yoshini kiriting:")
    elif target_state_name == "family_author":  # Oila -> Kim yozmoqda
        await state.set_state(Form.FAMILY_AUTHOR)
        await callback.message.edit_text("Kim yozmoqda:", reply_markup=family_author_keyboard())
    elif target_state_name == "family_husband_choice":  # Oila -> Erkak tanlovi
        await state.set_state(Form.FAMILY_HUSBAND_CHOICE)
        await callback.message.edit_text("Tanlang:", reply_markup=family_husband_choice_keyboard())
    # --- UPDATED BACK LOGIC FOR FAMILY AGREEMENT STATES (REMOVED REDUNDANT add_navigation_buttons CALLS) ---
    elif target_state_name == "family_wife_agreement":  # Back to Wife Agreement (from ABOUT)
        # family_wife_agreement_keyboard already adds navigation buttons internally
        await callback.message.edit_text("Ayolning roziligi:", reply_markup=family_wife_agreement_keyboard())
        await state.set_state(Form.FAMILY_WIFE_AGREEMENT)
    elif target_state_name == "family_wife_choice":  # Back to Family Wife Choice (from ABOUT or Husband Agreement)
        await state.set_state(Form.FAMILY_WIFE_CHOICE)
        await callback.message.edit_text("Tanlang:", reply_markup=family_wife_choice_keyboard())
    elif target_state_name == "family_husband_agreement":  # Back to Husband Agreement (from ABOUT)
        # family_husband_agreement_keyboard already adds navigation buttons internally
        await callback.message.edit_text("Erkakning roziligi:", reply_markup=family_husband_agreement_keyboard())
        await state.set_state(Form.FAMILY_HUSBAND_AGREEMENT)
    # -------------------------------------------------
    # --- BACK LOGIC FROM ABOUT ---
    elif target_state_name == "about":  # Determine the previous state based on the flow data
        prev_state_for_about = None
        if data.get('gender') == 'female':
            choice = data.get('choice')
            if choice == '1':  # Erkak bilan
                prev_state_for_about = Form.POSE_WOMAN
            elif choice == '2':  # MJM
                prev_state_for_about = Form.MJM_EXPERIENCE_FEMALE  # Back to female specific MJM state
            elif choice == '3':  # JMJ
                prev_state_for_about = Form.JMJ_DETAILS
        elif data.get('gender') == 'family':
            author = data.get('author')
            if author == 'husband':
                h_choice = data.get('h_choice')
                if h_choice in ['mjm', 'erkak']:  # Both MJM and Erkak lead to Wife Agreement before ABOUT
                    prev_state_for_about = Form.FAMILY_WIFE_AGREEMENT
            elif author == 'wife':
                w_choice = data.get('w_choice')
                if w_choice == 'mjm_husband':
                    prev_state_for_about = Form.FAMILY_HUSBAND_AGREEMENT
                elif w_choice in ['mjm_strangers', 'erkak']:  # These lead directly to ABOUT from Wife Choice
                    prev_state_for_about = Form.FAMILY_WIFE_CHOICE

        if prev_state_for_about:
            await state.set_state(prev_state_for_about)
            # Need to send the correct message/keyboard for the previous state
            if prev_state_for_about == Form.POSE_WOMAN:
                await callback.message.edit_text("Iltimos, pozitsiyalardan birini tanlang:",
                                                 reply_markup=poses_keyboard())
            elif prev_state_for_about == Form.MJM_EXPERIENCE_FEMALE:  # Female specific MJM state
                await callback.message.edit_text("MJM tajribangizni tanlang:",
                                                 reply_markup=mjm_experience_keyboard(is_female=True))
            elif prev_state_for_about == Form.MJM_EXPERIENCE:  # Family MJM state
                await callback.message.edit_text("MJM tajribangizni tanlang:",
                                                 reply_markup=mjm_experience_keyboard(is_female=False))
            elif prev_state_for_about == Form.JMJ_DETAILS:
                await callback.message.edit_text("Dugonangiz haqida qo'shimcha ma'lumot kiriting:")
            elif prev_state_for_about == Form.FAMILY_WIFE_AGREEMENT:
                await callback.message.edit_text("Ayolning roziligi:", reply_markup=family_wife_agreement_keyboard())
            elif prev_state_for_about == Form.FAMILY_WIFE_CHOICE:
                await callback.message.edit_text("Tanlang:", reply_markup=family_wife_choice_keyboard())
            elif prev_state_for_about == Form.FAMILY_HUSBAND_AGREEMENT:
                await callback.message.edit_text("Erkakning roziligi:",
                                                 reply_markup=family_husband_agreement_keyboard())
            else:  # Fallback if previous state logic is missing
                await state.set_state(Form.CHOOSE_GENDER)
                await callback.message.edit_text("Iltimos, jinsingizni tanlang:", reply_markup=gender_keyboard())
                logging.warning(f"User {callback.from_user.id} back from ABOUT to unhandled previous state.")
        else:  # Fallback if previous state cannot be determined
            await state.set_state(Form.CHOOSE_GENDER)
            await callback.message.edit_text("Iltimas, jinsingizni tanlang:", reply_markup=gender_keyboard())
            logging.warning(f"User {callback.from_user.id} back from ABOUT with no determined previous state.")
    # -----------------------------
    await callback.answer()


# Jinsni tanlash handleri
@dp.callback_query(F.data.startswith("gender_"), Form.CHOOSE_GENDER)
async def gender_handler(callback: types.CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[1]
    await state.update_data(gender=gender)
    logging.info(f"User {callback.from_user.id} chose gender: {gender}")

    if gender == "male":
        await callback.message.edit_text(
            "Kechirasiz, bu xizmat faqat ayollar va oilalar uchun.\n"
            "Agar oila bo'lsangiz iltimos «Oilaman» bo'limini tanlang.",
            reply_markup=InlineKeyboardBuilder().button(
                text="Qayta boshlash",
                callback_data="back_start"
            ).as_markup()
        )
        await state.clear()
        await callback.answer("Erkaklar uchun ro'yxatdan o'tish hozircha mavjud emas.", show_alert=True)
        return

    # Agar Ayol yoki Oila bo'lsa, viloyat tanlashga o'tish
    await callback.message.edit_text("Viloyatingizni tanlang:", reply_markup=viloyat_keyboard())
    await state.set_state(Form.VILOYAT)
    await callback.answer()


# Viloyatni tanlash handleri
@dp.callback_query(F.data.startswith("vil_"), Form.VILOYAT)
async def viloyat_handler(callback: types.CallbackQuery, state: FSMContext):
    viloyat = callback.data.split("_")[1]
    await state.update_data(viloyat=viloyat)
    logging.info(f"User {callback.from_user.id} chose viloyat: {viloyat}")
    await callback.message.edit_text("Tumaningizni tanlang:", reply_markup=tuman_keyboard(viloyat))
    await state.set_state(Form.TUMAN)
    await callback.answer()


# Tumanni tanlash handleri
@dp.callback_query(F.data.startswith("tum_"), Form.TUMAN)
async def tuman_handler(callback: types.CallbackQuery, state: FSMContext):
    tuman = callback.data.split("_")[1]
    await state.update_data(tuman=tuman)
    logging.info(f"User {callback.from_user.id} chose tuman: {tuman}")
    # Jinsga qarab keyingi bosqichga o'tish
    data = await state.get_data()
    if data.get('gender') == 'female':
        await callback.message.edit_text("Yoshingizni tanlang:", reply_markup=age_female_keyboard())
        await state.set_state(Form.AGE_FEMALE)
    elif data.get('gender') == 'family':
        await callback.message.edit_text("Erkakning yoshini kiriting:")
        await state.set_state(Form.FAMILY_HUSBAND_AGE)
    await callback.answer()


# Ayolning yoshini tanlash handleri
@dp.callback_query(F.data.startswith("age_"), Form.AGE_FEMALE)
async def age_female_handler(callback: types.CallbackQuery, state: FSMContext):
    age = callback.data.split("_")[1]
    await state.update_data(age=age)
    logging.info(f"User {callback.from_user.id} chose female age: {age}")
    await callback.message.edit_text("Tanlang:", reply_markup=female_choice_keyboard())
    await state.set_state(Form.FEMALE_CHOICE)
    await callback.answer()


# Ayolning tanlovini handleri (MJM/Erkak bilan/JMJ)
@dp.callback_query(F.data.startswith("choice_"), Form.FEMALE_CHOICE)
async def female_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    await state.update_data(choice=choice)
    logging.info(f"User {callback.from_user.id} chose female choice: {choice}")

    if choice == "1":  # Erkak bilan
        await callback.message.edit_text("Iltimos, yotirgan pozalaringizdan birini tanlang:",
                                         reply_markup=poses_keyboard())
        await state.set_state(Form.POSE_WOMAN)
    elif choice == "2":  # MJM (2ta erkak)
        await callback.message.edit_text("MJM tajribangizni tanlang:",
                                         reply_markup=mjm_experience_keyboard(is_female=True))
        await state.set_state(Form.MJM_EXPERIENCE_FEMALE)
    elif choice == "3":  # JMJ (Dugonam bor)
        await callback.message.edit_text("Dugonangizning yoshini kiriting:")
        await state.set_state(Form.JMJ_AGE)
    await callback.answer()


# Ayolning pozitsiyasini tanlash handleri
@dp.callback_query(F.data.startswith("pose_"), Form.POSE_WOMAN)
async def pose_woman_handler(callback: types.CallbackQuery, state: FSMContext):
    pose_index = int(callback.data.split("_")[1]) - 1  # Adjust for 0-indexed list
    if 0 <= pose_index < len(POSES_WOMAN):
        pose = POSES_WOMAN[pose_index]
        await state.update_data(pose=pose)
        logging.info(f"User {callback.from_user.id} chose female pose: {pose}")
        await callback.message.edit_text(
            "Bu uchrashuvdan nimalarni kutyapsiz va sizga nimalar yoqadi(hohlayapsiz) \n\n Ko’rishish uchun sizda joy mavjudmi(batafsil yozing)??:")
        await state.set_state(Form.ABOUT)
    else:
        await callback.message.edit_text("Noto'g'ri pozitsiya tanlandi. Iltimos, qaytadan tanlang.",
                                         reply_markup=poses_keyboard())
    await callback.answer()


# MJM tajribasi handleri (Oila uchun) - Adjusted to use index from callback data
@dp.callback_query(F.data.startswith("mjm_exp_family_"), Form.MJM_EXPERIENCE)
async def mjm_experience_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        exp_index = int(callback.data.split("_")[-1])
        if 0 <= exp_index < len(MJM_EXPERIENCE_OPTIONS):
            original_option_text = MJM_EXPERIENCE_OPTIONS[exp_index]
            await state.update_data(mjm_experience=original_option_text)
            logging.info(f"User {callback.from_user.id} chose MJM experience (family): {original_option_text}")
            await callback.message.edit_text("Ayolning roziligi:", reply_markup=family_wife_agreement_keyboard())
            await state.set_state(Form.FAMILY_WIFE_AGREEMENT)
        else:
            await callback.message.edit_text("Noto'g'ri tanlov. Iltimos, qaytadan tanlang.",
                                             reply_markup=mjm_experience_keyboard(is_female=False))
    except ValueError:
        await callback.message.edit_text("Noto'g'ri ma'lumot qabul qilindi. Iltimos, tugmalardan birini bosing.",
                                         reply_markup=mjm_experience_keyboard(is_female=False))
    await callback.answer()


# MJM tajribasi handleri (Ayol uchun) - Adjusted to use index from callback data
@dp.callback_query(F.data.startswith("mjm_exp_female_"), Form.MJM_EXPERIENCE_FEMALE)
async def mjm_experience_female_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        exp_index = int(callback.data.split("_")[-1])
        if 0 <= exp_index < len(MJM_EXPERIENCE_FEMALE_OPTIONS):
            original_option_text = MJM_EXPERIENCE_FEMALE_OPTIONS[exp_index]
            await state.update_data(mjm_experience_female=original_option_text)
            logging.info(f"User {callback.from_user.id} chose MJM experience (female): {original_option_text}")
            await callback.message.edit_text(
                "Bu uchrashuvdan nimalarni kutyapsiz va sizga nimalar yoqadi(hohlayapsiz) \n\n Ko’rishish uchun sizda joy mavjudmi(batafsil yozing)??:")
            await state.set_state(Form.ABOUT)
        else:
            await callback.message.edit_text("Noto'g'ri tanlov. Iltimos, qaytadan tanlang.",
                                             reply_markup=mjm_experience_keyboard(is_female=True))
    except ValueError:
        await callback.message.edit_text("Noto'g'ri ma'lumot qabul qilindi. Iltimos, tugmalardan birini bosing.",
                                         reply_markup=mjm_experience_keyboard(is_female=True))
    await callback.answer()


# JMJ yoshini kiritish handleri
@dp.message(Form.JMJ_AGE)
async def jmj_age_handler(message: types.Message, state: FSMContext):
    age_input = message.text
    if age_input and age_input.isdigit() and 18 <= int(age_input) <= 60:
        await state.update_data(jmj_age=age_input)
        logging.info(f"User {message.from_user.id} entered JMJ age: {age_input}")
        await message.answer("Dugonangiz haqida qo'shimcha ma'lumot kiriting (masalan, bo'yi, vazni, qiziqishlari):")
        await state.set_state(Form.JMJ_DETAILS)
    else:
        await message.answer("Iltimos, dugonangizning yoshini 18 yoshdan 60 yoshgacha bo'lgan raqamda kiriting.")


# JMJ yoshini noto'g'ri kiritish handleri (matn kiritilganda)
@dp.message(F.text, Form.JMJ_AGE)
async def jmj_age_invalid_handler(message: types.Message):
    await message.answer("Yoshingizni faqat raqamlarda kiriting. Iltimos, qaytadan urinib ko'ring.")


# JMJ tafsilotlarini kiritish handleri
@dp.message(Form.JMJ_DETAILS)
async def jmj_details_handler(message: types.Message, state: FSMContext):
    details = message.text
    if details and len(details) >= 10:  # Minimal 10 belgi
        await state.update_data(jmj_details=details)
        logging.info(f"User {message.from_user.id} entered JMJ details.")
        await message.answer(
            "Bu uchrashuvdan nimalarni kutyapsiz va sizga nimalar yoqadi(hohlayapsiz) \n\n Ko’rishish uchun sizda joy mavjudmi(batafsil yozing)??:")
        await state.set_state(Form.ABOUT)
    else:
        await message.answer("Iltimos, dugonangiz haqida kamida 10 ta belgidan iborat batafsil ma'lumot kiriting.")


# Oila: Erkakning yoshini kiritish handleri
@dp.message(Form.FAMILY_HUSBAND_AGE)
async def family_husband_age_handler(message: types.Message, state: FSMContext):
    age_input = message.text
    if age_input and age_input.isdigit() and 18 <= int(age_input) <= 70:
        await state.update_data(husband_age=age_input)
        logging.info(f"User {message.from_user.id} entered husband age: {age_input}")
        await message.answer("Ayolning yoshini kiriting:")
        await state.set_state(Form.FAMILY_WIFE_AGE)
    else:
        await message.answer("Iltimos, erkakning yoshini 18 yoshdan 70 yoshgacha bo'lgan raqamda kiriting.")


# Oila: Erkak yoshini noto'g'ri kiritish handleri (matn kiritilganda)
@dp.message(F.text, Form.FAMILY_HUSBAND_AGE)
async def family_husband_age_invalid_handler(message: types.Message):
    await message.answer("Yoshingizni faqat raqamlarda kiriting. Iltimos, qaytadan urinib ko'ring.")


# Oila: Ayolning yoshini kiritish handleri
@dp.message(Form.FAMILY_WIFE_AGE)
async def family_wife_age_handler(message: types.Message, state: FSMContext):
    age_input = message.text
    if age_input and age_input.isdigit() and 18 <= int(age_input) <= 60:
        await state.update_data(wife_age=age_input)
        logging.info(f"User {message.from_user.id} entered wife age: {age_input}")
        await message.answer("Kim yozmoqda:", reply_markup=family_author_keyboard())
        await state.set_state(Form.FAMILY_AUTHOR)
    else:
        await message.answer("Iltimos, ayolning yoshini 18 yoshdan 60 yoshgacha bo'lgan raqamda kiriting.")


# Oila: Ayol yoshini noto'g'ri kiritish handleri (matn kiritilganda)
@dp.message(F.text, Form.FAMILY_WIFE_AGE)
async def family_wife_age_invalid_handler(message: types.Message):
    await message.answer("Yoshingizni faqat raqamlarda kiriting. Iltimos, qaytadan urinib ko'ring.")


# Oila: Kim yozmoqda handleri
@dp.callback_query(F.data.startswith("author_"), Form.FAMILY_AUTHOR)
async def family_author_handler(callback: types.CallbackQuery, state: FSMContext):
    author = callback.data.split("_")[1]
    await state.update_data(author=author)
    logging.info(f"User {callback.from_user.id} chose family author: {author}")

    if author == "husband":
        await callback.message.edit_text("Tanlang:", reply_markup=family_husband_choice_keyboard())
        await state.set_state(Form.FAMILY_HUSBAND_CHOICE)
    elif author == "wife":
        await callback.message.edit_text("Tanlang:", reply_markup=family_wife_choice_keyboard())
        await state.set_state(Form.FAMILY_WIFE_CHOICE)
    await callback.answer()


# Oila: Erkakning tanlovi handleri
@dp.callback_query(F.data.startswith("h_choice_"), Form.FAMILY_HUSBAND_CHOICE)
async def family_husband_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    h_choice = callback.data.split("_")[2]
    await state.update_data(h_choice=h_choice)
    logging.info(f"User {callback.from_user.id} chose husband choice: {h_choice}")

    if h_choice == "mjm":
        await callback.message.edit_text("MJM tajribangizni tanlang:",
                                         reply_markup=mjm_experience_keyboard(is_female=False))
        await state.set_state(Form.MJM_EXPERIENCE)
    elif h_choice == "erkak":
        await callback.message.edit_text("Ayolning roziligi:", reply_markup=family_wife_agreement_keyboard())
        await state.set_state(Form.FAMILY_WIFE_AGREEMENT)
    await callback.answer()


# Oila: Ayolning roziligi handleri
@dp.callback_query(F.data.startswith("wife_agree_"), Form.FAMILY_WIFE_AGREEMENT)
async def family_wife_agreement_handler(callback: types.CallbackQuery, state: FSMContext):
    wife_agreement = callback.data.split("_")[2]
    await state.update_data(wife_agreement=wife_agreement)
    logging.info(f"User {callback.from_user.id} chose wife agreement: {wife_agreement}")
    await callback.message.edit_text(
        "Bu uchrashuvdan nimalarni kutyapsiz va sizga nimalar yoqadi(hohlayapsiz) \n\n Ko’rishish uchun sizda joy mavjudmi(batafsil yozing)??:")
    await state.set_state(Form.ABOUT)
    await callback.answer()


# Oila: Ayolning tanlovi handleri
@dp.callback_query(F.data.startswith("w_choice_"), Form.FAMILY_WIFE_CHOICE)
async def family_wife_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    w_choice = callback.data.split("_")[2]
    await state.update_data(w_choice=w_choice)
    logging.info(f"User {callback.from_user.id} chose wife choice: {w_choice}")

    if w_choice == "mjm_husband":
        await callback.message.edit_text("Erakning roziligi:", reply_markup=family_husband_agreement_keyboard())
        await state.set_state(Form.FAMILY_HUSBAND_AGREEMENT)
    elif w_choice in ["mjm_strangers", "erkak"]:
        await callback.message.edit_text(
            "Bu uchrashuvdan nimalarni kutyapsiz va sizga nimalar yoqadi(hohlayapsiz) \n\n Ko’rishish uchun sizda joy mavjudmi(batafsil yozing)??:")
        await state.set_state(Form.ABOUT)
    await callback.answer()


# Oila: Erkakning roziligi handleri
@dp.callback_query(F.data.startswith("husband_agree_"), Form.FAMILY_HUSBAND_AGREEMENT)
async def family_husband_agreement_handler(callback: types.CallbackQuery, state: FSMContext):
    husband_agreement = callback.data.split("_")[2]
    await state.update_data(husband_agreement=husband_agreement)
    logging.info(f"User {callback.from_user.id} chose husband agreement: {husband_agreement}")
    await callback.message.edit_text(
        "Bu uchrashuvdan nimalarni kutyapsiz va sizga nimalar yoqadi(hohlayapsiz) \n\n Ko’rishish uchun sizda joy mavjudmi(batafsil yozing)??:")
    await state.set_state(Form.ABOUT)
    await callback.answer()


# Yakuniy ma'lumotni kiritish handleri
@dp.message(Form.ABOUT)
async def about_handler(message: types.Message, state: FSMContext):
    about_text = message.text
    if about_text and len(about_text) >= 20:  # Minimal 20 belgi
        await state.update_data(about=about_text)
        data = await state.get_data()
        logging.info(f"User {message.from_user.id} submitted 'about' data. Final data: {data}")

        await send_application_to_destinations(data, message.from_user)

        await message.answer("Arizangiz qabul qilindi. Tez orada siz bilan bog'lanamiz.")
        await state.clear()
    else:
        await message.answer("Iltimos, kamida 20 ta belgidan iborat batafsil ma'lumot kiriting.")


# 1. Adminlar bilan foydalanuvchi o'rtasida suhbat boshlash tugmasi
@dp.callback_query(F.data.startswith("admin_initiate_reply_"))
async def admin_initiate_reply(callback: types.CallbackQuery, state: FSMContext):
    user_id_to_reply = int(callback.data.split("_")[3])

    # Adminda javob berish holatini o'rnatish
    await state.set_state(AdminState.REPLYING_TO_USER)
    await state.update_data(target_user_id=user_id_to_reply)

    # Foydalanuvchini suhbat rejimiga qo'shish
    chat_mode_users.add(user_id_to_reply)

    await callback.message.answer(
        f"Foydalanuvchi `{user_id_to_reply}` ga javob yozish rejimida. Xabaringizni yuboring. "
        f"Suhbatni tugatish uchun /endreply buyrug'ini bosing.",
        parse_mode="Markdown"
    )
    await callback.answer()
    logging.info(f"Admin {callback.from_user.id} initiated reply to user {user_id_to_reply}")


# 2. Admin yozgan xabarni foydalanuvchiga forward qilish
@dp.message(F.chat.id.in_([ADMIN_USER_ID, ADMIN_GROUP_ID]), AdminState.REPLYING_TO_USER)
async def admin_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        await message.answer("Javob beriladigan foydalanuvchi topilmadi. Qayta urinib ko'ring yoki /start bosing.")
        await state.clear()
        return

    try:
        # Check for message content type and forward accordingly
        if message.text:
            await bot.send_message(target_user_id, message.text, parse_mode="Markdown")
            logging.info(f"Admin {message.from_user.id} replied text message to user {target_user_id}")
        elif message.photo:
            await bot.send_photo(target_user_id, message.photo[-1].file_id, caption=message.caption,
                                 parse_mode="Markdown")
            logging.info(f"Admin {message.from_user.id} replied photo message to user {target_user_id}")
        elif message.video:
            await bot.send_video(target_user_id, message.video.file_id, caption=message.caption, parse_mode="Markdown")
            logging.info(f"Admin {message.from_user.id} replied video message to user {target_user_id}")
        elif message.animation:
            await bot.send_animation(target_user_id, message.animation.file_id, caption=message.caption,
                                     parse_mode="Markdown")
            logging.info(f"Admin {message.from_user.id} replied animation (GIF) message to user {target_user_id}")
        elif message.sticker:
            await bot.send_sticker(target_user_id, message.sticker.file_id)
            logging.info(f"Admin {message.from_user.id} replied sticker message to user {target_user_id}")
        elif message.document:
            await bot.send_document(target_user_id, message.document.file_id, caption=message.caption,
                                    parse_mode="Markdown")
            logging.info(f"Admin {message.from_user.id} replied document message to user {target_user_id}")
        elif message.audio:
            await bot.send_audio(target_user_id, message.audio.file_id, caption=message.caption, parse_mode="Markdown")
            logging.info(f"Admin {message.from_user.id} replied audio message to user {target_user_id}")
        elif message.voice:
            await bot.send_voice(target_user_id, message.voice.file_id, caption=message.caption, parse_mode="Markdown")
            logging.info(f"Admin {message.from_user.id} replied voice message to user {target_user_id}")
        else:
            await message.answer("Kechirasiz, bu turdagi xabarni hozircha yubora olmayman.")
            logging.warning(
                f"Admin {message.from_user.id} tried to reply with unhandled message type to user {target_user_id}")
            return  # Don't send "Xabar yuborildi." for unhandled types

        await message.answer("Xabar foydalanuvchiga yuborildi.")

    except Exception as e:
        logging.error(f"Error replying to user {target_user_id} from admin {message.from_user.id}: {e}")
        await message.answer(f"Xabar yuborishda xatolik yuz berdi: {e}")


# 3. Admin suhbatini tugatish komandasi
@dp.message(Command("endreply"), F.chat.id.in_([ADMIN_USER_ID, ADMIN_GROUP_ID]), AdminState.REPLYING_TO_USER)
async def admin_end_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    if target_user_id:
        # Foydalanuvchini suhbat rejimdan olib tashlash
        chat_mode_users.discard(target_user_id)
        logging.info(f"User {target_user_id} removed from chat_mode_users.")

    await state.clear()
    await message.answer("Suhbat rejimi tugatildi. Endi siz botning boshqa buyruqlaridan foydalanishingiz mumkin.")
    logging.info(f"Admin {message.from_user.id} ended reply mode for user {target_user_id}")


# 4. Foydalanuvchi suhbatini tugatish komandasi
@dp.message(Command("endchat"), F.chat.id.in_(chat_mode_users))
async def user_end_chat(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in chat_mode_users:
        chat_mode_users.discard(user_id)
        logging.info(f"User {user_id} ended chat mode.")
        await message.answer(
            "Suhbat rejimi tugatildi. Adminlar sizga xabar yubora olmaydi. Agar qayta boshlamoqchi bo'lsangiz /start buyrug'ini bosing.")
    else:
        await message.answer("Siz suhbat rejimida emassiz. /start buyrug'ini bosing.")


# 5. Suhbat rejimida bo'lmagan userlardan kelgan xabarlarga javob
@dp.message(F.chat.id != ADMIN_USER_ID, F.chat.id != ADMIN_GROUP_ID, ~F.chat.id.in_(chat_mode_users))
async def handle_unregistered_messages(message: types.Message):
    await message.answer(
        "Iltimos, bot funksiyalaridan foydalanish uchun /start buyrug'ini bosing. "
        "Agar suhbatni davom ettirmoqchi bo'lsangiz, avval /endchat buyrug'ini bosing."
    )
    logging.info(f"Unhandled message from user {message.from_user.id}: {message.text}")


# Webhookni ishga tushirish funksiyasi
async def on_startup(bot: Bot) -> None:
    logging.info(f"Setting webhook to {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Webhook successfully set!")


async def on_shutdown(bot: Bot) -> None:
    logging.info("Deleting webhook...")
    await bot.delete_webhook()
    logging.info("Webhook deleted!")


async def main() -> None:
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Aiogram 3.x uchun message handlerlarni ro'yxatdan o'tkazish
    dp.message.register(start_handler, Command("start"))

    # Callback query handlerlar
    dp.callback_query.register(cancel_handler, F.data == "cancel")
    dp.callback_query.register(about_bot_handler, F.data == "about_bot")
    dp.callback_query.register(back_handler, F.data.startswith("back_"))
    dp.callback_query.register(gender_handler, F.data.startswith("gender_"), Form.CHOOSE_GENDER)
    dp.callback_query.register(viloyat_handler, F.data.startswith("vil_"), Form.VILOYAT)
    dp.callback_query.register(tuman_handler, F.data.startswith("tum_"), Form.TUMAN)
    dp.callback_query.register(age_female_handler, F.data.startswith("age_"), Form.AGE_FEMALE)
    dp.callback_query.register(female_choice_handler, F.data.startswith("choice_"), Form.FEMALE_CHOICE)
    dp.callback_query.register(pose_woman_handler, F.data.startswith("pose_"), Form.POSE_WOMAN)
    dp.callback_query.register(mjm_experience_handler, F.data.startswith("mjm_exp_family_"), Form.MJM_EXPERIENCE)
    dp.callback_query.register(mjm_experience_female_handler, F.data.startswith("mjm_exp_female_"),
                               Form.MJM_EXPERIENCE_FEMALE)
    dp.callback_query.register(family_author_handler, F.data.startswith("author_"), Form.FAMILY_AUTHOR)
    dp.callback_query.register(family_husband_choice_handler, F.data.startswith("h_choice_"),
                               Form.FAMILY_HUSBAND_CHOICE)
    dp.callback_query.register(family_wife_agreement_handler, F.data.startswith("wife_agree_"),
                               Form.FAMILY_WIFE_AGREEMENT)
    dp.callback_query.register(family_wife_choice_handler, F.data.startswith("w_choice_"), Form.FAMILY_WIFE_CHOICE)
    dp.callback_query.register(family_husband_agreement_handler, F.data.startswith("husband_agree_"),
                               Form.FAMILY_HUSBAND_AGREEMENT)

    # Message handlerlar (statega bog'liq)
    dp.message.register(jmj_age_handler, Form.JMJ_AGE)
    dp.message.register(jmj_age_invalid_handler, F.text, Form.JMJ_AGE)  # Agar raqam bo'lmasa
    dp.message.register(jmj_details_handler, Form.JMJ_DETAILS)
    dp.message.register(family_husband_age_handler, Form.FAMILY_HUSBAND_AGE)
    dp.message.register(family_husband_age_invalid_handler, F.text, Form.FAMILY_HUSBAND_AGE)  # Agar raqam bo'lmasa
    dp.message.register(family_wife_age_handler, Form.FAMILY_WIFE_AGE)
    dp.message.register(family_wife_age_invalid_handler, F.text, Form.FAMILY_WIFE_AGE)  # Agar raqam bo'lmasa
    dp.message.register(about_handler, Form.ABOUT)

    # Admin va user suhbatini boshqarish handlerlari
    dp.callback_query.register(admin_initiate_reply, F.data.startswith("admin_initiate_reply_"))
    dp.message.register(admin_reply_to_user, F.chat.id.in_([ADMIN_USER_ID, ADMIN_GROUP_ID]),
                        AdminState.REPLYING_TO_USER)
    dp.message.register(admin_end_reply, Command("endreply"), F.chat.id.in_([ADMIN_USER_ID, ADMIN_GROUP_ID]),
                        AdminState.REPLYING_TO_USER)
    dp.message.register(user_end_chat, Command("endchat"), F.chat.id.in_(chat_mode_users))

    # Suhbat rejimida bo'lmagan userlardan kelgan xabarlarni admin chatlariga forward qilish
    # This handler forwards user messages and adds the reply button
    # Muhim: Bu handler barcha qolgan message handlerlaridan keyin bo'lishi kerak!
    # Shuningdek, u admin chatlari emas, faqat foydalanuvchi chatlaridan kelgan xabarlarni qamrab oladi
    dp.message.register(forward_user_message_to_admins_and_group, F.chat.id != ADMIN_USER_ID,
                        F.chat.id != ADMIN_GROUP_ID, F.chat.id.in_(chat_mode_users))

    # Boshqa message handlerlaridan keyin turishi kerak
    # Bu handler suhbat rejimida bo'lmagan foydalanuvchilarning botga yozgan xabarlarini qayta ishlaydi.
    # Uning F.chat.id.in_(chat_mode_users) filtrining negatsiyasi bo'lishi muhim, ya'ni
    # faqat suhbat rejimida bo'lmagan foydalanuvchilarning xabarlarini tutadi.
    dp.message.register(handle_unregistered_messages)

    # Webhook serverini sozlash
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, "/webhook")  # /webhook yo'li orqali kiruvchi xabarlar

    # Webhook URLni Telegramga o'rnatish
    await on_startup(bot)

    # Serverni ishga tushirish
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    logging.info("Bot starting in webhook mode...")
    try:
        import asyncio

        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by KeyboardInterrupt.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
