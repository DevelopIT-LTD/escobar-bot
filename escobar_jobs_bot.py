"""
🤖 ESCOBAR JOBS BOT
Telegram бот для рекрутингу з WebApp та вбудованою формою
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Optional

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
    CallbackQuery
)

# ════════════════════════════════════════════════════════════
# НАЛАШТУВАННЯ
# ════════════════════════════════════════════════════════════

# Токен з змінних середовища (для безпеки)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8527555104:AAGzVVy7-VZmrH4HmgoqPNRrn5UIaucITyw")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://developit-ltd.github.io/escobar_leadform/")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL", "https://script.google.com/macros/s/AKfycbzSTwJbWzFORXFwBgh6Jrkc1BHf6kKYQUB2qbseoJbzGPNqmtCUUvPf8rY0tIxzDBjDig/exec")

# ADMIN IDS - твій Telegram ID
ADMIN_IDS = [7952260718]

# КАНАЛ ДЛЯ ПОСТІВ - пустий, щоб пости йшли тобі в приватні
POST_CHANNEL_ID = ""

# ════════════════════════════════════════════════════════════
# ВАКАНСІЇ
# ════════════════════════════════════════════════════════════

VACANCIES = [
    {
        "id": 1,
        "name": "Адміністратор",
        "salary": "від 42 000 грн",
        "max_age": 35,
        "emoji": "🏢"
    },
    {
        "id": 2,
        "name": "Менеджер з продажу",
        "salary": "від 60 000 грн + премії",
        "max_age": 35,
        "emoji": "📊"
    },
    {
        "id": 3,
        "name": "Менеджер з клієнтами",
        "salary": "від 55 000 грн + премії",
        "max_age": 35,
        "emoji": "🤝"
    },
    {
        "id": 4,
        "name": "HR-менеджер",
        "salary": "від 48 000 грн + премії",
        "max_age": 35,
        "emoji": "👥"
    },
    {
        "id": 5,
        "name": "Sale Manager",
        "salary": "від 60 000 грн + премії",
        "max_age": 35,
        "emoji": "🎯"
    },
    {
        "id": 6,
        "name": "Рекрутер",
        "salary": "від 40 000 грн + премії",
        "max_age": 35,
        "emoji": "🔍"
    },
    {
        "id": 7,
        "name": "Менеджер по роботі з персоналом",
        "salary": "від 45 000 грн + премії",
        "max_age": 35,
        "emoji": "👤"
    },
    {
        "id": 8,
        "name": "Спеціаліст з комунікацій",
        "salary": "від 38 000 грн",
        "max_age": 35,
        "emoji": "📢"
    },
    {
        "id": 9,
        "name": "Project Manager",
        "salary": "від 55 000 грн + премії",
        "max_age": 35,
        "emoji": "📋"
    }
]

# ════════════════════════════════════════════════════════════
# FSM СТАНИ
# ════════════════════════════════════════════════════════════

class ApplicationForm(StatesGroup):
    vacancy = State()
    name = State()
    age = State()
    city = State()
    telegram = State()
    phone = State()


class PostCreation(StatesGroup):
    photo = State()
    text = State()
    confirm = State()

# ════════════════════════════════════════════════════════════
# ІНІЦІАЛІЗАЦІЯ
# ════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# ════════════════════════════════════════════════════════════
# ДОПОМІЖНІ ФУНКЦІЇ
# ════════════════════════════════════════════════════════════

def get_vacancy_by_id(vacancy_id: int) -> Optional[Dict]:
    """Отримати вакансію по ID"""
    for v in VACANCIES:
        if v["id"] == vacancy_id:
            return v
    return None


async def send_to_google_sheets(data: Dict) -> bool:
    """Відправка даних в Google Sheets"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                APPS_SCRIPT_URL,
                json=data,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 200:
                    logging.info("✅ Дані відправлено в Google Sheets")
                    return True
                else:
                    logging.error(f"❌ Помилка Google Sheets: {response.status}")
                    return False
    except Exception as e:
        logging.error(f"❌ Помилка відправки в Google Sheets: {e}")
        return False

