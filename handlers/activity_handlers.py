from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.requests import get_all_exercises, log_activity
from keyboards.user_kb import get_exercise_kb
from handlers.states import CustomAchievement


activity_router = Router()


@activity_router.message(F.text == "💪 Отметить активность")
async def track_workout(message: Message):
    exercises = await get_all_exercises()
    keyboard = get_exercise_kb(exercises)
    await message.answer("Выбери, что именно ты сделал сегодня:", reply_markup=keyboard)


@activity_router.callback_query(F.data.startswith("ex_"))
async def process_Exercise_callback(callback: CallbackQuery, state: FSMContext):
    exercise_id = int(callback.data.split("_")[1])

    new_balance, exercise, error = await log_activity(
        telegram_id=callback.from_user.id,
        exercise_id=exercise_id
    )

    if error:
        await callback.message.edit_text(
            f"{error}\n"
            f"Текущий баланс <b>{new_balance}</b>"
        )
        await callback.answer()
        return

    if exercise:
        if exercise.stars_reward > 0:
            await callback.message.edit_text(
                f"Отлично! Засчитано: <b>{exercise.name}</b> (+{exercise.stars_reward}⭐️)\n"
                f"Твой новый баланс ⭐️ <b>{new_balance}</b>"
            )
        else:
            await state.set_state(CustomAchievement.waiting_for_text)
            await callback.message.edit_text(
                "✨ Ты выбрала кастомное достижение!\n"
                "Напиши текстом следующим сообщением, что именно ты сделал."
            )

    await callback.answer()
