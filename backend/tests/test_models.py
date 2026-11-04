from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import local_to_utc
from app.domain.enums import AppointmentStatus
from app.models import Appointment
from tests.factories import make_appointment, make_doctor, make_patient

SLOT = datetime(2026, 11, 16, 7, 0, tzinfo=UTC)


def test_two_active_appointments_cannot_share_a_slot(session: Session) -> None:
    doctor = make_doctor(session)
    make_appointment(session, make_patient(session), doctor, SLOT)
    with pytest.raises(IntegrityError):
        make_appointment(session, make_patient(session), doctor, SLOT)


def test_cancelled_appointment_frees_the_slot(session: Session) -> None:
    doctor = make_doctor(session)
    make_appointment(session, make_patient(session), doctor, SLOT, AppointmentStatus.CANCELLED)
    make_appointment(session, make_patient(session), doctor, SLOT)  # no IntegrityError


def test_datetimes_come_back_timezone_aware_in_utc(session: Session) -> None:
    doctor, patient = make_doctor(session), make_patient(session)
    make_appointment(session, patient, doctor, SLOT)
    session.expire_all()
    stored = session.query(Appointment).one()
    assert stored.starts_at == SLOT
    assert stored.starts_at.tzinfo is not None


def test_local_to_utc_follows_daylight_saving() -> None:
    # 09:00 in Kyiv is 06:00 UTC in summer (UTC+3) and 07:00 UTC in winter (UTC+2)
    assert local_to_utc(date(2026, 7, 1), time(9)).hour == 6
    assert local_to_utc(date(2026, 12, 1), time(9)).hour == 7