# ════════════════════════════════════════════════════════════
# КЛАВІАТУРИ
# ════════════════════════════════════════════════════════════

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Головна клавіатура з 2 кнопками"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Заповнити онлайн", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="📋 Вибрати вакансію в боті", callback_data="select_vacancy")]
    ])


def get_vacancies_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура зі списком вакансій"""
    buttons = []
    for v in VACANCIES:
        buttons.append([
            InlineKeyboardButton(
                text=f"{v['emoji']} {v['name']} • {v['salary']}",
                callback_data=f"vacancy_{v['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад до вакансій", callback_data="back_to_vacancies")]
    ])


def get_telegram_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для кроку Telegram з кнопкою автопідстановки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Підставити мій @username", callback_data="auto_username")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_city")]
    ])


def get_skip_phone_keyboard() -> InlineKeyboardMarkup:
    """Кнопка пропустити телефон"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустити", callback_data="skip_phone")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_telegram")]
    ])

# ════════════════════════════════════════════════════════════
# ОБРОБНИКИ КОМАНД
# ════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обробник команди /start"""
    await state.clear()
    
    text = """
<b>🎯 ESCOBAR JOBS</b>
<i>Ваша кар'єра починається тут</i>

━━━━━━━━━━━━━━━━

💼 <b>Ми пропонуємо:</b>

💰 Високі зарплати від 38 000 грн
📈 Швидке кар'єрне зростання  
🏢 Сучасний офіс в центрі міста
✅ Офіційне працевлаштування
🎓 Навчання з першого дня
🎁 Бонуси та преміальні до 150%

━━━━━━━━━━━━━━━━

<b>🔥 Актуальні вакансії:</b>

• Адміністратор
• Менеджер з продажу
• Менеджер з клієнтами
• HR-менеджер
• Sale Manager
• Рекрутер
• Менеджер по роботі з персоналом
• Спеціаліст з комунікацій
• Project Manager

━━━━━━━━━━━━━━━━

👇 <b>Оберіть зручний спосіб подачі заявки:</b>
"""
    
    await message.answer(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════════════════
# ВИБІР ВАКАНСІЇ В БОТІ
# ════════════════════════════════════════════════════════════

@router.callback_query(F.data == "select_vacancy")
async def select_vacancy_in_bot(callback: CallbackQuery, state: FSMContext):
    """Показати список вакансій"""
    await state.clear()
    
    text = """
<b>📋 ВАКАНСІЇ</b>

Оберіть вакансію, яка вас цікавить:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_vacancies_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ════════════════════════════════════════════════════════════
# ОБРОБНИКИ CALLBACK
# ════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("vacancy_"))
async def vacancy_selected(callback: CallbackQuery, state: FSMContext):
    """Вибрана вакансія"""
    vacancy_id = int(callback.data.split("_")[1])
    vacancy = get_vacancy_by_id(vacancy_id)
    
    if not vacancy:
        await callback.answer("❌ Вакансію не знайдено")
        return
    
    # Зберігаємо вакансію
    await state.update_data(vacancy=vacancy, message_id=callback.message.message_id)
    await state.set_state(ApplicationForm.name)
    
    text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>
💰 {vacancy['salary']}

━━━━━━━━━━━━━━━━

<b>Крок 1 з 5</b>

👤 Як вас звати?

<i>Введіть ваше ім'я та прізвище</i>
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_vacancies")
async def back_to_vacancies(callback: CallbackQuery, state: FSMContext):
    """Повернення до списку вакансій"""
    await state.clear()
    
    text = """
<b>📋 ВАКАНСІЇ</b>

Оберіть вакансію, яка вас цікавить:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_vacancies_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, state: FSMContext):
    """Повернення на старт"""
    await state.clear()
    await callback.message.delete()
    await cmd_start(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "back_to_telegram")
async def back_to_telegram(callback: CallbackQuery, state: FSMContext):
    """Повернення до кроку Telegram"""
    data = await state.get_data()
    vacancy = data.get('vacancy')
    
    if not vacancy:
        await callback.answer("❌ Помилка")
        return
    
    await state.set_state(ApplicationForm.telegram)
    
    text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 4 з 5</b>

