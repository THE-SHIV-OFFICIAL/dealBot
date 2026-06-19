import asyncio
import os
import uuid
import random
import re
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATION ---
try:
    API_ID = int(os.getenv("API_ID", "0"))
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    SUDO_USERS = [int(x) for x in os.getenv("SUDO_USERS", "").split()]
except ValueError:
    print("❌ CRITICAL ERROR: API_ID or OWNER_ID is incorrectly formatted in Heroku Config Vars.")
    exit()
except Exception:
    SUDO_USERS = []

API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URL = os.getenv("MONGO_URL", "")

def parse_env_chat(env_var):
    val = os.getenv(env_var, "").strip()
    if not val: return None
    try: return int(val)
    except ValueError: return val

# --- LOGGING SETUP ---
LOG_GROUP = parse_env_chat("LOG_GROUP")
LOG_GROUP_2 = parse_env_chat("LOG_GROUP_2")
VALID_LOG_CHATS = [c for c in [LOG_GROUP, LOG_GROUP_2] if c]

# Default Fallback Values
DEFAULT_UPI = "shivashish-kumar@ptyes"
DEFAULT_QR = "https://files.catbox.moe/hiyazb.jpg"
DEFAULT_START_IMG = "https://files.catbox.moe/hxp6b4.jpg"
DEFAULT_BTN_TEXT = "Premium Store"

# Text Templates
DEFAULT_START_TEXT = (
    "Hey, **{name}**\n\n"
    "🌟 **Welcome to Mahi Premium Store!**\n"
    "❤️ Trust Is Our First Priority!\n\n"
    "💳 Securely make payments using UPI!\n\n"
    "👇 **Click below to explore:**"
)

DEFAULT_CHANNEL_TEMPLATE = (
    "✅ **Verified Purchase!**\n\n"
    "🛒 Item: {item}\n"
    "📅 Plan: {plan}\n"
    "💰 Price: {price}\n\n"
    "🤖 **Buy via:** @{bot_username}"
)

ORDER_COMPLETE_TEXT = (
    "🎉 **Order Completed**\n\n"
    "Aapka order successfully deliver ho gaya hai!\n"
    "Agar koi issue ho, to turant humein DM karein — turant replacement milega.\n\n"
    "**Warranty Activation:**\n"
    "Please @preet_dealreview group me apna review karein aur uska screenshot humein bhejein.\n"
    "_No review screenshot = no warranty._\n\n"
    "> Enjoy your subscription ❤️\n"
    "❤️ Team @preet_deal_bot | @movie_x_update | @betabot_hub | @betabot_SUPPORT"
)

# --- MEMORY & STATES ---
USER_STATE = {}
SERVICES = {}
BOT_HOSTING = {}
TELEGRAM_ACCS = {}
SETTINGS = {}
ADMIN_LIST = list(set([OWNER_ID] + SUDO_USERS))
FORWARD_MAP = {} 

# Steps
ST_PHOTO = 1
ST_UTR = 2
ST_WAIT_EMAIL = 3
ST_WAIT_NUM = 4
ST_WAIT_OTP = 5
ST_ADMIN_TXT = 6
ST_ADMIN_GIVE_NUM = 7
ST_ADMIN_GIVE_OTP = 8

# Admin Edit States
ST_EDIT_INPUT = 10
ST_ADD_PLAN_LABEL = 11
ST_ADD_PLAN_PRICE = 12
ST_EDIT_SETTING_TEXT = 13
ST_ADD_SRV_NAME = 20
ST_ADD_SRV_TYPE = 21
ST_ADD_SRV_DESC = 22
ST_BROADCAST = 30
ST_SET_IMAGE = 40
ST_EDIT_CHANNEL_TEMPLATE = 50

# Bot Making & Hosting Edit States
ST_ADD_BOT_NAME = 60
ST_ADD_BOT_DESC = 61
ST_ADD_BOT_PLAN_LABEL = 62
ST_ADD_BOT_PLAN_PRICE = 63
ST_EDIT_BOT_INPUT = 64

# Telegram Edit States
ST_ADD_TG_NAME = 70
ST_ADD_TG_DESC = 71
ST_ADD_TG_PLAN_LABEL = 72
ST_ADD_TG_PLAN_PRICE = 73
ST_EDIT_TG_INPUT = 74

# --- RANDOM START STICKERS & EFFECTS ---
START_STICKERS = [
    "CAACAgUAAxkBAAFJgZ1qBGwx9Z9vW5BhG3dw0l1A5j4CyQACXRYAAuc-wVWs4--9DGlDKzsE",
    "CAACAgUAAxkBAAFKelNqEpxWO7Puzufo1iQiJ7wQCeC2TgACFSUAAtcjOFV-i8xuB1WKAzsE",
    "CAACAgUAAxkBAAFKelFqEpxJd70d9l15zijAieL5u0DRMwACiBwAAvJYAAFVqPwt3IyEx_s7BA",
    "CAACAgQAAxkBAAFKek9qEpxBZ6gVTWVdZtOz2buMI2LDrgACfhgAAji5eFOhuyuu8mKCLDsE",
    "CAACAgUAAxkBAAFKHl9qDSvjGaSMG6TS76wNuIeo2oyzrAAC2gQAAsmEqVUTv53n2G5gFDsE",
    "CAACAgUAAxkBAAFJgZ9qBGw3JfuXSHzy2b6iDYQWZ2bQUQACLwUAAmZV0VZ9oUejPkLcOjsE",
    "CAACAgQAAxkBAAFKHllqDSvVgtBMTpg8uBQqf1eAHFHP4AACBBIAAvAG2VFd6aEJ0tmFXDsE",
]

EFFECT_IDS = [5046509860389126442, 5107584321108051014, 5104841245755180586, 5159385139981059251]

def get_safe_photo(photo_url):
    if isinstance(photo_url, list): return random.choice(photo_url)
    elif isinstance(photo_url, str):
        if "," in photo_url: return random.choice(photo_url.split(","))
        return photo_url
    return "https://files.catbox.moe/n22tbs.jpg"

# --- DEFAULT TEXT ---
DESC_OTP = "• Activation via Mobile Number & OTP.\n• 100% Secure & Trusted."
DESC_INVITE = "• Subscription activated on your Email.\n• We will send an invite link."
DESC_IDPASS = "• We will provide Email & Password.\n• Login and enjoy."
DESC_HOTSTAR_PREM = (
    "• **We Provide the Number:** Admin will send you a registered Mobile Number.\n"
    "• **Easy Login:** Just enter that number in your App & request OTP here.\n"
    "• **Instant Access:** We give you the code, and you start watching! 🍿"
)

# --- DEFAULT DATA GENERATORS ---
DEFAULT_BOT_HOSTING = {
    "bot_dev": { "name": "🤖 Custom Bot Development", "desc": "Get your own Telegram Bot fully tailored to your needs.\n• High-quality clean code\n• Direct support from dev", "plans": [{"id": "b_basic", "label": "Basic Setup", "price": 499}, {"id": "b_adv", "label": "Advanced Bot", "price": 1499}]},
    "vps_hosting": { "name": "🖥️ VPS & Bot Hosting", "desc": "Keep your bot online 24/7 with zero downtime.\n• Fast & Reliable Server\n• Free setup assistance", "plans": [{"id": "v_1m", "label": "1 Month Hosting", "price": 150}, {"id": "v_3m", "label": "3 Months Hosting", "price": 400}]},
    "source_code": { "name": "⚙️ Premium Source Codes", "desc": "Buy premium python scripts & source codes.\n• Ready to deploy\n• Error free", "plans": [{"id": "sc_store", "label": "Store Bot Script", "price": 500}]}
}

