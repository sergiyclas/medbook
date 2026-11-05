from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime, str_enum
from app.domain.appointment_state import STATES, AppointmentState, TransitionContext
from app.domain.enums import AppointmentStatus
from app.domain.events import (
    AppointmentBooked,
    AppointmentRescheduled,
    AppointmentStatusChanged,
    DomainEvent,
)

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

    # GRASP Creator: the appointment knows how to come into existence correctly
    @classmethod
    def book(
        cls,
        patient: Patient,
        doctor: Doctor,
        starts_at: datetime,
        reason: str | None,
        actor: User,
        now: datetime,
    ) -> Appointment:
        appt = cls(
            patient=patient,
            doctor=doctor,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=doctor.slot_minutes),
            status=AppointmentStatus.SCHEDULED,
            reason=reason,
            created_at=now,
        )
        appt.record(AppointmentBooked(appt, actor.id, now))
        return appt

    # ---------- GoF State: Context side ----------
    @property
    def state(self) -> AppointmentState:
        return STATES[self.status]

    def confirm(self, ctx: TransitionContext) -> None:
        self.state.confirm(self, ctx)

    def cancel(self, ctx: TransitionContext, reason: str | None = None) -> None:
        self.state.cancel(self, ctx, reason)

    def complete(self, ctx: TransitionContext, notes: str | None = None) -> None:
        self.state.complete(self, ctx, notes)

    def mark_no_show(self, ctx: TransitionContext) -> None:
        self.state.mark_no_show(self, ctx)

    def reschedule(self, ctx: TransitionContext, starts_at: datetime) -> None:
        ends_at = starts_at + timedelta(minutes=self.doctor.slot_minutes)
        self.state.reschedule(self, ctx, starts_at, ends_at)

    # Called by state objects only – they have already validated the transition
    def transition_to(
        self, new: AppointmentStatus, ctx: TransitionContext, reason: str | None
    ) -> None:
        old, self.status = self.status, new
        self.record(AppointmentStatusChanged(self, old, new, ctx.actor.id, reason, ctx.now))

    def move_to(self, starts_at: datetime, ends_at: datetime, ctx: TransitionContext) -> None:
        old_status, old_start = self.status, self.starts_at
        self.starts_at, self.ends_at, self.status = starts_at, ends_at, AppointmentStatus.SCHEDULED
        self.record(AppointmentRescheduled(self, old_status, old_start, ctx.actor.id, ctx.now))

    # ---------- domain events (not persisted) ----------
    def record(self, event: DomainEvent) -> None:
        self.__dict__.setdefault("_pending_events", []).append(event)

    def pull_events(self) -> list[DomainEvent]:
        return self.__dict__.pop("_pending_events", [])

    @property
    def cancellation_reason(self) -> str | None:
        if self.status != AppointmentStatus.CANCELLED:
            return None
        return next((h.reason for h in reversed(self.history) if h.to_status == self.status), None)


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

    @property
    def changed_by_email(self) -> str | None:
        return self.changed_by.email if self.changed_by else None

    @property
    def changed_by_role(self) -> str | None:
        return self.changed_by.role.value if self.changed_by else None