📱 Ваш Telegram?

<i>Введіть username (@ додасться автоматично) або натисніть кнопку</i>
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_telegram_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "auto_username")
async def auto_username(callback: CallbackQuery, state: FSMContext):
    """Автоматична підстановка username"""
    username = callback.from_user.username
    
    if not username:
        await callback.answer("❌ У вас немає @username в Telegram", show_alert=True)
        return
    
    # Зберігаємо username
    telegram = f"@{username}"
    await state.update_data(telegram=telegram)
    await state.set_state(ApplicationForm.phone)
    
    # Оновлюємо повідомлення
    data = await state.get_data()
    vacancy = data['vacancy']
    message_id = data['message_id']
    
    text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 5 з 5</b>

📞 Ваш номер телефону?

<i>Введіть номер або пропустіть цей крок</i>
"""
    
    await bot.edit_message_text(
        text,
        chat_id=callback.message.chat.id,
        message_id=message_id,
        reply_markup=get_skip_phone_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_city")
async def back_to_city(callback: CallbackQuery, state: FSMContext):
    """Повернення до кроку Місто"""
    data = await state.get_data()
    vacancy = data.get('vacancy')
    
    if not vacancy:
        await callback.answer("❌ Помилка")
        return
    
    await state.set_state(ApplicationForm.city)
    
    text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 3 з 5</b>

🏙 З якого ви міста?

<i>Введіть назву вашого міста</i>
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ════════════════════════════════════════════════════════════
# ЗАПОВНЕННЯ ФОРМИ - ІМ'Я
# ════════════════════════════════════════════════════════════

@router.message(ApplicationForm.name)
async def process_name(message: Message, state: FSMContext):
    """Обробка імені"""
    name = message.text.strip()
    
    # Видаляємо повідомлення користувача
    await message.delete()
    
    data = await state.get_data()
    vacancy = data['vacancy']
    message_id = data['message_id']
    
    # Перевірка довжини
    if len(name) < 2:
        text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>
💰 {vacancy['salary']}

━━━━━━━━━━━━━━━━

<b>Крок 1 з 5</b>

👤 Як вас звати?

❌ <b>Ім'я занадто коротке</b>
<i>Введіть ваше повне ім'я та прізвище</i>
"""
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Перевірка на літери (українські, російські, латинські, пробіл, дефіс)
    if not re.match(r'^[а-яА-ЯіІїЇєЄґҐёЁa-zA-Z\s\-]+$', name):
        text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>
💰 {vacancy['salary']}

━━━━━━━━━━━━━━━━

<b>Крок 1 з 5</b>

👤 Як вас звати?

