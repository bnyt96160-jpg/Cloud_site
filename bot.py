import os
import random
import string
import re
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# تنظیمات لاگ برای بررسی وضعیت ربات در کنسول
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# توکن ربات و آیدی عددی ادمین
# می‌تونی مستقیم اینجا بذاری یا توی بخش Environment Variables هاست تعریف کنی
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))  # آیدی عددی تلگرام خودت رو جایگزین کن
# اطلاعات حساب بانکی و پشتیبانی
CARD_NUMBER = "6219861858158784"
CARD_HOLDER = "علیرضا نوروزی"
SUPPORT_ID = "@Mrbottelegram88"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# وب‌سرور سبک برای اینکه سایت‌هایی مثل Render.com به خاطر پورت به ربات گیر ندن و ۲۴ ساعته روشن بمونه
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")
    def log_message(self, format, *args):
        return

def start_keep_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    logging.info(f"Keep-alive web server started on port {port}")
    server.serve_forever()

# لیست محصولات و قیمت‌ها (به راحتی می‌تونی قیمت سایت و ممبر رو اینجا ویرایش کنی)
PRODUCTS = {
    "bot": {"name": "🤖 ساخت بات تلگرام", "price": "۱۲۵,۰۰۰ تومان"},
    "site": {"name": "🌐 طراحی سایت (پارس‌پک)", "price": "محاسبه خودکار با ماشین‌حساب"},
    "app_game": {"name": "📱 برنامه و بازی (جفت)", "price": "۹۹۹,۰۰۰ تومان"},
    "fake_member": {"name": "👥 ممبر فیک تلگرام", "price": "تعرفه در چت / ثبت سفارش"},
    "real_member": {"name": "👤 ممبر واقعی تلگرام", "price": "تعرفه در چت / ثبت سفارش"}
}

# تعرفه‌های پایه سرویس‌های پارس‌پک (به تومان) برای انتخاب سریع یا محاسبه آزاد
PARSPACK_PLANS = {
    "pp_cloud_1": {"name": "☁️ هاست ابری پایه پارس‌پک", "base_price": 450000},
    "pp_cloud_2": {"name": "🚀 هاست ابری حرفه‌ای پارس‌پک", "base_price": 890000},
    "pp_vps_1": {"name": "🖥 سرور مجازی (VPS) پارس‌پک", "base_price": 1350000},
    "pp_dedicated": {"name": "🏢 سرور اختصاصی و سازمانی پارس‌پک", "base_price": 2900000},
}

# ذخیره‌سازی موقت وضعیت کاربران و سفارش‌ها در حافظه
user_states = {}
orders_db = {}
tickets_db = []
users_list = set()

def calculate_parspack_with_profit(base_price: int):
    """
    ماشین حساب دقیق پارس‌پک:
    - زیر ۱ میلیون تومان -> ۵۰۰,۰۰۰ تومان سود اضافه می‌شود
    - ۱ میلیون تومان و بالاتر -> ۱,۰۰۰,۰۰۰ تومان سود اضافه می‌شود
    """
    if base_price < 1_000_000:
        profit = 500_000
    else:
        profit = 1_000_000
    total_price = base_price + profit
    return total_price, profit

def format_toman(amount: int) -> str:
    """فرمت کردن عدد به صورت سه رقم سه رقم با واحد تومان"""
    return f"{amount:,} تومان"

def generate_fresh_gmail_suggestion():
    """تولید یک نام، جیمیل خام پیشنهادی و رمز عبور قوی برای ساخت اکانت پارس‌پک"""
    rand_tag = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    suggested_name = f"ParspackUser_{rand_tag[:3]}"
    suggested_email = f"parspack.site.{rand_tag}@gmail.com"
    suggested_pass = ''.join(random.choices(string.ascii_letters + string.digits + "@#!", k=12))
    return suggested_name, suggested_email, suggested_pass

def is_valid_channel_id(text: str) -> bool:
    """بررسی معتبر بودن آیدی کانال یا لینک تلگرام برای سفارش ممبر"""
    text = text.strip()
    if text.startswith("@") and len(text) >= 5 and " " not in text:
        return True
    if ("t.me/" in text or "telegram.me/" in text) and " " not in text:
        return True
    return False

def check_parspack_status() -> bool:
    """بررسی اتصال لحظه‌ای به سایت پارس‌پک"""
    try:
        resp = requests.get("https://parspack.com", timeout=3)
        return resp.status_code == 200
    except Exception:
        return True

def generate_tracking_code(length=8):
    """تولید کد رهگیری رندوم ترکیبی از حروف کوچک و اعداد مثل gh235vsk"""
    chars = string.ascii_lowercase + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(length))
        if code not in orders_db:
            return code

