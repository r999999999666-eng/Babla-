import os
import sqlite3
import time
import threading
import html
import random
from datetime import datetime

from flask import Flask
import telebot
from telebot import types

=========================================================

1. ТОКЕН И ОСНОВНЫЕ НАСТРОЙКИ

=========================================================

TOKEN = os.environ.get("TOKEN_REF", "СЮДА_ВСТАВИТЬ_ТОКЕН")

Замените на свой Telegram ID

MAIN_ADMIN = 8957913298

SUPPORT = "@Bablahp_bot"
BOT_USERNAME = "BABLA_KG_BOT"
BOT_NAME = "Babla.KG"

DB_NAME = "ggkassa_main.db"

=========================================================

2. PREMIUM / CUSTOM EMOJI

=========================================================

Важно:

emoji-id должны быть реальными custom_emoji_id Telegram.

Они работают в сообщениях с parse_mode="HTML".

EMOJI = {
"star": '<tg-emoji emoji-id="5368324170671202286">⭐</tg-emoji>',
"vip": '<tg-emoji emoji-id="5368324170671202287">👑</tg-emoji>',
"gem": '<tg-emoji emoji-id="5368324170671202288">💎</tg-emoji>',
"sparkles": '<tg-emoji emoji-id="5368324170671202289">✨</tg-emoji>',
"wallet": '<tg-emoji emoji-id="5368324170671202290">👛</tg-emoji>',
"deposit": '<tg-emoji emoji-id="5368324170671202291">📥</tg-emoji>',
"withdraw": '<tg-emoji emoji-id="5368324170671202292">📤</tg-emoji>',
"support": '<tg-emoji emoji-id="5368324170671202293">👨‍💻</tg-emoji>',
"admin": '<tg-emoji emoji-id="5368324170671202294">⚙️</tg-emoji>',
"money": '<tg-emoji emoji-id="5368324170671202295">💸</tg-emoji>',
"fire": '<tg-emoji emoji-id="5368324170671202296">🔥</tg-emoji>',
"target": '<tg-emoji emoji-id="5368324170671202297">🎯</tg-emoji>',
"check": '<tg-emoji emoji-id="5368324170671202298">✅</tg-emoji>',
"cross": '<tg-emoji emoji-id="5368324170671202299">❌</tg-emoji>',
"clock": '<tg-emoji emoji-id="5368324170671202300">⏳</tg-emoji>',
"rocket": '<tg-emoji emoji-id="5368324170671202301">🚀</tg-emoji>',
"lightning": '<tg-emoji emoji-id="5368324170671202302">⚡️</tg-emoji>',
"stats": '<tg-emoji emoji-id="5368324170671202303">📈</tg-emoji>',
"broadcast": '<tg-emoji emoji-id="5368324170671202304">📢</tg-emoji>',
"qr": '<tg-emoji emoji-id="5368324170671202305">🖼</tg-emoji>',
"off": '<tg-emoji emoji-id="5368324170671202306">🔴</tg-emoji>',
"on": '<tg-emoji emoji-id="5368324170671202307">🟢</tg-emoji>',
"info": '<tg-emoji emoji-id="5368324170671202308">ℹ️</tg-emoji>',
"key": '<tg-emoji emoji-id="5368324170671202309">🔑</tg-emoji>'
}

bot = telebot.TeleBot(TOKEN)
app = Flask(name)

temp_data = {}
user_messages = {}
payment_timers = {}

=========================================================

3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ

=========================================================

def safe_html(text):
if not text:
return ""
return html.escape(str(text))

def is_admin(user_id):
return user_id == MAIN_ADMIN or user_id in get_admins()

def save_msg(chat_id, msg_id):
if not msg_id:
return

if chat_id not in user_messages:
    user_messages[chat_id] = []

if msg_id not in user_messages[chat_id]:
    user_messages[chat_id].append(msg_id)

def clear_user_messages(chat_id):
if chat_id not in user_messages:
return

for msg_id in user_messages[chat_id]:
    try:
        bot.delete_message(chat_id, msg_id)
    except Exception:
        pass

user_messages[chat_id] = []

def send_msg(
chat_id,
text,
reply_markup=None,
disable_web_page_preview=False
):
try:
msg = bot.send_message(
chat_id,
text,
parse_mode="HTML",
reply_markup=reply_markup,
disable_web_page_preview=disable_web_page_preview
)

    if msg:
        save_msg(chat_id, msg.message_id)

    return msg

except Exception as e:
    print(f"Ошибка отправки сообщения: {e}")
    return None

def send_media_bulletproof(
chat_id,
file_id,
caption=None,
reply_markup=None
):
if not file_id:
if caption:
return send_msg(
chat_id,
caption,
reply_markup=reply_markup
)
return None

