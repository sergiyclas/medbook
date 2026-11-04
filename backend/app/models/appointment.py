from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime, str_enum
from app.domain.enums import AppointmentStatus

if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.notification import Notification
    from app.models.patient import Patient
    from app.models.user import User

_ACTIVE = text("status IN ('scheduled', 'confirmed')")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        # Last line of defence against double booking: two concurrent requests
        # may both pass validation, but only one active row per slot can exist.
        Index(
            "uq_appointments_doctor_slot_active",
            "doctor_id",
            "starts_at",
            unique=True,
            postgresql_where=_ACTIVE,
            sqlite_where=_ACTIVE,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[AppointmentStatus] = mapped_column(
        str_enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED
    )
    reason: Mapped[str | None] = mapped_column(String(500))  # patient's complaint
    doctor_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    patient: Mapped[Patient] = relationship(back_populates="appointments")
    doctor: Mapped[Doctor] = relationship(back_populates="appointments")
    history: Mapped[list[AppointmentStatusChange]] = relationship(
        back_populates="appointment",
        cascade="all, delete-orphan",
        order_by="AppointmentStatusChange.changed_at",
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )


class AppointmentStatusChange(Base):
    __tablename__ = "appointment_status_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[AppointmentStatus | None] = mapped_column(str_enum(AppointmentStatus))
    to_status: Mapped[AppointmentStatus] = mapped_column(str_enum(AppointmentStatus))
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(String(500))
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    appointment: Mapped[Appointment] = relationship(back_populates="history")
    changed_by: Mapped[User | None] = relationship()