def get_main_menu(user_id):
    """ساخت منوی شیشه‌ای اصلی برای کاربران و نمایش دکمه مدیریت فقط برای ادمین"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    btn_bot = InlineKeyboardButton("🤖 بات (۱۲۵ تومن)", callback_data="buy_bot")
    btn_site = InlineKeyboardButton("🌐 طراحی سایت (پارس‌پک)", callback_data="buy_site")
    btn_app = InlineKeyboardButton("📱 برنامه و بازی (۹۹۹ تومن)", callback_data="buy_app_game")
    btn_fake = InlineKeyboardButton("👥 ممبر فیک", callback_data="buy_fake_member")
    btn_real = InlineKeyboardButton("👤 ممبر واقعی", callback_data="buy_real_member")
    btn_support = InlineKeyboardButton("🎧 پشتیبانی و ارسال مشکل", callback_data="support_menu")
    
    markup.add(btn_bot, btn_site)
    markup.add(btn_app)
    markup.add(btn_fake, btn_real)
    markup.add(btn_support)
    
    # این بخش فقط و فقط برای آیدی عددی خودت نمایش داده میشه و هیچکس دیگه نمی‌بینه
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("🔐 پنل مدیریت اختصاصی", callback_data="admin_panel"))
        
    return markup

def get_admin_keyboard():
    """کیبورد شیشه‌ای مخصوص پنل مدیریت"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📦 سفارش‌های در انتظار", callback_data="admin_pending"),
        InlineKeyboardButton("📊 آمار کل ربات", callback_data="admin_stats")
    )
    markup.add(InlineKeyboardButton("📩 پیام‌های پشتیبانی", callback_data="admin_tickets"))
    markup.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
    return markup

