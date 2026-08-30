import os
import logging
import time
import threading
from flask import Flask
import telebot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN_REF") or os.environ.get("TOKEN")
logger.info(f"TOKEN получен: {bool(TOKEN)} | длина: {len(TOKEN) if TOKEN else 0}")

if not TOKEN or len(TOKEN) < 30:
    logger.error("ТОКЕН НЕ НАЙДЕН ИЛИ НЕПРАВИЛЬНЫЙ!")
    raise SystemExit("No token")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f"Получена команда /start от {message.chat.id}")
    bot.reply_to(message, "✅ Бот работает! Привет!")

@bot.message_handler(func=lambda m: True)
def echo(message):
    logger.info(f"Сообщение от {message.chat.id}: {message.text}")
    bot.reply_to(message, f"Я получил: {message.text}")

@app.route('/')
def home():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        logger.info("Webhook удалён")
    except Exception as e:
        logger.warning(f"remove_webhook: {e}")

    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port)

    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Flask запущен")

    logger.info("Запускаю polling...")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=40)
        except Exception as e:
            logger.error(f"Ошибка polling: {e}")
            time.sleep(5)