DEFAULT_TELEGRAM_ACCS = {
    "fresh_session": { "name": "⚡ Fresh Session Accounts", "desc": "Fresh Telegram Accounts in .session + .json format.\nBest for Bulk adder & Bots.", "plans": [{"id": "tg_5acc", "label": "5 Accounts Pack", "price": 150}, {"id": "tg_10acc", "label": "10 Accounts Pack", "price": 280}]},
    "indian_num": { "name": "🇮🇳 Indian Number Accounts", "desc": "Telegram Accounts created on Fresh Indian (+91) Numbers.\nLogin via OTP string/code.", "plans": [{"id": "ind_1acc", "label": "1 Account", "price": 45}]}
}

DEFAULT_SERVICES_LIST = {
    "yt_prem": { "name": "YouTube Premium", "type": "invite", "desc": DESC_INVITE, "plans": [{"id": "1m", "label": "1 Month", "price": 35}]},
    "gemini": { "name": "Gemini AI", "type": "invite", "desc": DESC_INVITE, "plans": [{"id": "1m", "label": "1 Month", "price": 50}]},
    "hotstar_super": { "name": "Hotstar Super", "type": "otp", "desc": DESC_OTP, "plans": [{"id": "sup_1m", "label": "1 Month", "price": 60}]},
    "hotstar_prem": { "name": "Hotstar Premium", "type": "admin_otp", "desc": DESC_HOTSTAR_PREM, "plans": [{"id": "prem_1m", "label": "1 Month", "price": 79}, {"id": "prem_3m", "label": "3 Months", "price": 199}]},
    "sonyliv": { "name": "SonyLIV Premium", "type": "otp", "desc": DESC_OTP, "plans": [{"id": "1m", "label": "1 Month", "price": 60}]},
    "zee5": { "name": "Zee5 Premium", "type": "otp", "desc": DESC_OTP, "plans": [{"id": "1y", "label": "1 Year", "price": 199}]},
    "appletv": { "name": "Apple Tv", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "1m", "label": "1 Month", "price": 399}]},
    "canva": { "name": "Canva Premium", "type": "invite", "desc": DESC_INVITE, "plans": [{"id": "1m", "label": "1 Month", "price": 25}, {"id": "3m", "label": "3 Month", "price": 50}, {"id": "6m", "label": "6 Month", "price": 75}, {"id": "12m", "label": "12 Month", "price": 100}]},
    "apple_music": { "name": "Apple Music", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "6m", "label": "6 Months", "price": 399}]},
    "linkedin": { "name": "LinkedIn Career", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "6m", "label": "6 Months", "price": 299}]},
    "capcut": { "name": "CapCut Pro", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "1m", "label": "1 Month", "price": 299}]},
    "proton": { "name": "Proton VPN", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "1m", "label": "1 Month", "price": 299}]},
    "prime": { "name": "Prime Video", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "1m", "label": "1 Month", "price": 49}]},
    "adobe": { "name": "Adobe Creative Cloud", "type": "invite", "desc": DESC_INVITE, "plans": [{"id": "1m", "label": "1 Month", "price": 499}]},
    "ms365": { "name": "Microsoft 365", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "life", "label": "Lifetime", "price": 499}]},
    "gemini_pro": { "name": "Gemini Pro Full", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "1m", "label": "1 Month", "price": 99}]},
    "google_one": { "name": "Google One", "type": "invite", "desc": DESC_INVITE, "plans": [{"id": "1m", "label": "1 Month", "price": 49}]},
    "times_prime": { "name": "Times Prime", "type": "otp", "desc": DESC_OTP, "plans": [{"id": "1y", "label": "1 Year", "price": 199}]},
    "chatgpt": { "name": "ChatGpt", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "1m", "label": "1 Month", "price": 149}]},
    "surfshark": { "name": "Surfshark VPN", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "1m", "label": "1 Month", "price": 69}]},
    "octohide": { "name": "Octohide VPN", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "1m", "label": "1 Month", "price": 59}]},
    "crunchyroll": { "name": "Crunchyroll", "type": "std", "desc": DESC_IDPASS, "plans": [{"id": "1m", "label": "1 Month", "price": 49}, {"id": "3m", "label": "3 Month", "price": 99}, {"id": "6m", "label": "6 Month", "price": 149}, {"id": "12m", "label": "12 Month", "price": 199}]},
    "duolingo": { "name": "Duolingo (Super)", "type": "invite", "desc": DESC_INVITE, "plans": [{"id": "1y", "label": "1 Year", "price": 799}]}
}

DEFAULT_SETTINGS = {
    "terms": "📜 **Terms of Service**\n\n1. Refunds available only when you have submitted review as a proof or rating. \n2. Order processing takes 24 - 48 hrs. \n3. No refund available for telegram accounts or whatsapp accounts. \n4. We are not responsible for any kind of freezing or banning. \n5. In case of bots making or hosting we are not responsible for hacking account or freezing account.\n6. IT IS COMPULSARY TO JOIN - @betabot_hub to buy any thing or for any kind of refund👍🏻.",
    "help": "🆘 **Help & Support**\n\nContact Admin for support. \n\n@betabot_hub \n@betabot_support \n@preet_dealreview",
    "contact": f"📞 **Contact Us**\n\n• Owner: @sukoon_s",
    "maintenance": False,
    "banned_users": [],
    "admins": [OWNER_ID],
    "start_image": DEFAULT_START_IMG,
    "qr_image": DEFAULT_QR,
    "upi_id": DEFAULT_UPI,
    "start_btn_text": DEFAULT_BTN_TEXT,
    "proof_channel": "-1003842056667",
    "channel_template": DEFAULT_CHANNEL_TEMPLATE,
    "start_text": DEFAULT_START_TEXT,
    "btn1_text": "📢 Join Channel",
    "btn1_url": "https://t.me/",
    "btn2_text": "💬 Support Group",
    "btn2_url": "https://t.me/"
}

if not MONGO_URL:
    print("❌ Error: MONGO_URL variable missing hai!")
    exit()

mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["ShivStoreDB"]
col_services = db["services_data"]
col_bots = db["bot_hosting_data"]            
col_telegram_accs = db["telegram_data"] 
col_settings = db["settings_data"]
col_users = db["users_list"]

app = Client("ShivStore", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- DB HELPERS ---
async def save_services_to_db(data): await col_services.update_one({"_id": "main_store"}, {"$set": {"data": data}}, upsert=True)
async def save_bots_to_db(data): await col_bots.update_one({"_id": "bot_store"}, {"$set": {"data": data}}, upsert=True)
async def save_telegram_accs_to_db(data): await col_telegram_accs.update_one({"_id": "telegram_store"}, {"$set": {"data": data}}, upsert=True)
async def save_settings_to_db(data):
    global ADMIN_LIST
    await col_settings.update_one({"_id": "site_settings"}, {"$set": {"data": data}}, upsert=True)
    ADMIN_LIST = list(set(data.get("admins", [OWNER_ID]) + SUDO_USERS))
async def add_user_to_db(user_id): await col_users.update_one({"_id": user_id}, {"$set": {"active": True}}, upsert=True)
async def get_total_users(): return await col_users.count_documents({})

# --- KEYBOARDS (ORIGINAL PYROGRAM) ---
def get_start_keyboard():
    btn_txt = SETTINGS.get("start_btn_text", DEFAULT_BTN_TEXT).replace("🛒 ", "")
    b1_txt = SETTINGS.get("btn1_text", "📢 Channel")
    b1_url = SETTINGS.get("btn1_url", "https://t.me/")
    b2_txt = SETTINGS.get("btn2_text", "💬 Group")
    b2_url = SETTINGS.get("btn2_url", "https://t.me/")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔹 {btn_txt}", callback_data="open_shop")],
        [InlineKeyboardButton("ℹ️ Terms of Service", callback_data="terms")],
        [InlineKeyboardButton("⚠️ Contact", callback_data="contact"), InlineKeyboardButton("⚠️ Help", callback_data="help")],
        [InlineKeyboardButton(f"🔹 {b1_txt}", url=b1_url), InlineKeyboardButton(f"🔹 {b2_txt}", url=b2_url)]
    ])