try:
    msg = bot.send_photo(
        chat_id,
        file_id,
        caption=caption,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    if msg:
        save_msg(chat_id, msg.message_id)

    return msg

except Exception as e:
    print(f"Ошибка отправки фото: {e}")

    if caption:
        return send_msg(
            chat_id,
            caption,
            reply_markup=reply_markup
        )

    return None

=========================================================

4. SQLITE

=========================================================

def init_db():

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute("PRAGMA journal_mode=WAL;")

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            join_date TEXT,
            balance REAL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            chat_id INTEGER PRIMARY KEY
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            account_id TEXT,
            photo_id TEXT,
            status TEXT,
            date TEXT,
            timestamp INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            date TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            wallet_qr TEXT,
            account_id TEXT,
            amount REAL,
            status TEXT,
            date TEXT
        )
    """)

    c.execute(
        "INSERT OR IGNORE INTO admins (chat_id) VALUES (?)",
        (MAIN_ADMIN,)
    )

    c.execute("""
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ("bot_active", "True")
    """)

    conn.commit()

def get_admins():

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute("SELECT chat_id FROM admins")

    admins = [row[0] for row in c.fetchall()]

    if MAIN_ADMIN not in admins:
        admins.append(MAIN_ADMIN)

    return admins

def add_admin(chat_id):

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute(
        "INSERT OR IGNORE INTO admins (chat_id) VALUES (?)",
        (chat_id,)
    )

    conn.commit()

def add_user(chat_id):

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute(
        "SELECT chat_id FROM users WHERE chat_id = ?",
        (chat_id,)
    )

    if c.fetchone():
        return False

    c.execute(
        """
        INSERT INTO users (chat_id, join_date)
        VALUES (?, ?)
        """,
        (
            chat_id,
            datetime.now().strftime("%d.%m.%Y %H:%M")
        )
    )

    conn.commit()

    return True

def get_all_users():

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute("SELECT chat_id FROM users")

    return [row[0] for row in c.fetchall()]

def is_bot_active():

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute(
        "SELECT value FROM settings WHERE key = 'bot_active'"
    )

    row = c.fetchone()

    return True if not row else row[0] == "True"

def set_bot_active(active):

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO settings (key, value)
        VALUES ("bot_active", ?)
    """, (str(active),))

    conn.commit()

def save_qr(file_id):

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute("""
        INSERT INTO qr_codes (file_id, date)
        VALUES (?, ?)
    """, (
        file_id,
        datetime.now().strftime("%d.%m.%Y %H:%M")
    ))

    conn.commit()

def get_last_qr():

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute("""
        SELECT file_id
        FROM qr_codes
        ORDER BY id DESC
        LIMIT 1
    """)

    row = c.fetchone()

    return row[0] if row else None

def add_deposit(
user_id,
amount,
account_id,
photo_id
):

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    now = datetime.now()

    c.execute("""
        INSERT INTO deposits (
            user_id,
            amount,
            account_id,
            photo_id,
            status,
            date,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        amount,
        account_id,
        photo_id,
        "pending",
        now.strftime("%d.%m.%Y %H:%M:%S"),
        int(time.time())
    ))

    dep_id = c.lastrowid

    conn.commit()

    return dep_id

def add_withdrawal(
user_id,
wallet_qr,
account_id,
amount
):

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute("""
        INSERT INTO withdrawals (
            user_id,
            wallet_qr,
            account_id,
            amount,
            status,
            date
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        wallet_qr,
        account_id,
        amount,
        "pending",
        datetime.now().strftime("%d.%m.%Y %H:%M")
    ))

    withdrawal_id = c.lastrowid

    conn.commit()

    return withdrawal_id

def get_pending_deposits():

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute("""
        SELECT
            id,
            user_id,
            amount,
            account_id,
            photo_id,
            date,
            timestamp
        FROM deposits
        WHERE status = "pending"
        ORDER BY id ASC
    """)

    return c.fetchall()

def get_stats():

with sqlite3.connect(DB_NAME, timeout=10) as conn:

    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*)
        FROM deposits
        WHERE status = "pending"
    """)
    pending = c.fetchone()[0]

    c.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM deposits
        WHERE status = "approved"
    """)
    total = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*)
        FROM withdrawals
        WHERE status = "pending"
    """)
    pending_withdrawals = c.fetchone()[0]

    return {
        "users": users,
        "pending": pending,
        "total": total,
        "pending_withdrawals": pending_withdrawals
    }

init_db()

=========================================================

5. МЕНЮ

=========================================================

def main_menu(user_id):

markup = types.ReplyKeyboardMarkup(
    resize_keyboard=True,
    row_width=2
)

markup.add(
    "📥 Пополнить",
    "📤 Вывести"
)

markup.add("👨‍💻 Поддержка")

if is_admin(user_id):
    markup.add("⚙️ Admin")

return markup

def admin_menu():

active = is_bot_active()

markup = types.ReplyKeyboardMarkup(
    resize_keyboard=True,
    row_width=2
)

markup.add(
    "📋 Заявки",
    "📈 Статистика"
)

markup.add(
    "🖼 Изменить QR",
    "➕ Админ"
)

markup.add("📢 Рассылка")

markup.add(
    "🔴 ВЫКЛ" if active else "🟢 ВКЛ"
)

markup.add("🔙 Главное меню")

return markup

def back_menu():

markup = types.ReplyKeyboardMarkup(
    resize_keyboard=True
)

markup.add("🔙 Назад")

return markup

=========================================================

6. START

=========================================================

@bot.message_handler(commands=["start"])
def start(msg):

chat_id = msg.chat.id

save_msg(chat_id, msg.message_id)

clear_user_messages(chat_id)

bot.clear_step_handler_by_chat_id(chat_id)

if chat_id in payment_timers:

    try:
        payment_timers[chat_id].cancel()
    except Exception:
        pass

    payment_timers.pop(chat_id, None)

temp_data[chat_id] = {}

if not is_bot_active() and not is_admin(msg.from_user.id):

    send_msg(
        chat_id,
        f"{EMOJI['off']} "
        f"<b>Бот временно отключен.</b>"
    )

    return

add_user(chat_id)

welcome_text = f"""

