from aiogram import Router, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_TELEGRAM_ID
from database.requests import (
    get_all_exercises,
    delete_exercise,
    update_exercise
)


admin_router = Router()


class AdminEditExercise(StatesGroup):
    waiting_for_name = State()
    waiting_for_stars = State()


@admin_router.message(Command("manage"))
async def admin_manage_exercises(message: Message):
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        return

    exercises = await get_all_exercises()

    builder = InlineKeyboardBuilder()
    for ex in exercises:
        builder.button(
            text=f"✏️ Изменить: {ex.name} ({ex.stars_reward}⭐)",
            callback_data=f"editex_{ex.id}"
        )
        builder.button(
            text=f"❌ Удалить: {ex.name} ({ex.stars_reward}⭐)",
            callback_data=f"delex_{ex.id}"
        )
    builder.adjust(1)

    await message.answer(
        "🛠 <b>Управление общим списком привычек</b>\n"
        "Нажми на кнопку нужной привычки, чтобы навсегда удалить её из списка:",
        reply_markup=builder.as_markup()
    )


@admin_router.callback_query(F.data.startswith("editex_"))
async def admin_edit_exercise(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_TELEGRAM_ID:
        await callback.answer()
        return

    exercise_id = int(callback.data.split("_")[1])
    exercises = await get_all_exercises()
    exercise = next((ex for ex in exercises if ex.id == exercise_id), None)

    if not exercise:
        await callback.answer("Активность не найдена", show_alert=True)
        return

    await state.update_data(
        exercise_id=exercise.id,
        old_name=exercise.name,
        old_stars=exercise.stars_reward
    )
    await state.set_state(AdminEditExercise.waiting_for_name)

    await callback.message.answer(
        f"✏️ Текущее название: {exercise.name}\n"
        "Отправь новое название активности:"
    )
    await callback.answer()


@admin_router.message(AdminEditExercise.waiting_for_stars)
async def admin_edit_exercise_stars(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        return

    if not message.text.isdigit():
        await message.answer("Отправь количество звёзд целым неотрицательным числом:")
        return

    new_stars = int(message.text)

    data = await state.get_data()

    success = await update_exercise(
        exercise_id=data["exercise_id"],
        new_name=data["new_name"],
        new_stars=new_stars
    )

    await state.clear()

    if success:
        await message.answer(
            f"✅ Активность обновлена!\n"
            f"Название: {data['new_name']}\n"
            f"Награда: {new_stars}⭐"
        )
    else:
        await message.answer("Не удалось обновить активность.")


@admin_router.message(AdminEditExercise.waiting_for_name)
async def admin_edit_exercise_name(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        return

    new_name = message.text.strip()

    if not new_name:
        await message.answer("Название не может быть пустым. Попробуй ещё раз:")
        return

    await state.update_data(new_name=new_name)
    await state.set_state(AdminEditExercise.waiting_for_stars)

    await message.answer("Теперь отправь новое количество звёзд за эту активность:")


@admin_router.callback_query(F.data.startswith("delex_"))
async def process_delete_exercise(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_TELEGRAM_ID:
        await callback.answer("У тебя нет прав администратора!", show_alert=True)
        return

    exercise_id = int(callback.data.split("_")[1])
    success = await delete_exercise(exercise_id)

    if success:
        await callback.answer("Привычка успешно удалена!", show_alert=True)

        exercises = await get_all_exercises()
        builder = InlineKeyboardBuilder()
        for ex in exercises:
            builder.button(
                text=f"✏️ Изменить: {ex.name} ({ex.stars_reward}⭐)",
                callback_data=f"editex_{ex.id}"
            )
            builder.button(
                text=f"❌ Удалить: {ex.name} ({ex.stars_reward}⭐)",
                callback_data=f"delex_{ex.id}"
            )
        builder.adjust(1)

        try:
            await callback.message.edit_text(
                "🛠 <b>Управление общим списком привычек</b>\n"
                "Привычка удалена. Актуальный список:",
                reply_markup=builder.as_markup()
            )
        except Exception:
            pass
    else:
        await callback.answer("Не удалось найти такую привычку.", show_alert=True)

