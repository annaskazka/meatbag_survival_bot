from datetime import datetime, date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, BigInteger, Integer, Boolean, ForeignKey, func, Date

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String)
    display_name: Mapped[str | None] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    logs: Mapped[list["ActivityLog"]] = relationship(back_populates="user")


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    stars_reward: Mapped[int] = mapped_column(default=1)
    is_repeatable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    logs: Mapped[list["ActivityLog"]] = relationship(back_populates="exercise")


class ActivityLog(Base):
    __tablename__ = "workout_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    activity_day: Mapped[date] = mapped_column(Date, nullable=False)

    user: Mapped["User"] = relationship(back_populates="logs")
    exercise: Mapped["Exercise"] = relationship(back_populates="logs", passive_deletes=True)


class PendingAchievement(Base):
    __tablename__ = "pending_achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(200), nullable=False)

    user: Mapped["User"] = relationship()
