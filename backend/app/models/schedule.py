from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.doctor import Doctor


# Weekly template in local clinic time. Several rows per weekday describe
# a working day with breaks (08:00–12:00, 13:00–17:00).
class WorkingHours(Base):
    __tablename__ = "working_hours"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("start_time < end_time", name="start_before_end"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int]  # 0 = Monday, as in date.weekday()
    start_time: Mapped[time]
    end_time: Mapped[time]

    doctor: Mapped[Doctor] = relationship(back_populates="working_hours")


class DayOff(Base):
    __tablename__ = "days_off"
    __table_args__ = (UniqueConstraint("doctor_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), index=True)
    day: Mapped[date]
    reason: Mapped[str | None] = mapped_column(String(200))

    doctor: Mapped[Doctor] = relationship(back_populates="days_off")