❌ <b>Тільки букви</b>
<i>Ім'я може містити тільки літери (без цифр та символів)</i>
"""
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Зберігаємо ім'я
    await state.update_data(name=name)
    await state.set_state(ApplicationForm.age)
    
    # Оновлюємо повідомлення
    text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 2 з 5</b>

🎂 Скільки вам років?

<i>Введіть ваш вік (від 17 до {vacancy['max_age']} років)</i>
"""
    
    await bot.edit_message_text(
        text,
        chat_id=message.chat.id,
        message_id=message_id,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════════════════
# ЗАПОВНЕННЯ ФОРМИ - ВІК
# ════════════════════════════════════════════════════════════

@router.message(ApplicationForm.age)
async def process_age(message: Message, state: FSMContext):
    """Обробка віку"""
    # Видаляємо повідомлення користувача
    await message.delete()
    
    data = await state.get_data()
    vacancy = data['vacancy']
    message_id = data['message_id']
    
    try:
        age = int(message.text.strip())
    except ValueError:
        # Помилка валідації - не число
        text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 2 з 5</b>

🎂 Скільки вам років?

❌ <b>Введіть коректний вік (число)</b>
<i>Наприклад: 23</i>
"""
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Валідація віку - менше 17
    if age < 17:
        text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 2 з 5</b>

🎂 Скільки вам років?

❌ <b>Мінімальний вік - 17 років</b>
<i>Введіть ваш вік (від 17 до {vacancy['max_age']} років)</i>
"""
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Валідація віку - більше максимального для вакансії
    if age > vacancy['max_age']:
        # Показуємо альтернативні вакансії
        suitable = [v for v in VACANCIES if age <= v['max_age']]
        
        if suitable:
            alt_text = "\n".join([f"• {v['emoji']} {v['name']} (до {v['max_age']} років)" for v in suitable])
            text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 2 з 5</b>

⚠️ <b>На вакансію "{vacancy['name']}" максимальний вік - {vacancy['max_age']} років</b>

<b>Вакансії, які вам підходять:</b>
{alt_text}

<i>Поверніться назад та оберіть іншу вакансію</i>
"""
        else:
            text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 2 з 5</b>

❌ <b>На жаль, ваш вік ({age} років) перевищує максимальний для всіх наших вакансій</b>

<i>Поверніться назад</i>
"""
        
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Вік валідний - зберігаємо
    await state.update_data(age=age)
    await state.set_state(ApplicationForm.city)
    
    # Оновлюємо повідомлення - наступний крок
    text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 3 з 5</b>

🏙 З якого ви міста?

<i>Введіть назву вашого міста</i>
"""
    
    await bot.edit_message_text(
        text,
        chat_id=message.chat.id,
        message_id=message_id,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════════════════
# ЗАПОВНЕННЯ ФОРМИ - МІСТО
# ════════════════════════════════════════════════════════════

@router.message(ApplicationForm.city)
async def process_city(message: Message, state: FSMContext):
    """Обробка міста"""
    city = message.text.strip()
    
    # Видаляємо повідомлення користувача
    await message.delete()
    
    data = await state.get_data()
    vacancy = data['vacancy']
    message_id = data['message_id']
    
    if len(city) < 2:
        # Помилка валідації
        text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 3 з 5</b>

🏙 З якого ви міста?

❌ <b>Введіть коректну назву міста</b>
<i>Наприклад: Київ, Львів, Одеса</i>
"""
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Перевірка на літери (українські, російські, латинські, пробіл, дефіс)
    if not re.match(r'^[а-яА-ЯіІїЇєЄґҐёЁa-zA-Z\s\-]+$', city):
        text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 3 з 5</b>

🏙 З якого ви міста?

❌ <b>Тільки букви</b>
<i>Назва міста може містити тільки літери (без цифр та символів)</i>
"""
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Зберігаємо місто
    await state.update_data(city=city)
    await state.set_state(ApplicationForm.telegram)
    
    # Оновлюємо повідомлення
    text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 4 з 5</b>

📱 Ваш Telegram?

<i>Введіть username (@ додасться автоматично) або натисніть кнопку</i>
"""
    
    await bot.edit_message_text(
        text,
        chat_id=message.chat.id,
        message_id=message_id,
        reply_markup=get_telegram_keyboard(),
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════════════════
# ЗАПОВНЕННЯ ФОРМИ - TELEGRAM
# ════════════════════════════════════════════════════════════

@router.message(ApplicationForm.telegram)
async def process_telegram(message: Message, state: FSMContext):
    """Обробка Telegram"""
    telegram = message.text.strip()
    
    # Видаляємо повідомлення користувача
    await message.delete()
    
    data = await state.get_data()
    vacancy = data['vacancy']
    message_id = data['message_id']
    
    # Автоматично додаємо @ якщо немає
    if not telegram.startswith('@'):
        telegram = '@' + telegram
    
    # Видаляємо подвійні собачки
    telegram = telegram.replace('@@', '@')
    
    if len(telegram) < 3:  # @ + мінімум 2 символи
        # Помилка валідації
        text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 4 з 5</b>

📱 Ваш Telegram?

❌ <b>Введіть ваш Telegram username</b>
<i>Наприклад: @username або username</i>
"""
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_telegram_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Перевірка на формат Telegram username (англійські літери, цифри, _)
    username = telegram[1:]  # без @
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 4 з 5</b>

📱 Ваш Telegram?

❌ <b>Невірний формат</b>
<i>Username може містити тільки англійські літери, цифри та _
Наприклад: @username або username</i>
"""
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_telegram_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Зберігаємо telegram
    await state.update_data(telegram=telegram)
    await state.set_state(ApplicationForm.phone)
    
    # Оновлюємо повідомлення
    text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 5 з 5</b>

📞 Ваш номер телефону?

<i>Введіть номер або пропустіть цей крок</i>
"""
    
    await bot.edit_message_text(
        text,
        chat_id=message.chat.id,
        message_id=message_id,
        reply_markup=get_skip_phone_keyboard(),
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════════════════
# ЗАПОВНЕННЯ ФОРМИ - ТЕЛЕФОН
# ════════════════════════════════════════════════════════════

@router.message(ApplicationForm.phone)
async def process_phone(message: Message, state: FSMContext):
    """Обробка телефону"""
    phone = message.text.strip()
    await message.delete()
    
    data = await state.get_data()
    vacancy = data['vacancy']
    message_id = data['message_id']
    
    # Видаляємо всі символи крім цифр для перевірки
    phone_digits = re.sub(r'[^\d]', '', phone)
    
    # Якщо ввели щось крім цифр та +
    if phone and not re.match(r'^[\d\+\-\s\(\)]+$', phone):
        text = f"""
<b>{vacancy['emoji']} {vacancy['name']}</b>

━━━━━━━━━━━━━━━━

<b>Крок 5 з 5</b>

📞 Ваш номер телефону?

❌ <b>Тільки цифри</b>
<i>Номер може містити тільки цифри
Наприклад: 0501234567 або +380501234567</i>
"""
        await bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=get_skip_phone_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await finalize_application(message, state, phone)


@router.callback_query(F.data == "skip_phone")
async def skip_phone(callback: CallbackQuery, state: FSMContext):
    """Пропустити телефон"""
    await callback.answer()
    await finalize_application(callback.message, state, "")

# ════════════════════════════════════════════════════════════
# ФІНАЛІЗАЦІЯ ЗАЯВКИ
# ════════════════════════════════════════════════════════════

async def finalize_application(message: Message, state: FSMContext, phone: str):
    """Фінальна обробка заявки"""
    data = await state.get_data()
    vacancy = data['vacancy']
    message_id = data['message_id']
    
    # Готуємо дані
    application_data = {
        "name": data['name'],
        "age": data['age'],
        "city": data['city'],
        "telegram": data['telegram'],
        "phone": phone,
        "vacancy": vacancy['name']
    }
    
    # Показуємо "Обробка..."
    await bot.edit_message_text(
        "⏳ <b>Обробка заявки...</b>",
        chat_id=message.chat.id,
        message_id=message_id,
        parse_mode="HTML"
    )
    
    # Відправляємо в Google Sheets
    sheets_success = await send_to_google_sheets(application_data)
    
    # Показуємо результат
    if sheets_success:
        result_text = """
✅ <b>Заявка успішно відправлена!</b>

Дякуємо за інтерес до нашої компанії!

Наш HR-відділ зв'яжеться з вами найближчим часом для обговорення деталей.

━━━━━━━━━━━━━━━━

Гарного дня! 🌟
"""
    else:
        result_text = """
✅ <b>Заявка отримана!</b>

Дякуємо! Ми зв'яжемося з вами найближчим часом.

Гарного дня! 🌟
"""
    
    await bot.edit_message_text(
        result_text,
        chat_id=message.chat.id,
        message_id=message_id,
        parse_mode="HTML"
    )
    
    # Очищаємо стан
    await state.clear()
    
    # Чекаємо 2 секунди і показуємо пропозицію подати ще одну заявку
    await asyncio.sleep(2)
    
    new_text = """
✅ <b>Заявка успішно відправлена!</b>

Дякуємо за інтерес до нашої компанії!

Наш HR-відділ зв'яжеться з вами найближчим часом для обговорення деталей.

━━━━━━━━━━━━━━━━

Гарного дня! 🌟

━━━━━━━━━━━━━━━━

💼 <b>Цікавлять інші вакансії?</b>
Заповнюй ще раз 👇
"""
    
    await bot.edit_message_text(
        new_text,
        chat_id=message.chat.id,
        message_id=message_id,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════════════════
# WEBAPP DATA
# ════════════════════════════════════════════════════════════

@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    """Обробка даних з WebApp"""
    try:
        # Парсимо дані
        data = json.loads(message.web_app_data.data)
        
        # Відправляємо в Google Sheets
        await send_to_google_sheets(data)
        
        # Підтвердження користувачу
        await message.answer(
            "✅ <b>Дякуємо за заявку!</b>\n\n"
            "Ваші дані успішно відправлені. Ми зв'яжемося з вами найближчим часом!\n\n"
            "Гарного дня! 🌟",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Помилка обробки WebApp data: {e}")
        await message.answer(
            "❌ Помилка обробки заявки. Спробуйте ще раз або зверніться до підтримки."
        )

# ════════════════════════════════════════════════════════════
# ADMIN ПАНЕЛЬ
# ════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    """Перевірка чи є користувач адміном"""
    return user_id in ADMIN_IDS


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура адмін-панелі"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Створити пост", callback_data="create_post")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="❌ Закрити", callback_data="close_admin")]
    ])


@router.message(F.text == "/admin")
async def admin_panel(message: Message, state: FSMContext):
    """Адмін-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адмін-панелі")
        return
    
    await state.clear()
    
    text = """
<b>🔧 АДМІН-ПАНЕЛЬ</b>
<b>Escobar Jobs Bot</b>

━━━━━━━━━━━━━━━━

Оберіть дію:
"""
    
    msg = await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    # Зберігаємо message_id адмін-панелі
    await state.update_data(admin_message_id=msg.message_id)


@router.callback_query(F.data == "close_admin")
async def close_admin(callback: CallbackQuery):
    """Закрити адмін-панель"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Немає доступу")
        return
    
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика (заглушка)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Немає доступу")
        return
    
    await callback.answer("📊 Статистика поки недоступна", show_alert=True)


# ════════════════════════════════════════════════════════════
# СТВОРЕННЯ ПОСТА
# ════════════════════════════════════════════════════════════

@router.callback_query(F.data == "create_post")
async def create_post_start(callback: CallbackQuery, state: FSMContext):
    """Початок створення поста"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Немає доступу")
        return
    
    await state.set_state(PostCreation.photo)
    
    text = """
<b>📝 СТВОРЕННЯ ПОСТА</b>

━━━━━━━━━━━━━━━━

<b>Крок 1:</b> Відправте фото для поста

Це може бути:
• Фото вакансії
• Баннер компанії
• Будь-яке зображення

<i>Відправте фото...</i>
"""
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_post")]
    ])
    
    await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "cancel_post")