def send_payment_prompt(chat_id, state):
    """نمایش خلاصه اطلاعات دریافت‌شده (جیمیل/کانال/ایده) و ارسال شماره کارت برای واریز"""
    cancel_markup = InlineKeyboardMarkup()
    cancel_markup.add(InlineKeyboardButton("🔙 انصراف و بازگشت به منو", callback_data="back_main"))

    details_summary = ""
    if state.get("site_credentials"):
        details_summary += f"📧 <b>نام، جیمیل خام و رمز ثبت‌شده:</b>\n<code>{state['site_credentials']}</code>\n"
    if state.get("channel_id"):
        details_summary += f"📢 <b>آیدی کانال ثبت‌شده:</b> <code>{state['channel_id']}</code>\n"
    if state.get("project_idea"):
        details_summary += f"💡 <b>ایده و توضیحات درخواستی شما:</b>\n<code>{state['project_idea']}</code>\n"

    payment_text = (
        f"✅ <b>اطلاعات و ایده شما با موفقیت ثبت شد!</b>\n\n"
        f"🛍 <b>سفارش:</b> {state['product_name']}\n"
        f"💰 <b>مبلغ قابل پرداخت:</b> <b>{state['price']}</b>\n"
        f"{details_summary}\n"
        f"💳 لطفا مبلغ <b>{state['price']}</b> رو به شماره کارت زیر واریز کن:\n"
        f"<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        f"📸 <b>مرحله آخر:</b> بعد از واریز، <b>عکس فیش پرداخت (اسکرین‌شات یا عکس رسید)</b> رو همینجا بفرست تا کد رهگیری اختصاصی برات صادر بشه و سفارشت مستقیم بره بخش مدیریت.\n\n"
        f"🛟 پشتیبانی مستقیم: {SUPPORT_ID}"
    )
    bot.send_message(chat_id, payment_text, reply_markup=cancel_markup)

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    users_list.add(user_id)
    user_states.pop(user_id, None)  # پاک کردن وضعیت قبلی در صورت وجود
    
    welcome_text = (
        f"سلام <b>{message.from_user.first_name}</b> عزیز! 👋\n\n"
        "به ربات رسمی فروش خدمات ما خوش اومدی.\n"
        "از طریق دکمه‌های شیشه‌ای زیر می‌تونی سرویس مورد نظرت رو انتخاب و سفارش بدی 👇\n\n"
        f"🎧 آیدی پشتیبانی: {SUPPORT_ID}"
    )
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=get_main_menu(user_id)
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    # بازگشت به منوی اصلی
    if data == "back_main":
        user_states.pop(user_id, None)
        bot.edit_message_text(
            f"منوی اصلی خدمات ما 👇\nلطفا یکی از گزینه‌های زیر رو انتخاب کن:\n\n🎧 پشتیبانی: {SUPPORT_ID}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu(user_id)
        )

    # بخش پشتیبانی و ارسال مشکل به مدیریت
    elif data == "support_menu":
        user_states[user_id] = {"step": "waiting_for_support_msg"}
        sup_markup = InlineKeyboardMarkup(row_width=1)
        sup_markup.add(
            InlineKeyboardButton("💬 پیام مستقیم به @Mrbottelegram88", url="https://t.me/Mrbottelegram88"),
            InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")
        )
        sup_text = (
            "🎧 <b>بخش پشتیبانی و ارتباط با مدیریت</b>\n\n"
            f"👤 اگر هرگونه سوال یا مشکلی داری، می‌تونی مستقیم به آیدی پشتیبانی ما پیام بدی:\n"
            f"🆔 {SUPPORT_ID}\n\n"
            "✍️ <b>همچنین می‌تونی همین الان مشکل، سوال یا پیام خودت رو همینجا تایپ کنی و بفرستی تا مستقیم توی بخش مدیریت برای ادمین ارسال بشه:</b>"
        )
        bot.edit_message_text(
            sup_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=sup_markup
        )

    # باز کردن پنل مدیریت (با بررسی امنیتی که فقط خودت بتونی ببینی)
    elif data == "admin_panel":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ شما اجازه دسترسی به این بخش را ندارید!", show_alert=True)
            return
        
        bot.edit_message_text(
            "👑 <b>پنل مدیریت اختصاصی</b>\n\nاز دکمه‌های شیشه‌ای زیر برای بررسی سفارش‌ها، پیام‌های پشتیبانی و آمار استفاده کن:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_admin_keyboard()
        )

    # مشاهده آمار در پنل مدیریت
    elif data == "admin_stats":
        if user_id != ADMIN_ID:
            return
        total_orders = len(orders_db)
        pending_orders = sum(1 for o in orders_db.values() if o['status'] == 'pending')
        approved_orders = sum(1 for o in orders_db.values() if o['status'] == 'approved')
        
        stats_text = (
            "📊 <b>آمار لحظه‌ای ربات:</b>\n\n"
            f"👥 تعداد کاربران استارت زده: <code>{len(users_list)}</code>\n"
            f"🧾 کل سفارش‌های ثبت شده: <code>{total_orders}</code>\n"
            f"⏳ سفارش‌های در انتظار تایید: <code>{pending_orders}</code>\n"
            f"✅ سفارش‌های تایید شده: <code>{approved_orders}</code>\n"
            f"📩 تیکت‌های پشتیبانی دریافتی: <code>{len(tickets_db)}</code>"
        )
        bot.edit_message_text(
            stats_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_admin_keyboard()
        )

    # مشاهده لیست پیام‌های پشتیبانی در پنل مدیریت
    elif data == "admin_tickets":
        if user_id != ADMIN_ID:
            return
        if not tickets_db:
            text = "✅ تا این لحظه هیچ پیام پشتیبانی ثبت نشده است."
        else:
            recent_tickets = tickets_db[-10:]
            text = "📩 <b>آخرین پیام‌های پشتیبانی کاربران:</b>\n\n" + "\n➖➖➖➖➖➖\n".join(recent_tickets)
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_admin_keyboard()
        )

    # مشاهده لیست سفارش‌های در انتظار در پنل مدیریت
    elif data == "admin_pending":
        if user_id != ADMIN_ID:
            return
        pending = [f"🔹 کد: <code>{code}</code> | {info['product_name']} | {info['price']} (کاربر: <code>{info['user_id']}</code>)" 
                   for code, info in orders_db.items() if info['status'] == 'pending']
        
        if not pending:
            text = "✅ در حال حاضر هیچ سفارش بررسی‌نشده‌ای وجود ندارد."
        else:
            text = "⏳ <b>لیست سفارش‌های در انتظار بررسی:</b>\n\n" + "\n".join(pending)
            
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_admin_keyboard()
        )

    # بخش اختصاصی طراحی سایت متصل به پارس‌پک و ماشین حساب دقیق
    elif data == "buy_site":
        user_states.pop(user_id, None)
        is_online = check_parspack_status()
        status_badge = "🟢 متصل به سرور پارس‌پک (ParsPack.com)" if is_online else "🟢 محاسبه‌گر آنلاین پارس‌پک فعال"

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🌐 مشاهده سایت پارس‌پک (ParsPack.com)", url="https://parspack.com"))
        markup.add(InlineKeyboardButton("🧮 ماشین‌حساب دقیق پارس‌پک (وارد کردن قیمت دلخواه)", callback_data="pp_custom_calc"))

        for plan_key, plan_info in PARSPACK_PLANS.items():
            final_p, _ = calculate_parspack_with_profit(plan_info["base_price"])
            btn_text = f"{plan_info['name']} | با سود: {format_toman(final_p)}"
            markup.add(InlineKeyboardButton(btn_text, callback_data=f"ppsel_{plan_key}"))
        
        markup.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))

        site_text = (
            f"🌐 <b>بخش سفارش طراحی سایت ({status_badge})</b>\n\n"
            "⚡️ <b>فرمول ماشین‌حساب فوق‌دقیق ما (در کسری از ثانیه):</b>\n"
            "🔹 سرویس‌های زیر ۱ میلیون تومان ⬅️ <b>+۵۰۰,۰۰۰ تومان</b> هزینه طراحی و راه‌اندازی\n"
            "🔹 سرویس‌های بالای ۱ میلیون تومان ⬅️ <b>+۱,۰۰۰,۰۰۰ تومان</b> هزینه طراحی و راه‌اندازی\n\n"
            "👇 می‌تونی قیمت هر سرویسی رو که توی پارس‌پک دیدی با <b>«ماشین‌حساب دقیق پارس‌پک»</b> در لحظه حساب کنی و یا از پلن‌های آماده زیر انتخاب کنی:"
        )
        bot.edit_message_text(
            site_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

    # ماشین حساب آزاد پارس‌پک برای وارد کردن هر مبلغی توسط مشتری
    elif data == "pp_custom_calc":
        user_states[user_id] = {"step": "waiting_for_parspack_price"}
        cancel_markup = InlineKeyboardMarkup()
        cancel_markup.add(InlineKeyboardButton("🔙 بازگشت به بخش سایت", callback_data="buy_site"))
        
        calc_prompt = (
            "🧮 <b>ماشین‌حساب فوق‌سریع پارس‌پک</b>\n\n"
            "لطفا قیمت سرویسی که توی سایت پارس‌پک (parspack.com) انتخاب کردی رو <b>به تومان (فقط عدد)</b> بفرست تا در کسری از ثانیه قیمت نهایی با سود برات محاسبه بشه:\n\n"
            "📌 <i>مثال زیر یک میلیون: 650000 (۵۰۰ تومن اضافه میشه)</i>\n"
            "📌 <i>مثال بالای یک میلیون: 1450000 (۱ میلیون اضافه میشه)</i>"
        )
        bot.edit_message_text(
            calc_prompt,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=cancel_markup
        )

    # انتخاب یکی از پلن‌های آماده پارس‌پک
    elif data.startswith("ppsel_"):
        plan_key = data.replace("ppsel_", "")
        plan = PARSPACK_PLANS.get(plan_key)
        if not plan:
            bot.answer_callback_query(call.id, "پلن یافت نشد!")
            return
        
        base_price = plan["base_price"]
        total_price, profit = calculate_parspack_with_profit(base_price)
        suggested_name, suggested_email, suggested_pass = generate_fresh_gmail_suggestion()

        user_states[user_id] = {
            "step": "waiting_for_site_credentials",
            "product_key": "site",
            "product_name": f"🌐 طراحی سایت ({plan['name']})",
            "base_price": format_toman(base_price),
            "profit": format_toman(profit),
            "price": format_toman(total_price),
            "suggested_name": suggested_name,
            "suggested_email": suggested_email,
            "suggested_pass": suggested_pass
        }

        cancel_markup = InlineKeyboardMarkup()
        cancel_markup.add(InlineKeyboardButton("🔙 بازگشت به بخش سایت", callback_data="buy_site"))

        cred_msg = (
            f"⚡️ <b>محاسبه آنی ماشین‌حساب پارس‌پک در کسری از ثانیه انجام شد!</b>\n\n"
            f"📦 <b>سرویس:</b> {plan['name']}\n"
            f"💵 <b>قیمت پایه پارس‌پک:</b> {format_toman(base_price)}\n"
            f"➕ <b>مبلغ اضافه شده (سود و تعرفه):</b> {format_toman(profit)}\n"
            f"💰 <b>قیمت نهایی با سود:</b> <b>{format_toman(total_price)}</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"📧 <b>مرحله ۱: ارسال نام، جیمیل کاملاً خام و رمز عبور</b>\n"
            f"برای ساخت اکانت و ثبت سایت در پارس‌پک، یک <b>نام</b> و یک <b>جیمیل کاملاً درست و خام (که قبلاً هیچی روش نباشه) به همراه رمز عبورش</b> برامون بفرست.\n\n"
            f"💡 <i>مشخصات خام پیشنهادی برای شما (می‌تونی دقیقا همین جیمیل رو بسازی و با رمزش بفرستی):</i>\n"
            f"👤 نام پیشنهادی: <code>{suggested_name}</code>\n"
            f"📩 جیمیل خام: <code>{suggested_email}</code>\n"
            f"🔑 رمز عبور: <code>{suggested_pass}</code>\n\n"
            f"✍️ <b>لطفا الان توی یک پیام «نام + جیمیل خام + رمز جیمیل» رو بفرست:</b>"
        )
        bot.edit_message_text(
            cred_msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=cancel_markup
        )

    # انتخاب سایر محصولات (بات، برنامه و بازی، ممبر فیک، ممبر واقعی)
    elif data.startswith("buy_"):
        product_key = data.replace("buy_", "")
        product = PRODUCTS.get(product_key)
        
        if not product:
            bot.answer_callback_query(call.id, "محصول یافت نشد!")
            return

        cancel_markup = InlineKeyboardMarkup()
        cancel_markup.add(InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="back_main"))

        # اگر ممبر فیک یا ممبر واقعی بود، اول آیدی کانال رو بگیره
        if product_key in ["fake_member", "real_member"]:
            user_states[user_id] = {
                "step": "waiting_for_channel_id",
                "product_key": product_key,
                "product_name": product["name"],
                "price": product["price"]
            }
            channel_prompt = (
                f"🛍 <b>ثبت سفارش: {product['name']}</b>\n\n"
                f"📢 <b>مرحله ۱: ارسال آیدی کانال</b>\n"
                f"لطفا <b>آیدی کانال تلگرام</b> (با @) یا <b>لینک کانال</b> خودت رو به صورت صحیح بفرست تا بررسی بشه:\n\n"
                f"📌 <i>مثال درست: @MyChannel یا https://t.me/MyChannel</i>\n\n"
                f"🎧 در صورت نیاز به راهنمایی یا استعلام تعرفه دقیق: {SUPPORT_ID}"
            )
            bot.edit_message_text(
                channel_prompt,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=cancel_markup
            )
        else:
            # برای ساخت بات و برنامه/بازی، اول ایده و توضیحات پروژه رو ازش می‌پرسیم
            user_states[user_id] = {
                "step": "waiting_for_project_idea",
                "product_key": product_key,
                "product_name": product["name"],
                "price": product["price"]
            }
            idea_prompt = (
                f"🛍 <b>ثبت سفارش: {product['name']}</b>\n"
                f"💰 <b>قیمت:</b> {product['price']}\n\n"
                f"💡 <b>قبل از پرداخت، ایده‌ای که می‌خوای توی این سفارش پیاده‌سازی بشه رو بگو!</b>\n"
                f"لطفا کامل توضیح بده چه امکاناتی، چه ظاهری یا چه ایده‌ای مد نظرت هست تا دقیقا همون برات ساخته بشه 👇"
            )
            bot.edit_message_text(
                idea_prompt,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=cancel_markup
            )

    # تایید یا رد کردن فیش واریزی توسط ادمین از روی دکمه شیشه‌ای زیر عکس فیش
    elif data.startswith("approve_") or data.startswith("reject_"):
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ فقط مدیر اصلی می‌تونه این دکمه رو بزنه!", show_alert=True)
            return

        action, tracking_code = data.split("_", 1)
        order = orders_db.get(tracking_code)

        if not order:
            bot.answer_callback_query(call.id, "این سفارش در حافظه یافت نشد!", show_alert=True)
            return

        customer_id = order["user_id"]

        if action == "approve":
            order["status"] = "approved"
            bot.answer_callback_query(call.id, "✅ سفارش تایید شد.")
            # اطلاع به مشتری
            try:
                bot.send_message(
                    customer_id,
                    f"🎉 <b>تبریک! سفارش شما تایید شد.</b>\n\n"
                    f"📦 سفارش: {order['product_name']}\n"
                    f"🔖 کد رهگیری: <code>{tracking_code}</code>\n\n"
                    f"به‌زودی از طرف مدیریت برای تحویل سفارش با شما هماهنگ می‌شود."
                )
            except Exception as e:
                logging.error(f"Error sending message to customer: {e}")

            # آپدیت کپشن عکس در پیوی ادمین
            new_caption = call.message.caption + "\n\n✅ <b>وضعیت: توسط شما تایید شد</b>"
            bot.edit_message_caption(new_caption, call.message.chat.id, call.message.message_id)

        elif action == "reject":
            order["status"] = "rejected"
            bot.answer_callback_query(call.id, "❌ سفارش رد شد.")
            # اطلاع به مشتری
            try:
                bot.send_message(
                    customer_id,
                    f"⚠️ <b>وضعیت سفارش شما: رد شد</b>\n\n"
                    f"📦 سفارش: {order['product_name']}\n"
                    f"🔖 کد رهگیری: <code>{tracking_code}</code>\n\n"
                    f"فیش واریزی شما مورد تایید قرار نگرفت. در صورت ابهام مجددا بررسی کنید."
                )
            except Exception as e:
                logging.error(f"Error sending message to customer: {e}")

            new_caption = call.message.caption + "\n\n❌ <b>وضعیت: توسط شما رد شد</b>"
            bot.edit_message_caption(new_caption, call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['photo'])
