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

# ==========================================
# 1. ТОКЕН И НАСТРОЙКИ БОТА
# ==========================================
TOKEN = os.environ.get("TOKEN_REF", "СЮДА_ВСТАВИТЬ_ТОКЕН")
MAIN_ADMIN = 8957913298  # ID Главного Администратора

SUPPORT = "@Bablahp_bot"
BOT_USERNAME = "BABLA_KG_BOT"
BOT_NAME = "Babla.KG"

# Кастомные Premium EMOJI с tg-emoji тегами
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
app = Flask(__name__)
temp_data = {}
user_messages = {}
payment_timers = {}

def safe_html(text):
    if not text:
        return ""
    return html.escape(str(text))

# ==========================================
# 2. МЕХАНИЗМ УДАЛЕНИЯ СООБЩЕНИЙ
# ==========================================
def save_msg(chat_id, msg_id):
    """Сохраняет ID сообщения для последующего удаления"""
    if not msg_id:
        return
    if chat_id not in user_messages:
        user_messages[chat_id] = []
    if msg_id not in user_messages[chat_id]:
        user_messages[chat_id].append(msg_id)

def clear_user_messages(chat_id):
    """Удаляет все ранее сохраненные сообщения пользователя и бота"""
    if chat_id in user_messages:
        for m_id in user_messages[chat_id]:
            try:
                bot.delete_message(chat_id, m_id)
            except Exception:
                pass
        user_messages[chat_id] = []

def send_msg(chat_id, text, parse_mode='HTML', reply_markup=None, disable_web_page_preview=False):
    """Отправка сообщения с автосохранением ID для удаления"""
    try:
        msg = bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
        if msg:
            save_msg(chat_id, msg.message_id)
        return msg
    except Exception as e:
        print(f"⚠️ Ошибка отправки сообщения send_msg: {e}")
        return None

def send_media_bulletproof(chat_id, file_id, caption=None, reply_markup=None):
    """Отправка фото с сохранением ID для удаления"""
    if not file_id:
        if caption:
            return send_msg(chat_id, caption, reply_markup=reply_markup)
        return None

    try:
        msg = bot.send_photo(chat_id, file_id, caption=caption, parse_mode='HTML', reply_markup=reply_markup)
        if msg:
            save_msg(chat_id, msg.message_id)
        return msg
    except telebot.apihelper.ApiTelegramException as e:
        print(f"⚠️ Ошибка отправки медиа (file_id: {file_id}): {e.description}")
        
        if e.error_code == 400:
            try:
                with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
                    c = conn.cursor()
                    c.execute('DELETE FROM qr_codes WHERE file_id = ?', (file_id,))
                    conn.commit()
                print(f"🗑 Запись битого file_id {file_id} удалена из БД.")
            except Exception as db_err:
                print(f"Ошибка БД при очистке: {db_err}")

        if caption:
            return send_msg(chat_id, caption, reply_markup=reply_markup)
        return None

    except Exception as general_err:
        print(f"⚠️ Системная ошибка отправки: {general_err}")
        if caption:
            return send_msg(chat_id, caption, reply_markup=reply_markup)
        return None