async def cancel_post(callback: CallbackQuery, state: FSMContext):
    """Скасування створення поста"""
    data = await state.get_data()
    admin_message_id = data.get('admin_message_id')
    
    await state.clear()
    await state.update_data(admin_message_id=admin_message_id)
    
    # Повертаємося до адмін-панелі
    text = """
<b>🔧 АДМІН-ПАНЕЛЬ</b>
<b>Escobar Jobs Bot</b>

━━━━━━━━━━━━━━━━

Оберіть дію:
"""
    
    # Пробуємо відредагувати, якщо не вийде - створюємо нове
    try:
        if admin_message_id:
            await bot.edit_message_text(
                text,
                chat_id=callback.message.chat.id,
                message_id=admin_message_id,
                reply_markup=get_admin_keyboard(),
                parse_mode="HTML"
            )
        else:
            raise ValueError("No admin_message_id")
    except:
        # Якщо не вдалось відредагувати - створюємо нове
        new_msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await state.update_data(admin_message_id=new_msg.message_id)
    
    await callback.answer("❌ Створення поста скасовано")


@router.message(PostCreation.photo, F.photo)
async def post_photo_received(message: Message, state: FSMContext):
    """Отримано фото для поста"""
    if not is_admin(message.from_user.id):
        return
    
    # Видаляємо повідомлення користувача з фото
    await message.delete()
    
    # Зберігаємо найбільше фото
    photo = message.photo[-1].file_id
    await state.update_data(photo=photo)
    await state.set_state(PostCreation.text)
    
    # Редагуємо адмін повідомлення
    data = await state.get_data()
    admin_message_id = data.get('admin_message_id')
    
    text = """
<b>📝 СТВОРЕННЯ ПОСТА</b>

━━━━━━━━━━━━━━━━

<b>Крок 2:</b> Відправте текст для поста

Можна використовувати HTML форматування:
• <b>жирний</b>
• <i>курсив</i>
• <code>код</code>

<i>Відправте текст...</i>
"""
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_post")]
    ])
    
    # Пробуємо відредагувати, якщо не вийде - створюємо нове
    try:
        if admin_message_id:
            await bot.edit_message_text(
                text,
                chat_id=message.chat.id,
                message_id=admin_message_id,
                reply_markup=cancel_kb,
                parse_mode="HTML"
            )
        else:
            raise ValueError("No admin_message_id")
    except:
        # Якщо не вдалось відредагувати - створюємо нове
        new_msg = await message.answer(text, reply_markup=cancel_kb, parse_mode="HTML")
        await state.update_data(admin_message_id=new_msg.message_id)


