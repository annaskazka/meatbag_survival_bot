from sqlalchemy import select, delete, func
from datetime import date, datetime
from database.base import async_session
from database.models import User, Exercise, ActivityLog, PendingAchievement


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
    """Возвращает список всех полезных привычек из базы, отсортированныъх по ценности"""
    async with async_session() as session:
        # Сортируем сначала по количеству звезд, потом по ID
        stmt = select(Exercise).order_by(
            (Exercise.stars_reward == 0).asc(),
            Exercise.stars_reward.asc(),
            Exercise.id.asc())
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_top_users(limit: int = 10):
    """Возвращает топ 10 пользователей по количеству звезд"""
    async with async_session() as session:
        stmt = select(User).order_by(User.stars.desc(), User.id.asc()).limit(limit)
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


async def create_pending_achievement(telegram_id: int, text: str) -> int:
    """Сохраняет кастомное достижение на модерацию и возвращает ID заявки"""
    async with async_session() as session:
        user_stmt = select(User).where(User.telegram_id == telegram_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if user:
            pending = PendingAchievement(user_id=user.id, text=text)
            session.add(pending)
            await session.commit()
            await session.refresh(pending)
            return pending.id
        return 0


async def approve_achievement(pending_id: int, reward_stars: int = 3, custom_text: str | None = None):
    """Одобряет заявкуЖ создает новое упражнение для всех и начисляет звезды автору"""
    async with async_session() as session:
        stmt = select(PendingAchievement).where(PendingAchievement.id == pending_id)
        res = await session.execute(stmt)
        pending = res.scalar_one_or_none()

        if not pending:
            return None, None

        # Подтягиваем пользователя по foreign key
        user_stmt = select(User).where(User.id == pending.user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        # Если админ указал новый текст, берем его, иначе текст из заявки
        exercise_name = custom_text.strip() if custom_text else pending.text

        new_exercise = Exercise(name=exercise_name, stars_reward=reward_stars)
        session.add(new_exercise)

        await session.flush()

        #Начисляем звезды автору заявки
        if user:
            user.stars += reward_stars

            #Также запишем в лог активности
            session.add(ActivityLog(user_id=user.id, exercise_id=new_exercise.id))

        #Удаляем заявку из таблицы ожидания
        await session.delete(pending)
        await session.commit()

        return user.telegram_id if user else None, exercise_name


async def reject_achievement(pending_id: int):
    """Отклоняет заявку без наград"""
    async with async_session() as session:
        stmt = select(PendingAchievement).where(PendingAchievement.id == pending_id)
        res = await session.execute(stmt)
        pending = res.scalar_one_or_none()

        if pending:
            #Узнаем telegram_id автора перед удалением
            user_stmt = select(User).where(User.id == pending.user_id)
            user_res = await session.execute(user_stmt)
            user = user_res.scalar_one_or_none()
            telegram_id = user.telegram_id if user else None

            await session.delete(pending)
            await session.commit()
            return telegram_id
        return None


async def delete_exercise(exercise_id: int):
    """Удаляет упражнение из общего списка"""
    async with async_session() as session:
        exercise = await session.get(Exercise, exercise_id)

        if not exercise:
            return False

        await session.execute(
            delete(ActivityLog).where(
                ActivityLog.exercise_id == exercise_id
            )
        )

        await session.delete(exercise)
        await session.commit()

        return True


async def update_exercise(exercise_id: int, new_name: str, new_stars: int):
    """Изменяет название или ценность существующего упражнения"""
    async with async_session() as session:
        exercise = await session.get(Exercise, exercise_id)
        if exercise:
            exercise.name = new_name.strip()
            exercise.stars_reward = new_stars
            await session.commit()
            return True
        return False


async def update_display_name(telegram_id: int, display_name: str):
    """Обновляет отображаемое имя пользователя в рейтинге"""
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.display_name = display_name.strip()
            await session.commit()


async def set_user_inactive(telegram_id: int):
    """Помечает пользователя неактивным, если он заблокировал бота"""
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.is_active = False
            await session.commit()



