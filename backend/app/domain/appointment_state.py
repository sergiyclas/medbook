from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, ClassVar

from app.domain.enums import AppointmentStatus, Role
from app.domain.errors import Conflict, Forbidden

if TYPE_CHECKING:
    from app.models import Appointment, User

STATUS_LABELS = {
    AppointmentStatus.SCHEDULED: "заплановано",
    AppointmentStatus.CONFIRMED: "підтверджено",
    AppointmentStatus.COMPLETED: "завершено",
    AppointmentStatus.CANCELLED: "скасовано",
    AppointmentStatus.NO_SHOW: "неявка",
}
ACTION_LABELS = {
    "confirm": "підтвердити",
    "cancel": "скасувати",
    "complete": "завершити",
    "mark_no_show": "позначити неявку",
    "reschedule": "перенести",
}


class InvalidTransition(Conflict):
    code = "invalid_transition"


@dataclass(frozen=True)
class TransitionContext:
    actor: User
    now: datetime
    patient_cancel_cutoff_hours: int


# GoF State. Appointment is the Context: it keeps only the status value and
# delegates every lifecycle action to the state object for that status. States
# hold no data, so one shared instance per status is enough (see STATES).
class AppointmentState:
    status: ClassVar[AppointmentStatus]
    is_active: ClassVar[bool] = False

    def confirm(self, appt: Appointment, ctx: TransitionContext) -> None:
        raise self._refuse("confirm")

    def cancel(self, appt: Appointment, ctx: TransitionContext, reason: str | None) -> None:
        raise self._refuse("cancel")

    def complete(self, appt: Appointment, ctx: TransitionContext, notes: str | None) -> None:
        raise self._refuse("complete")

    def mark_no_show(self, appt: Appointment, ctx: TransitionContext) -> None:
        raise self._refuse("mark_no_show")

    def reschedule(
        self, appt: Appointment, ctx: TransitionContext, starts_at: datetime, ends_at: datetime
    ) -> None:
        raise self._refuse("reschedule")

    def _refuse(self, action: str) -> InvalidTransition:
        return InvalidTransition(
            f"Неможливо {ACTION_LABELS[action]} прийом зі статусом «{STATUS_LABELS[self.status]}»"
        )


# Behaviour shared by both states that still hold a slot in the schedule
class _ActiveState(AppointmentState):
    is_active = True

    def cancel(self, appt: Appointment, ctx: TransitionContext, reason: str | None) -> None:
        if ctx.actor.role == Role.DOCTOR:
            raise Forbidden("Лікар не скасовує прийоми – зверніться до адміністратора")
        if ctx.actor.role == Role.PATIENT:
            self._ensure_before_cutoff(appt, ctx)
        appt.transition_to(AppointmentStatus.CANCELLED, ctx, reason)

    def complete(self, appt: Appointment, ctx: TransitionContext, notes: str | None) -> None:
        self._ensure_staff(ctx)
        self._ensure_started(appt, ctx)
        appt.doctor_notes = notes
        appt.transition_to(AppointmentStatus.COMPLETED, ctx, None)

    def mark_no_show(self, appt: Appointment, ctx: TransitionContext) -> None:
        self._ensure_staff(ctx)
        self._ensure_started(appt, ctx)
        appt.transition_to(AppointmentStatus.NO_SHOW, ctx, None)

    # A moved visit needs to be confirmed again, so it always lands in Scheduled
    def reschedule(
        self, appt: Appointment, ctx: TransitionContext, starts_at: datetime, ends_at: datetime
    ) -> None:
        if ctx.actor.role == Role.DOCTOR:
            raise Forbidden("Лікар не переносить прийоми – зверніться до адміністратора")
        if ctx.actor.role == Role.PATIENT:
            self._ensure_before_cutoff(appt, ctx)
        appt.move_to(starts_at, ends_at, ctx)

    @staticmethod
    def _ensure_before_cutoff(appt: Appointment, ctx: TransitionContext) -> None:
        cutoff = timedelta(hours=ctx.patient_cancel_cutoff_hours)
        if appt.starts_at - ctx.now < cutoff:
            raise InvalidTransition(
                f"Онлайн це можна зробити не пізніше ніж за {ctx.patient_cancel_cutoff_hours} год "
                "до прийому. Зателефонуйте в реєстратуру.",
                "too_late",
            )

    @staticmethod
    def _ensure_staff(ctx: TransitionContext) -> None:
        if ctx.actor.role == Role.PATIENT:
            raise Forbidden("Ця дія доступна лише персоналу клініки")

    @staticmethod
    def _ensure_started(appt: Appointment, ctx: TransitionContext) -> None:
        if ctx.now < appt.starts_at:
            raise InvalidTransition("Прийом ще не розпочався", "not_started")


class ScheduledState(_ActiveState):
    status = AppointmentStatus.SCHEDULED

    def confirm(self, appt: Appointment, ctx: TransitionContext) -> None:
        self._ensure_staff(ctx)
        appt.transition_to(AppointmentStatus.CONFIRMED, ctx, None)


class ConfirmedState(_ActiveState):
    status = AppointmentStatus.CONFIRMED


class CompletedState(AppointmentState):
    status = AppointmentStatus.COMPLETED


class CancelledState(AppointmentState):
    status = AppointmentStatus.CANCELLED


class NoShowState(AppointmentState):
    status = AppointmentStatus.NO_SHOW


STATES: dict[AppointmentStatus, AppointmentState] = {
    state.status: state
    for state in (
        ScheduledState(),
        ConfirmedState(),
        CompletedState(),
        CancelledState(),
        NoShowState(),
    )
}
