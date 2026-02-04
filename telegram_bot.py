from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest
import logging
import sqlite3
import openai

# Настройка API ключей и токенов
bot = Bot(token='8223332451:AAHCfEQr2gvBPn6MEYZA26dLTHsKcPGksyA')
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
logging.basicConfig(level=logging.INFO)

# Настройка OpenAI API
openai.api_key = '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'

# Подключение к базе данных SQLite (если необходимо)
conn = sqlite3.connect('database.db')
cursor = conn.cursor()


def get_keyboard():
    buttons = []

    buttons.append([
        InlineKeyboardButton(text="✍ Записать день", callback_data=)
    ])
    buttons.append([
        InlineKeyboardButton(text="🤖 ИИ-сборка недели", callback_data=)
    ])
    buttons.append([
        InlineKeyboardButton(text="🤖 ИИ-сборка месяца", callback_data=)
    ])
    buttons.append([
        InlineKeyboardButton(text="🤖 Итоги года", callback_data=)
    ])
    buttons.append([
        InlineKeyboardButton(text="📜 История", callback_data=)
    ])
    buttons.append([
        InlineKeyboardButton(text="⚙️ Настройки", callback_data=)
    ])
#``
async def record_event_step(message: types.Message):
    event = message.text
    cursor.execute("INSERT INTO events (text) VALUES (?)", (event,))
    conn.commit()
    await bot.send_message(message.chat.id, "Событие сохранено!")
    conn.close()

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот-коуч. Как я могу помочь вам сегодня?")

# Обработка остальных сообщений и команд
@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(message.text)

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