@router.message(PostCreation.photo)
async def post_photo_invalid(message: Message):
    """Невалідне фото"""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("❌ Будь ласка, відправте фото (не документ, не файл)")


@router.message(PostCreation.text, F.text)
async def post_text_received(message: Message, state: FSMContext):
    """Отримано текст для поста"""
    if not is_admin(message.from_user.id):
        return
    
    # Видаляємо повідомлення користувача з текстом
    await message.delete()
    
    # Зберігаємо текст з HTML форматуванням (жирний, курсив, і т.д.)
    text = message.html_text if message.html_text else message.text
    await state.update_data(text=text)
    await state.set_state(PostCreation.confirm)
    
    # Показуємо превью
    data = await state.get_data()
    photo = data['photo']
    admin_message_id = data.get('admin_message_id')
    
    # Кнопка для поста (URL - працює при пересиланні)
    post_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Залишити заявку", url=WEBAPP_URL)]
    ])
    
    # Відправляємо превью
    preview_msg = await bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=f"{text}\n\n<i>━━━━━━━━━━━━━━━━\n👇 Натисніть кнопку нижче</i>",
        reply_markup=post_button,
        parse_mode="HTML"
    )
    
    # Зберігаємо ID превью для видалення
    await state.update_data(preview_message_id=preview_msg.message_id)
    
    # Редагуємо адмін повідомлення з кнопками підтвердження
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опублікувати", callback_data="publish_post"),
            InlineKeyboardButton(text="🗑 Видалити пост", callback_data="delete_preview")
        ],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_post")]
    ])
    
    # Пробуємо відредагувати, якщо не вийде - створюємо нове
    try:
        if admin_message_id:
            await bot.edit_message_text(
                "☝️ <b>ПРЕВЬЮ ПОСТА</b>\n\nПодобається? Публікуємо?",
                chat_id=message.chat.id,
                message_id=admin_message_id,
                reply_markup=confirm_kb,
                parse_mode="HTML"
            )
        else:
            raise ValueError("No admin_message_id")
    except:
        # Якщо не вдалось відредагувати - створюємо нове
        new_msg = await message.answer(
            "☝️ <b>ПРЕВЬЮ ПОСТА</b>\n\nПодобається? Публікуємо?",
            reply_markup=confirm_kb,
            parse_mode="HTML"
        )
        await state.update_data(admin_message_id=new_msg.message_id)


