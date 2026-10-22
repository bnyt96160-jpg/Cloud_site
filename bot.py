import os
import random
import string
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_TOKEN = "8260218568:AAFcGh1OSuZoqF0riYkwyZ9zWCj0AcTfpYg"
ADMIN_ID = 8268734462
CARD_NUMBER = "6219861858158784"
CARD_HOLDER = "علیرضا نوروزی"
SUPPORT_ID = "@Mrbottelegram88"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

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
    server.serve_forever()

PRODUCTS = {
    "bot": {"name": "🤖 ساخت بات تلگرام", "price": 125000},
    "site": {"name": "🌐 طراحی سایت", "price": 1500000},
    "app": {"name": "📱 ساخت برنامه", "price": 999000},
    "game": {"name": "🎮 ساخت بازی", "price": 999000},
    "fake_member": {"name": "👥 ممبر فیک تلگرام", "price": 250000}
}

user_states = {}
orders_db = {}
tickets_db = []
users_list = set()

def format_toman(amount: int) -> str:
    return f"{amount:,} تومان"

def generate_fresh_gmail_suggestion():
    rand_tag = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    suggested_name = f"User_{rand_tag[:3]}"
    suggested_email = f"web.site.{rand_tag}@gmail.com"
    suggested_pass = ''.join(random.choices(string.ascii_letters + string.digits + "@#!", k=12))
    return suggested_name, suggested_email, suggested_pass

def is_valid_channel_id(text: str) -> bool:
    text = text.strip()
    if text.startswith("@") and len(text) >= 5 and " " not in text:
        return True
    if ("t.me/" in text or "telegram.me/" in text) and " " not in text:
        return True
    return False

def generate_tracking_code(length=8):
    chars = string.ascii_lowercase + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(length))
        if code not in orders_db:
            return code

def get_main_menu(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_bot = InlineKeyboardButton("🤖 ساخت بات تلگرام", callback_data="buy_bot")
    btn_site = InlineKeyboardButton("🌐 طراحی سایت", callback_data="buy_site")
    btn_app = InlineKeyboardButton("📱 ساخت برنامه", callback_data="buy_app")
    btn_game = InlineKeyboardButton("🎮 ساخت بازی", callback_data="buy_game")
    btn_fake = InlineKeyboardButton("👥 ممبر فیک", callback_data="buy_fake_member")
    btn_support = InlineKeyboardButton("🎧 پشتیبانی", callback_data="support_menu")
    markup.add(btn_bot, btn_site)
    markup.add(btn_app, btn_game)
    markup.add(btn_fake)
    markup.add(btn_support)
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("🔐 پنل مدیریت اختصاصی", callback_data="admin_panel"))
    return markup

def get_admin_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📦 سفارش‌های در انتظار", callback_data="admin_pending"),
        InlineKeyboardButton("📊 آمار کل ربات", callback_data="admin_stats")
    )
    markup.add(InlineKeyboardButton("📩 پیام‌های پشتیبانی", callback_data="admin_tickets"))
    markup.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
    return markup

