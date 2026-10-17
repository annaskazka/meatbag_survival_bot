# Точка входа. Тут бот только запускается

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import ErrorEvent

from config import BOT_TOKEN
from database.base import Base, engine
from database.requests import init_exercises, set_user_inactive  # <--- Добавили set_user_inactive сюда
from handlers.user_commands import user_router


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await init_exercises()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Глобальный обработчик ошибок: гасит блокировки и ставит флаг неактивности в БД
    @dp.error()
    async def global_error_handler(event: ErrorEvent):
        if isinstance(event.exception, TelegramForbiddenError):
            if event.update.message and event.update.message.from_user:
                await set_user_inactive(event.update.message.from_user.id)
            elif event.update.callback_query and event.update.callback_query.from_user:
                await set_user_inactive(event.update.callback_query.from_user.id)

            return True  # Тихо гасим ошибку, бот не падает
        raise event.exception

    dp.include_router(user_router)

    print("Бот запущен и ждет сообщения...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())