@router.callback_query(F.data == "delete_preview")
async def delete_preview(callback: CallbackQuery, state: FSMContext):
    """Видалення превью поста"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Немає доступу")
        return
    
    data = await state.get_data()
    preview_message_id = data.get('preview_message_id')
    admin_message_id = data.get('admin_message_id')
    
    # Видаляємо превью
    if preview_message_id:
        try:
            await bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=preview_message_id
            )
        except:
            pass
    
    # Повертаємося до введення тексту
    await state.set_state(PostCreation.text)
    
    text = """
<b>📝 СТВОРЕННЯ ПОСТА</b>

━━━━━━━━━━━━━━━━

<b>Крок 2:</b> Відправте текст для поста

Можна використовувати HTML форматування:
• <b>жирний</b>
• <i>курсив</i>
• <code>код</code>

<i>Відправте текст...</i>
"""
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_post")]
    ])
    
    # Пробуємо відредагувати, якщо не вийде - створюємо нове
    try:
        if admin_message_id:
            await bot.edit_message_text(
                text,
                chat_id=callback.message.chat.id,
                message_id=admin_message_id,
                reply_markup=cancel_kb,
                parse_mode="HTML"
            )
        else:
            raise ValueError("No admin_message_id")
    except:
        # Якщо не вдалось відредагувати - створюємо нове
        new_msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=cancel_kb,
            parse_mode="HTML"
        )
        await state.update_data(admin_message_id=new_msg.message_id)
    
    await callback.answer("🗑 Пост видалено, спробуйте ще раз")


@router.callback_query(F.data == "publish_post")
async def publish_post(callback: CallbackQuery, state: FSMContext):
    """Публікація поста"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Немає доступу")
        return
    
    data = await state.get_data()
    photo = data['photo']
    text = data['text']
    preview_message_id = data.get('preview_message_id')
    admin_message_id = data.get('admin_message_id')
    
    # Кнопка для поста (URL - працює при пересиланні)
    post_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Залишити заявку", url=WEBAPP_URL)]
    ])
    
    caption = f"{text}\n\n<i>━━━━━━━━━━━━━━━━\n👇 Натисніть кнопку нижче щоб залишити заявку</i>"
    
    success = False
    
    # Відправляємо в канал (якщо вказаний)
    if POST_CHANNEL_ID and POST_CHANNEL_ID != "":
        try:
            await bot.send_photo(
                chat_id=POST_CHANNEL_ID,
                photo=photo,
                caption=caption,
                reply_markup=post_button,
                parse_mode="HTML"
            )
            success = True
            logging.info(f"✅ Пост опубліковано в {POST_CHANNEL_ID}")
        except Exception as e:
            logging.error(f"❌ Помилка публікації: {e}")
    else:
        # Якщо канал не вказаний, відправляємо адміну
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=photo,
            caption=f"✅ <b>Пост створено!</b>\n\n{caption}",
            reply_markup=post_button,
            parse_mode="HTML"
        )
        success = True
    
    # Видаляємо превью
    if preview_message_id:
        try:
            await bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=preview_message_id
            )
        except:
            pass
    
    # Повертаємося до адмін-панелі
    await state.clear()
    await state.update_data(admin_message_id=admin_message_id)
    
    result_text = """
<b>🔧 АДМІН-ПАНЕЛЬ</b>
<b>Escobar Jobs Bot</b>

━━━━━━━━━━━━━━━━

✅ <b>Пост успішно опубліковано!</b>

Оберіть дію:
"""
    
    # Пробуємо відредагувати, якщо не вийде - створюємо нове
    try:
        if admin_message_id:
            await bot.edit_message_text(
                result_text,
                chat_id=callback.message.chat.id,
                message_id=admin_message_id,
                reply_markup=get_admin_keyboard(),
                parse_mode="HTML"
            )
        else:
            raise ValueError("No admin_message_id")
    except:
        # Якщо не вдалось відредагувати - створюємо нове
        new_msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=result_text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await state.update_data(admin_message_id=new_msg.message_id)
    
    await callback.answer("✅ Готово!")


# ════════════════════════════════════════════════════════════
# ЗАПУСК БОТА
# ════════════════════════════════════════════════════════════

async def main():
    """Головна функція"""
    dp.include_router(router)
    
    # Видаляємо webhook
    await bot.delete_webhook(drop_pending_updates=True)
    
    logging.info("🤖 Бот Escobar Jobs запущено!")
    
    # Запускаємо polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
