from sqlalchemy import select
from database.base import async_session
from database.models import User, Exercise, ActivityLog


async def set_user(telegram_id: int, username: str | None = None) -> User:
    async with async_session() as session:
        stmt = select(User). where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user


async def get_user(telegram_id: int) -> User:
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def add_stars(telegram_id: int, count: int = 1) -> int:
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.stars += count
            await session.commit()
            return user.stars
        return 0


async def init_exercises():
    """Заполняет справочник упражнений при первом запуске, если он пуст"""
    initial_data = [
        {"name": "🥗 Порция овощей", "stars_reward": 1},
        {"name": "🍫 0 сахара за день", "stars_reward": 2},
        {"name": "🌭 0 фастфуда и колбасы", "stars_reward": 2},
        {"name": "📊 Норма КБЖУ", "stars_reward": 3},
        {"name": "🍷 0 алкоголя (пт-вс)", "stars_reward": 3},
        {"name": "🏋️ Кроссфит", "stars_reward": 3},
        {"name": "🏃 Бег", "stars_reward": 3},
        {"name": "🏔 Поход (1 день)", "stars_reward": 5},
        {"name": "🧊 Закаливание / холодный душ", "stars_reward": 1},
        {"name": "✨ Свое достижение", "stars_reward": 0},
    ]

    async with async_session() as session:
        #Проверяем есть ли уже записи в таблице Exercise
        stmt = select(Exercise)
        result = await session.execute(stmt)
        existing = result.scalars().all()

        if not existing:
            for item in initial_data:
                exercise = Exercise(name=item["name"], stars_reward=item["stars_reward"])
                session.add(exercise)
            await session.commit()
            print("Справочник упражнений успешно инициализирован")

async def get_all_exercises():
    """Возвращает список всех полезных привычек из базы"""
    async with async_session() as session:
        stmt = select(Exercise)
        result = await session.execute(stmt)
        return result.scalars().all()


async def log_activity(telegram_id: int, exercise_id: int):
    """Записывает выполненную активность в лог и начисляет звезды"""
    async with async_session() as session:
        #Находим юзера
        user_stmt = select(User).where(User.telegram_id == telegram_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        #Находим упражнение
        ex_stmt = select(Exercise).where(Exercise.id == exercise_id)
        ex_res = await session.execute(ex_stmt)
        exercise = ex_res.scalar_one_or_none()

        if user and exercise:
            #Создаем запись в логе
            log = ActivityLog(user_id=user.id, exercise_id=exercise_id)
            session.add(log)
            #Начисляем звезды, если это не кастомное достижение в 0 звезд
            if exercise.stars_reward > 0:
                user.stars += exercise.stars_reward

            await session.commit()
            return user.stars, exercise
        return 0, None



