from aiogram import Bot, Dispatcher, executor, types
from config import TOKEN, ADMIN_ID, WALLET

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.answer("👋 Добро пожаловать! Отправь сумму депозита в USDT (TRC20).")
    await message.answer(f"💸 Адрес кошелька: `{WALLET}`", parse_mode="Markdown")

@dp.message_handler(commands=["help"])
async def help_cmd(message: types.Message):
    await message.answer("/start — начать\n/help — помощь\n/status — статус депозита")

@dp.message_handler(commands=["status"])
async def status_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🔍 Пока что нет проверок, функционал в разработке.")
    else:
        await message.answer("🔐 Только администратор может проверять статус.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
