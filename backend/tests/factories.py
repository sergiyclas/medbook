from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.domain.enums import AppointmentStatus, Role
from app.models import Appointment, Doctor, Patient, Specialization, User, WorkingHours

_counter = iter(range(1, 1_000_000))


def make_user(session: Session, role: Role, email: str | None = None) -> User:
    user = User(email=email or f"user{next(_counter)}@clinic.example", password_hash="x", role=role)
    session.add(user)
    session.flush()
    return user


def make_patient(session: Session, **fields) -> Patient:
    user = make_user(session, Role.PATIENT, fields.pop("email", None))
    patient = Patient(
        user=user,
        last_name=fields.pop("last_name", "Шевченко"),
        first_name=fields.pop("first_name", "Олена"),
        phone=fields.pop("phone", "+380671234567"),
        birth_date=fields.pop("birth_date", date(1990, 5, 17)),
        **fields,
    )
    session.add(patient)
    session.flush()
    return patient


# Doctor working Monday–Friday 09:00–13:00 and 14:00–17:00 local time
def make_doctor(session: Session, slot_minutes: int = 30, **fields) -> Doctor:
    spec = fields.pop("specialization", None) or Specialization(name=f"Spec {next(_counter)}")
    doctor = Doctor(
        user=make_user(session, Role.DOCTOR),
        specialization=spec,
        last_name=fields.pop("last_name", "Коваленко"),
        first_name=fields.pop("first_name", "Андрій"),
        slot_minutes=slot_minutes,
        **fields,
    )
    for weekday in range(5):
        for start, end in ((time(9), time(13)), (time(14), time(17))):
            doctor.working_hours.append(
                WorkingHours(weekday=weekday, start_time=start, end_time=end)
            )
    session.add(doctor)
    session.flush()
    return doctor


def make_appointment(
    session: Session,
    patient: Patient,
    doctor: Doctor,
    starts_at: datetime,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> Appointment:
    appointment = Appointment(
        patient=patient,
        doctor=doctor,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=doctor.slot_minutes),
        status=status,
    )
    session.add(appointment)
    session.flush()
    return appointment