{EMOJI['sparkles']} <b>Добро пожаловать в {BOT_NAME}!</b> {EMOJI['vip']}

{EMOJI['money']} <b>Пополнение и обработка заявок.</b>

{EMOJI['gem']} <b>Защищённые заявки</b>
{EMOJI['rocket']} <b>Быстрая обработка</b>
{EMOJI['lightning']} <b>Поддержка пользователей</b>

{EMOJI['star']} Работаем <b>24/7</b>

{EMOJI['support']} <b>Поддержка:</b> {SUPPORT}
"""

send_msg(
    chat_id,
    welcome_text,
    reply_markup=main_menu(chat_id)
)

@bot.message_handler(
func=lambda m: m.text == "🔙 Главное меню"
)
def back_to_main(msg):

start(msg)

@bot.message_handler(
func=lambda m: m.text == "🔙 Назад"
)
def back_handler(msg):

clear_user_messages(msg.chat.id)

start(msg)

=========================================================

7. SUPPORT

=========================================================

@bot.message_handler(
func=lambda m: m.text in [
"👨‍💻 Поддержка",
"Поддержка"
]
)
def support_handler(msg):

save_msg(msg.chat.id, msg.message_id)

clear_user_messages(msg.chat.id)

send_msg(
    msg.chat.id,
    f"""

{EMOJI['support']} <b>Служба поддержки</b>

{SUPPORT}

{EMOJI['sparkles']} Пишите по любым вопросам.
""",
reply_markup=back_menu()
)

=========================================================

8. ПОПОЛНЕНИЕ

=========================================================

@bot.message_handler(
func=lambda m: m.text in [
"📥 Пополнить",
"Пополнить"
]
)
def deposit_start(msg):

chat_id = msg.chat.id

save_msg(chat_id, msg.message_id)

clear_user_messages(chat_id)

if not is_bot_active() and not is_admin(msg.from_user.id):

    send_msg(
        chat_id,
        f"{EMOJI['off']} Бот на техническом обслуживании."
    )

    return

temp_data[chat_id] = {}

markup = types.InlineKeyboardMarkup(
    row_width=2
)

markup.add(
    types.InlineKeyboardButton(
        "1xBet 🏆",
        callback_data="dep_bk_1xbet"
    ),
    types.InlineKeyboardButton(
        "Melbet 🎯",
        callback_data="dep_bk_melbet"
    )
)

send_msg(
    chat_id,
    f"{EMOJI['target']} "
    f"<b>Выберите платформу:</b>",
    reply_markup=markup
)

@bot.callback_query_handler(
func=lambda call: call.data in [
"dep_bk_1xbet",
"dep_bk_melbet"
]
)
def deposit_select_platform(call):

chat_id = call.message.chat.id

try:
    bot.answer_callback_query(call.id)
except Exception:
    pass

clear_user_messages(chat_id)

platform = (
    "1xBet"
    if call.data == "dep_bk_1xbet"
    else "Melbet"
)

temp_data[chat_id] = {
    "platform": platform
}

send_msg(
    chat_id,
    f"{EMOJI['info']} "
    f"<b>Введите ваш ID аккаунта {platform}:</b>",
    reply_markup=back_menu()
)

bot.register_next_step_handler_by_chat_id(
    chat_id,
    get_account_id
)

def get_account_id(msg):

save_msg(
    msg.chat.id,
    msg.message_id
)

if msg.text == "🔙 Назад":

    clear_user_messages(msg.chat.id)

    start(msg)

    return

if not msg.text or not msg.text.strip():

    send_msg(
        msg.chat.id,
        f"{EMOJI['cross']} "
        f"Введите корректный ID."
    )

    bot.register_next_step_handler(
        msg,
        get_account_id
    )

    return

platform = temp_data.get(
    msg.chat.id,
    {}
).get(
    "platform",
    "1xBet"
)

temp_data.setdefault(
    msg.chat.id,
    {}
)

temp_data[msg.chat.id]["account_id"] = (
    f"{platform} | {msg.text.strip()}"
)

clear_user_messages(msg.chat.id)

send_msg(
    msg.chat.id,
    f"{EMOJI['money']} "
    f"<b>Введите сумму для пополнения "
    f"(от 100 до 500 000 сом):</b>",
    reply_markup=back_menu()
)

bot.register_next_step_handler(
    msg,
    get_amount
)

def get_amount(msg):

save_msg(
    msg.chat.id,
    msg.message_id
)

if msg.text == "🔙 Назад":

    clear_user_messages(msg.chat.id)

    start(msg)

    return

try:

    base_amount = float(
        msg.text.replace(",", ".")
    )

except Exception:

    clear_user_messages(msg.chat.id)

    send_msg(
        msg.chat.id,
        f"{EMOJI['cross']} "
        f"Введите корректную сумму.",
        reply_markup=back_menu()
    )

    bot.register_next_step_handler(
        msg,
        get_amount
    )

    return

if base_amount < 100 or base_amount > 500000:

    clear_user_messages(msg.chat.id)

    send_msg(
        msg.chat.id,
        f"{EMOJI['cross']} "
        f"Сумма должна быть от 100 до 500 000 сом.",
        reply_markup=back_menu()
    )

    bot.register_next_step_handler(
        msg,
        get_amount
    )

    return

cents = random.randint(
    10,
    99
) / 100

final_amount = round(
    base_amount + cents,
    2
)

temp_data.setdefault(
    msg.chat.id,
    {}
)

temp_data[msg.chat.id]["amount"] = (
    final_amount
)

qr_file_id = get_last_qr()

clear_user_messages(msg.chat.id)

if qr_file_id:

    send_media_bulletproof(
        msg.chat.id,
        qr_file_id,
        caption=(
            f"{EMOJI['wallet']} "
            f"<b>ОПЛАТИТЕ РОВНО "
            f"{final_amount:.2f} сом</b>\n\n"
            f"{EMOJI['clock']} "
            f"Время на оплату: 5 минут"
        )
    )

else:

    send_msg(
        msg.chat.id,
        f"{EMOJI['qr']} "
        f"QR-код пока не загружен."
    )

account_id = temp_data[
    msg.chat.id
].get(
    "account_id",
    "Не указан"
)

send_msg(
    msg.chat.id,
    f"""

