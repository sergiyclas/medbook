from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.schedule import DayOff, WorkingHours
    from app.models.user import User


class Specialization(Base):
    __tablename__ = "specializations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    doctors: Mapped[list[Doctor]] = relationship(back_populates="specialization")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specializations.id"), index=True)
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100))
    room: Mapped[str | None] = mapped_column(String(20))
    bio: Mapped[str | None] = mapped_column(Text)
    slot_minutes: Mapped[int] = mapped_column(default=20)
    is_active: Mapped[bool] = mapped_column(default=True)

    user: Mapped[User] = relationship(back_populates="doctor")
    specialization: Mapped[Specialization] = relationship(back_populates="doctors")
    working_hours: Mapped[list[WorkingHours]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan", order_by="WorkingHours.weekday"
    )
    days_off: Mapped[list[DayOff]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan", order_by="DayOff.day"
    )
    appointments: Mapped[list[Appointment]] = relationship(back_populates="doctor")

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)

    @property
    def email(self) -> str:
        return self.user.email
