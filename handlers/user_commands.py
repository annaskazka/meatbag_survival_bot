# Старт, меню, нажатия на кнопки
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.requests import get_all_exercises, log_activity, set_user, get_user, add_stars
from keyboards.user_kb import main_kb, get_exercise_kb

user_router = Router()


class CustomAchievement(StatesGroup):
    waiting_for_text = State()


@user_router.message(CommandStart())
async def cmd_start(message: Message):
    #Регистрируем пользователя в базе данных
    user = await set_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    await message.answer(
        f"Здорово, {message.from_user.first_name}! 🔥\n\n"
        f"Ты зарегистрирован в системе 'ЗОЖ ачивки'.\n"
        f"Сейчас у тебя звезд: ⭐️ <b>{user.stars}</b>",
        reply_markup=main_kb
    )

@user_router.message(F.text == "⭐️ Мой баланс")
async def show_balance(message: Message):
    user = await get_user(message.from_user.id)
    stars = user.stars if user else 0
    await message.answer(f"твой текущий баланс: ⭐️ <b>{stars}</b> звезд.")


@user_router.message(F.text == "💪 Отметить активность")
async def track_workout(message: Message):
    exercises = await get_all_exercises()
    keyboard = get_exercise_kb(exercises)
    await message.answer("Выбери, что именно ты сделал сегодня:", reply_markup=keyboard)


@user_router.callback_query(F.data.startswith("ex_"))
async def process_Exercise_callback(callback: CallbackQuery):
    exercise_id = int(callback.data.split("_")[1])

    #Логируем активность в базу
    new_balance, exercise = await log_activity(
        telegram_id=callback.from_user.id,
        exercise_id=exercise_id
    )

    if exercise:
        if exercise.stars_reward > 0:
            await callback.message.edit_text(
                f"Отлично! Засчитано: <b>{exercise.name}</b> (+{exercise.stars_reward}⭐️)\n"
                f"Твой новый баланс ⭐️ <b>{new_balance}</b>"
            )
        else:
            #Здесь позже сделаем логику для кастомного достижения
            await callback.message.edit_text(
                "✨ Ты выбрал кастомное достижение!\n"
                "Напиши текстом следующим сообщением, что именно ты сделал."
            )

    await callback.answer()


#Ловим текст, когда бот находится в состоянии ожижания достижения
@user_router.message(CustomAchievement.waiting_for_text)
async def process_custom_achievement_text(message: Message, state: FSMContext):
    achievement_text = message.text

    #Сбрасываем состояние, чтобы бот снова перешел в обычный режим
    await state.clear()

    #Здесь в будущем мы добавим отправку текста администратору
    await message.answer(
        f"✅ Твое достижение принято и отправлено на рассмотрение:\n"
        f"<i>«{achievement_text}»</i>\n\n"
        f"Администратор проверит его и начислит заслуженные звезды!"
    )



