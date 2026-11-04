from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy.orm import Session

from app.bootstrap import build_bus
from app.core.clock import local_to_utc
from app.domain.enums import AppointmentStatus as S
from app.domain.enums import NotificationChannel as Ch
from app.domain.enums import NotificationKind as K
from app.domain.enums import NotificationStatus as N
from app.domain.enums import Role
from app.services import booking_facade
from app.services.booking_facade import BookingFacade
from app.services.booking_rules import SlotTaken
from tests.factories import make_doctor, make_patient, make_user

NOW = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)  # Monday 08:00 in Kyiv
WEDNESDAY = date(2026, 11, 18)
SLOT = local_to_utc(WEDNESDAY, time(9))


@pytest.fixture
def facade(session: Session) -> BookingFacade:
    return BookingFacade(session, build_bus(session), clock=lambda: NOW)


def outbox(appt) -> set[tuple[Ch, K, N, datetime]]:
    return {(n.channel, n.kind, n.status, n.send_at) for n in appt.notifications}


def test_booking_writes_history_and_schedules_notifications(session, facade) -> None:
    patient, doctor = make_patient(session), make_doctor(session)
    appt = facade.book(patient.user, doctor.id, SLOT, "Біль у горлі")

    assert appt.status == S.SCHEDULED
    assert [(h.from_status, h.to_status) for h in appt.history] == [(None, S.SCHEDULED)]
    assert outbox(appt) == {
        (Ch.EMAIL, K.CONFIRMATION, N.PENDING, NOW),
        (Ch.EMAIL, K.REMINDER, N.PENDING, SLOT - timedelta(hours=24)),
        (Ch.SMS, K.REMINDER, N.PENDING, SLOT - timedelta(hours=2)),
    }


def test_late_booking_skips_reminders_that_are_already_due(session, facade) -> None:
    patient, doctor = make_patient(session), make_doctor(session)
    soon = local_to_utc(date(2026, 11, 16), time(11))  # three hours from NOW
    appt = facade.book(patient.user, doctor.id, soon)
    kinds = {(n.channel, n.kind) for n in appt.notifications}
    assert kinds == {(Ch.EMAIL, K.CONFIRMATION), (Ch.SMS, K.REMINDER)}


def test_sms_only_patient_gets_confirmation_by_sms(session, facade) -> None:
    patient, doctor = make_patient(session, notify_email=False), make_doctor(session)
    appt = facade.book(patient.user, doctor.id, SLOT)
    assert {(n.channel, n.kind) for n in appt.notifications} == {
        (Ch.SMS, K.CONFIRMATION),
        (Ch.SMS, K.REMINDER),
    }


def test_cancel_stops_reminders_and_sends_a_cancellation(session, facade) -> None:
    patient, doctor = make_patient(session), make_doctor(session)
    appt = facade.book(patient.user, doctor.id, SLOT)
    facade.cancel(patient.user, appt.id, "Змінилися плани")

    assert appt.status == S.CANCELLED
    by_kind = {(n.channel, n.kind): n.status for n in appt.notifications}
    assert by_kind[(Ch.EMAIL, K.REMINDER)] == N.CANCELLED
    assert by_kind[(Ch.SMS, K.REMINDER)] == N.CANCELLED
    assert by_kind[(Ch.EMAIL, K.CANCELLATION)] == N.PENDING
    assert appt.history[-1].reason == "Змінилися плани"


def test_reschedule_replaces_pending_reminders(session, facade) -> None:
    patient, doctor = make_patient(session), make_doctor(session)
    appt = facade.book(patient.user, doctor.id, SLOT)
    new_slot = SLOT + timedelta(days=1, hours=1)
    facade.reschedule(patient.user, appt.id, new_slot)

    pending = {(n.channel, n.kind, n.send_at) for n in appt.notifications if n.status == N.PENDING}
    assert pending == {
        (Ch.EMAIL, K.CONFIRMATION, NOW),
        (Ch.EMAIL, K.REMINDER, new_slot - timedelta(hours=24)),
        (Ch.SMS, K.REMINDER, new_slot - timedelta(hours=2)),
    }
    assert appt.history[-1].reason.startswith("Перенесено з 18.11.2026 09:00")


def test_second_booking_of_the_same_slot_is_refused(session, facade) -> None:
    doctor = make_doctor(session)
    facade.book(make_patient(session).user, doctor.id, SLOT)
    with pytest.raises(SlotTaken):
        facade.book(make_patient(session).user, doctor.id, SLOT)


def test_unique_index_catches_a_race_the_rules_missed(session, facade, monkeypatch) -> None:
    # Simulate two requests that both passed validation before either committed
    class PassEverything:
        def check(self, request) -> None:
            pass

    monkeypatch.setattr(booking_facade, "build_patient_chain", lambda *_: PassEverything())
    doctor = make_doctor(session)
    facade.book(make_patient(session).user, doctor.id, SLOT)
    with pytest.raises(SlotTaken):
        facade.book(make_patient(session).user, doctor.id, SLOT)


def test_day_off_cancels_only_that_days_visits(session, facade) -> None:
    doctor = make_doctor(session)
    admin = make_user(session, Role.ADMIN)
    hit = facade.book(make_patient(session).user, doctor.id, SLOT)
    spared = facade.book(make_patient(session).user, doctor.id, SLOT + timedelta(days=1))

    cancelled = facade.cancel_doctor_day(admin, doctor, WEDNESDAY, "Лікар на конференції")

    assert cancelled == [hit]
    assert hit.status == S.CANCELLED
    assert spared.status == S.SCHEDULED
    assert any(n.kind == K.CANCELLATION for n in hit.notifications)


def test_free_slots_exclude_taken_and_past_ones(session, facade) -> None:
    doctor = make_doctor(session)
    facade.book(make_patient(session).user, doctor.id, SLOT)
    slots = [s for s, _ in facade.available_slots(doctor.id, WEDNESDAY)]
    assert SLOT not in slots
    assert len(slots) == 13  # 14 half-hour slots in 09–13 and 14–17, one taken
    today_slots = facade.available_slots(doctor.id, date(2026, 11, 16))
    assert all(s > NOW for s, _ in today_slots)
