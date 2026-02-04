import logging
import sqlite3
import openai
from typing import Callable, Dict, Any, Awaitable
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Update
import asyncio

# === Настройки ===
BOT_TOKEN = '8223332451:AAHCfEQr2gvBPn6MEYZA26dLTHsKcPGksyA'
OPENAI_API_KEY = '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'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Middleware ===
class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Update):
            logger.info("Получено обновление: %s", event.model_dump_json(exclude_none=True)[:500])
        else:
            logger.info("Получено событие: %s", type(event).__name__)
        return await handler(event, data)

dp.update.middleware(LoggingMiddleware())

# === OpenAI ===
openai.api_key = OPENAI_API_KEY

# === База данных ===
def get_db_connection():
    return sqlite3.connect('database.db')

# Создание таблиц
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thanks (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS choices (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL
        )
    ''')
    conn.commit()

# === FSM States ===
class RecordStates(StatesGroup):
    waiting_for_event = State()
    waiting_for_thanks = State()
    waiting_for_choice = State()

# === Команда /start ===
@dp.message(Command("start"))
async def send_welcome(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍ Записать день", callback_data='record_day'),
            InlineKeyboardButton(text="🤖 ИИ-сборка недели", callback_data='week_report')
        ],
        [
            InlineKeyboardButton(text="🤖 ИИ-сборка месяца", callback_data='month_report'),
            InlineKeyboardButton(text="🤖 Итоги года", callback_data='year_report')
        ],
        [
            InlineKeyboardButton(text="📜 История", callback_data='history'),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data='settings')
        ]
    ])
    await message.answer("Добро пожаловать! Выберите действие:", reply_markup=keyboard)

# === Обработка нажатий на кнопки ===
@dp.callback_query(F.data == "record_day")
async def process_record_day(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Пожалуйста, введите ваше значимое событие дня:")
    await state.set_state(RecordStates.waiting_for_event)

@dp.callback_query(F.data.in_({"week_report", "month_report", "year_report", "history", "settings"}))
async def handle_other_callbacks(callback: CallbackQuery):
    await callback.answer()
    mapping = {
        "week_report": "Недельная ИИ-сборка пока недоступна.",
        "month_report": "Месячная ИИ-сборка пока недоступна.",
        "year_report": "Годовые итоги пока недоступны.",
        "history": "История записей пока не реализована.",
        "settings": "Настройки пока не реализованы."
    }
    await callback.message.answer(mapping[callback.data])

# === Обработка ввода после выбора "Записать день" ===
@dp.message(RecordStates.waiting_for_event)
async def handle_event_input(message: Message, state: FSMContext):
    event = message.text.strip()
    with get_db_connection() as conn:
        conn.execute("INSERT INTO events (text) VALUES (?)", (event,))
        conn.commit()
    await message.answer("Событие сохранено!")
    await state.clear()

# === Эхо-обработчик для остальных сообщений ===
@dp.message()
async def echo(message: Message):
    await message.answer("Извините, я не понимаю. Используйте меню.")

# === Запуск ===
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