{EMOJI['sparkles']} <b>Прикрепите чек об оплате</b>

━━━━━━━━━━━━━━━━━━━━

🆔 <b>Счёт:</b>
<code>{safe_html(account_id)}</code>

{EMOJI['money']} <b>К оплате:</b>
<code>{final_amount:.2f}</code> сом

⚠️ <b>Важно:</b>
переводите точную сумму.

━━━━━━━━━━━━━━━━━━━━

{EMOJI['clock']}
<b>Отправьте чек в течение 5 минут.</b>
""",
reply_markup=back_menu()
)

user_id = msg.chat.id

if user_id in payment_timers:

    try:
        payment_timers[user_id].cancel()
    except Exception:
        pass

timer = threading.Timer(
    300,
    cancel_payment,
    args=[user_id]
)

payment_timers[user_id] = timer

timer.start()

bot.register_next_step_handler(
    msg,
    get_check_photo
)

def cancel_payment(user_id):

payment_timers.pop(
    user_id,
    None
)

temp_data.pop(
    user_id,
    None
)

try:

    clear_user_messages(user_id)

    send_msg(
        user_id,
        f"""

{EMOJI['clock']}
<b>Время оплаты истекло!</b>

Заявка автоматически отменена.
""",
reply_markup=main_menu(user_id)
)

except Exception:
    pass

def get_check_photo(msg):

save_msg(
    msg.chat.id,
    msg.message_id
)

user_id = msg.chat.id

if msg.text == "🔙 Назад":

    if user_id in payment_timers:

        payment_timers[user_id].cancel()

        payment_timers.pop(
            user_id,
            None
        )

    temp_data.pop(
        user_id,
        None
    )

    clear_user_messages(user_id)

    start(msg)

    return

photo_id = None

if msg.photo:
    photo_id = msg.photo[-1].file_id

elif msg.document:
    photo_id = msg.document.file_id

if not photo_id:

    clear_user_messages(user_id)

    send_msg(
        user_id,
        f"{EMOJI['cross']} "
        f"Отправьте фото или файл чека.",
        reply_markup=back_menu()
    )

    bot.register_next_step_handler(
        msg,
        get_check_photo
    )

    return

if user_id in payment_timers:

    payment_timers[user_id].cancel()

    payment_timers.pop(
        user_id,
        None
    )

account_id = temp_data.get(
    user_id,
    {}
).get(
    "account_id"
)

amount = temp_data.get(
    user_id,
    {}
).get(
    "amount"
)

if not account_id or amount is None:

    clear_user_messages(user_id)

    send_msg(
        user_id,
        f"{EMOJI['cross']} "
        f"Данные заявки утеряны."
    )

    start(msg)

    return

dep_id = add_deposit(
    user_id,
    amount,
    account_id,
    photo_id
)

markup = types.InlineKeyboardMarkup()

markup.add(
    types.InlineKeyboardButton(
        "✅ Одобрить",
        callback_data=f"approve_{dep_id}"
    ),
    types.InlineKeyboardButton(
        "❌ Отклонить",
        callback_data=f"reject_{dep_id}"
    )
)

admin_caption = f"""

{EMOJI['lightning']}
<b>ЗАЯВКА НА ПОПОЛНЕНИЕ #{dep_id}</b>

👤 Пользователь: <code>{user_id}</code>

{EMOJI['money']} Сумма:
<b>{amount:.2f} сом</b>

