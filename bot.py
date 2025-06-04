import json
import os
from datetime import datetime
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Токен твоего бота
TOKEN = '7924481837:AAHipYFH4O5OR8a0mr_NRL6RG4iu-buOaBI'

# Файл для хранения истории участников и результатов
HISTORY_FILE = 'history.json'

# Админские ID — сюда твой ID для управления ботом
ADMIN_IDS = [1629374747]

# Кошелек для депозитов, который видит только админ
WALLET_ADDRESS = "TCewPzprLNxPYeCuitkXXEihf1tN1GNxJR"

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def find_user(history, user_id=None, username=None):
    for rec in history:
        if user_id and rec.get('user_id') == user_id:
            return rec
        if username and rec.get('username', '').lower() == username.lower():
            return rec
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для записи участников Extra Blitz.\n"
        "Используй /join чтобы участвовать.\n"
        "Участники могут установить свой кошелек через /setwallet <адрес>.\n"
        "Админ может управлять через /history, /winners, /wallet, /setstake, /setwin."
    )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history = load_history()

    if find_user(history, user_id=user.id):
        await update.message.reply_text("Ты уже записан в Extra Blitz.")
        return

    record = {
        'user_id': user.id,
        'username': user.username or user.full_name,
        'date': now,
        'stake': None,
        'win': None,
        'wallet': None
    }
    history.append(record)
    save_history(history)

    await update.message.reply_text(f"Спасибо, {record['username']}! Ты записан на Extra Blitz.")

async def setwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text("Пожалуйста, укажи адрес кошелька. Пример: /setwallet TXYZ...")
        return
    wallet = args[0]

    history = load_history()
    rec = find_user(history, user_id=user.id)
    if not rec:
        await update.message.reply_text("Ты ещё не записан. Сначала используй /join")
        return

    rec['wallet'] = wallet
    save_history(history)
    await update.message.reply_text(f"Кошелек установлен: {wallet}")

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Извините, эта команда доступна только администратору.")
        return

    history = load_history()
    if not history:
        await update.message.reply_text("История пуста.")
        return

    messages = []
    sorted_history = sorted(history, key=lambda x: x['date'])
    for rec in sorted_history:
        msg = (f"{rec['date']} — {rec['username']} — ставка: {rec['stake']} — "
               f"выигрыш: {rec['win']} — кошелек: {rec['wallet']}")
        messages.append(msg)

    chunk_size = 10
    for i in range(0, len(messages), chunk_size):
        await update.message.reply_text("\n".join(messages[i:i+chunk_size]))

async def winners_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Извините, эта команда доступна только администратору.")
        return

    history = load_history()
    winners = [rec for rec in history if rec.get('win') and rec['win'] > 0]
    if not winners:
        await update.message.reply_text("Победителей пока нет.")
        return

    messages = []
    for rec in winners:
        msg = f"{rec['date']} — {rec['username']} — выигрыш: {rec['win']}"
        messages.append(msg)

    chunk_size = 10
    for i in range(0, len(messages), chunk_size):
        await update.message.reply_text("\n".join(messages[i:i+chunk_size]))

async def wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Извините, эта команда доступна только администратору.")
        return

    await update.message.reply_text(f"Текущий кошелек для депозитов Extra Blitz:\n{WALLET_ADDRESS}")

async def setstake_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Команда доступна только администратору.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Использование: /setstake <username> <сумма>")
        return

    username, stake_str = args
    try:
        stake = float(stake_str)
    except ValueError:
        await update.message.reply_text("Сумма ставки должна быть числом.")
        return

    history = load_history()
    rec = find_user(history, username=username)
    if not rec:
        await update.message.reply_text(f"Пользователь {username} не найден.")
        return

    rec['stake'] = stake
    save_history(history)
    await update.message.reply_text(f"Ставка для {username} установлена: {stake}")

async def setwin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Команда доступна только администратору.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Использование: /setwin <username> <сумма>")
        return

    username, win_str = args
    try:
        win = float(win_str)
    except ValueError:
        await update.message.reply_text("Сумма выигрыша должна быть числом.")
        return

    history = load_history()
    rec = find_user(history, username=username)
    if not rec:
        await update.message.reply_text(f"Пользователь {username} не найден.")
        return

    rec['win'] = win
    save_history(history)
    await update.message.reply_text(f"Выигрыш для {username} установлен: {win}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("setwallet", setwallet))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("winners", winners_cmd))
    app.add_handler(CommandHandler("wallet", wallet_cmd))
    app.add_handler(CommandHandler("setstake", setstake_cmd))
    app.add_handler(CommandHandler("setwin", setwin_cmd))

    print("Бот запущен...")
    app.run_polling()