def send_payment_prompt(chat_id, state):
    cancel_markup = InlineKeyboardMarkup()
    cancel_markup.add(InlineKeyboardButton("🔙 انصراف و بازگشت به منو", callback_data="back_main"))
    details_summary = ""
    if state.get("site_credentials"):
        details_summary += f"📧 <b>اطلاعات هاست/سایت ثبت‌شده:</b>\n<code>{state['site_credentials']}</code>\n"
    if state.get("channel_id"):
        details_summary += f"📢 <b>آیدی کانال ثبت‌شده:</b> <code>{state['channel_id']}</code>\n"
    if state.get("project_idea"):
        details_summary += f"💡 <b>ایده و توضیحات درخواستی شما:</b>\n<code>{state['project_idea']}</code>\n"

    payment_text = (
        f"✅ <b>اطلاعات و ایده شما با موفقیت ثبت شد!</b>\n\n"
        f"🛍 <b>سفارش:</b> {state['product_name']}\n"
        f"💰 <b>مبلغ نهایی قابل پرداخت:</b> <b>{state['price']}</b>\n"
        f"{details_summary}\n"
        f"💳 لطفا مبلغ <b>{state['price']}</b> رو به شماره کارت زیر واریز کن:\n"
        f"<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        f"📸 <b>مرحله آخر:</b> بعد از واریز، <b>عکس فیش پرداخت</b> رو همینجا بفرست.\n\n"
        f"🛟 پشتیبانی مستقیم: {SUPPORT_ID}"
    )
    bot.send_message(chat_id, payment_text, reply_markup=cancel_markup)

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    users_list.add(user_id)
    user_states.pop(user_id, None)
    welcome_text = (
        f"سلام <b>{message.from_user.first_name}</b> عزیز! 👋\n\n"
        "به ربات رسمی فروش خدمات ما خوش اومدی.\n"
        f"🎧 آیدی پشتیبانی: {SUPPORT_ID}"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu(user_id))

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if data == "back_main":
        user_states.pop(user_id, None)
        bot.edit_message_text(
            f"منوی اصلی خدمات ما 👇\n\n🎧 پشتیبانی: {SUPPORT_ID}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu(user_id)
        )
    elif data == "support_menu":
        user_states[user_id] = {"step": "waiting_for_support_msg"}
        sup_markup = InlineKeyboardMarkup(row_width=1)
        sup_markup.add(
            InlineKeyboardButton("💬 پیام مستقیم به @Mrbottelegram88", url="https://t.me/Mrbottelegram88"),
            InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")
        )
        sup_text = (
            "🎧 <b>بخش پشتیبانی و ارتباط با مدیریت</b>\n\n"
            f"🆔 {SUPPORT_ID}\n\n"
            "✍️ <b>مشکل یا پیام خودت رو همینجا تایپ کن و بفرست تا برای مدیریت ارسال بشه:</b>"
        )
        bot.edit_message_text(sup_text, call.message.chat.id, call.message.message_id, reply_markup=sup_markup)
    elif data == "admin_panel":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!", show_alert=True)
            return
        bot.edit_message_text("👑 <b>پنل مدیریت اختصاصی</b>", call.message.chat.id, call.message.message_id, reply_markup=get_admin_keyboard())
    elif data == "admin_stats":
        if user_id != ADMIN_ID:
            return
        total_orders = len(orders_db)
        pending_orders = sum(1 for o in orders_db.values() if o['status'] == 'pending')
        approved_orders = sum(1 for o in orders_db.values() if o['status'] == 'approved')
        stats_text = (
            f"📊 <b>آمار لحظه‌ای ربات:</b>\n\n"
            f"👥 کاربران: <code>{len(users_list)}</code>\n"
            f"🧾 کل سفارش‌ها: <code>{total_orders}</code>\n"
            f"⏳ در انتظار: <code>{pending_orders}</code>\n"
            f"✅ تایید شده: <code>{approved_orders}</code>\n"
            f"📩 تیکت‌ها: <code>{len(tickets_db)}</code>"
        )
        bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, reply_markup=get_admin_keyboard())
    elif data == "admin_tickets":
        if user_id != ADMIN_ID:
            return
        text = "✅ هیچ پیامی نیست." if not tickets_db else "📩 <b>آخرین پیام‌ها:</b>\n\n" + "\n➖➖➖➖➖➖\n".join(tickets_db[-10:])
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_admin_keyboard())
    elif data == "admin_pending":
        if user_id != ADMIN_ID:
            return
        pending = [f"🔹 کد: <code>{code}</code> | {info['product_name']} | {info['price']}" for code, info in orders_db.items() if info['status'] == 'pending']
        text = "✅ هیچ سفارشی نیست." if not pending else "⏳ <b>سفارش‌های در انتظار:</b>\n\n" + "\n".join(pending)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_admin_keyboard())
    elif data == "buy_site":
        p = PRODUCTS["site"]
        s_name, s_email, s_pass = generate_fresh_gmail_suggestion()
        user_states[user_id] = {
            "step": "waiting_for_site_credentials",
            "product_key": "site",
            "product_name": p["name"],
            "price": format_toman(p["price"]),
            "suggested_name": s_name, "suggested_email": s_email, "suggested_pass": s_pass
        }
        cancel_markup = InlineKeyboardMarkup()
        cancel_markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
        cred_msg = (
            f"🌐 <b>بخش طراحی سایت</b>\n\n"
            f"📧 اطلاعات پیشنهادی برای ثبت‌نام (جیمیل خام و رمز):\n"
            f"👤 نام پیشنهادی: <code>{s_name}</code>\n"
            f"📩 جیمیل خام: <code>{s_email}</code>\n"
            f"🔑 رمز: <code>{s_pass}</code>\n\n"
            f"✍️ <b>لطفا «نام + جیمیل خام + رمز» خودتون رو بفرستید:</b>"
        )
        bot.edit_message_text(cred_msg, call.message.chat.id, call.message.message_id, reply_markup=cancel_markup)
    elif data.startswith("buy_"):
        p_key = data.replace("buy_", "")
        p = PRODUCTS.get(p_key)
        if not p:
            return
        cancel_markup = InlineKeyboardMarkup()
        cancel_markup.add(InlineKeyboardButton("🔙 انصراف", callback_data="back_main"))
        if p_key == "fake_member":
            user_states[user_id] = {"step": "waiting_for_channel_id", "product_key": p_key, "product_name": p["name"], "price": format_toman(p["price"])}
            bot.edit_message_text(f"🛍 <b>{p['name']}</b>\n\n📢 <b>آیدی کانال یا لینک رو بفرست:</b>", call.message.chat.id, call.message.message_id, reply_markup=cancel_markup)
        else:
            user_states[user_id] = {"step": "waiting_for_project_idea", "product_key": p_key, "product_name": p["name"], "price": format_toman(p["price"])}
            bot.edit_message_text(f"🛍 <b>{p['name']}</b>\n\n💡 <b>ایده‌ای که می‌خوای رو کامل توضیح بده:</b>", call.message.chat.id, call.message.message_id, reply_markup=cancel_markup)
    elif data.startswith("approve_") or data.startswith("reject_"):
        if user_id != ADMIN_ID:
            return
        action, t_code = data.split("_", 1)
        order = orders_db.get(t_code)
        if not order:
            return
        if action == "approve":
            order["status"] = "approved"
            bot.answer_callback_query(call.id, "✅ تایید شد.")
            try:
                bot.send_message(order["user_id"], f"🎉 <b>سفارش شما تایید شد!</b>\n🔖 کد رهگیری: <code>{t_code}</code>")
            except:
                pass
            bot.edit_message_caption(call.message.caption + "\n\n✅ <b>تایید شد</b>", call.message.chat.id, call.message.message_id)
        elif action == "reject":
            order["status"] = "rejected"
            bot.answer_callback_query(call.id, "❌ رد شد.")
            try:
                bot.send_message(order["user_id"], f"⚠️ <b>سفارش شما رد شد.</b>")
            except:
                pass
            bot.edit_message_caption(call.message.caption + "\n\n❌ <b>رد شد</b>", call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['photo'])