🆔 Счёт:
<code>{safe_html(account_id)}</code>
"""

for admin_id in get_admins():

    send_media_bulletproof(
        admin_id,
        photo_id,
        caption=admin_caption,
        reply_markup=markup
    )

clear_user_messages(user_id)

send_msg(
    user_id,
    f"""

{EMOJI['check']}
<b>Заявка принята!</b>

🆔 <code>{safe_html(account_id)}</code>

{EMOJI['money']}
<b>Сумма:</b> {amount:.2f} сом

{EMOJI['clock']}
Ожидайте обработки оператором.
""",
reply_markup=main_menu(user_id)
)

temp_data.pop(
    user_id,
    None
)

=========================================================

9. ВЫВОД БЕЗ SMS / OTP

=========================================================

@bot.message_handler(
func=lambda m: m.text in [
"📤 Вывести",
"Вывести"
]
)
def withdraw_start(msg):

chat_id = msg.chat.id

save_msg(
    chat_id,
    msg.message_id
)

clear_user_messages(chat_id)

if not is_bot_active() and not is_admin(msg.from_user.id):

    send_msg(
        chat_id,
        f"{EMOJI['off']} "
        f"Бот на техническом обслуживании."
    )

    return

temp_data[chat_id] = {}

send_msg(
    chat_id,
    f"""

{EMOJI['qr']}
<b>Отправьте QR-код кошелька
для получения средств.</b>

⚠️ Никому не отправляйте пароли,
SMS-коды или коды подтверждения.
""",
reply_markup=back_menu()
)

bot.register_next_step_handler(
    msg,
    withdraw_get_wallet
)

def withdraw_get_wallet(msg):

save_msg(
    msg.chat.id,
    msg.message_id
)

if msg.text == "🔙 Назад":

    clear_user_messages(msg.chat.id)

    start(msg)

    return

wallet_qr = None

if msg.photo:
    wallet_qr = msg.photo[-1].file_id

elif msg.document:
    wallet_qr = msg.document.file_id

if not wallet_qr:

    clear_user_messages(msg.chat.id)

    send_msg(
        msg.chat.id,
        f"{EMOJI['cross']} "
        f"Отправьте изображение QR-кода.",
        reply_markup=back_menu()
    )

    bot.register_next_step_handler(
        msg,
        withdraw_get_wallet
    )

    return

temp_data.setdefault(
    msg.chat.id,
    {}
)

temp_data[msg.chat.id]["wallet_qr"] = (
    wallet_qr
)

clear_user_messages(msg.chat.id)

send_msg(
    msg.chat.id,
    f"""

{EMOJI['info']}
<b>Введите ID вашего аккаунта
1xBet / Melbet:</b>
""",
reply_markup=back_menu()
)

bot.register_next_step_handler(
    msg,
    withdraw_get_account
)

def withdraw_get_account(msg):

save_msg(
    msg.chat.id,
    msg.message_id
)

if msg.text == "🔙 Назад":

    clear_user_messages(msg.chat.id)

    start(msg)

    return

if not msg.text or not msg.text.strip():

    send_msg(
        msg.chat.id,
        f"{EMOJI['cross']} "
        f"Введите корректный ID."
    )

    bot.register_next_step_handler(
        msg,
        withdraw_get_account
    )

    return

temp_data.setdefault(
    msg.chat.id,
    {}
)

temp_data[msg.chat.id]["withdraw_account"] = (
    msg.text.strip()
)

clear_user_messages(msg.chat.id)

send_msg(
    msg.chat.id,
    f"""

{EMOJI['money']}
<b>Введите сумму для вывода:</b>
""",
reply_markup=back_menu()
)

bot.register_next_step_handler(
    msg,
    withdraw_get_amount
)

def withdraw_get_amount(msg):

save_msg(
    msg.chat.id,
    msg.message_id
)

if msg.text == "🔙 Назад":

    clear_user_messages(msg.chat.id)

    start(msg)

    return

try:

    amount = float(
        msg.text.replace(",", ".")
    )

except Exception:

    send_msg(
        msg.chat.id,
        f"{EMOJI['cross']} "
        f"Введите корректную сумму."
    )

    bot.register_next_step_handler(
        msg,
        withdraw_get_amount
    )

    return

if amount <= 0:

    send_msg(
        msg.chat.id,
        f"{EMOJI['cross']} "
        f"Сумма должна быть больше нуля."
    )

    bot.register_next_step_handler(
        msg,
        withdraw_get_amount
    )

    return

user_id = msg.chat.id

wallet_qr = temp_data.get(
    user_id,
    {}
).get(
    "wallet_qr"
)

account_id = temp_data.get(
    user_id,
    {}
).get(
    "withdraw_account"
)

if not wallet_qr or not account_id:

    send_msg(
        user_id,
        f"{EMOJI['cross']} "
        f"Данные заявки утеряны."
    )

    start(msg)

    return

withdrawal_id = add_withdrawal(
    user_id,
    wallet_qr,
    account_id,
    amount
)

markup = types.InlineKeyboardMarkup()

markup.add(
    types.InlineKeyboardButton(
        "✅ Выполнено",
        callback_data=f"w_done_{withdrawal_id}"
    ),
    types.InlineKeyboardButton(
        "❌ Отклонить",
        callback_data=f"w_cancel_{withdrawal_id}"
    )
)

admin_caption = f"""

