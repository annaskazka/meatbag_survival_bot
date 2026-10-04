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
    create_pending_achievement, approve_achievement, reject_achievement, delete_exercise
)
from keyboards.user_kb import main_kb, get_exercise_kb, get_admin_approval_kb

user_router = Router()


class CustomAchievement(StatesGroup):
    waiting_for_text = State()


class AdminApproval(StatesGroup):
    waiting_for_stars = State()


@user_router.message(CommandStart())
async def cmd_start(message: Message):
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
    await message.answer(f"Твой текущий баланс: ⭐️ <b>{stars}</b> звезд.")


@user_router.message(F.text == "💪 Отметить активность")
async def track_workout(message: Message):
    exercises = await get_all_exercises()
    keyboard = get_exercise_kb(exercises)
    await message.answer("Выбери, что именно ты сделал сегодня:", reply_markup=keyboard)


@user_router.callback_query(F.data.startswith("ex_"))
async def process_Exercise_callback(callback: CallbackQuery, state: FSMContext):
    exercise_id = int(callback.data.split("_")[1])

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
            await state.set_state(CustomAchievement.waiting_for_text)
            await callback.message.edit_text(
                "✨ Ты выбрала кастомное достижение!\n"
                "Напиши текстом следующим сообщением, что именно ты сделал."
            )

    await callback.answer()


# Ловим текст кастомного достижения от пользователя
@user_router.message(CustomAchievement.waiting_for_text)
async def process_custom_achievement_text(message: Message, state: FSMContext):
    achievement_text = message.text
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    await state.clear()

    # Сохраняем заявку в базу и получаем ее ID
    pending_id = await create_pending_achievement(telegram_id=user_id, text=achievement_text)

    if pending_id:
        admin_text = (
            f"🔔 <b>Новая заявка на кастомное достижение!</b>\n\n"
            f"От: @{username} (ID: <code>{user_id}</code>)\n"
            f"Достижение: <i>«{achievement_text}»</i>"
        )

        try:
            # Отправляем сообщение админу С КНОПКАМИ
            await message.bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=admin_text,
                reply_markup=get_admin_approval_kb(pending_id)
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление админу: {e}")

    await message.answer(
        f"✅ Твое достижение принято и отправлено на рассмотрение:\n"
        f"<i>«{achievement_text}»</i>\n\n"
        f"Администратор проверит его. Если оно ценное, оно появится в общем списке для всех!",
        reply_markup=main_kb
    )


# 1. Администратор нажал "Одобрить" -> переводим его в состояние ожидания цифры звезд
@user_router.callback_query(F.data.startswith("approve_"))
async def process_approve_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_TELEGRAM_ID:
        await callback.answer("У тебя нет прав администратора!", show_alert=True)
        return

    pending_id = int(callback.data.split("_")[1])

    await state.set_state(AdminApproval.waiting_for_stars)
    await state.update_data(pending_id=pending_id)

    await callback.message.edit_text(
        "✍️ <b>Одобрение кастомного достижения</b>\n\n"
        "Отправь следующим сообщением количество звезд (числом), которое нужно начислить:"
    )
    await callback.answer()


# 2. Ловим цифру, которую прислал администратор
@user_router.message(AdminApproval.waiting_for_stars)
async def process_admin_stars_input(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        return

    text = message.text.strip()
    custom_text = None

    if "|" in text:
        parts = text.split("|", 1)
        custom_text = parts[0].strip()
        stars_str = parts[1].strip()
    else:
        stars_str = text

    if not stars_str.isdigit():
        await message.answer(
            "⚠️ Неверный формат!\n"
            "Отправь просто число (например: <code>3</code>)\n"
            "или новый текст с количеством через черту (например: <code>Пройти 10к шагов | 4</code>)."
        )
        return

    reward_stars = int(stars_str)
    data = await state.get_data()
    pending_id = data.get("pending_id")

    await state.clear()

    # Запускаем одобрение в базе с введенным количеством звезд
    author_telegram_id, achievement_text = await approve_achievement(
        pending_id,
        reward_stars=reward_stars,
        custom_text=custom_text
    )

    if author_telegram_id:
        try:
            await message.bot.send_message(
                chat_id=author_telegram_id,
                text=f"🎉 <b>Твое достижение одобрено!</b>\n\n"
                     f"<i>«{achievement_text}»</i>\n"
                     f"Оно добавлено в общий список привычек для всех, а тебе начислено <b>+{reward_stars}⭐</b>!"
            )
        except Exception:
            pass

    await message.answer(
        f"✅ <b>Успешно добавлено в общий список!</b>\n"
        f"Достижение: <i>«{achievement_text}»</i>\n"
        f"Награда: <b>+{reward_stars}⭐</b>"
    )


# Обработка нажатия кнопки "Отклонить" администратором
@user_router.callback_query(F.data.startswith("reject_"))
async def process_reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_TELEGRAM_ID:
        await callback.answer("У тебя нет прав администратора!", show_alert=True)
        return

    pending_id = int(callback.data.split("_")[1])
    author_telegram_id = await reject_achievement(pending_id)

    if author_telegram_id:
        try:
            await callback.bot.send_message(
                chat_id=author_telegram_id,
                text="❌ К сожалению, твое кастомное достижение было отклонено администратором."
            )
        except Exception:
            pass

    await callback.message.edit_text(
        f"❌ <b>Заявка отклонена.</b>"
    )
    await callback.answer("Заявка отклонена.")


@user_router.message(Command("manage"))
async def admin_manage_exercises(message: Message):
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        return

    exercises = await get_all_exercises()

    builder = InlineKeyboardBuilder()
    for ex in exercises:
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


@user_router.callback_query(F.data.startswith("delex_"))
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

