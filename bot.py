import telebot
import requests
import json
import os
import hmac
import hashlib
import base64
from datetime import datetime

# === НАСТРОЙКИ ===
BOT_TOKEN = '7620910107:AAFbbfyZIaijTYTuUZxbAJ3tDUfywcxUAMA'
WAYFORPAY_LINK = 'https://secure.wayforpay.com/button/b55749e6e1ec8'
COURSE_LINK = 'https://t.me/+b-d546qUk0Q0MzUy'
MERCHANT_ACCOUNT = 'your_merchant_login'       # ← Вставь свой логин WayForPay
MERCHANT_SECRET_KEY = 'your_secret_key'        # ← Вставь свой секретный ключ
ORDER_REFERENCE = 'botox_course'               # будет дополнен user_id
ADMIN_ID = 902623569

bot = telebot.TeleBot(BOT_TOKEN)
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_signature(data_dict, secret_key):
    ordered_keys = [
        'merchantAccount',
        'orderReference',
        'orderDate',
    ]
    signature_str = ';'.join([str(data_dict[key]) for key in ordered_keys])
    signature = base64.b64encode(
        hmac.new(secret_key.encode(), signature_str.encode(), hashlib.md5).digest()
    ).decode()
    return signature

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{user_id}"
    args = message.text.split()

    # Загружаем пользователей
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    else:
        users = {}

    if user_id not in users:
        users[user_id] = {
            "username": username,
            "ref": None,
            "paid": False
        }

        # Сохраняем реферала
        if len(args) > 1 and args[1].startswith("ref_"):
            ref_name = args[1][4:]
            users[user_id]["ref"] = ref_name

    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

    bot.send_message(message.chat.id, f"""
👋 Добро пожаловать, {username}, на курс по ботоксу!

💳 Для оплаты курса перейдите по ссылке:
{WAYFORPAY_LINK}

✅ После оплаты нажмите /check

❓ Если возникли вопросы — напишите в поддержку: @andreixc
""")

@bot.message_handler(commands=['check'])
def check_payment(message):
    user_id = str(message.from_user.id)
    reference = f"{ORDER_REFERENCE}_{user_id}"

    data = {
        "transactionType": "CHECK_STATUS",
        "merchantAccount": MERCHANT_ACCOUNT,
        "orderReference": reference,
        "apiVersion": 1
    }

    # Генерация подписи
    keys = [
        data["merchantAccount"],
        data["orderReference"],
        data["apiVersion"]
    ]
    message_string = ";".join(str(k) for k in keys)
    signature = base64.b64encode(
        hmac.new(MERCHANT_SECRET_KEY.encode(), message_string.encode(), hashlib.md5).digest()
    ).decode()
    data["merchantSignature"] = signature

    try:
        response = requests.post("https://api.wayforpay.com/api", json=data)
        result = response.json()

        if 'transactionStatus' in result and result['transactionStatus'] == "Approved":
            # Сохраняем пользователя как оплатившего
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r") as f:
                    users = json.load(f)
            else:
                users = {}

            users[user_id] = {
                "username": message.from_user.username,
                "ref": message.text.split(" ")[1] if len(message.text.split()) > 1 else None
            }

            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=2)

            bot.send_message(message.chat.id, f"✅ Оплата подтверждена!\nВот ссылка на курс: {COURSE_LINK}")
        else:
            bot.send_message(message.chat.id, "❗️Оплата не найдена.\nУбедитесь, что вы оплатили курс.")
            bot.send_message(message.chat.id, "Если вы точно оплатили, но не получили ссылку — напишите в поддержку: @andreixc")

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при проверке оплаты: {str(e)}")

@bot.message_handler(commands=['статистика'])
def stats_handler(message):
    if message.from_user.id != ADMIN_ID:
        return

    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    else:
        bot.send_message(message.chat.id, "Нет данных.")
        return

    ref_count = {}
    paid_ref_count = {}

    for user in users.values():
        ref = user.get("ref")
        if ref:
            ref_count[ref] = ref_count.get(ref, 0) + 1
            if user.get("paid"):
                paid_ref_count[ref] = paid_ref_count.get(ref, 0) + 1

    text = "📈 Статистика по рефералам:\n"
    if not ref_count:
        text += "Нет привлечённых пользователей."
    else:
        for ref, total in ref_count.items():
            paid = paid_ref_count.get(ref, 0)
            text += f"👤 {ref}: {total} пригласил, из них {paid} оплатили\n"

    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['id'])
def get_id(message):
    bot.send_message(message.chat.id, f"🆔 Ваш Telegram ID: {message.chat.id}")

print("🤖 Бот запущен")
bot.polling()