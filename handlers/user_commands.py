# Старт, меню, нажатия на кнопки
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_TELEGRAM_ID

from database.requests import (
    get_all_exercises, log_activity, set_user, get_user, add_stars,
    create_pending_achievement, approve_achievement, reject_achievement, delete_exercise,
    get_top_users, update_display_name, update_exercise
)
from keyboards.user_kb import main_kb, get_exercise_kb, get_admin_approval_kb
from handlers.states import CustomAchievement


user_router = Router()


class ProfileStates(StatesGroup):
    waiting_for_name = State()


class AdminApproval(StatesGroup):
    waiting_for_stars = State()



@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await set_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    if not user.display_name:
        await state.set_state(ProfileStates.waiting_for_name)

        welcome_intro = (
            f"🤖 <b>Добро пожаловать в Meatbag Survival Bot!</b> 🔥\n\n"
            f"Это твоя личная система прокачки и выживания в суровых будках ЗОЖ. "
            f"Здесь мы фиксируем полезные привычки, тренируемся, зарабатываем звезды (⭐️) и боремся за место в Зале Славы.\n\n"
            f"<b>Как тут всё устроено:</b>\n"
            f"• Жми «Отметить активность» и выбирай, что полезного ты сделал за сегодня.\n"
            f"• За каждую привычку насыпаются заслуженные звезды.\n"
            f"• Следи за соперниками во вкладке Рейтинг.\n\n"
            f"⚠️ <b>Для участия в рейтинге нужно представиться.</b>\n"
            f"Напиши ответным сообщением свое <b>имя или прозвище</b>, под которым тебя увидят другие (просто текстом, без команд):"
        )
        await message.answer(welcome_intro)
        return

    await message.answer(
        f"С возвращением, <b>{user.display_name}</b>! Твой текущий баланс: ⭐️ <b>{user.stars}</b> звезд.",
        reply_markup=main_kb
    )


@user_router.message(ProfileStates.waiting_for_name)
async def process_mandatory_name(message: Message, state: FSMContext):
    new_name = message.text.strip()

    if not new_name or len(new_name) > 50:
        await message.answer("Имя не должно быть пустым и длиннее 50 символов. Напиши нормальное имя:")
        return

    await update_display_name(message.from_user.id, new_name)

    await state.clear()
    await message.answer(
        f"Отлично, принято! Твое имя в рейтинге: <b>{new_name}</b>.\n"
        f"Теперь ты в системе. Погнали выживать! 💪",
        reply_markup=main_kb
    )


@user_router.message(F.text == "⭐️ Мой баланс")
async def show_balance(message: Message):
    user = await get_user(message.from_user.id)
    stars = user.stars if user else 0
    await message.answer(f"Твой текущий баланс: ⭐️ <b>{stars}</b> звезд.")


@user_router.message(F.text == "🏆 Рейтинг")
async def show_leaderboard(message: Message):
    top_users = await get_top_users(limit=10)

    text = "🏆 <b>Топ-10 участников по звездам:</b>\n\n"
    for idx, u in enumerate(top_users, 1):
        name = u.display_name or (f"@{u.username}" if u.username else f"Участник {u.telegram_id}")
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
        text += f"{medal} <b>{name}</b> — ⭐️ <b>{u.stars}</b>\n"

    await message.answer(text)

