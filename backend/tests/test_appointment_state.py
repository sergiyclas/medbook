from datetime import UTC, datetime, timedelta

import pytest

from app.domain.appointment_state import InvalidTransition, TransitionContext
from app.domain.enums import AppointmentStatus as S
from app.domain.enums import Role
from app.domain.errors import Forbidden
from app.domain.events import AppointmentRescheduled, AppointmentStatusChanged
from app.models import Appointment, Doctor, Patient, User

NOW = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)
PATIENT = User(id=1, email="p@clinic.example", password_hash="x", role=Role.PATIENT)
DOCTOR = User(id=2, email="d@clinic.example", password_hash="x", role=Role.DOCTOR)
ADMIN = User(id=3, email="a@clinic.example", password_hash="x", role=Role.ADMIN)


def appointment(status: S = S.SCHEDULED, starts_in: timedelta = timedelta(days=1)) -> Appointment:
    starts = NOW + starts_in
    return Appointment(
        patient=Patient(user=PATIENT),
        doctor=Doctor(user=DOCTOR, slot_minutes=30),
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        status=status,
    )


def ctx(actor: User, now: datetime = NOW) -> TransitionContext:
    return TransitionContext(actor=actor, now=now, patient_cancel_cutoff_hours=2)


def test_states_are_shared_flyweight_like_instances() -> None:
    assert appointment().state is appointment().state
    assert appointment(S.CONFIRMED).state is not appointment().state


def test_admin_confirms_scheduled_visit_and_an_event_is_recorded() -> None:
    appt = appointment()
    appt.confirm(ctx(ADMIN))
    assert appt.status == S.CONFIRMED
    [event] = appt.pull_events()
    assert isinstance(event, AppointmentStatusChanged)
    assert (event.old, event.new, event.actor_id) == (S.SCHEDULED, S.CONFIRMED, ADMIN.id)
    assert appt.pull_events() == []  # events are handed out once


def test_patient_cannot_confirm_and_confirmed_cannot_be_confirmed_twice() -> None:
    with pytest.raises(Forbidden):
        appointment().confirm(ctx(PATIENT))
    with pytest.raises(InvalidTransition):
        appointment(S.CONFIRMED).confirm(ctx(ADMIN))


def test_patient_cancels_only_before_the_cutoff_admin_any_time() -> None:
    early = appointment(starts_in=timedelta(hours=5))
    early.cancel(ctx(PATIENT), "Захворіла дитина")
    assert early.status == S.CANCELLED

    late = appointment(starts_in=timedelta(hours=1))
    with pytest.raises(InvalidTransition) as err:
        late.cancel(ctx(PATIENT))
    assert err.value.code == "too_late"
    late.cancel(ctx(ADMIN))
    assert late.status == S.CANCELLED


def test_doctor_cannot_cancel() -> None:
    with pytest.raises(Forbidden):
        appointment().cancel(ctx(DOCTOR))


def test_visit_is_completed_only_after_it_started() -> None:
    appt = appointment(S.CONFIRMED, starts_in=timedelta(minutes=30))
    with pytest.raises(InvalidTransition) as err:
        appt.complete(ctx(DOCTOR), "Огляд")
    assert err.value.code == "not_started"

    appt.complete(ctx(DOCTOR, now=NOW + timedelta(minutes=45)), "Стан задовільний")
    assert appt.status == S.COMPLETED
    assert appt.doctor_notes == "Стан задовільний"


def test_reschedule_moves_the_visit_and_requires_new_confirmation() -> None:
    appt = appointment(S.CONFIRMED)
    old_start = appt.starts_at
    appt.reschedule(ctx(ADMIN), old_start + timedelta(days=2))
    assert appt.status == S.SCHEDULED
    assert appt.ends_at - appt.starts_at == timedelta(minutes=30)
    [event] = appt.pull_events()
    assert isinstance(event, AppointmentRescheduled)
    assert (event.old_status, event.old_starts_at) == (S.CONFIRMED, old_start)


@pytest.mark.parametrize("status", [S.COMPLETED, S.CANCELLED, S.NO_SHOW])
@pytest.mark.parametrize(
    "action",
    [
        lambda a: a.confirm(ctx(ADMIN)),
        lambda a: a.cancel(ctx(ADMIN)),
        lambda a: a.complete(ctx(ADMIN, NOW + timedelta(days=2)), None),
        lambda a: a.mark_no_show(ctx(ADMIN, NOW + timedelta(days=2))),
        lambda a: a.reschedule(ctx(ADMIN), NOW + timedelta(days=3)),
    ],
    ids=["confirm", "cancel", "complete", "no_show", "reschedule"],
)
def test_final_states_refuse_every_action(status: S, action) -> None:
    appt = appointment(status)
    with pytest.raises(InvalidTransition):
        action(appt)
    assert appt.status == status
