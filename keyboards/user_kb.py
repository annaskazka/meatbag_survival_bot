from aiogram.types import (KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup,
                           InlineKeyboardButton, InlineKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder



#Главное меню пользователя
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💪 Отметить активность"), KeyboardButton(text="⭐️ Мой баланс")],
        [KeyboardButton(text="🏆 Рейтинг")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери действие..."
)


def get_exercise_kb(exercises) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ex in exercises:
        builder.row(
            InlineKeyboardButton(
                text=f"{ex.name} +{ex.stars_reward}⭐" if ex.stars_reward > 0 else ex.name, callback_data=f"ex_{ex.id}"
            )
        )
    return builder.as_markup()

