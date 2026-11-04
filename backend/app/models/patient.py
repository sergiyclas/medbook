from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.user import User


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))  # E.164, e.g. +380671234567
    birth_date: Mapped[date]
    notify_email: Mapped[bool] = mapped_column(default=True)
    notify_sms: Mapped[bool] = mapped_column(default=True)
    # Registration moment – the "new patients" report is built from it
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, index=True)

    user: Mapped[User] = relationship(back_populates="patient")
    appointments: Mapped[list[Appointment]] = relationship(back_populates="patient")

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)

    @property
    def email(self) -> str:
        return self.user.email