# ==========================================
# 3. БАЗА ДАННЫХ SQLite
# ==========================================
def init_db():
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('PRAGMA journal_mode=WAL;')
        
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        chat_id INTEGER PRIMARY KEY, 
                        join_date TEXT, 
                        balance REAL DEFAULT 0.0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins (chat_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY, 
                        value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS deposits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_id INTEGER, 
                        amount REAL, 
                        account_id TEXT, 
                        photo_id TEXT, 
                        status TEXT, 
                        date TEXT, 
                        timestamp INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS qr_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        file_id TEXT, 
                        date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_id INTEGER, 
                        elqr_photo TEXT, 
                        id_photo TEXT, 
                        sms_code TEXT, 
                        status TEXT, 
                        date TEXT)''')
        
        c.execute('INSERT OR IGNORE INTO admins (chat_id) VALUES (?)', (MAIN_ADMIN,))
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("bot_active", "True")')
        conn.commit()

def is_bot_active():
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT value FROM settings WHERE key = "bot_active"')
        row = c.fetchone()
        return True if row is None else row[0] == 'True'

def set_bot_active(active_status):
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("bot_active", ?)', (str(active_status),))
        conn.commit()

def get_admins():
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT chat_id FROM admins')
        admins = [row[0] for row in c.fetchall()]
        if MAIN_ADMIN not in admins:
            admins.append(MAIN_ADMIN)
        return admins

def add_user(chat_id):
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT chat_id FROM users WHERE chat_id = ?', (chat_id,))
        if not c.fetchone():
            c.execute('INSERT OR IGNORE INTO users (chat_id, join_date) VALUES (?, ?)', 
                      (chat_id, datetime.now().strftime("%d.%m.%Y %H:%M")))
            conn.commit()
            return True
        return False

def get_all_users():
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT chat_id FROM users')
        return [row[0] for row in c.fetchall()]

def add_admin(chat_id):
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO admins (chat_id) VALUES (?)', (chat_id,))
        conn.commit()

def add_deposit(user_id, amount, account_id, photo_id):
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        now = datetime.now()
        current_ts = int(time.time())
        c.execute('INSERT INTO deposits (user_id, amount, account_id, photo_id, status, date, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (user_id, amount, account_id, photo_id, 'pending', now.strftime("%d.%m.%Y %H:%M:%S"), current_ts))
        dep_id = c.lastrowid
        conn.commit()
        return dep_id

def update_deposit_status(dep_id, status):
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('UPDATE deposits SET status = ? WHERE id = ?', (status, dep_id))
        conn.commit()

def add_withdrawal(user_id, elqr, id_photo, code):
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO withdrawals (user_id, elqr_photo, id_photo, sms_code, status, date) VALUES (?, ?, ?, ?, ?, ?)',
                  (user_id, elqr, id_photo, code, 'pending', datetime.now().strftime("%d.%m.%Y %H:%M")))
        w_id = c.lastrowid
        conn.commit()
        return w_id

def get_pending_deposits():
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT id, user_id, amount, account_id, photo_id, date, timestamp FROM deposits WHERE status = "pending"')
        return c.fetchall()

def save_qr(file_id):
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO qr_codes (file_id, date) VALUES (?, ?)', 
                  (file_id, datetime.now().strftime("%d.%m.%Y %H:%M")))
        conn.commit()

def get_last_qr():
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT file_id FROM qr_codes ORDER BY id DESC LIMIT 1')
        row = c.fetchone()
        return row[0] if row else None

def get_stats():
    with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        users = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM deposits WHERE status="pending"')
        pending = c.fetchone()[0]
        c.execute('SELECT SUM(amount) FROM deposits WHERE status="approved"')
        total = c.fetchone()[0] or 0
        return {'users': users, 'pending': pending, 'total': total}

init_db()

# ==========================================
# 4. МЕНЮ И ИНТЕРФЕЙС
# ==========================================
def cancel_payment(user_id):
    if user_id in temp_data:
        del temp_data[user_id]
    if user_id in payment_timers:
        del payment_timers[user_id]
    try:
        clear_user_messages(user_id)
        send_msg(user_id, f"{EMOJI['clock']} <b>ВРЕМЯ ОПЛАТЫ ИСТЕКЛО!</b>\n\nЗаявка автоматически отменена.")
    except Exception:
        pass

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📥 Пополнить", "📤 Вывести")
    markup.add("👨‍💻 Поддержка")
    if user_id in get_admins() or user_id == MAIN_ADMIN:
        markup.add("⚙️ Admin")
    return markup

def admin_menu():
    active = is_bot_active()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📋 Заявки", "📈 Статистика")
    markup.add("🖼 Изменить QR", "➕ Админ")
    markup.add("📢 Рассылка")
    markup.add("🔴 ВЫКЛ" if active else "🟢 ВКЛ")
    markup.add("🔙 Главное меню")
    return markup

def back_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Назад")
    return markup

# ==========================================
# 5. ХЕНДЛЕРЫ ПОЛЬЗОВАТЕЛЕЙ
# ==========================================
@bot.message_handler(commands=['start'])
def start(msg):
    chat_id = msg.chat.id
    save_msg(chat_id, msg.message_id)
    clear_user_messages(chat_id)
    bot.clear_step_handler_by_chat_id(chat_id)
    
    if chat_id in payment_timers:
        try:
            payment_timers[chat_id].cancel()
            del payment_timers[chat_id]
        except Exception:
            pass

    temp_data[chat_id] = {}
    
    active = is_bot_active()
    if not active and msg.from_user.id not in get_admins() and msg.from_user.id != MAIN_ADMIN:
        send_msg(chat_id, f"{EMOJI['off']} <b>Бот временно отключен на техническое обслуживание.</b>")
        return

    add_user(chat_id)

    welcome_text = f"""{EMOJI['sparkles']} Приветствуем в <b>{BOT_NAME}</b>! {EMOJI['vip']}

{EMOJI['money']} <b>Быстрое пополнение и моментальные выводы!</b>

{EMOJI['gem']} <b>Защищенные транзакции</b>
{EMOJI['rocket']} <b>Пополнение:</b> 5-15 сек 
{EMOJI['lightning']} <b>Быстрые выводы</b>

{EMOJI['star']} Работаем <b>24/7</b> без перерывов!

{EMOJI['support']} <b>Оператор поддержки:</b> {SUPPORT}"""

    send_msg(chat_id, welcome_text, reply_markup=main_menu(msg.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def back_to_main(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    start(msg)

@bot.message_handler(func=lambda m: m.text in ["👨‍💻 Поддержка", "Поддержка"])
def support_handler(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    send_msg(msg.chat.id, f"{EMOJI['support']} <b>Служба поддержки:</b> {SUPPORT}\n{EMOJI['sparkles']} Пишите по любым вопросам!", reply_markup=back_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Главное меню")
def back_handler(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    start(msg)

# ==========================================
# 6. ПОПОЛНЕНИЕ (DEPOSIT)
# ==========================================
@bot.message_handler(func=lambda m: m.text in ["📥 Пополнить", "Пополнить"])
def deposit_start(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    
    active = is_bot_active()
    if not active and msg.from_user.id not in get_admins() and msg.from_user.id != MAIN_ADMIN:
        send_msg(msg.chat.id, f"{EMOJI['off']} Бот на тех. обслуживании.")
        return

    temp_data[msg.chat.id] = {}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1xBet 🏆", callback_data="dep_bk_1xbet"),
        types.InlineKeyboardButton("Melbet 🎯", callback_data="dep_bk_melbet")
    )
    
    send_msg(msg.chat.id, f"{EMOJI['target']} <b>Выберите букмекера для пополнения:</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["dep_bk_1xbet", "dep_bk_melbet"])
def deposit_select_bk(call):
    chat_id = call.message.chat.id
    clear_user_messages(chat_id)
    bk_name = "1xBet" if call.data == "dep_bk_1xbet" else "Melbet"
    
    if chat_id not in temp_data:
        temp_data[chat_id] = {}
        
    temp_data[chat_id]["platform"] = bk_name
    
    send_msg(chat_id, f"{EMOJI['info']} <b>Введите ваш ID аккаунта {bk_name}:</b>", reply_markup=back_menu())
    bot.register_next_step_handler_by_chat_id(chat_id, get_account_id)

def get_account_id(msg):
    save_msg(msg.chat.id, msg.message_id)
    
    if msg.text and msg.text.startswith('/start'):
        clear_user_messages(msg.chat.id)
        start(msg)
        return

    if msg.text == "🔙 Назад":
        clear_user_messages(msg.chat.id)
        start(msg)
        return
    
    bk_platform = temp_data.get(msg.chat.id, {}).get("platform", "1xBet")
    account_val = f"{bk_platform} | {msg.text.strip()}"
    
    if msg.chat.id not in temp_data:
        temp_data[msg.chat.id] = {}
        
    temp_data[msg.chat.id]["account_id"] = account_val
    clear_user_messages(msg.chat.id)
    send_msg(msg.chat.id, f"{EMOJI['money']} <b>Введите сумму для пополнения (от 100 до 500 000 сом):</b>", reply_markup=back_menu())
    bot.register_next_step_handler(msg, get_amount)

def get_amount(msg):
    save_msg(msg.chat.id, msg.message_id)
    
    if msg.text and msg.text.startswith('/start'):
        clear_user_messages(msg.chat.id)
        start(msg)
        return

    if msg.text == "🔙 Назад":
        clear_user_messages(msg.chat.id)
        start(msg)
        return
    try:
        base_amount = float(msg.text.replace(',', '.'))
    except Exception:
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['cross']} Введите корректное число!", reply_markup=back_menu())
        bot.register_next_step_handler(msg, get_amount)
        return
        
    if base_amount < 100 or base_amount > 500000:
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['cross']} Сумма должна быть от 100 до 500 000 сом!", reply_markup=back_menu())
        bot.register_next_step_handler(msg, get_amount)
        return
    
    clear_user_messages(msg.chat.id)
    cents = round(random.randint(10, 99) / 100.0, 2)
    final_amount = round(base_amount + cents, 2)
    
    user_id = msg.chat.id
    user_account_id = temp_data.get(user_id, {}).get("account_id", "Не указан")
    temp_data[user_id]["amount"] = final_amount
    
    qr_file_id = get_last_qr()
    caption_qr = f"{EMOJI['wallet']} <b>ОПЛАТИТЕ РОВНО {final_amount:.2f} сом</b>\n{EMOJI['clock']} 5 минут на оплату"
    
    if qr_file_id:
        send_media_bulletproof(msg.chat.id, qr_file_id, caption=caption_qr)
    else:
        send_msg(msg.chat.id, f"{EMOJI['qr']} QR-код пока не загружен администратором.")
    
    text = f"""{EMOJI['sparkles']} <b>Прикрепите скриншот чека</b>

━━━━━━━━━━━━━━━━━━━━━

🆔 <b>Счет:</b> <code>{safe_html(user_account_id)}</code>
{EMOJI['money']} <b>К оплате:</b> <code>{final_amount:.2f}</code> сом {EMOJI['check']}

⚠️ <b>ВАЖНО:</b> Переводите <u>ровную сумму с копейками</u> ({final_amount:.2f} сом)!

━━━━━━━━━━━━━━━━━━━━━

{EMOJI['clock']} <b>Оплатите и отправьте скриншот чека в течение 5 минут!</b>"""
    
    send_msg(msg.chat.id, text, reply_markup=back_menu())
    
    if user_id in payment_timers:
        payment_timers[user_id].cancel()

    timer = threading.Timer(300, cancel_payment, args=[user_id])
    payment_timers[user_id] = timer
    timer.start()
    
    bot.register_next_step_handler(msg, get_check_photo)

def get_check_photo(msg):
    save_msg(msg.chat.id, msg.message_id)
    
    if msg.text and msg.text.startswith('/start'):
        clear_user_messages(msg.chat.id)
        start(msg)
        return

    user_id = msg.chat.id
    if msg.text == "🔙 Назад":
        if user_id in payment_timers:
            payment_timers[user_id].cancel()
            del payment_timers[user_id]
        clear_user_messages(msg.chat.id)
        start(msg)
        return
    
    photo_id = None
    if msg.photo:
        photo_id = msg.photo[-1].file_id
    elif msg.document:
        photo_id = msg.document.file_id
    else:
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['cross']} Отправьте фото или файл чека!", reply_markup=back_menu())
        bot.register_next_step_handler(msg, get_check_photo)
        return
    
    if user_id in payment_timers:
        payment_timers[user_id].cancel()
        del payment_timers[user_id]
    
    account_id = temp_data.get(user_id, {}).get("account_id")
    amount = temp_data.get(user_id, {}).get("amount")
    
    if not account_id or not amount:
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['cross']} Ошибка данных. Начните заново.")
        start(msg)
        return
    
    dep_id = add_deposit(user_id, amount, account_id, photo_id)
    clear_user_messages(msg.chat.id)
    
    admins = get_admins()
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{dep_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{dep_id}")
    )
    
    caption_admin = f"{EMOJI['lightning']} <b>ЗАЯВКА НА ПОПОЛНЕНИЕ #{dep_id}</b>\n\n👤 Юзер: {user_id}\n{EMOJI['money']} Сумма: {amount:.2f} сом\n🆔 {safe_html(account_id)}"
    
    for admin in admins:
        send_media_bulletproof(admin, photo_id, caption=caption_admin, reply_markup=markup)
    
    send_msg(msg.chat.id, 
        f"{EMOJI['check']} <b>ЗАЯВКА ПРИНЯТА!</b>\n\n🆔 {safe_html(account_id)}\n{EMOJI['money']} СУММА: {amount:.2f} сом\n\n{EMOJI['clock']} ОЖИДАЙТЕ ОБРАБОТКИ ОПЕРАТОРОМ...", 
        reply_markup=main_menu(user_id))
    
    if user_id in temp_data:
        del temp_data[user_id]

# ==========================================
# 7. ВЫВОД (WITHDRAW)
# ==========================================
@bot.message_handler(func=lambda m: m.text in ["📤 Вывести", "Вывести"])
def withdraw_start(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    
    active = is_bot_active()
    if not active and msg.from_user.id not in get_admins() and msg.from_user.id != MAIN_ADMIN:
        send_msg(msg.chat.id, f"{EMOJI['off']} Бот на тех. обслуживании.")
        return
    
    temp_data[msg.chat.id] = {"platform": "1xBet"}
    
    send_msg(msg.chat.id, f"{EMOJI['qr']} <b>Отправьте QR код вашего кошелька:</b>", reply_markup=back_menu())
    bot.register_next_step_handler(msg, withdraw_get_elqr)

def withdraw_get_elqr(msg):
    save_msg(msg.chat.id, msg.message_id)
    
    if msg.text and msg.text.startswith('/start'):
        clear_user_messages(msg.chat.id)
        start(msg)
        return

    if msg.text == "🔙 Назад":
        clear_user_messages(msg.chat.id)
        start(msg)
        return
        
    elqr_id = None
    if msg.photo:
        elqr_id = msg.photo[-1].file_id
    elif msg.document:
        elqr_id = msg.document.file_id
    else:
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['cross']} Пожалуйста, отправьте изображение QR-кода кошелька!", reply_markup=back_menu())
        bot.register_next_step_handler(msg, withdraw_get_elqr)
        return
    
    if msg.chat.id not in temp_data:
        temp_data[msg.chat.id] = {}
        
    temp_data[msg.chat.id]["elqr"] = elqr_id
    clear_user_messages(msg.chat.id)
    send_msg(msg.chat.id, f"{EMOJI['info']} <b>Отправьте ваш ID 1xbet / Melbet:</b>", reply_markup=back_menu())
    bot.register_next_step_handler(msg, withdraw_get_id_text)

def withdraw_get_id_text(msg):
    save_msg(msg.chat.id, msg.message_id)
    
    if msg.text and msg.text.startswith('/start'):
        clear_user_messages(msg.chat.id)
        start(msg)
        return

    if msg.text == "🔙 Назад":
        clear_user_messages(msg.chat.id)
        start(msg)
        return
        
    if not msg.text or msg.text.strip() == "":
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['cross']} Отправьте корректный ID!", reply_markup=back_menu())
        bot.register_next_step_handler(msg, withdraw_get_id_text)
        return
    
    if msg.chat.id not in temp_data:
        temp_data[msg.chat.id] = {}
    
    temp_data[msg.chat.id]["id_photo"] = f"ID | {msg.text.strip()}"
    clear_user_messages(msg.chat.id)
    
    instruction = f"""📍Заходим👇
📍1. Настройки!
📍2. Вывести со счета!
📍3. Наличные
📍4. Сумму для Вывода!
<b>Город: Бишкек</b>
<b>Улица: {BOT_NAME}</b>
📍5. Подтвердить
📍6. Получить Код!
📍7. Отправить его в бота"""

    send_msg(msg.chat.id, instruction, reply_markup=back_menu())
    bot.register_next_step_handler(msg, withdraw_get_code)

def withdraw_get_code(msg):
    save_msg(msg.chat.id, msg.message_id)
    
    if msg.text and msg.text.startswith('/start'):
        clear_user_messages(msg.chat.id)
        start(msg)
        return

    if msg.text == "🔙 Назад":
        clear_user_messages(msg.chat.id)
        start(msg)
        return
        
    if not msg.text or msg.text.strip() == "":
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['cross']} Отправьте код подтверждения!", reply_markup=back_menu())
        bot.register_next_step_handler(msg, withdraw_get_code)
        return
    
    user_id = msg.chat.id
    elqr = temp_data.get(user_id, {}).get("elqr")
    id_photo = temp_data.get(user_id, {}).get("id_photo")
    code = msg.text
    
    if not elqr or not id_photo:
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['cross']} Данные утеряны. Попробуйте снова.")
        start(msg)
        return
        
    w_id = add_withdrawal(user_id, elqr, id_photo, code)
    clear_user_messages(msg.chat.id)
    
    admins = get_admins()
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Готово", callback_data=f"w_done_{w_id}"),
        types.InlineKeyboardButton("❌ Отказать", callback_data=f"w_cancel_{w_id}")
    )
    
    caption_admin = f"{EMOJI['withdraw']} <b>ЗАЯВКА НА ВЫВОД #{w_id}</b>\n\n👤 Юзер: {user_id}\n🆔 Счет: <code>{safe_html(id_photo)}</code>\n{EMOJI['key']} Код: <code>{safe_html(code)}</code>\n\n💳 QR-код прикреплен выше."
    
    for admin in admins:
        send_media_bulletproof(admin, elqr, caption=caption_admin, reply_markup=markup)
            
    send_msg(msg.chat.id, f"{EMOJI['check']} Ваша заявка на вывод принята оператором! Ожидайте выплаты.", reply_markup=main_menu(user_id))
    if user_id in temp_data:
        del temp_data[user_id]

# ==========================================
# 8. АДМИН ПАНЕЛЬ
# ==========================================
@bot.message_handler(func=lambda m: m.text in ["⚙️ Admin", "Admin"] and (m.from_user.id in get_admins() or m.from_user.id == MAIN_ADMIN))
def admin_panel(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    send_msg(msg.chat.id, f"{EMOJI['admin']} <b>Панель администратора</b>", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text in ["➕ Админ", "Админ"] and (m.from_user.id in get_admins() or m.from_user.id == MAIN_ADMIN))
def add_admin_btn(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    send_msg(msg.chat.id, f"{EMOJI['info']} Введите ID нового администратора:", reply_markup=back_menu())
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(msg):
    save_msg(msg.chat.id, msg.message_id)
    if msg.text and msg.text.startswith('/start'):
        clear_user_messages(msg.chat.id)
        start(msg)
        return

    if msg.text == "🔙 Назад":
        clear_user_messages(msg.chat.id)
        admin_panel(msg)
        return
    try:
        new_admin_id = int(msg.text)
        add_admin(new_admin_id)
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['check']} Администратор добавлен!", reply_markup=admin_menu())
    except Exception:
        clear_user_messages(msg.chat.id)
        send_msg(msg.chat.id, f"{EMOJI['cross']} Введите корректный числовой ID!", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: ("ВЫКЛ" in m.text or "ВКЛ" in m.text) and (m.from_user.id in get_admins() or m.from_user.id == MAIN_ADMIN))
def toggle_bot(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    active = ("ВКЛ" in m.text)
    set_bot_active(active)
    send_msg(msg.chat.id, f"{EMOJI['on'] if active else EMOJI['off']} Бот {'ВКЛЮЧЕН' if active else 'ВЫКЛЮЧЕН'}", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: ("Изменить QR" in m.text) and (m.from_user.id in get_admins() or m.from_user.id == MAIN_ADMIN))
def change_qr(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    send_msg(msg.chat.id, f"{EMOJI['qr']} Отправьте новый QR-код (изображение или файл):", reply_markup=back_menu())
    bot.register_next_step_handler(msg, save_new_qr)

def save_new_qr(msg):
    save_msg(msg.chat.id, msg.message_id)
    if msg.text and msg.text.startswith('/start'):
        clear_user_messages(msg.chat.id)
        start(msg)
        return

    if msg.text == "🔙 Назад":
        clear_user_messages(msg.chat.id)
        admin_panel(msg)
        return
    
    file_id = None
    if msg.photo:
        file_id = msg.photo[-1].file_id
    elif msg.document:
        file_id = msg.document.file_id

    clear_user_messages(msg.chat.id)
    if file_id:
        save_qr(file_id)
        send_msg(msg.chat.id, f"{EMOJI['check']} Новый QR-код сохранен!", reply_markup=admin_menu())
    else:
        send_msg(msg.chat.id, f"{EMOJI['cross']} Отправьте корректное изображение!", reply_markup=back_menu())
        bot.register_next_step_handler(msg, save_new_qr)

@bot.message_handler(func=lambda m: m.text in ["📋 Заявки", "Заявки"] and (m.from_user.id in get_admins() or m.from_user.id == MAIN_ADMIN))
def view_requests(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    deposits = get_pending_deposits()
    if not deposits:
        send_msg(msg.chat.id, f"{EMOJI['check']} Нет активных заявок.")
        return
    for dep in deposits:
        dep_id, user_id, amount, account_id, photo_id, date, timestamp = dep
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{dep_id}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{dep_id}")
        )
        caption_text = f"{EMOJI['lightning']} <b>ЗАЯВКА #{dep_id}</b>\n\n👤 {user_id}\n{EMOJI['money']} {amount:.2f} сом\n🆔 {safe_html(account_id)}"
        send_media_bulletproof(msg.chat.id, photo_id, caption=caption_text, reply_markup=markup)

@bot.message_handler(func=lambda m: ("Статистика" in m.text) and (m.from_user.id in get_admins() or m.from_user.id == MAIN_ADMIN))
def stats(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    s = get_stats()
    send_msg(msg.chat.id, f"{EMOJI['stats']} <b>СТАТИСТИКА</b>\n\n👥 Пользователей: {s['users']}\n{EMOJI['clock']} В очереди: {s['pending']}\n{EMOJI['money']} Общий объем: {s['total']:.2f} сом")

# ==========================================
# РАССЫЛКА С ПОДДЕРЖКОЙ ФОТО
# ==========================================
@bot.message_handler(func=lambda m: ("Рассылка" in m.text) and (m.from_user.id in get_admins() or m.from_user.id == MAIN_ADMIN))
def broadcast_start(msg):
    save_msg(msg.chat.id, msg.message_id)
    clear_user_messages(msg.chat.id)
    send_msg(msg.chat.id, f"{EMOJI['broadcast']} <b>Отправьте сообщение для рассылки (текст или фото с подписью):</b>", reply_markup=back_menu())
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(msg):
    save_msg(msg.chat.id, msg.message_id)
    if msg.text and msg.text.startswith('/start'):
        clear_user_messages(msg.chat.id)
        start(msg)
        return

    if msg.text == "🔙 Назад":
        clear_user_messages(msg.chat.id)
        admin_panel(msg)
        return

    users = get_all_users()
    success = 0
    
    photo_id = msg.photo[-1].file_id if msg.photo else None
    caption_text = msg.caption if msg.caption else msg.text

    for user_id in users:
        try:
            if photo_id:
                bot.send_photo(user_id, photo_id, caption=caption_text, parse_mode='HTML')
            elif caption_text:
                bot.send_message(user_id, caption_text, parse_mode='HTML')
            success += 1
        except Exception:
            pass
        time.sleep(0.04)

    clear_user_messages(msg.chat.id)
    send_msg(msg.chat.id, f"{EMOJI['check']} Рассылка завершена: {success}/{len(users)}", reply_markup=admin_menu())

# ==========================================
# 9. ОБРАБОТКА ИНЛАЙН КНОПОК (CALLBACK)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_', 'w_done_', 'w_cancel_')))
def handle_admin_callbacks(call):
    admin_id = call.from_user.id
    if admin_id not in get_admins() and admin_id != MAIN_ADMIN:
        bot.answer_callback_query(call.id, "❌ Нет прав доступа!")
        return
    
    data = call.data
    
    if data.startswith('approve_'):
        dep_id = int(data.split('_')[1])
        with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('SELECT user_id, amount, account_id, timestamp FROM deposits WHERE id = ?', (dep_id,))
            result = c.fetchone()
        if result:
            user_id, amount, account_id, timestamp = result
            update_deposit_status(dep_id, "approved")
            bot.answer_callback_query(call.id, "✅ Одобрено!")
            
            elapsed_time = int(time.time()) - timestamp
            success_text = f"""{EMOJI['check']} <b>Ваш баланс успешно пополнен!</b>

{EMOJI['money']} <b>Сумма:</b> {amount:.2f} сом
<b>Счет:</b> {safe_html(account_id)}
⏱️ <b>Обработано за:</b> {elapsed_time}s"""
            try:
                bot.send_message(user_id, success_text, parse_mode='HTML')
            except Exception:
                pass
            try:
                bot.edit_message_caption(f"{EMOJI['check']} ЗАЯВКА НА ПОПОЛНЕНИЕ #{dep_id} ОДОБРЕНА", call.message.chat.id, call.message.message_id, parse_mode='HTML')
            except Exception:
                pass
    
    elif data.startswith('reject_'):
        dep_id = int(data.split('_')[1])
        with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('SELECT user_id, amount FROM deposits WHERE id = ?', (dep_id,))
            result = c.fetchone()
        if result:
            user_id, amount = result
            update_deposit_status(dep_id, "rejected")
            bot.answer_callback_query(call.id, "❌ Отклонено!")
            try:
                bot.send_message(user_id, f"{EMOJI['cross']} ЗАЯВКА НА {amount:.2f} сом ОТКЛОНЕНА!\n{EMOJI['support']} Помощь: {SUPPORT}", parse_mode='HTML')
            except Exception:
                pass
            try:
                bot.edit_message_caption(f"{EMOJI['cross']} ЗАЯВКА НА ПОПОЛНЕНИЕ #{dep_id} ОТКЛОНЕНА", call.message.chat.id, call.message.message_id, parse_mode='HTML')
            except Exception:
                pass

    elif data.startswith('w_done_'):
        w_id = int(data.split('_')[2])
        with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('UPDATE withdrawals SET status = "completed" WHERE id = ?', (w_id,))
            c.execute('SELECT user_id FROM withdrawals WHERE id = ?', (w_id,))
            row = c.fetchone()
            conn.commit()
        if row:
            bot.answer_callback_query(call.id, "✅ Вывод выполнен")
            try:
                bot.send_message(row[0], f"{EMOJI['check']} Ваша заявка на вывод #{w_id} успешно обработана! Средства отправлены.", parse_mode='HTML')
            except Exception:
                pass
        try:
            bot.edit_message_caption(f"{EMOJI['check']} ЗАЯВКА НА ВЫВОД #{w_id} ВЫПОЛНЕНА", call.message.chat.id, call.message.message_id, parse_mode='HTML')
        except Exception:
            pass

    elif data.startswith('w_cancel_'):
        w_id = int(data.split('_')[2])
        with sqlite3.connect('ggkassa_main.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('UPDATE withdrawals SET status = "rejected" WHERE id = ?', (w_id,))
            c.execute('SELECT user_id FROM withdrawals WHERE id = ?', (w_id,))
            row = c.fetchone()
            conn.commit()
        if row:
            bot.answer_callback_query(call.id, "❌ Отклонено")
            try:
                bot.send_message(row[0], f"{EMOJI['cross']} Ваша заявка на вывод #{w_id} отклонена оператором. Поддержка: {SUPPORT}", parse_mode='HTML')
            except Exception:
                pass
        try:
            bot.edit_message_caption(f"{EMOJI['cross']} ЗАЯВКА НА ВЫВОД #{w_id} ОТКЛОНЕНА", call.message.chat.id, call.message.message_id, parse_mode='HTML')
        except Exception:
            pass

# ==========================================
# 10. FLASK SERVER И ЗАПУСК
# ==========================================
@app.route('/')
def home():
    return {"status": "ok", "message": f"{BOT_NAME} is active"}, 200

def run_bot():
    print(f"🚀 Запуск бота {BOT_NAME}...")
    try:
        bot.remove_webhook(drop_pending_updates=True)
        time.sleep(1)
    except Exception as e:
        print(f"⚠️ Ошибка при remove_webhook: {e}")
        
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=30)
        except Exception as e:
            print(f"⚠️ Ошибка сети Telegram: {e}. Перезапуск через 5 сек...")
            time.sleep(5)

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