{EMOJI['withdraw']}
<b>ЗАЯВКА НА ВЫВОД #{withdrawal_id}</b>

👤 Пользователь:
<code>{user_id}</code>

🆔 Аккаунт:
<code>{safe_html(account_id)}</code>

{EMOJI['money']} Сумма:
<b>{amount:.2f} сом</b>

💳 QR кошелька прикреплён.
"""

for admin_id in get_admins():

    send_media_bulletproof(
        admin_id,
        wallet_qr,
        caption=admin_caption,
        reply_markup=markup
    )

clear_user_messages(user_id)

send_msg(
    user_id,
    f"""

{EMOJI['check']}
<b>Заявка на вывод принята!</b>

{EMOJI['money']}
Сумма: <b>{amount:.2f} сом</b>

{EMOJI['clock']}
Ожидайте обработки оператором.
""",
reply_markup=main_menu(user_id)
)

temp_data.pop(
    user_id,
    None
)

=========================================================

10. АДМИН-ПАНЕЛЬ

=========================================================

@bot.message_handler(
func=lambda m: m.text in [
"⚙️ Admin",
"Admin"
] and is_admin(m.from_user.id)
)
def admin_panel(msg):

save_msg(
    msg.chat.id,
    msg.message_id
)

clear_user_messages(msg.chat.id)

send_msg(
    msg.chat.id,
    f"{EMOJI['admin']} "
    f"<b>Панель администратора</b>",
    reply_markup=admin_menu()
)

@bot.message_handler(
func=lambda m: m.text in [
"➕ Админ",
"Админ"
] and is_admin(m.from_user.id)
)
def add_admin_btn(msg):

clear_user_messages(msg.chat.id)

send_msg(
    msg.chat.id,
    f"{EMOJI['info']} "
    f"Введите Telegram ID нового администратора:",
    reply_markup=back_menu()
)

bot.register_next_step_handler(
    msg,
    process_add_admin
)

def process_add_admin(msg):

if msg.text == "🔙 Назад":

    admin_panel(msg)

    return

try:

    new_admin_id = int(
        msg.text.strip()
    )

    add_admin(new_admin_id)

    send_msg(
        msg.chat.id,
        f"{EMOJI['check']} "
        f"Администратор добавлен.",
        reply_markup=admin_menu()
    )

except Exception:

    send_msg(
        msg.chat.id,
        f"{EMOJI['cross']} "
        f"Введите корректный числовой ID.",
        reply_markup=back_menu()
    )

    bot.register_next_step_handler(
        msg,
        process_add_admin
    )

@bot.message_handler(
func=lambda m:
m.text in [
"🔴 ВЫКЛ",
"🟢 ВКЛ"
] and is_admin(m.from_user.id)
)
def toggle_bot(msg):

active = (
    msg.text == "🟢 ВКЛ"
)

set_bot_active(active)

send_msg(
    msg.chat.id,
    (
        f"{EMOJI['on']} "
        f"<b>Бот включён.</b>"
        if active
        else
        f"{EMOJI['off']} "
        f"<b>Бот отключён.</b>"
    ),
    reply_markup=admin_menu()
)

=========================================================

11. ИЗМЕНЕНИЕ QR

=========================================================

@bot.message_handler(
func=lambda m:
m.text == "🖼 Изменить QR"
and is_admin(m.from_user.id)
)
def change_qr(msg):

clear_user_messages(msg.chat.id)

send_msg(
    msg.chat.id,
    f"{EMOJI['qr']} "
    f"<b>Отправьте новый QR-код:</b>",
    reply_markup=back_menu()
)

bot.register_next_step_handler(
    msg,
    save_new_qr
)

def save_new_qr(msg):

if msg.text == "🔙 Назад":

    admin_panel(msg)

    return

file_id = None

if msg.photo:
    file_id = msg.photo[-1].file_id

elif msg.document:
    file_id = msg.document.file_id

if not file_id:

    send_msg(
        msg.chat.id,
        f"{EMOJI['cross']} "
        f"Отправьте изображение QR-кода."
    )

    bot.register_next_step_handler(
        msg,
        save_new_qr
    )

    return

save_qr(file_id)

send_msg(
    msg.chat.id,
    f"{EMOJI['check']} "
    f"<b>Новый QR-код сохранён.</b>",
    reply_markup=admin_menu()
)

=========================================================

12. ЗАЯВКИ НА ПОПОЛНЕНИЕ

=========================================================

@bot.message_handler(
func=lambda m: m.text in [
"📋 Заявки",
"Заявки"
] and is_admin(m.from_user.id)
)
def view_requests(msg):

clear_user_messages(msg.chat.id)

deposits = get_pending_deposits()

if not deposits:

    send_msg(
        msg.chat.id,
        f"{EMOJI['check']} "
        f"<b>Нет активных заявок.</b>",
        reply_markup=admin_menu()
    )

    return

for dep in deposits:

    (
        dep_id,
        user_id,
        amount,
        account_id,
        photo_id,
        date,
        timestamp
    ) = dep

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✅ Одобрить",
            callback_data=f"approve_{dep_id}"
        ),
        types.InlineKeyboardButton(
            "❌ Отклонить",
            callback_data=f"reject_{dep_id}"
        )
    )

    caption = f"""

