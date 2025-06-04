import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor

# ==== НАСТРОЙКИ ====
API_TOKEN = '7924481837:AAHipYFH4O5OR8a0mr_NRL6RG4iu-buOaBI'  # Твой токен бота
ADMIN_IDS = [1629374747]  # Твой Telegram ID для админских команд

TRC20_WALLET = "trc20TCewPzprLNxPYeCuitkXXEihf1tN1GNxJR"  # Кошелек TRC20 для депозита

# ==== ЛОГИРОВАНИЕ ====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== ИНИЦИАЛИЗАЦИЯ БОТА И ДИСПЕТЧЕРА ====
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# ==== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ SQLite ====

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language TEXT DEFAULT 'ru',
            balance REAL DEFAULT 0.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tx_type TEXT,
            amount REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==== ФУНКЦИИ РАБОТЫ С БАЗОЙ ====

def user_exists(user_id: int) -> bool:
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result)

def add_user(user_id: int, username: str, first_name: str, last_name: str):
    if user_exists(user_id):
        return
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                   (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()

def get_balance(user_id: int) -> float:
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.0

def update_balance(user_id: int, amount: float):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_transaction(user_id: int, tx_type: str, amount: float, status: str = 'pending'):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO transactions (user_id, tx_type, amount, status) VALUES (?, ?, ?, ?)',
                   (user_id, tx_type, amount, status))
    conn.commit()
    conn.close()

def get_transactions(user_id: int, limit=10):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tx_type, amount, timestamp, status FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ==== МIDDLEWARE ДЛЯ АВТОРЕГИСТРАЦИИ ====

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ''
    first_name = message.from_user.first_name or ''
    last_name = message.from_user.last_name or ''
    add_user(user_id, username, first_name, last_name)
    text = (
        f"Привет, {first_name}!\n"
        "Я бот проекта Win-Win Синдикат.\n\n"
        "Команды:\n"
        "/balance - посмотреть баланс\n"
        "/deposit - получить адрес для депозита\n"
        "/withdraw - вывести средства\n"
        "/history - история транзакций\n"
        "/help - помощь"
    )
    await message.answer(text)

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    help_text = (
        "Доступные команды:\n"
        "/start - перезапустить бота\n"
        "/balance - посмотреть текущий баланс\n"
        "/deposit - получить адрес кошелька для пополнения (TRC20)\n"
        "/withdraw <сумма> - запросить вывод средств\n"
        "/history - показать последние транзакции\n"
        "/help - показать это сообщение"
    )
    await message.answer(help_text)

