from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.clock import local_to_utc
from app.domain.errors import DomainError
from app.models import ClinicSettings, DayOff
from app.repositories.appointments import AppointmentRepository
from app.services.availability import AvailabilityCalendar
from app.services.booking_rules import (
    BookingRequest,
    SlotTaken,
    build_admin_chain,
    build_patient_chain,
)
from tests.factories import make_appointment, make_doctor, make_patient

NOW = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)  # Monday 08:00 in Kyiv
WEDNESDAY = date(2026, 11, 18)


def at(hour: int, minute: int = 0, day: date = WEDNESDAY) -> datetime:
    return local_to_utc(day, time(hour, minute))


@pytest.fixture
def world(session: Session):
    doctor = make_doctor(session, slot_minutes=30)  # Mon–Fri 09–13, 14–17
    patient = make_patient(session)
    calendar = AvailabilityCalendar(AppointmentRepository(session))
    settings = ClinicSettings(booking_horizon_days=30, max_daily_bookings_per_patient=2)

    def request(starts_at: datetime, **kw) -> BookingRequest:
        return BookingRequest(
            kw.pop("doctor", doctor), kw.pop("patient", patient), starts_at, NOW, settings, **kw
        )

    patient_chain = build_patient_chain(calendar, calendar.appointments)
    admin_chain = build_admin_chain(calendar, calendar.appointments)
    return doctor, patient, request, patient_chain, admin_chain


def rejected_code(chain, request) -> str:
    with pytest.raises(DomainError) as err:
        chain.check(request)
    return err.value.code


def test_valid_slot_passes_the_whole_chain(world) -> None:
    _, _, request, patient_chain, _ = world
    patient_chain.check(request(at(9, 30)))


@pytest.mark.parametrize(
    ("starts_at", "code"),
    [
        (NOW - timedelta(hours=1), "in_past"),
        (at(9, day=WEDNESDAY + timedelta(days=42)), "beyond_horizon"),
        (at(13, 0), "outside_hours"),  # lunch break
        (at(16, 45), "outside_hours"),  # the visit would end after 17:00
        (at(9, 10), "not_on_grid"),
    ],
)
def test_each_rule_rejects_its_own_case(world, starts_at: datetime, code: str) -> None:
    _, _, request, patient_chain, _ = world
    assert rejected_code(patient_chain, request(starts_at)) == code


def test_day_off_and_inactive_doctor(session: Session, world) -> None:
    doctor, _, request, patient_chain, _ = world
    doctor.days_off.append(DayOff(day=WEDNESDAY))
    assert rejected_code(patient_chain, request(at(9))) == "day_off"
    doctor.is_active = False
    assert rejected_code(patient_chain, request(at(9))) == "doctor_inactive"


def test_taken_slot_is_a_conflict(session: Session, world) -> None:
    doctor, _, request, patient_chain, _ = world
    make_appointment(session, make_patient(session), doctor, at(9))
    with pytest.raises(SlotTaken):
        patient_chain.check(request(at(9)))


def test_patient_cannot_be_in_two_places_at_once(session: Session, world) -> None:
    _, patient, request, patient_chain, _ = world
    make_appointment(session, patient, make_doctor(session), at(9))
    assert rejected_code(patient_chain, request(at(9))) == "patient_overlap"


def test_daily_limit_applies_to_patients_but_not_to_reception(session: Session, world) -> None:
    _, patient, request, patient_chain, admin_chain = world
    make_appointment(session, patient, make_doctor(session), at(10))
    make_appointment(session, patient, make_doctor(session), at(11))
    assert rejected_code(patient_chain, request(at(14))) == "daily_limit"
    admin_chain.check(request(at(14)))


def test_reception_may_book_beyond_the_online_horizon(world) -> None:
    _, _, request, patient_chain, admin_chain = world
    far = at(9, day=WEDNESDAY + timedelta(days=42))
    assert rejected_code(patient_chain, request(far)) == "beyond_horizon"
    admin_chain.check(request(far))


def test_rescheduling_does_not_clash_with_itself(session: Session, world) -> None:
    doctor, patient, request, patient_chain, _ = world
    other = make_appointment(session, patient, make_doctor(session), at(10))
    moving = make_appointment(session, patient, doctor, at(11))
    assert other.id != moving.id
    # Two visits that day already: a third is over the limit, moving one is not
    assert rejected_code(patient_chain, request(at(14))) == "daily_limit"
    patient_chain.check(request(at(14), exclude_id=moving.id))