{EMOJI['lightning']}
<b>ЗАЯВКА #{dep_id}</b>

👤 Пользователь:
<code>{user_id}</code>

{EMOJI['money']}
<b>{amount:.2f} сом</b>

🆔
<code>{safe_html(account_id)}</code>
"""

    send_media_bulletproof(
        msg.chat.id,
        photo_id,
        caption=caption,
        reply_markup=markup
    )

=========================================================

13. СТАТИСТИКА

=========================================================

@bot.message_handler(
func=lambda m:
m.text == "📈 Статистика"
and is_admin(m.from_user.id)
)
def stats(msg):

s = get_stats()

send_msg(
    msg.chat.id,
    f"""

{EMOJI['stats']}
<b>СТАТИСТИКА</b>

👥 Пользователей:
<b>{s['users']}</b>

{EMOJI['clock']}
Пополнений в очереди:
<b>{s['pending']}</b>

📤 Выводов в очереди:
<b>{s['pending_withdrawals']}</b>

{EMOJI['money']}
Одобренный объём:
<b>{s['total']:.2f} сом</b>
""",
reply_markup=admin_menu()
)

=========================================================

14. РАССЫЛКА

=========================================================

@bot.message_handler(
func=lambda m:
m.text == "📢 Рассылка"
and is_admin(m.from_user.id)
)
def broadcast_start(msg):

clear_user_messages(msg.chat.id)

send_msg(
    msg.chat.id,
    f"""

{EMOJI['broadcast']}
<b>Отправьте сообщение для рассылки.</b>

Можно отправить:
• текст;
• фото с подписью.
""",
reply_markup=back_menu()
)

bot.register_next_step_handler(
    msg,
    broadcast_send
)

def broadcast_send(msg):

if msg.text == "🔙 Назад":

    admin_panel(msg)

    return

users = get_all_users()

success = 0

photo_id = (
    msg.photo[-1].file_id
    if msg.photo
    else None
)

text = (
    msg.caption
    if msg.caption
    else msg.text
)

for user_id in users:

    try:

        if photo_id:

            bot.send_photo(
                user_id,
                photo_id,
                caption=text,
                parse_mode="HTML"
            )

        elif text:

            bot.send_message(
                user_id,
                text,
                parse_mode="HTML"
            )

        success += 1

    except Exception:
        pass

    time.sleep(0.04)

send_msg(
    msg.chat.id,
    f"""

{EMOJI['check']}
<b>Рассылка завершена.</b>

Отправлено: {success}/{len(users)}
""",
reply_markup=admin_menu()
)

=========================================================

15. CALLBACK КНОПКИ АДМИНА

=========================================================

@bot.callback_query_handler(
func=lambda call:
call.data.startswith(
(
"approve_",
"reject_",
"w_done_",
"w_cancel_"
)
)
)
def handle_admin_callbacks(call):

if not is_admin(call.from_user.id):

    bot.answer_callback_query(
        call.id,
        "❌ Нет доступа."
    )

    return

data = call.data


# -----------------------------------------------------
# ОДОБРЕНИЕ ПОПОЛНЕНИЯ
# -----------------------------------------------------

if data.startswith("approve_"):

    dep_id = int(
        data.split("_")[1]
    )

    with sqlite3.connect(
        DB_NAME,
        timeout=10
    ) as conn:

        c = conn.cursor()

        c.execute("""
            SELECT
                user_id,
                amount,
                account_id,
                timestamp,
                status
            FROM deposits
            WHERE id = ?
        """, (dep_id,))

        row = c.fetchone()

        if not row:

            bot.answer_callback_query(
                call.id,
                "Заявка не найдена."
            )

            return

        (
            user_id,
            amount,
            account_id,
            timestamp,
            status
        ) = row

        if status != "pending":

            bot.answer_callback_query(
                call.id,
                "Заявка уже обработана."
            )

            return

        c.execute("""
            UPDATE deposits
            SET status = "approved"
            WHERE id = ?
            AND status = "pending"
        """, (dep_id,))

        conn.commit()

    elapsed = max(
        0,
        int(time.time()) - timestamp
    )

    bot.answer_callback_query(
        call.id,
        "✅ Заявка одобрена."
    )

    try:

        bot.send_message(
            user_id,
            f"""

{EMOJI['check']}
<b>Ваша заявка одобрена!</b>

{EMOJI['money']}
Сумма: <b>{amount:.2f} сом</b>

🆔 Счёт:
<code>{safe_html(account_id)}</code>

{EMOJI['clock']}
Обработано за: <b>{elapsed} сек.</b>
""",
parse_mode="HTML"
)

    except Exception:
        pass

    try:

        bot.edit_message_caption(
            f"""