def handle_receipt_photo(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    # بررسی اینکه آیا کاربر در مرحله ارسال فیش هست یا نه
    if not state or state.get("step") != "waiting_for_receipt":
        bot.reply_to(
            message,
            "⚠️ لطفا اول از طریق منوی شیشه‌ای (/start) محصول مورد نظرت رو انتخاب کن، مراحلش رو پر کن و در مرحله آخر عکس فیش رو بفرست."
        )
        return

    # تولید کد رهگیری اختصاصی (مثلا gh235vsk)
    tracking_code = generate_tracking_code(8)
    photo_file_id = message.photo[-1].file_id
    username = f"@{message.from_user.username}" if message.from_user.username else "ندارد"
    full_name = message.from_user.first_name + (" " + message.from_user.last_name if message.from_user.last_name else "")
    site_credentials = state.get("site_credentials")
    channel_id = state.get("channel_id")
    project_idea = state.get("project_idea")

    # ذخیره اطلاعات سفارش در دیتابیس موقت
    orders_db[tracking_code] = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "product_name": state["product_name"],
        "price": state["price"],
        "site_credentials": site_credentials,
        "channel_id": channel_id,
        "project_idea": project_idea,
        "photo_id": photo_file_id,
        "status": "pending"
    }

    # پاک کردن وضعیت انتظار کاربر
    user_states.pop(user_id, None)

    # ۱. ارسال پیام تایید و کد رهگیری برای مشتری
    customer_reply_markup = InlineKeyboardMarkup()
    customer_reply_markup.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))

    extra_customer_info = ""
    if site_credentials:
        extra_customer_info += f"📧 <b>نام، جیمیل خام و رمز ثبت‌شده:</b>\n<code>{site_credentials}</code>\n"
    if channel_id:
        extra_customer_info += f"📢 <b>آیدی کانال:</b> <code>{channel_id}</code>\n"
    if project_idea:
        extra_customer_info += f"💡 <b>ایده و توضیحات شما:</b>\n<code>{project_idea}</code>\n"

    customer_msg = (
        f"✅ <b>فیش پرداختی شما با موفقیت دریافت شد!</b>\n\n"
        f"🛍 <b>سفارش شما:</b> {state['product_name']}\n"
        f"💰 <b>مبلغ نهایی:</b> {state['price']}\n"
        f"🔖 <b>کد رهگیری اختصاصی شما:</b> <code>{tracking_code}</code>\n\n"
        f"{extra_customer_info}\n"
        f"سفارش، مشخصات و فیش واریزی شما برای بخش مدیریت ارسال شد. به محض بررسی، نتیجه از همینجا بهتون اطلاع داده میشه.\n"
        f"🎧 آیدی پشتیبانی: {SUPPORT_ID}"
    )
    bot.reply_to(message, customer_msg, reply_markup=customer_reply_markup)

    # ۲. ارسال عکس فیش + کد رهگیری + جیمیل/کانال/ایده به بخش مدیریت (فقط برای ADMIN_ID)
    admin_Order_markup = InlineKeyboardMarkup(row_width=2)
    admin_Order_markup.add(
        InlineKeyboardButton("✅ تایید فیش و سفارش", callback_data=f"approve_{tracking_code}"),
        InlineKeyboardButton("❌ رد کردن فیش", callback_data=f"reject_{tracking_code}")
    )

    admin_extra_details = ""
    if site_credentials:
        base_p = state.get("base_price", "نامشخص")
        prof_p = state.get("profit", "نامشخص")
        admin_extra_details += (
            f"\n🌐 <b>اطلاعات سایت (پارس‌پک):</b>\n"
            f"🔸 قیمت پایه پارس‌پک: <code>{base_p}</code>\n"
            f"🔸 سود اضافه شده: <code>{prof_p}</code>\n"
            f"📧 <b>نام، جیمیل خام و رمز مشتری:</b>\n<code>{site_credentials}</code>\n"
        )
    if channel_id:
        admin_extra_details += f"\n📢 <b>آیدی کانال جهت ممبر:</b> <code>{channel_id}</code>\n"
    if project_idea:
        admin_extra_details += f"\n💡 <b>ایده و توضیحات مشتری:</b>\n<code>{project_idea}</code>\n"

    admin_caption = (
        f"🔔 <b>سفارش و فیش واریزی جدید دریافت شد!</b>\n\n"
        f"🔖 <b>کد رهگیری:</b> <code>{tracking_code}</code>\n"
        f"🛍 <b>محصول سفارشی:</b> {state['product_name']}\n"
        f"💰 <b>مبلغ نهایی:</b> {state['price']}\n"
        f"{admin_extra_details}\n"
        f"👤 <b>نام مشتری:</b> {full_name}\n"
        f"🆔 <b>یوزرنیم:</b> {username}\n"
        f"🔢 <b>آیدی عددی:</b> <code>{user_id}</code>"
    )

    try:
        bot.send_photo(
            ADMIN_ID,
            photo_file_id,
            caption=admin_caption,
            reply_markup=admin_Order_markup
        )
    except Exception as e:
        logging.error(f"خطا در ارسال فیش به ادمین (مطمئن شو ادمین ربات رو استارت زده): {e}")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    text = message.text.strip()

    # ارسال پیام مشکل یا سوال به بخش پشتیبانی و مدیریت
    if state and state.get("step") == "waiting_for_support_msg":
        username = f"@{message.from_user.username}" if message.from_user.username else "ندارد"
        full_name = message.from_user.first_name + (" " + message.from_user.last_name if message.from_user.last_name else "")
        ticket_info = (
            f"🆘 <b>پیام پشتیبانی جدید!</b>\n"
            f"👤 کاربر: {full_name} ({username} | <code>{user_id}</code>)\n"
            f"📝 متن مشکل/پیام:\n<code>{text}</code>"
        )
        tickets_db.append(ticket_info)
        user_states.pop(user_id, None)

        try:
            bot.send_message(ADMIN_ID, ticket_info)
        except Exception as e:
            logging.error(f"خطا در ارسال پیام پشتیبانی به ادمین: {e}")

        back_markup = InlineKeyboardMarkup()
        back_markup.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
        bot.reply_to(
            message,
            f"✅ پیام و مشکل شما مستقیم برای مدیریت ارسال شد!\n"
            f"همچنین می‌تونی مستقیماً با آیدی پشتیبانی در ارتباط باشی: {SUPPORT_ID}",
            reply_markup=back_markup
        )
        return

    # مرحله ۱ سایت: کاربر عدد قیمت پایه پارس‌پک را وارد می‌کند تا ماشین‌حساب در کسری از ثانیه سود را اضافه کند
    if state and state.get("step") == "waiting_for_parspack_price":
        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        arabic_digits = "٠١٢٣٤٥٦٧٨٩"
        trans_table = str.maketrans(persian_digits + arabic_digits, "01234567890123456789")
        cleaned_num = re.sub(r"[^\d]", "", text.translate(trans_table))

        if not cleaned_num or int(cleaned_num) <= 0:
            bot.reply_to(
                message,
                "⚠️ لطفا فقط مبلغ پایه پارس‌پک رو به صورت عدد (به تومان) وارد کن!\nمثلا بنویس: <code>750000</code> یا <code>1200000</code>"
            )
            return

        base_price = int(cleaned_num)
        total_price, profit = calculate_parspack_with_profit(base_price)
        suggested_name, suggested_email, suggested_pass = generate_fresh_gmail_suggestion()

        user_states[user_id] = {
            "step": "waiting_for_site_credentials",
            "product_key": "site",
            "product_name": "🌐 طراحی سایت (سرویس پارس‌پک)",
            "base_price": format_toman(base_price),
            "profit": format_toman(profit),
            "price": format_toman(total_price),
            "suggested_name": suggested_name,
            "suggested_email": suggested_email,
            "suggested_pass": suggested_pass
        }

        cancel_markup = InlineKeyboardMarkup()
        cancel_markup.add(InlineKeyboardButton("🔙 بازگشت به بخش سایت", callback_data="buy_site"))

        rule_note = "زیر ۱ میلیون تومان (+۵۰۰ هزار تومان)" if base_price < 1_000_000 else "بالای ۱ میلیون تومان (+۱ میلیون تومان)"

        calc_result_msg = (
            f"⚡️ <b>نتیجه آنی ماشین‌حساب پارس‌پک (در کسری از ثانیه):</b>\n\n"
            f"💵 <b>مبلغ پایه سرویس پارس‌پک:</b> {format_toman(base_price)}\n"
            f"📈 <b>سود و تعرفه اضافه شده ({rule_note}):</b> {format_toman(profit)}\n"
            f"💰 <b>قیمت نهایی با سود:</b> <b>{format_toman(total_price)}</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"📧 <b>مرحله ۱: ارسال نام، جیمیل خام و رمز عبور</b>\n"
            f"لطفا یک <b>نام</b> و یک <b>جیمیل کاملاً درست و خام (که هیچی روش نباشه) به همراه رمز عبورش</b> بفرست تا به همراه سفارشت بره بخش مدیریت.\n\n"
            f"💡 <i>پیشنهاد آماده ربات (می‌تونی همین جیمیل خام رو بسازی و با رمزش بفرستی):</i>\n"
            f"👤 نام: <code>{suggested_name}</code>\n"
            f"📩 جیمیل خام: <code>{suggested_email}</code>\n"
            f"🔑 رمز پیشنهادی: <code>{suggested_pass}</code>\n\n"
            f"✍️ <b>الان توی یک پیام «نام + جیمیل خام + رمز جیمیل» رو بفرست:</b>"
        )
        bot.reply_to(message, calc_result_msg, reply_markup=cancel_markup)
        return

    # مرحله ۲ سایت: دریافت نام، جیمیل خام و رمز از مشتری و پرسیدن ایده سایت
    if state and state.get("step") == "waiting_for_site_credentials":
        if "@gmail.com" not in text.lower() or len(text) < 12:
            bot.reply_to(
                message,
                "⚠️ <b>اطلاعات جیمیل کامل یا معتبر نیست!</b>\n"
                "لطفا مطمئن شو که یک <b>جیمیل کاملاً درست (@gmail.com) که هیچی روش نیست</b> به همراه <b>نام</b> و <b>رمز عبورش</b> توی پیام نوشتی.\n\n"
                "📌 <i>مثال: علی رضایی - alireza.pp99@gmail.com - رمز: Ali@123456</i>"
            )
            return

        state["site_credentials"] = text
        state["step"] = "waiting_for_project_idea"

        cancel_markup = InlineKeyboardMarkup()
        cancel_markup.add(InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="back_main"))

        bot.reply_to(
            message,
            "✅ <b>نام، جیمیل خام و رمز عبور شما ثبت شد!</b>\n\n"
            "💡 <b>حالا در مرحله آخر قبل از پرداخت: ایده‌ای که می‌خوای برای سایتت پیاده بشه رو بگو!</b>\n"
            "مثلاً سایت فروشگاهی، شرکتی، شخصی یا هر امکانات خاصی که توی ذهنت هست رو بنویس:",
            reply_markup=cancel_markup
        )
        return

    # مرحله ۱ ممبر فیک/واقعی: دریافت و بررسی آیدی کانال مشتری
    if state and state.get("step") == "waiting_for_channel_id":
        if not is_valid_channel_id(text):
            bot.reply_to(
                message,
                "⚠️ <b>آیدی کانال وارد شده معتبر نیست!</b>\n"
                "لطفا آیدی کانال رو حتماً با <code>@</code> (مثل <code>@MyChannel</code>) یا لینک <code>https://t.me/...</code> بدون فاصله بفرست."
            )
            return

        state["channel_id"] = text
        state["step"] = "waiting_for_project_idea"

        cancel_markup = InlineKeyboardMarkup()
        cancel_markup.add(InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="back_main"))

        bot.reply_to(
            message,
            f"✅ <b>آیدی کانال (<code>{text}</code>) با موفقیت ثبت شد!</b>\n\n"
            "💡 <b>حالا تعداد ممبر درخواستی، نظر یا ایده‌ای که می‌خوای توی سفارشت لحاظ بشه رو بفرست:</b>",
            reply_markup=cancel_markup
        )
        return

    # مرحله مشترک آخر برای همه محصولات: دریافت ایده مشتری و نمایش اطلاعات کارت به کارت
    if state and state.get("step") == "waiting_for_project_idea":
        state["project_idea"] = text
        state["step"] = "waiting_for_receipt"
        send_payment_prompt(message.chat.id, state)
        return

    if state and state.get("step") == "waiting_for_receipt":
        bot.reply_to(
            message,
            "📸 داداش الان باید <b>عکس فیش واریزی</b> رو بفرستی تا کد رهگیری برات صادر بشه!\n"
            f"اگر مشکلی داری می‌تونی به پشتیبانی پیام بدی: {SUPPORT_ID}"
        )
    else:
        bot.send_message(
            message.chat.id,
            f"لطفا از دکمه‌های شیشه‌ای زیر استفاده کن 👇\n🎧 پشتیبانی: {SUPPORT_ID}",
            reply_markup=get_main_menu(user_id)
        )

if __name__ == "__main__":
    logging.info("Starting Keep-Alive Server and Telegram Shop Bot...")
    threading.Thread(target=start_keep_alive_server, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
