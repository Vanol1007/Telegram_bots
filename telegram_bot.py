import json
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta

import openai  # pip install openai
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters.command import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


BOT_TOKEN = "8223332451:AAHCfEQr2gvBPn6MEYZA26dLTHsKcPGksyA "
OPENAI_API_KEY = "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"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


# 1. База данных 
DB_FILE = "coach_bot.db"


def get_db():
    #Получаем соединение с SQLite и создаём таблицы при необходимости
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            text TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS thanks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            text TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS choices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            text TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn

# 2. FSM‑состояния 
class RecordState(StatesGroup):
    """Состояния диалога при записи дня."""
    waiting_event = State()          # значимое событие
    waiting_thanks = State()         # благодарность
    waiting_choice = State()         # выбор себя

# 3. Команда /start 
@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Отправляем главное меню."""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("✍ Записать день", callback_data="record_day"),
                InlineKeyboardButton("🤖 ИИ‑сборка недели", callback_data="weekly_report"),
            ],
            [
                InlineKeyboardButton("🤖 ИИ‑сборка месяца", callback_data="monthly_report"),
                InlineKeyboardButton("🤖 Итоги года", callback_data="yearly_report"),
            ],
            [   InlineKeyboardButton("📜 История", callback_data="history"),
                InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
            ],
        ]
    )
    await message.answer(
        "Добро пожаловать в бота «Смыслы / Итоги / ИИ‑коуч»!\n"
        "Выберите действие:",
        reply_markup=kb,
    )

# 4. Обработка кнопок 
@dp.callback_query()
async def cb_handler(callback: CallbackQuery):
    data = callback.data
    await callback.answer() 

    if data == "record_day":
        await start_recording(callback.message, callback.from_user.id)

    elif data == "weekly_report":
        await get_last_n_days()

    elif data in ("weekly_report", "monthly_report", "yearly_report"):
        await callback.message.answer("Функция пока недоступна. Пожалуйста, попробуйте позже.")

    elif data == "history":
        await show_history(callback.message, callback.from_user.id)

# 5. Запись дня
async def start_recording(message: Message, user_id: int):
    """Начинаем цепочку вопросов."""
    await message.answer("💡 Введите самое значимое событие дня (одно предложение).")
    await RecordState.waiting_event.set()


@dp.message(RecordState.waiting_event)
async def handle_event(msg: Message, state: FSMContext):
    event = msg.text.strip()
    if not event:
        await msg.answer("Пожалуйста, напишите одно предложение.")
        return

    # Сохраняем
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (user_id, date, text) VALUES (?, ?, ?)",
        (msg.from_user.id, datetime.utcnow().date(), event),
    )
    conn.commit()

    await msg.answer("✅ Событие сохранено.\n\n"
                     "💬 За что ты благодарен сегодня? (одно предложение)")
    await RecordState.waiting_thanks.set()


@dp.message(RecordState.waiting_thanks)
async def handle_thanks(msg: Message, state: FSMContext):
    thanks = msg.text.strip()
    if not thanks:
        await msg.answer("Пожалуйста, напишите одно предложение.")
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO thanks (user_id, date, text) VALUES (?, ?, ?)",
        (msg.from_user.id, datetime.utcnow().date(), thanks),
    )
    conn.commit()

    await msg.answer("✅ Благодарность сохранена.\n\n"
                     "⚙️ Какой выбор себя ты сделал сегодня? "
                     "(начинается со слова «Выбрал»)")
    await RecordState.waiting_choice.set()


@dp.message(RecordState.waiting_choice)
async def handle_choice(msg: Message, state: FSMContext):
    choice = msg.text.strip()
    if not choice:
        await msg.answer("Пожалуйста, напишите одно предложение.")
        return

    # Сохраняем
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO choices (user_id, date, text) VALUES (?, ?, ?)",
        (msg.from_user.id, datetime.utcnow().date(), choice),
    )
    conn.commit()

    await msg.answer("🎉 Запись дня завершена!\n"
                     "Вы можете вернуться к меню /start для дальнейших действий.")
    await state.finish()


# ИИ-Сборка недели
async def get_week_summary(user_id: int):
    # 7 дней, начиная с последнего завершённого дня
    events, thanks, choices = await db.get_last_n_days(user_id, n=7)

    prompt = f"""
    Тебе нужно проанализировать следующие данные за прошлую неделю:
    События:
    {chr(10).join(f'- {e}' for e in events)}

    Благодарности:
    {chr(10).join(f'- {t}' for t in thanks)}

    Выборы себя:
    {chr(10).join(f'- {c}' for c in choices)}

    Ответ должен содержать:
    1. 3–5 ключевых паттернов недели
    2. Где пользователь выбирал себя
    3. Где терял ресурс
    4. Главный вектор недели
    5. Мягкий коуч‑вопрос

    Пиши только JSON без лишних объяснений.
    """

    resp = await openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.2,
    )
    text = resp['choices'][0]['message']['content']
    return json.loads(text)


# 6. История пользователя 
async def show_history(message: Message, user_id: int):
    """Отображаем список дат с последним вводом."""
    conn = get_db()
    cur = conn.cursor()

    # Получаем все даты (события + благодарности + выборы)
    cur.execute(
        """
        SELECT DISTINCT date
          FROM events WHERE user_id=?
        UNION
        SELECT DISTINCT date
          FROM thanks WHERE user_id=?
        UNION
        SELECT DISTINCT date
          FROM choices WHERE user_id=?
        ORDER BY date DESC
        """,
        (user_id, user_id, user_id),
    )
    dates = [row[0] for row in cur.fetchall()]

    if not dates:
        await message.answer("📜 В истории пока нет записей.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("⬅️ Предыдущий день", callback_data=f"view_{dates[0]}"),
                InlineKeyboardButton(f"{dates[0]}", callback_data="noop"),
                InlineKeyboardButton("Следующий день ➡️", callback_data=f"view_{dates[-1]}"),
            ],
        ]
    )

    await message.answer(
        f"<b>Выберите дату для просмотра</b>\n"
        f"Сейчас отображаем: <i>{dates[0]}</i>",
        reply_markup=kb,
    )


@dp.callback_query(lambda c: c.data.startswith("view_"))
async def view_day(callback: CallbackQuery):
# Показываем запись конкретного дня
    date_str = callback.data.split("_", 1)[1]
    user_id = callback.from_user.id
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT text FROM events WHERE user_id=? AND date=?", (user_id, date_str)
    )
    event_rows = cur.fetchall()

    cur.execute(
        "SELECT text FROM thanks WHERE user_id=? AND date=?", (user_id, date_str)
    )
    thanks_rows = cur.fetchall()

    cur.execute(
        "SELECT text FROM choices WHERE user_id=? AND date=?", (user_id, date_str)
    )
    choice_rows = cur.fetchall()

    text_parts = []
    if event_rows:
        text_parts.append(f"<b>Событие:</b>\n{event_rows[0][0]}")
    if thanks_rows:
        text_parts.append(f"\n<b>Благодарность:</b>\n{thanks_rows[0][0]}")
    if choice_rows:
        text_parts.append(f"\n<b>Выбор себя:</b>\n{choice_rows[0][0]}")

    await callback.message.answer("\n".join(text_parts))



# 7. Ежедневное напоминание
async def daily_reminder():
    """Отправляем каждому пользователю сообщение с вопросами в заданное время."""
    while True:
        now = datetime.utcnow()
        target_time = now.replace(hour=18, minute=0, second=0, microsecond=0)  # 18:00 UTC
        if now > target_time:
            target_time += timedelta(days=1)

        sleep_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(sleep_seconds)

        # Получаем всех пользователей из бд
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT user_id FROM events")
        users = [row[0] for row in cur.fetchall()]

        for uid in users:
            try:
                await bot.send_message(
                    chat_id=uid,
                    text="📅 Время записать день:\n\n"
                         "1️⃣ Самое значимое событие дня?\n"
                         "2️⃣ За что ты благодарен сегодня?\n"
                         "3️⃣ Какой выбор себя ты сделал?",
                )
            except Exception as e:
                logging.warning(f"Не удалось отправить напоминание пользователю {uid}: {e}")

        # Ждём 24 часа
        await asyncio.sleep(86400)



# 8. Запуск 
if __name__ == "__main__":
    # Включаем фоновую задачу с напоминаниями
    dp.startup.register(daily_reminder)
    logging.info("Бот запущен!")
    asyncio.run(dp.start_polling())
