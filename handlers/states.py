from aiogram.fsm.state import State, StatesGroup


class CustomAchievement(StatesGroup):
    waiting_for_text = State()