@dp.message_handler(commands=['balance'])
async def cmd_balance(message: types.Message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    await message.answer(f"Ваш текущий баланс: {balance:.2f} USDT")

@dp.message_handler(commands=['deposit'])
async def cmd_deposit(message: types.Message):
    text = (
        f"Для пополнения баланса отправьте средства на следующий адрес TRC20:\n\n"
        f"{TRC20_WALLET}\n\n"
        "Обратите внимание, что принимаются только USDT TRC20."
    )
    await message.answer(text)

@dp.message_handler(commands=['history'])
async def cmd_history(message: types.Message):
    user_id = message.from_user.id
    transactions = get_transactions(user_id, limit=5)
    if not transactions:
        await message.answer("У вас пока нет транзакций.")
        return
    text = "Последние транзакции:\n"
    for tx in transactions:
        tx_type, amount, timestamp, status = tx
        text += f"{timestamp} | {tx_type} | {amount:.2f} USDT | Статус: {status}\n"
    await message.answer(text)

@dp.message_handler(lambda message: message.text and message.text.startswith('/withdraw'))
async def cmd_withdraw(message: types.Message):
    user_id = message.from_user.id
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /withdraw <сумма>")
        return
    try:
        amount = float(parts[1])
    except ValueError:
        await message.answer("Сумма должна быть числом.")
        return
    balance = get_balance(user_id)
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return
    if amount > balance:
        await message.answer(f"Недостаточно средств. Ваш баланс: {balance:.2f} USDT")
        return
    # Регистрируем заявку на вывод, статус "pending"
    add_transaction(user_id, "withdraw", -amount, status="pending")
    update_balance(user_id, -amount)
    await message.answer(f"Заявка на вывод {amount:.2f} USDT принята и обрабатывается.")

# ==== Пример админ-команды (только для админов) ====

@dp.message_handler(commands=['broadcast'])
async def cmd_broadcast(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    text = message.text[10:].strip()
    if not text:
        await message.answer("Использование: /broadcast <сообщение>")
        return
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    count = 0
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.05)  # чтобы не забанили за флуд
        except Exception:
            pass
    await message.answer(f"Сообщение отправлено {count} пользователям.")

# ==== Запуск бота ====

if __name__ == '__main__':
    print("Бот запущен. Ctrl+C для остановки.")
    executor.start_polling(dp, skip_updates=True)
# Продолжение бота: команды, обработчики и дополнительные функции

from telegram.ext import Filters

# Команда /balance — показать баланс пользователя
def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = user_data.get(user_id)
    if not user:
        update.message.reply_text("Вы ещё не зарегистрированы. Используйте /start для регистрации.")
        return
    balance = user.get('balance', 0.0)
    update.message.reply_text(f"Ваш текущий баланс: {balance:.2f} USDT")

# Команда /deposit — показать кошелёк для пополнения
def deposit(update: Update, context: CallbackContext):
    wallet_address = "trc20TCewPzprLNxPYeCuitkXXEihf1tN1GNxJR"
    update.message.reply_text(
        f"Для пополнения депозита используйте кошелёк TRC20:\n{wallet_address}\n\n"
        "После пополнения, пожалуйста, отправьте сумму и TxID через /confirm_tx команда.\n"
        "Пример: /confirm_tx 100 0x123abc..."
    )

# Команда /confirm_tx — подтвердить пополнение
def confirm_tx(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = user_data.get(user_id)
    if not user:
        update.message.reply_text("Вы ещё не зарегистрированы. Используйте /start для регистрации.")
        return
    args = context.args
    if len(args) < 2:
        update.message.reply_text("Использование: /confirm_tx <сумма> <TxID>")
        return
    try:
        amount = float(args[0])
        txid = args[1]
    except ValueError:
        update.message.reply_text("Ошибка в формате суммы. Попробуйте снова.")
        return
    # Тут можно добавить проверку TxID в блокчейне, но для MVP — примем как есть
    user['balance'] += amount
    update.message.reply_text(f"Баланс успешно пополнен на {amount:.2f} USDT. Транзакция: {txid}")

# Команда /play — начать игру (например, ставка в покер)
def play(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = user_data.get(user_id)
    if not user:
        update.message.reply_text("Вы ещё не зарегистрированы. Используйте /start для регистрации.")
        return
    if user['balance'] < 10:
        update.message.reply_text("Недостаточно средств для ставки. Минимальная ставка 10 USDT.")
        return
    # Простая игра — ставим 10 USDT, выигрываем или проигрываем случайно
    import random
    stake = 10.0
    win = random.choice([True, False])
    if win:
        winnings = stake * 1.8  # выигрыш 80%
        user['balance'] += winnings - stake
        update.message.reply_text(f"Поздравляем! Вы выиграли {winnings:.2f} USDT.\n"
                                  f"Ваш новый баланс: {user['balance']:.2f} USDT")
    else:
        user['balance'] -= stake
        update.message.reply_text(f"К сожалению, вы проиграли ставку {stake:.2f} USDT.\n"
                                  f"Ваш новый баланс: {user['balance']:.2f} USDT")

# Команда /withdraw — запрос на вывод средств
def withdraw(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = user_data.get(user_id)
    if not user:
        update.message.reply_text("Вы ещё не зарегистрированы. Используйте /start для регистрации.")
        return
    args = context.args
    if len(args) < 1:
        update.message.reply_text("Использование: /withdraw <сумма>")
        return
    try:
        amount = float(args[0])
    except ValueError:
        update.message.reply_text("Ошибка в формате суммы. Попробуйте снова.")
        return
    if amount > user['balance']:
        update.message.reply_text("Недостаточно средств на балансе.")
        return
    # В реальной системе здесь должна быть интеграция с выводом через API
    user['balance'] -= amount
    update.message.reply_text(f"Запрос на вывод {amount:.2f} USDT принят.\n"
                              "Обработка будет выполнена в ближайшее время.\n"
                              f"Оставшийся баланс: {user['balance']:.2f} USDT")

# Команда /help — помощь и список команд
def help_command(update: Update, context: CallbackContext):
    help_text = (
        "Доступные команды:\n"
        "/start - Регистрация и приветствие\n"
        "/balance - Показать баланс\n"
        "/deposit - Кошелёк для пополнения депозита\n"
        "/confirm_tx <сумма> <TxID> - Подтвердить пополнение\n"
        "/play - Сделать ставку 10 USDT в игре\n"
        "/withdraw <сумма> - Запрос на вывод средств\n"
        "/help - Показать это сообщение\n"
    )
    update.message.reply_text(help_text)

# Обработчик неизвестных команд
def unknown(update: Update, context: CallbackContext):
    update.message.reply_text("Извините, я не знаю такую команду. Используйте /help для списка команд.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CommandHandler("deposit", deposit))
    dp.add_handler(CommandHandler("confirm_tx", confirm_tx))
    dp.add_handler(CommandHandler("play", play))
    dp.add_handler(CommandHandler("withdraw", withdraw))
    dp.add_handler(CommandHandler("help", help_command))

    # Обработчик нераспознанных команд
    dp.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
# Часть 3 из 3 для телеграм-бота Win-Win Синдикат

import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware

API_TOKEN = '7924481837:AAHipYFH4O5OR8a0mr_NRL6RG4iu-buOaBI'
TRC20_WALLET = 'trc20TCewPzprLNxPYeCuitkXXEihf1tN1GNxJR'
CHANNEL_ID = -1001234567890  # замените на свой ID канала
ADMIN_ID = 1629374747  # ID администратора (ваш)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# --- Продвинутые функции и команды ---

# Хранилище пользователей с балансами и статусами
users_db = {}

# Команда /balance - показать баланс пользователя
@dp.message_handler(commands=['balance'])
async def cmd_balance(message: types.Message):
    user_id = message.from_user.id
    user = users_db.get(user_id, {'balance': 0})
    await message.answer(f"Ваш текущий баланс: {user['balance']} USDT")

# Команда /deposit - информация о депозите
@dp.message_handler(commands=['deposit'])
async def cmd_deposit(message: types.Message):
    text = (
        f"Для депозита используйте кошелек TRC20:\n\n"
        f"`{TRC20_WALLET}`\n\n"
        "Обязательно указывайте в примечании ваш Telegram ID, "
        "чтобы мы могли подтвердить ваш платеж."
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

# Команда /withdraw - вывод средств (запрос)
@dp.message_handler(commands=['withdraw'])
async def cmd_withdraw(message: types.Message):
    user_id = message.from_user.id
    user = users_db.get(user_id, {'balance': 0})
    if user['balance'] <= 0:
        await message.answer("У вас нет средств для вывода.")
        return
    await message.answer(
        "Введите сумму для вывода. Минимальная сумма — 10 USDT."
    )
    # Сохраняем состояние ожидания суммы
    users_db[user_id]['awaiting_withdraw_amount'] = True

@dp.message_handler()
async def handle_withdraw_amount(message: types.Message):
    user_id = message.from_user.id
    user = users_db.get(user_id)
    if not user or not user.get('awaiting_withdraw_amount'):
        return  # Не в состоянии вывода
    try:
        amount = float(message.text)
        if amount < 10:
            await message.answer("Минимальная сумма для вывода — 10 USDT. Попробуйте ещё раз.")
            return
        if amount > user['balance']:
            await message.answer("У вас недостаточно средств для вывода.")
            return
        # Подтверждение запроса
        user['awaiting_withdraw_amount'] = False
        # Логика вывода (отправка заявки админам)
        await message.answer(f"Запрос на вывод {amount} USDT принят. Ожидайте подтверждения.")
        # Здесь можно отправить уведомление админу:
        await bot.send_message(
            ADMIN_ID,
            f"Пользователь @{message.from_user.username} ({user_id}) запросил вывод {amount} USDT."
        )
        # Обновляем баланс (заблокируем сумму)
        user['balance'] -= amount
        user.setdefault('withdraw_requests', []).append(amount)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")

# Команда /help - список доступных команд
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    text = (
        "Доступные команды:\n"
        "/balance — показать ваш баланс\n"
        "/deposit — информация для депозита\n"
        "/withdraw — запросить вывод средств\n"
        "/play — начать игру (пока в разработке)\n"
        "/help — помощь по командам\n\n"
        "Поддержка: @kapitan1708"
    )
    await message.answer(text)

# Функция приветствия новых пользователей
@dp.message_handler(content_types=['new_chat_members'])
async def welcome_new_user(message: types.Message):
    for new_member in message.new_chat_members:
        await message.reply(
            f"Добро пожаловать, {new_member.full_name}! "
            "Чтобы узнать команды, введите /help"
        )
        # Инициализация пользователя
        if new_member.id not in users_db:
            users_db[new_member.id] = {'balance': 0}

# Админ-команда для добавления баланса
@dp.message_handler(commands=['addbalance'])
async def cmd_addbalance(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для этой команды.")
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = float(parts[2])
        user = users_db.setdefault(user_id, {'balance': 0})
        user['balance'] += amount
        await message.answer(f"Баланс пользователя {user_id} пополнен на {amount} USDT.")
        await bot.send_message(user_id, f"Ваш баланс пополнен на {amount} USDT администратором.")
    except (IndexError, ValueError):
        await message.answer("Использование: /addbalance <user_id> <amount>")

# Таймер для рассылок (пример)
async def periodic_news():
    while True:
        await asyncio.sleep(3600)  # каждый час
        for user_id in users_db.keys():
            try:
                await bot.send_message(user_id, "Напоминание: играйте и выигрывайте с Win-Win Синдикат!")
            except Exception:
                pass  # Игнорируем ошибки доставки

# Запуск бота
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_news())
    executor.start_polling(dp, skip_updates=True)

