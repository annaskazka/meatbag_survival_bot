from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_TELEGRAM_ID

from database.requests import (
    create_pending_achievement,
    approve_achievement,
    reject_achievement
)

from keyboards.user_kb import (
    get_admin_approval_kb,
    main_kb
)

from handlers.states import CustomAchievement


achievement_router = Router()


def get_repeatability_kb():
    builder = InlineKeyboardBuilder

    builder.button(
        text="🔒 Один раз в день",
        callback_data="repeat_0"
    )
    builder.button(
        text="🔁 Несколько раз в день",
        callback_data="repeat_1"
    )

    builder.adjust(1)
    return builder.as_markup()


class AdminApproval(StatesGroup):
    waiting_for_stars = State()
    waiting_for_repeatability = State()


# Ловим текст кастомного достижения от пользователя
@achievement_router.message(CustomAchievement.waiting_for_text)
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
@achievement_router.callback_query(F.data.startswith("approve_"))
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
@achievement_router.message(AdminApproval.waiting_for_stars)
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

    await state.update_data(
        reward_stars=reward_stars,
        custom_text=custom_text
    )

    await state.set_state(AdminApproval.waiting_for_repeatability)

    await message.answer(
        "Выбери, как часто пользователи смогут отмечать это достижение:",
        reply_markup=get_repeatability_kb()
    )


# Обработка нажатия кнопки "Отклонить" администратором
@achievement_router.callback_query(F.data.startswith("reject_"))
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