def get_main_shop_keyboard():
    buttons = [[InlineKeyboardButton("🤖 Bot Making & Hosting 📂", callback_data="open_bots")], [InlineKeyboardButton("📱 Telegram Accounts 📂", callback_data="open_telegram_accs")]]
    all_keys = list(SERVICES.keys())
    for i in range(0, len(all_keys), 2):
        row = []
        k1 = all_keys[i]
        row.append(InlineKeyboardButton(f"🔹 {SERVICES[k1]['name']}", callback_data=f"srv|{k1}"))
        if i + 1 < len(all_keys):
            key2 = all_keys[i+1]
            row.append(InlineKeyboardButton(f"🔹 {SERVICES[key2]['name']}", callback_data=f"srv|{key2}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("❌ Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def get_bots_keyboard():
    btns = []
    all_keys = list(BOT_HOSTING.keys())
    for i in range(0, len(all_keys), 2):
        row = []
        k1 = all_keys[i]
        row.append(InlineKeyboardButton(f"{BOT_HOSTING[k1]['name']}", callback_data=f"bot_srv|{k1}"))
        if i + 1 < len(all_keys):
            k2 = all_keys[i+1]
            row.append(InlineKeyboardButton(f"{BOT_HOSTING[k2]['name']}", callback_data=f"bot_srv|{k2}"))
        btns.append(row)
    btns.append([InlineKeyboardButton("❌ Back to Store", callback_data="open_shop")])
    return InlineKeyboardMarkup(btns)

def get_telegram_accs_keyboard():
    btns = []
    all_keys = list(TELEGRAM_ACCS.keys())
    for i in range(0, len(all_keys), 2):
        row = []
        k1 = all_keys[i]
        row.append(InlineKeyboardButton(f"{TELEGRAM_ACCS[k1]['name']}", callback_data=f"tg_srv|{k1}"))
        if i + 1 < len(all_keys):
            k2 = all_keys[i+1]
            row.append(InlineKeyboardButton(f"{TELEGRAM_ACCS[k2]['name']}", callback_data=f"tg_srv|{k2}"))
        btns.append(row)
    btns.append([InlineKeyboardButton("❌ Back to Store", callback_data="open_shop")])
    return InlineKeyboardMarkup(btns)

def get_admin_dashboard():
    m_text = "🟢 Maint: OFF" if not SETTINGS.get("maintenance") else "🔴 Maint: ON"
    btns = [
        [InlineKeyboardButton("✅ Add Service", callback_data="add_service")],
        [InlineKeyboardButton("🤖 Manage Bots/Hosting", callback_data="manage_bots"), InlineKeyboardButton("📱 Manage Telegram", callback_data="manage_telegram_accs")],
        [InlineKeyboardButton("⚠️ Website Settings", callback_data="edit_settings")],
        [InlineKeyboardButton("🔹 Broadcast", callback_data="broadcast_msg"), InlineKeyboardButton(m_text, callback_data="toggle_maint")]
    ]
    keys = list(SERVICES.keys())
    for i in range(0, len(keys), 2):
        row = []
        k1 = keys[i]
        row.append(InlineKeyboardButton(f"✏️ {SERVICES[k1]['name']}", callback_data=f"edit|{k1}"))
        if i+1 < len(keys):
            k2 = keys[i+1]
            row.append(InlineKeyboardButton(f"✏️ {SERVICES[k2]['name']}", callback_data=f"edit|{k2}"))
        btns.append(row)
    return InlineKeyboardMarkup(btns)

# --- COMMANDS ---

@app.on_message(filters.command("id"))
async def show_id(client, message):
    await message.reply(f"🆔 **ID:** `{message.from_user.id}`")

@app.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def add_admin_cmd(client, message):
    try:
        if len(message.command) < 2: return await message.reply("Usage: `/addadmin 123`")
        new_id = int(message.command[1])
        current = SETTINGS.get("admins", [OWNER_ID])
        if new_id not in current:
            current.append(new_id)
            SETTINGS["admins"] = current
            await save_settings_to_db(SETTINGS)
            await message.reply(f"✅ User `{new_id}` is now Admin.")
    except: pass

@app.on_message(filters.command("deladmin") & filters.user(OWNER_ID))
async def del_admin_cmd(client, message):
    try:
        target_id = int(message.command[1])
        if target_id == OWNER_ID: return await message.reply("❌ Cannot remove Owner.")
        current = SETTINGS.get("admins", [OWNER_ID])
        if target_id in current:
            current.remove(target_id)
            SETTINGS["admins"] = current
            await save_settings_to_db(SETTINGS)
            await message.reply(f"✅ User `{target_id}` removed.")
    except: pass

@app.on_message(filters.command("admins") & filters.user(OWNER_ID))
async def list_admins(client, message):
    txt = "👮‍♂️ **Admins:**\n" + "\n".join([f"`{a}`" for a in SETTINGS.get("admins", [])])
    await message.reply(txt)

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    uid = message.from_user.id
    if uid in SETTINGS.get("banned_users", []): return
    await add_user_to_db(uid)
    
    if SETTINGS.get("maintenance") and uid not in ADMIN_LIST:
        await message.reply("🚧 **Store Closed.**")
        return
        
    uname = f"@{message.from_user.username}" if message.from_user.username else "No Username"
    start_log_text = (
        "🆕 **New User Started Bot!**\n\n"
        f"👤 **Name:** {message.from_user.first_name}\n"
        f"🔗 **Link:** {message.from_user.mention}\n"
        f"📛 **Username:** {uname}\n"
        f"🆔 **ID:** `{message.from_user.id}`"
    )
    for log_chat in VALID_LOG_CHATS:
        try: await client.send_message(log_chat, start_log_text)
        except Exception as e: print(f"Log Error for {log_chat}: {e}")
    
    loading_1 = await message.reply_text("<b>ᴌᴏᴀᴅɪɴɢ....</b>")
    await asyncio.sleep(0.3)
    await loading_1.edit_text("<b>ꜱᴛᴀʀᴛɪɴɢ..ʙᴀʙʏ.❤️❤️</b>")
    await asyncio.sleep(0.3)
    await loading_1.edit_text("<b>ɪ ᴀᴍ ᴀʟɪᴠᴇ ʙᴀʙʏ❤️😌🫣🫣</b>")
    await asyncio.sleep(0.5)
    await loading_1.edit_text("<b>BETA BOTS 🫣🫣.</b>")
    await asyncio.sleep(0.5)
    await loading_1.delete()

    try: await message.reply_sticker(random.choice(START_STICKERS))
    except: pass 
    
    start_img = SETTINGS.get("start_image", DEFAULT_START_IMG)
    safe_img = get_safe_photo(start_img)
    raw_text = SETTINGS.get("start_text", DEFAULT_START_TEXT)
    final_text = raw_text.replace("{name}", message.from_user.first_name).replace("{mention}", message.from_user.mention)
    eff_id = random.choice(EFFECT_IDS)

    try: await message.reply_photo(safe_img, caption=final_text, reply_markup=get_start_keyboard(), effect_id=eff_id)
    except:
        try: await message.reply_photo(safe_img, caption=final_text, reply_markup=get_start_keyboard())
        except: await message.reply_photo(DEFAULT_START_IMG, caption=final_text, reply_markup=get_start_keyboard())

@app.on_message(filters.command("admin"))
async def admin_panel_cmd(client, message):
    if message.from_user.id not in ADMIN_LIST: return
    users = await get_total_users()
    await message.reply_text(f"🛠 **Admin Dashboard**\n👥 Total Users: `{users}`", reply_markup=get_admin_dashboard())

@app.on_message(filters.command("ban"))
async def ban_user(client, message):
    if message.from_user.id not in ADMIN_LIST: return
    try:
        tid = int(message.command[1])
        if tid in ADMIN_LIST: return
        banned = SETTINGS.get("banned_users", [])
        if tid not in banned:
            banned.append(tid)
            SETTINGS["banned_users"] = banned
            await save_settings_to_db(SETTINGS)
            await message.reply(f"🚫 Banned `{tid}`")
    except: pass

@app.on_message(filters.command("unban"))
async def unban_user(client, message):
    if message.from_user.id not in ADMIN_LIST: return
    try:
        tid = int(message.command[1])
        banned = SETTINGS.get("banned_users", [])
        if tid in banned:
            banned.remove(tid)
            SETTINGS["banned_users"] = banned
            await save_settings_to_db(SETTINGS)
            await message.reply(f"✅ Unbanned `{tid}`")
    except: pass

# --- CALLBACKS ---
@app.on_callback_query()
async def callbacks(client, callback: CallbackQuery):
    data = callback.data
    uid = callback.from_user.id
    
    if uid not in ADMIN_LIST:
        if uid in SETTINGS.get("banned_users", []): return await callback.answer("🚫 Banned.", show_alert=True)
        if SETTINGS.get("maintenance"): return await callback.answer("🚧 Store Closed.", show_alert=True)

    if data == "main_menu":
        start_img = SETTINGS.get("start_image", DEFAULT_START_IMG)
        safe_img = get_safe_photo(start_img)
        raw_text = SETTINGS.get("start_text", DEFAULT_START_TEXT)
        final_text = raw_text.replace("{name}", callback.from_user.first_name).replace("{mention}", callback.from_user.mention)
        try: await callback.message.edit_media(InputMediaPhoto(safe_img, caption=final_text), reply_markup=get_start_keyboard())
        except: 
            await callback.message.delete()
            await client.send_photo(uid, safe_img, caption=final_text, reply_markup=get_start_keyboard())

    elif data == "open_shop": await callback.message.edit_caption("🛒 **Shiv Store**\nSelect a category or service below:", reply_markup=get_main_shop_keyboard())
    elif data == "open_bots": await callback.message.edit_caption("🤖 **Bot Making & Hosting**\n\nSelect a configuration to purchase:", reply_markup=get_bots_keyboard())
    elif data == "open_telegram_accs": await callback.message.edit_caption("📱 **Telegram Accounts**\n\nSelect a configuration to purchase:", reply_markup=get_telegram_accs_keyboard())
    
    elif data in ["terms", "help", "contact"]:
        text = SETTINGS.get(data, "Not Set")
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Back", callback_data="main_menu")]])
        try: await callback.message.edit_caption(caption=text, reply_markup=back_kb)
        except: await callback.message.edit_text(text=text, reply_markup=back_kb)

    # ADMIN
    if uid in ADMIN_LIST:
        if data == "toggle_maint":
            curr = SETTINGS.get("maintenance", False)
            SETTINGS["maintenance"] = not curr
            await save_settings_to_db(SETTINGS)
            await callback.message.edit_reply_markup(get_admin_dashboard())
            return

        elif data == "manage_bots":
            btns = [[InlineKeyboardButton("✅ Add Bot/Hosting Setup", callback_data="add_bot")]]
            for k, v in BOT_HOSTING.items(): btns.append([InlineKeyboardButton(f"{v['name']}", callback_data=f"ed_bot|{k}")])
            btns.append([InlineKeyboardButton("❌ Back", callback_data="adm_back")])
            await callback.message.edit_text("🤖 **Manage Bot Making & Hosting**", reply_markup=InlineKeyboardMarkup(btns))
            return

        elif data == "add_bot":
            USER_STATE[uid] = {"step": ST_ADD_BOT_NAME}
            await callback.message.edit_text("✍️ **Enter Name:**\n(e.g. 🤖 Custom Bot)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("ed_bot|"):
            key = data.split("|")[1]
            if key not in BOT_HOSTING: return
            btns = [[InlineKeyboardButton("🔹 Name", callback_data=f"ed_bfield|{key}|name"), InlineKeyboardButton("ℹ️ Desc", callback_data=f"ed_bfield|{key}|desc")], [InlineKeyboardButton("✅ Add Plan", callback_data=f"add_bplan|{key}")]]
            for plan in BOT_HOSTING[key]["plans"]: btns.append([InlineKeyboardButton(f"❌ Del: {plan['label']} (₹{plan['price']})", callback_data=f"del_bplan|{key}|{plan['id']}")])
            btns.append([InlineKeyboardButton("❌ DELETE ITEM", callback_data=f"del_bot|{key}")])
            btns.append([InlineKeyboardButton("⚠️ Back", callback_data="manage_bots")])
            await callback.message.edit_text(f"🤖 **Editing:** {BOT_HOSTING[key]['name']}", reply_markup=InlineKeyboardMarkup(btns))
            return

        elif data.startswith("ed_bfield|"):
            _, key, field = data.split("|")
            USER_STATE[uid] = {"step": ST_EDIT_BOT_INPUT, "key": key, "field": field}
            await callback.message.edit_text(f"✍️ **Enter New {field}:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("add_bplan|"):
            key = data.split("|")[1]
            USER_STATE[uid] = {"step": ST_ADD_BOT_PLAN_LABEL, "key": key}
            await callback.message.edit_text("✍️ **Enter Plan Name:**\n(e.g. 1 Month Server)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("del_bplan|"):
            _, key, plan_id = data.split("|")
            BOT_HOSTING[key]["plans"] = [p for p in BOT_HOSTING[key]["plans"] if p["id"] != plan_id]
            await save_bots_to_db(BOT_HOSTING)
            callback.data = f"ed_bot|{key}" 
            await callbacks(client, callback)
            return

        elif data.startswith("del_bot|"):
            key = data.split("|")[1]
            if key in BOT_HOSTING:
                del BOT_HOSTING[key]
                await save_bots_to_db(BOT_HOSTING)
                await callback.message.edit_text("✅ Deleted.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Back", callback_data="manage_bots")]]))
            return

        elif data == "manage_telegram_accs":
            btns = [[InlineKeyboardButton("✅ Add Telegram Config", callback_data="add_telegram_acc")]]
            for k, v in TELEGRAM_ACCS.items(): btns.append([InlineKeyboardButton(f"🔹 {v['name']}", callback_data=f"ed_tg|{k}")])
            btns.append([InlineKeyboardButton("❌ Back", callback_data="adm_back")])
            await callback.message.edit_text("📱 **Manage Telegram Categories**", reply_markup=InlineKeyboardMarkup(btns))
            return

        elif data == "add_telegram_acc":
            USER_STATE[uid] = {"step": ST_ADD_TG_NAME}
            await callback.message.edit_text("✍️ **Enter Config Name:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("ed_tg|"):
            key = data.split("|")[1]
            if key not in TELEGRAM_ACCS: return
            btns = [[InlineKeyboardButton("🔹 Name", callback_data=f"ed_tgfield|{key}|name"), InlineKeyboardButton("ℹ️ Desc", callback_data=f"ed_tgfield|{key}|desc")], [InlineKeyboardButton("✅ Add Plan", callback_data=f"add_tgplan|{key}")]]
            for plan in TELEGRAM_ACCS[key]["plans"]: btns.append([InlineKeyboardButton(f"❌ Del: {plan['label']} (₹{plan['price']})", callback_data=f"del_tgplan|{key}|{plan['id']}")])
            btns.append([InlineKeyboardButton("❌ DELETE CATEGORY", callback_data=f"del_tg|{key}")])
            btns.append([InlineKeyboardButton("⚠️ Back", callback_data="manage_telegram_accs")])
            await callback.message.edit_text(f"📱 **Editing:** {TELEGRAM_ACCS[key]['name']}", reply_markup=InlineKeyboardMarkup(btns))
            return

        elif data.startswith("ed_tgfield|"):
            _, key, field = data.split("|")
            USER_STATE[uid] = {"step": ST_EDIT_TG_INPUT, "key": key, "field": field}
            await callback.message.edit_text(f"✍️ **Enter New {field}:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("add_tgplan|"):
            key = data.split("|")[1]
            USER_STATE[uid] = {"step": ST_ADD_TG_PLAN_LABEL, "key": key}
            await callback.message.edit_text("✍️ **Enter Plan Name:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("del_tgplan|"):
            _, key, plan_id = data.split("|")
            TELEGRAM_ACCS[key]["plans"] = [p for p in TELEGRAM_ACCS[key]["plans"] if p["id"] != plan_id]
            await save_telegram_accs_to_db(TELEGRAM_ACCS)
            callback.data = f"ed_tg|{key}" 
            await callbacks(client, callback)
            return

        elif data.startswith("del_tg|"):
            key = data.split("|")[1]
            if key in TELEGRAM_ACCS:
                del TELEGRAM_ACCS[key]
                await save_telegram_accs_to_db(TELEGRAM_ACCS)
                await callback.message.edit_text("✅ Deleted.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Back", callback_data="manage_telegram_accs")]]))
            return

        elif data == "broadcast_msg":
            USER_STATE[uid] = {"step": ST_BROADCAST}
            await callback.message.edit_text("📢 **Send Message:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data == "edit_settings":
            btns = [
                [InlineKeyboardButton("Terms", callback_data="ed_set|terms"), InlineKeyboardButton("Help", callback_data="ed_set|help")],
                [InlineKeyboardButton("Contact", callback_data="ed_set|contact"), InlineKeyboardButton("Set UPI", callback_data="ed_set|upi_id")],
                [InlineKeyboardButton("Btn Name", callback_data="ed_set|start_btn_text"), InlineKeyboardButton("Channel ID", callback_data="ed_set|proof_channel")],
                [InlineKeyboardButton("Start Text", callback_data="ed_set|start_text"), InlineKeyboardButton("Channel Template", callback_data="ed_set|channel_template")], 
                [InlineKeyboardButton("Btn 1 Name", callback_data="ed_set|btn1_text"), InlineKeyboardButton("Btn 1 URL", callback_data="ed_set|btn1_url")],
                [InlineKeyboardButton("Btn 2 Name", callback_data="ed_set|btn2_text"), InlineKeyboardButton("Btn 2 URL", callback_data="ed_set|btn2_url")],
                [InlineKeyboardButton("Start Image", callback_data="set_img|start_image"), InlineKeyboardButton("QR Image", callback_data="set_img|qr_image")],
                [InlineKeyboardButton("❌ Back", callback_data="adm_back")]
            ]
            await callback.message.edit_text("⚙️ **Settings**", reply_markup=InlineKeyboardMarkup(btns))
            return

        elif data.startswith("set_img|"):
            key = data.split("|")[1]
            USER_STATE[uid] = {"step": ST_SET_IMAGE, "key": key}
            await callback.message.edit_text("📸 **Send New Photo:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("ed_set|"):
            key = data.split("|")[1]
            if key == "channel_template":
                USER_STATE[uid] = {"step": ST_EDIT_CHANNEL_TEMPLATE}
                await callback.message.edit_text("📝 **Edit Channel Template**\nVariables: `{item}`, `{plan}`, `{price}`, `{bot_username}`\n👇 Send new template:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            elif key == "start_text":
                USER_STATE[uid] = {"step": ST_EDIT_SETTING_TEXT, "key": key}
                await callback.message.edit_text("📝 **Edit Start Text**\nVariables: `{name}`, `{mention}`\n👇 Send new text:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            else:
                USER_STATE[uid] = {"step": ST_EDIT_SETTING_TEXT, "key": key}
                curr = SETTINGS.get(key, "Not Set")
                await callback.message.edit_text(f"✍️ **Editing: {key}**\n\nCurrent: `{curr}`\n\n👇 **Send New Value:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data == "add_service":
            USER_STATE[uid] = {"step": ST_ADD_SRV_NAME}
            await callback.message.edit_text("✍️ **Enter Service Name:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("sel_type|"):
            srv_type = data.split("|")[1]
            USER_STATE[uid]["type"] = srv_type
            USER_STATE[uid]["step"] = ST_ADD_SRV_DESC
            await callback.message.edit_text("✍️ **Enter Description:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("edit|"):
            key = data.split("|")[1]
            if key not in SERVICES: return await callback.answer("Not found", show_alert=True)
            srv = SERVICES[key]
            btns = [[InlineKeyboardButton("🔹 Name", callback_data=f"ed_field|{key}|name"), InlineKeyboardButton("ℹ️ Desc", callback_data=f"ed_field|{key}|desc")], [InlineKeyboardButton("✅ Add Plan", callback_data=f"add_plan|{key}")]]
            for plan in srv["plans"]: btns.append([InlineKeyboardButton(f"❌ Del: {plan['label']} (₹{plan['price']})", callback_data=f"del_plan|{key}|{plan['id']}")])
            btns.append([InlineKeyboardButton("❌ DELETE SERVICE", callback_data=f"del_srv|{key}")])
            btns.append([InlineKeyboardButton("⚠️ Back", callback_data="adm_back")])
            await callback.message.edit_text(f"🔧 **Editing:** {srv['name']}", reply_markup=InlineKeyboardMarkup(btns))
            return

        elif data == "adm_back":
            await callback.message.edit_text("🛠 **Admin Dashboard**", reply_markup=get_admin_dashboard())
            return

        elif data.startswith("ed_field|"):
            _, key, field = data.split("|")
            USER_STATE[uid] = {"step": ST_EDIT_INPUT, "key": key, "field": field}
            await callback.message.edit_text(f"✍️ **Enter New {field}:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("del_srv|"):
            key = data.split("|")[1]
            if key in SERVICES:
                del SERVICES[key]
                await save_services_to_db(SERVICES)
                await callback.message.edit_text("🗑 **Service Deleted.**", reply_markup=get_admin_dashboard())
            return

        elif data.startswith("add_plan|"):
            key = data.split("|")[1]
            USER_STATE[uid] = {"step": ST_ADD_PLAN_LABEL, "key": key}
            await callback.message.edit_text("✍️ **Enter Plan Name:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]))
            return

        elif data.startswith("del_plan|"):
            _, key, plan_id = data.split("|")
            SERVICES[key]["plans"] = [p for p in SERVICES[key]["plans"] if p["id"] != plan_id]
            await save_services_to_db(SERVICES)
            callback.data = f"edit|{key}"
            await callbacks(client, callback)
            return

        elif data == "cancel_edit":
            if uid in USER_STATE: del USER_STATE[uid]
            await callback.message.edit_text("❌ Cancelled.", reply_markup=get_admin_dashboard())
            return

    # USER SECTIONS
    if data.startswith("srv|"):
        key = data.split("|")[1]
        if key not in SERVICES: return await callback.answer("Unavailable", show_alert=True)
        srv = SERVICES[key]
        if not srv["plans"]: return await callback.answer("Coming Soon", show_alert=True)
        btns = []
        for plan in srv["plans"]: btns.append([InlineKeyboardButton(f"🔹 {plan['label']} - ₹{plan['price']}", callback_data=f"pay|{key}|{plan['id']}")])
        btns.append([InlineKeyboardButton("❌ Back", callback_data="open_shop")])
        await callback.message.edit_caption(f"**{srv['name']}**\n\n{srv['desc']}\n\n👇 **Select duration:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("bot_srv|"):
        key = data.split("|")[1]
        if key not in BOT_HOSTING: return await callback.answer("Removed", show_alert=True)
        bot_item = BOT_HOSTING[key]
        if not bot_item.get("plans"): return await callback.answer("No plans", show_alert=True)
        btns = []
        for plan in bot_item["plans"]: btns.append([InlineKeyboardButton(f"🔹 {plan['label']} - ₹{plan['price']}", callback_data=f"pay|{key}|{plan['id']}")])
        btns.append([InlineKeyboardButton("❌ Back", callback_data="open_bots")])
        await callback.message.edit_caption(f"**{bot_item['name']}**\n\n{bot_item.get('desc', '')}\n\n👇 **Select Plan:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("tg_srv|"):
        key = data.split("|")[1]
        if key not in TELEGRAM_ACCS: return await callback.answer("Config Removed", show_alert=True)
        tg_acc = TELEGRAM_ACCS[key]
        if not tg_acc.get("plans"): return await callback.answer("No configurations", show_alert=True)
        btns = []
        for plan in tg_acc["plans"]: btns.append([InlineKeyboardButton(f"🔹 {plan['label']} - ₹{plan['price']}", callback_data=f"pay|{key}|{plan['id']}")])
        btns.append([InlineKeyboardButton("❌ Back", callback_data="open_telegram_accs")])
        await callback.message.edit_caption(f"**{tg_acc['name']}**\n\n{tg_acc.get('desc', '')}\n\n👇 **Select Package:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("pay|"):
        key = data.split("|")[1]
        plan_id = data.split("|")[2]
        
        if key in SERVICES: srv = SERVICES[key]
        elif key in BOT_HOSTING: srv = BOT_HOSTING[key]
        elif key in TELEGRAM_ACCS: srv = TELEGRAM_ACCS[key]
        else: return await callback.answer("Unavailable", show_alert=True)
        
        try: plan = next(p for p in srv["plans"] if p["id"] == plan_id)
        except: return await callback.answer("Error", show_alert=True)

        upi_val = SETTINGS.get("upi_id", DEFAULT_UPI)
        qr_img = SETTINGS.get("qr_image", DEFAULT_QR)
        text = (f"💳 **Place Your Order**\n\nService: **{srv['name']}**\nPlan: **{plan['label']}**\nAmount: **₹{plan['price']}**\nOrder ID: `SILENT{uid}X{plan_id}`\n\n⏰ Pay within 10 mins.\n👇 **Pay via UPI:**\n`{upi_val}`")
        USER_STATE[uid] = {"step": ST_PHOTO, "key": key, "plan_id": plan_id}
        btns = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Submit Proof", callback_data="ask_proof")],[InlineKeyboardButton("❌ Back", callback_data="open_shop")]])
        try: await callback.message.edit_media(InputMediaPhoto(qr_img, caption=text), reply_markup=btns)
        except: await callback.message.edit_media(InputMediaPhoto(DEFAULT_QR, caption=text), reply_markup=btns)

    elif data == "ask_proof":
        await callback.message.edit_caption("📸 **Upload Payment Screenshot**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]))

    elif data == "cancel":
        if uid in USER_STATE: del USER_STATE[uid]
        await callback.message.delete()
        await client.send_message(uid, "❌ Cancelled.", reply_markup=get_start_keyboard())

    elif data.startswith("usr_req_otp"):
        await callback.answer("Requesting...", show_alert=False)
        for admin in ADMIN_LIST:
            try: await client.send_message(admin, f"🔔 **OTP REQ**\nUser: {callback.from_user.mention}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Give OTP", callback_data=f"adm_give_otp|{uid}")]]))
            except: pass
        await callback.message.edit_text("⏳ **Waiting for OTP...**")

    # FULFILLMENT
    if uid in ADMIN_LIST and data.startswith("adm_"):
        if "|" not in data: return
        action = data.split("|")[0]
        try: target_uid = int(data.split("|")[1])
        except: return

        if action in ["adm_inv", "adm_std", "adm_otp", "adm_give_num"]:
            proof_channel = SETTINGS.get("proof_channel")
            if proof_channel:
                try:
                    orig = callback.message.caption or ""
                    ival="Unknown"; pval="Unknown"; prval="Unknown"
                    for line in orig.split("\n"):
                        if "🛒" in line: ival = line.split(":", 1)[1].strip()
                        if "📅" in line: pval = line.split(":", 1)[1].strip()
                        if "💰" in line: prval = line.split(":", 1)[1].strip()
                    tpl = SETTINGS.get("channel_template", DEFAULT_CHANNEL_TEMPLATE)
                    final = tpl.format(item=ival, plan=pval, price=prval, bot_username=app.me.username)
                    await client.copy_message(chat_id=int(proof_channel), from_chat_id=uid, message_id=callback.message.id, caption=final)
                except Exception as e: print(f"Channel Err: {e}")

        if action == "adm_inv":
            await client.send_message(target_uid, f"✅ **Invite Sent.**\n\n{ORDER_COMPLETE_TEXT}")
            await callback.edit_message_caption("✅ **Invite Sent.**")
        elif action == "adm_std":
            USER_STATE[uid] = {"step": ST_ADMIN_TXT, "target": target_uid}
            await callback.edit_message_caption("✍️ **Enter Fulfillment Info/Data:**")
        elif action == "adm_otp": 
            await client.send_message(target_uid, "✅ **Accepted!**\nSend Mobile Number.")
            USER_STATE[target_uid] = {"step": ST_WAIT_NUM}
            await callback.edit_message_caption("⏳ **Waiting for Num...**")
        elif action == "adm_give_num": 
            USER_STATE[uid] = {"step": ST_ADMIN_GIVE_NUM, "target": target_uid}
            await callback.edit_message_caption("✍️ **Enter Mobile Num:**")
        elif action == "adm_give_otp": 
            USER_STATE[uid] = {"step": ST_ADMIN_GIVE_OTP, "target": target_uid}
            await client.send_message(uid, "✍️ **Enter OTP:**")
            await callback.answer()
        elif action == "adm_reqotp": 
            await client.send_message(target_uid, "🔔 **Send OTP.**")
            USER_STATE[target_uid] = {"step": ST_WAIT_OTP}
            await callback.edit_message_caption("⏳ **Waiting for OTP...**")
        elif action == "adm_rej":
            await client.send_message(target_uid, "❌ **Payment Rejected.**")
            await callback.edit_message_caption("❌ **Rejected.**")


# --- MODULAR BOT DIRECT REPLY SYSTEM ---
if VALID_LOG_CHATS:
    @app.on_message(filters.chat(VALID_LOG_CHATS) & filters.reply)
    async def admin_direct_reply(client, message):
        replied_msg = message.reply_to_message
        if not replied_msg: return
        
        target_uid = None
        
        # Method 1: Extraction from Profile Card
        if replied_msg.text and "🆔 **ID:** `" in replied_msg.text:
            try: target_uid = int(replied_msg.text.split("🆔 **ID:** `")[1].split("`")[0])
            except: pass
            
        # Method 2: Fallback memory tracking
        elif replied_msg.id in FORWARD_MAP:
            target_uid = FORWARD_MAP[replied_msg.id]
            
        # Method 3: Telegram Native Forward track
        elif replied_msg.forward_from:
            target_uid = replied_msg.forward_from.id

        if target_uid:
            try:
                await client.copy_message(target_uid, from_chat_id=message.chat.id, message_id=message.id)
                await message.reply_text("✅ **Reply Sent to User!**", quote=True)
            except Exception as e:
                await message.reply_text(f"❌ **Failed to send:** {e}", quote=True)


# --- MAIN MESSAGE HANDLER ---
@app.on_message(filters.private & ~filters.command(["start", "id", "admin", "addadmin", "deladmin", "admins", "ban", "unban"]))
async def main_message_handler(client, message):
    uid = message.from_user.id

    # 1. CHECK IF USER/ADMIN IS IN A STATE
    if uid in USER_STATE:
        state = USER_STATE[uid]
        step = state.get("step")

        if uid in ADMIN_LIST:
            if step == ST_SET_IMAGE:
                if not message.photo: return await message.reply("⚠️ Photo needed.")
                SETTINGS[state["key"]] = message.photo.file_id
                await save_settings_to_db(SETTINGS)
                del USER_STATE[uid]
                await message.reply("✅ Saved!", reply_markup=get_admin_dashboard())
                return
            if step == ST_BROADCAST:
                await message.reply("📢 **Broadcasting...**")
                count = 0
                async for user in col_users.find():
                    try:
                        await message.copy(user["_id"])
                        count += 1
                        await asyncio.sleep(0.1)
                    except: pass
                del USER_STATE[uid]
                await message.reply(f"✅ **Sent to {count} users.**", reply_markup=get_admin_dashboard())
                return
            if step == ST_ADD_SRV_NAME:
                USER_STATE[uid]["name"] = message.text
                USER_STATE[uid]["step"] = ST_ADD_SRV_TYPE
                btns = [[InlineKeyboardButton("Standard OTP", callback_data="sel_type|otp")], [InlineKeyboardButton("Admin OTP", callback_data="sel_type|admin_otp")], [InlineKeyboardButton("Invite", callback_data="sel_type|invite")], [InlineKeyboardButton("ID/Pass", callback_data="sel_type|std")]]
                await message.reply("⚙️ **Select Type**", reply_markup=InlineKeyboardMarkup(btns))
                return
            if step == ST_ADD_SRV_DESC:
                new_key = f"srv_{uuid.uuid4().hex[:6]}"
                SERVICES[new_key] = {"name": state["name"], "type": state["type"], "desc": message.text, "plans": []}
                await save_services_to_db(SERVICES)
                del USER_STATE[uid]
                await message.reply("✅ **Added!**", reply_markup=get_admin_dashboard())
                return
            if step == ST_EDIT_INPUT:
                key = state["key"]
                if state["field"] == "name": SERVICES[key]["name"] = message.text
                elif state["field"] == "desc": SERVICES[key]["desc"] = message.text
                await save_services_to_db(SERVICES)
                del USER_STATE[uid]
                await message.reply("✅ Updated!", reply_markup=get_admin_dashboard())
                return
            if step == ST_EDIT_CHANNEL_TEMPLATE:
                SETTINGS["channel_template"] = message.text
                await save_settings_to_db(SETTINGS)
                del USER_STATE[uid]
                await message.reply("✅ Saved!", reply_markup=get_admin_dashboard())
                return
            if step == ST_EDIT_SETTING_TEXT:
                key = state["key"]
                if key == "proof_channel":
                    try: int(message.text)
                    except: return await message.reply("⚠️ Invalid ID.")
                SETTINGS[key] = message.text
                await save_settings_to_db(SETTINGS)
                del USER_STATE[uid]
                await message.reply(f"✅ **{key} Updated!**", reply_markup=get_admin_dashboard())
                return
            if step == ST_ADD_PLAN_LABEL:
                USER_STATE[uid]["label"] = message.text
                USER_STATE[uid]["step"] = ST_ADD_PLAN_PRICE
                await message.reply("✍️ **Enter Price:**")
                return
            if step == ST_ADD_PLAN_PRICE:
                if not message.text.isdigit(): return await message.reply("⚠️ Number only.")
                SERVICES[state["key"]]["plans"].append({"id": uuid.uuid4().hex[:6], "label": state["label"], "price": int(message.text)})
                await save_services_to_db(SERVICES)
                del USER_STATE[uid]
                await message.reply("✅ Plan Added!", reply_markup=get_admin_dashboard())
                return

            if step == ST_ADD_BOT_NAME:
                USER_STATE[uid]["name"] = message.text
                USER_STATE[uid]["step"] = ST_ADD_BOT_DESC
                await message.reply("✍️ **Enter Description:**")
                return
            if step == ST_ADD_BOT_DESC:
                USER_STATE[uid]["desc"] = message.text
                USER_STATE[uid]["step"] = ST_ADD_BOT_PLAN_LABEL
                await message.reply("✍️ **Enter Plan Name:**")
                return
            if step == ST_ADD_BOT_PLAN_LABEL:
                USER_STATE[uid]["label"] = message.text
                USER_STATE[uid]["step"] = ST_ADD_BOT_PLAN_PRICE
                await message.reply("✍️ **Enter Price:**")
                return
            if step == ST_ADD_BOT_PLAN_PRICE:
                if not message.text.isdigit(): return await message.reply("⚠️ Number only.")
                new_key = f"bot_{uuid.uuid4().hex[:4]}"
                if "name" in state: BOT_HOSTING[new_key] = {"name": state["name"], "desc": state["desc"], "plans": [{"id": uuid.uuid4().hex[:6], "label": state["label"], "price": int(message.text)}]}
                elif "key" in state: BOT_HOSTING[state["key"]]["plans"].append({"id": uuid.uuid4().hex[:6], "label": state["label"], "price": int(message.text)})
                await save_bots_to_db(BOT_HOSTING)
                del USER_STATE[uid]
                await message.reply("✅ Bot Setup Saved!", reply_markup=get_admin_dashboard())
                return
            if step == ST_EDIT_BOT_INPUT:
                if state["field"] == "name": BOT_HOSTING[state["key"]]["name"] = message.text
                elif state["field"] == "desc": BOT_HOSTING[state["key"]]["desc"] = message.text
                await save_bots_to_db(BOT_HOSTING)
                del USER_STATE[uid]
                await message.reply("✅ Updated!", reply_markup=get_admin_dashboard())
                return

            if step == ST_ADD_TG_NAME:
                USER_STATE[uid]["name"] = message.text
                USER_STATE[uid]["step"] = ST_ADD_TG_DESC
                await message.reply("✍️ **Enter Description:**")
                return
            if step == ST_ADD_TG_DESC:
                USER_STATE[uid]["desc"] = message.text
                USER_STATE[uid]["step"] = ST_ADD_TG_PLAN_LABEL
                await message.reply("✍️ **Enter Plan/Pack Name:**")
                return
            if step == ST_ADD_TG_PLAN_LABEL:
                USER_STATE[uid]["label"] = message.text
                USER_STATE[uid]["step"] = ST_ADD_TG_PLAN_PRICE
                await message.reply("✍️ **Enter Price:**")
                return
            if step == ST_ADD_TG_PLAN_PRICE:
                if not message.text.isdigit(): return await message.reply("⚠️ Number only.")
                new_key = f"tg_{uuid.uuid4().hex[:4]}"
                if "name" in state: TELEGRAM_ACCS[new_key] = {"name": state["name"], "desc": state["desc"], "plans": [{"id": uuid.uuid4().hex[:6], "label": state["label"], "price": int(message.text)}]}
                elif "key" in state: TELEGRAM_ACCS[state["key"]]["plans"].append({"id": uuid.uuid4().hex[:6], "label": state["label"], "price": int(message.text)})
                await save_telegram_accs_to_db(TELEGRAM_ACCS)
                del USER_STATE[uid]
                await message.reply("✅ Config Saved!", reply_markup=get_admin_dashboard())
                return
            if step == ST_EDIT_TG_INPUT:
                if state["field"] == "name": TELEGRAM_ACCS[state["key"]]["name"] = message.text
                elif state["field"] == "desc": TELEGRAM_ACCS[state["key"]]["desc"] = message.text
                await save_telegram_accs_to_db(TELEGRAM_ACCS)
                del USER_STATE[uid]
                await message.reply("✅ Updated!", reply_markup=get_admin_dashboard())
                return

            if "target" in state:
                target_uid = state["target"]
                if step == ST_ADMIN_TXT:
                    if message.text:
                        await client.send_message(target_uid, f"✅ **Delivered!**\n\n`{message.text}`\n\n{ORDER_COMPLETE_TEXT}")
                        await message.reply("✅ Sent.")
                    else: return await message.reply("⚠️ Please send text.")
                elif step == ST_ADMIN_GIVE_NUM:
                    if message.text:
                        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔹 🔓 Request OTP", callback_data="usr_req_otp")]])
                        await client.send_message(target_uid, f"✅ **Login Num:** `{message.text}`", reply_markup=btn)
                        await message.reply("✅ Sent.")
                    else: return
                elif step == ST_ADMIN_GIVE_OTP:
                    if message.text:
                        await client.send_message(target_uid, f"🔑 **OTP:** `{message.text}`\n\n{ORDER_COMPLETE_TEXT}")
                        await message.reply("✅ Sent.")
                    else: return
                del USER_STATE[uid]
                return

        # --- USER STATE HANDLING ---
        if step == ST_PHOTO:
            if message.photo:
                state["pid_proof"] = message.photo.file_id
                state["mention"] = message.from_user.mention
                state["step"] = ST_UTR
                await message.reply("📝 **Received.** Type UTR:")
            else: await message.reply("⚠️ Please send a valid payment screenshot.")
            return

        if step == ST_UTR:
            if message.text:
                state["utr"] = message.text
                key = state["key"]
                
                if key in SERVICES: srv_type = SERVICES[key]["type"]
                else: srv_type = "std"

                if srv_type == "invite":
                    state["step"] = ST_WAIT_EMAIL
                    await message.reply("📧 **Enter Email:**")
                else:
                    await send_proof_to_admin(client, uid, state)
                    await message.reply("✅ **Submitted!**")
                    del USER_STATE[uid] # Hanging bug is fixed here! It deletes state successfully.
            else: await message.reply("⚠️ Please send your UTR text.")
            return

        if step == ST_WAIT_EMAIL:
            if message.text:
                state["email"] = message.text
                await send_proof_to_admin(client, uid, state)
                await message.reply("✅ **Submitted!**")
                del USER_STATE[uid]
            return

        if step == ST_WAIT_NUM:
            if message.text:
                for admin in ADMIN_LIST:
                    try: await client.send_message(admin, f"📱 **User Num:** `{message.text}`\nUser: {uid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Request OTP", callback_data=f"adm_reqotp|{uid}")]]))
                    except: pass
                await message.reply("✅ Sent.")
            return

        if step == ST_WAIT_OTP:
            if message.text:
                for admin in ADMIN_LIST:
                    try: await client.send_message(admin, f"🔑 **OTP:** `{message.text}`\nUser: {uid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm", callback_data=f"adm_suc|{uid}")]]))
                    except: pass
                await message.reply("✅ Sent.")
                del USER_STATE[uid]
            return

    # 2. LOG NORMAL USER MESSAGES (MODULAR SYSTEM) - For both Logger groups
    if message.from_user and uid not in ADMIN_LIST:
        for log_chat in VALID_LOG_CHATS:
            try:
                # Forward user's message to log channels/groups
                fw = await message.forward(log_chat)
                FORWARD_MAP[fw.id] = uid
                
                uname = f"@{message.from_user.username}" if message.from_user.username else "No Username"
                log_text = (
                    f"📩 **New Message Received**\n\n"
                    f"👤 **Name:** {message.from_user.first_name}\n"
                    f"🔗 **Link:** {message.from_user.mention}\n"
                    f"📛 **Username:** {uname}\n"
                    f"🆔 **ID:** `{message.from_user.id}`\n\n"
                    f"💡 _Reply to this message to send a direct reply to the user._"
                )
                await client.send_message(log_chat, log_text, reply_to_message_id=fw.id)
            except Exception as e:
                print(f"Log Error for {log_chat}: {e}")

async def send_proof_to_admin(client, uid, state):
    key = state["key"]
    if key in SERVICES:
        srv = SERVICES[key]
        try:
            plan = next(p for p in srv["plans"] if p["id"] == state["plan_id"])
            name, price, label, srv_type = srv["name"], plan["price"], plan["label"], srv["type"]
        except: return
    elif key in BOT_HOSTING:
        srv = BOT_HOSTING[key]
        try:
            plan = next(p for p in srv["plans"] if p["id"] == state["plan_id"])
            name, price, label, srv_type = srv["name"], plan["price"], plan["label"], "std"
        except: return
    elif key in TELEGRAM_ACCS:
        srv = TELEGRAM_ACCS[key]
        try:
            plan = next(p for p in srv["plans"] if p["id"] == state["plan_id"])
            name, price, label, srv_type = srv["name"], plan["price"], plan["label"], "std"
        except: return
    else: return

    user_link = state.get("mention", f"User {uid}")
    caption = (f"🚨 **NEW ORDER** 🚨\n👤 {user_link}\n🛒 {name}\n📅 {label}\n💰 ₹{price}\n🧾 `{state['utr']}`")
    btns = []
    
    if srv_type == "invite": btns.append([InlineKeyboardButton("✅ Invite", callback_data=f"adm_inv|{uid}")])
    elif srv_type == "otp": btns.append([InlineKeyboardButton("✅ Approve", callback_data=f"adm_otp|{uid}")])
    elif srv_type == "admin_otp": btns.append([InlineKeyboardButton("✅ Approve", callback_data=f"adm_give_num|{uid}")])
    else: btns.append([InlineKeyboardButton("✅ Approve", callback_data=f"adm_std|{uid}")])
    btns.append([InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej|{uid}")])
    
    for admin in ADMIN_LIST:
        try:
            msg = await client.send_photo(admin, state["pid_proof"], caption=caption, reply_markup=InlineKeyboardMarkup(btns))
            await msg.pin()
        except: pass

async def main():
    global SERVICES, SETTINGS, ADMIN_LIST, BOT_HOSTING, TELEGRAM_ACCS
    await app.start()
    print("🔄 MongoDB Connecting...")
    
    doc = await col_services.find_one({"_id": "main_store"})
    if doc: SERVICES = doc["data"]
    else:
        SERVICES = DEFAULT_SERVICES_LIST
        await col_services.insert_one({"_id": "main_store", "data": SERVICES})
    
    doc_bots = await col_bots.find_one({"_id": "bot_store"})
    if doc_bots: BOT_HOSTING = doc_bots["data"]
    else:
        BOT_HOSTING = DEFAULT_BOT_HOSTING
        await col_bots.insert_one({"_id": "bot_store", "data": BOT_HOSTING})
        
    doc_tg = await col_telegram_accs.find_one({"_id": "telegram_store"})
    if doc_tg: TELEGRAM_ACCS = doc_tg["data"]
    else:
        TELEGRAM_ACCS = DEFAULT_TELEGRAM_ACCS
        await col_telegram_accs.insert_one({"_id": "telegram_store", "data": TELEGRAM_ACCS})

    doc_set = await col_settings.find_one({"_id": "site_settings"})
    if doc_set:
        SETTINGS = doc_set["data"]
        ADMIN_LIST = list(set(SETTINGS.get("admins", [OWNER_ID]) + SUDO_USERS))
    else:
        SETTINGS = DEFAULT_SETTINGS
        await col_settings.insert_one({"_id": "site_settings", "data": SETTINGS})

    print("✅ Ready!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