{EMOJI['check']}
<b>ЗАЯВКА #{dep_id} ОДОБРЕНА</b>
""",
call.message.chat.id,
call.message.message_id,
parse_mode="HTML"
)

    except Exception:
        pass


# -----------------------------------------------------
# ОТКЛОНЕНИЕ ПОПОЛНЕНИЯ
# -----------------------------------------------------

elif data.startswith("reject_"):

    dep_id = int(
        data.split("_")[1]
    )

    with sqlite3.connect(
        DB_NAME,
        timeout=10
    ) as conn:

        c = conn.cursor()

        c.execute("""
            SELECT
                user_id,
                amount,
                status
            FROM deposits
            WHERE id = ?
        """, (dep_id,))

        row = c.fetchone()

        if not row:

            bot.answer_callback_query(
                call.id,
                "Заявка не найдена."
            )

            return

        user_id, amount, status = row

        if status != "pending":

            bot.answer_callback_query(
                call.id,
                "Заявка уже обработана."
            )

            return

        c.execute("""
            UPDATE deposits
            SET status = "rejected"
            WHERE id = ?
            AND status = "pending"
        """, (dep_id,))

        conn.commit()

    bot.answer_callback_query(
        call.id,
        "❌ Заявка отклонена."
    )

    try:

        bot.send_message(
            user_id,
            f"""

{EMOJI['cross']}
<b>Заявка на {amount:.2f} сом отклонена.</b>

{EMOJI['support']}
Поддержка: {SUPPORT}
""",
parse_mode="HTML"
)

    except Exception:
        pass

    try:

        bot.edit_message_caption(
            f"""

{EMOJI['cross']}
<b>ЗАЯВКА #{dep_id} ОТКЛОНЕНА</b>
""",
call.message.chat.id,
call.message.message_id,
parse_mode="HTML"
)

    except Exception:
        pass


# -----------------------------------------------------
# ВЫВОД ВЫПОЛНЕН
# -----------------------------------------------------

elif data.startswith("w_done_"):

    withdrawal_id = int(
        data.split("_")[2]
    )

    with sqlite3.connect(
        DB_NAME,
        timeout=10
    ) as conn:

        c = conn.cursor()

        c.execute("""
            SELECT
                user_id,
                status
            FROM withdrawals
            WHERE id = ?
        """, (withdrawal_id,))

        row = c.fetchone()

        if not row:

            bot.answer_callback_query(
                call.id,
                "Заявка не найдена."
            )

            return

        user_id, status = row

        if status != "pending":

            bot.answer_callback_query(
                call.id,
                "Заявка уже обработана."
            )

            return

        c.execute("""
            UPDATE withdrawals
            SET status = "completed"
            WHERE id = ?
            AND status = "pending"
        """, (withdrawal_id,))

        conn.commit()

    bot.answer_callback_query(
        call.id,
        "✅ Вывод отмечен выполненным."
    )

    try:

        bot.send_message(
            user_id,
            f"""

{EMOJI['check']}
<b>Ваша заявка на вывод #{withdrawal_id}
успешно обработана.</b>
""",
parse_mode="HTML"
)

    except Exception:
        pass


# -----------------------------------------------------
# ВЫВОД ОТКЛОНЁН
# -----------------------------------------------------

elif data.startswith("w_cancel_"):

    withdrawal_id = int(
        data.split("_")[2]
    )

    with sqlite3.connect(
        DB_NAME,
        timeout=10
    ) as conn:

        c = conn.cursor()

        c.execute("""
            SELECT
                user_id,
                status
            FROM withdrawals
            WHERE id = ?
        """, (withdrawal_id,))

        row = c.fetchone()

        if not row:

            bot.answer_callback_query(
                call.id,
                "Заявка не найдена."
            )

            return

        user_id, status = row

        if status != "pending":

            bot.answer_callback_query(
                call.id,
                "Заявка уже обработана."
            )

            return

        c.execute("""
            UPDATE withdrawals
            SET status = "rejected"
            WHERE id = ?
            AND status = "pending"
        """, (withdrawal_id,))

        conn.commit()

    bot.answer_callback_query(
        call.id,
        "❌ Заявка отклонена."
    )

    try:

        bot.send_message(
            user_id,
            f"""

{EMOJI['cross']}
<b>Ваша заявка на вывод #{withdrawal_id}
отклонена.</b>

{EMOJI['support']}
Поддержка: {SUPPORT}
""",
parse_mode="HTML"
)

    except Exception:
        pass

=========================================================

16. FLASK

=========================================================

@app.route("/")
def home():

return {
    "status": "ok",
    "message": f"{BOT_NAME} is active"
}, 200

=========================================================

17. ЗАПУСК TELEGRAM BOT

=========================================================

def run_bot():

print(
    f"🚀 Запуск бота {BOT_NAME}..."
)

try:

    bot.remove_webhook(
        drop_pending_updates=True
    )

    time.sleep(1)

except Exception as e:

    print(
        f"Ошибка remove_webhook: {e}"
    )

while True:

    try:

        bot.infinity_polling(
            timeout=30,
            long_polling_timeout=30
        )

    except Exception as e:

        print(
            f"Ошибка Telegram: {e}"
        )

        time.sleep(5)

=========================================================

18. MAIN

=========================================================

if name == "main":

bot_thread = threading.Thread(
    target=run_bot,
    daemon=True
)

bot_thread.start()

port = int(
    os.environ.get(
        "PORT",
        5000
    )
)

app.run(
    host="0.0.0.0",
    port=port
)
