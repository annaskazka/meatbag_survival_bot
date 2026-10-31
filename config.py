import os
from dotenv import load_dotenv


# Подгружаем переменные из файла .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DB_URL")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", 0))

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в переменных окружения")

if not DB_URL:
    raise ValueError("Не найден DB_URL в переменных окружения")