def handle_receipt_photo(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if not state or state.get("step") != "waiting_for_receipt":
        bot.reply_to(message, "⚠️ اول از /start محصول انتخاب کن.")
        return
    t_code = generate_tracking_code(8)
    photo_id = message.photo[-1].file_id
    username = f"@{message.from_user.username}" if message.from_user.username else "ندارد"
    full_name = message.from_user.first_name
    orders_db[t_code] = {
        "user_id": user_id, "username": username, "full_name": full_name,
        "product_name": state["product_name"], "price": state["price"],
        "site_credentials": state.get("site_credentials"), "channel_id": state.get("channel_id"),
        "project_idea": state.get("project_idea"), "status": "pending"
    }
    user_states.pop(user_id, None)
    bot.reply_to(message, f"✅ فیش دریافت شد!\n🔖 کد رهگیری شما: <code>{t_code}</code>")
    
    admin_markup = InlineKeyboardMarkup(row_width=2)
    admin_markup.add(InlineKeyboardButton("✅ تایید", callback_data=f"approve_{t_code}"), InlineKeyboardButton("❌ رد", callback_data=f"reject_{t_code}"))
    admin_cap = f"🔔 <b>سفارش جدید!</b>\n🔖 <code>{t_code}</code>\n🛍 {state['product_name']}\n💰 {state['price']}\n👤 {full_name} ({username})"
    try:
        bot.send_photo(ADMIN_ID, photo_id, caption=admin_cap, reply_markup=admin_markup)
    except:
        pass

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    text = message.text.strip()

    if state and state.get("step") == "waiting_for_support_msg":
        tickets_db.append(f"🆘 پیام از {message.from_user.first_name} (`{user_id}`):\n{text}")
        user_states.pop(user_id, None)
        try:
            bot.send_message(ADMIN_ID, f"🆘 <b>تیکت جدید:</b>\n{text}")
        except:
            pass
        bot.reply_to(message, f"✅ پیام برای مدیریت ارسال شد.\n🆔 {SUPPORT_ID}")
        return

    if state and state.get("step") == "waiting_for_site_credentials":
        if "@gmail.com" not in text.lower():
            bot.reply_to(message, "⚠️ جیمیل معتبر نیست!")
            return
        state["site_credentials"] = text
        state["step"] = "waiting_for_project_idea"
        bot.reply_to(message, "✅ اطلاعات ثبت شد!\n\n💡 <b>ایده‌ای که می‌خوای سایتت داشته باشه رو کامل توضیح بده:</b>")
        return

    if state and state.get("step") == "waiting_for_channel_id":
        if not is_valid_channel_id(text):
            bot.reply_to(message, "⚠️ آیدی کانال معتبر نیست (با @ یا لینک بفرست).")
            return
        state["channel_id"] = text
        state["step"] = "waiting_for_project_idea"
        bot.reply_to(message, "✅ آیدی ثبت شد!\n\n💡 <b>ایده‌ای که می‌خوای رو کامل توضیح بده:</b>")
        return

    if state and state.get("step") == "waiting_for_project_idea":
        state["project_idea"] = text
        state["step"] = "waiting_for_receipt"
        send_payment_prompt(message.chat.id, state)
        return

    bot.send_message(message.chat.id, f"لطفا از منو استفاده کن 👇\n🎧 پشتیبانی: {SUPPORT_ID}", reply_markup=get_main_menu(user_id))

if __name__ == "__main__":
    threading.Thread(target=start_keep_alive_server, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
