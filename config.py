import os
from dotenv import load_dotenv


# Подгружаем переменные из файла .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DB_URL", "postgresql+asyncpg://postgres:100113@localhost:5432/meatbag")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", 0))

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в переменных окружения")
