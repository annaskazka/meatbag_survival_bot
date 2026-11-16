from aiogram import Router, F
from aiogram.types import Message

from database.requests import get_user, get_top_users

profile_router = Router()


@profile_router.message(F.text == "⭐️ Мой баланс")
async def show_balance(message: Message):
    user = await get_user(message.from_user.id)
    stars = user.stars if user else 0
    await message.answer(f"Твой текущий баланс: ⭐️ <b>{stars}</b> звезд.")


@profile_router.message(F.text == "🏆 Рейтинг")
async def show_leaderboard(message: Message):
    top_users = await get_top_users(limit=10)

    text = "🏆 <b>Топ-10 участников по звездам:</b>\n\n"
    for idx, u in enumerate(top_users, 1):
        name = u.display_name or (f"@{u.username}" if u.username else f"Участник {u.telegram_id}")
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
        text += f"{medal} <b>{name}</b> — ⭐️ <b>{u.stars}</b>\n"

    await message.answer(text)