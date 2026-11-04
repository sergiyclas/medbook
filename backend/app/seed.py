# Demo data: specializations, doctors with schedules, patients registered over the
# last months and appointment history, so every screen and report has content.
# Usage: python -m app.seed [--force]   (--force wipes existing data first)

import argparse
import bisect
import random
from datetime import date, datetime, time, timedelta

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import local_today, to_local, utc_now
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal
from app.domain.availability import slot_starts
from app.domain.enums import (
    AppointmentStatus as S,
)
from app.domain.enums import (
    NotificationChannel,
    NotificationKind,
    NotificationStatus,
    Role,
)
from app.models import (
    Appointment,
    AppointmentStatusChange,
    ClinicSettings,
    DayOff,
    Doctor,
    Notification,
    Patient,
    Specialization,
    User,
    WorkingHours,
)

HISTORY_DAYS = 180
FUTURE_DAYS = 14
DEMO_PASSWORDS = {"admin": "admin123", "doctor": "doctor123", "patient": "patient123"}

SPECIALIZATIONS = [
    ("Терапевт", "Первинний огляд, лікування застуди, направлення до вузьких спеціалістів", 20),
    ("Кардіолог", "Серцево-судинні захворювання, ЕКГ, контроль тиску", 30),
    ("Невролог", "Головний біль, порушення сну, захворювання нервової системи", 30),
    ("Педіатр", "Огляд і лікування дітей від народження до 18 років", 20),
    ("Офтальмолог", "Перевірка зору, підбір окулярів, захворювання очей", 20),
    ("Дерматолог", "Захворювання шкіри, волосся та нігтів", 20),
    ("Отоларинголог", "Захворювання вуха, горла та носа", 20),
    ("Ендокринолог", "Щитоподібна залоза, цукровий діабет, гормональні порушення", 30),
]
# Specialization index per doctor: two therapists and two paediatricians
DOCTOR_SPECS = [0, 0, 1, 2, 3, 3, 4, 5, 6, 7]

WEEKDAYS = range(5)
SCHEDULES = {
    "morning": {wd: [(time(8), time(14))] for wd in WEEKDAYS},
    "evening": {wd: [(time(13), time(19))] for wd in WEEKDAYS},
    "full": {wd: [(time(9), time(13)), (time(14), time(18))] for wd in WEEKDAYS}
    | {5: [(time(9), time(13))]},
}

REASONS = [
    "Підвищена температура, кашель",
    "Профілактичний огляд",
    "Головний біль протягом тижня",
    "Біль у горлі",
    "Повторна консультація за результатами аналізів",
    "Підвищений тиск",
    "Висип на шкірі",
    "Погіршення зору",
    "Довідка для роботи",
    "Біль у вусі",
]
NOTES = [
    "Призначено аналізи, повторний огляд через 2 тижні.",
    "Стан задовільний, рекомендації надано.",
    "Призначено лікування, контроль через 7 днів.",
    "Направлено до вузького спеціаліста.",
    "Патології не виявлено.",
]
PHONE_PREFIXES = ["50", "63", "66", "67", "68", "73", "93", "95", "96", "97", "98", "99"]


def _names(fake: Faker, rnd: random.Random) -> tuple[str, str, str]:
    if rnd.random() < 0.5:
        return fake.last_name_male(), fake.first_name_male(), fake.middle_name_male()
    return fake.last_name_female(), fake.first_name_female(), fake.middle_name_female()


def _phone(rnd: random.Random) -> str:
    return f"+380{rnd.choice(PHONE_PREFIXES)}{rnd.randint(0, 9_999_999):07d}"


def _user(email: str, password: str, role: Role, created_at: datetime) -> User:
    return User(
        email=email, password_hash=hash_password(password), role=role, created_at=created_at
    )


def _wipe(session: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())


def _create_doctors(
    session: Session, fake: Faker, rnd: random.Random, now: datetime
) -> list[tuple[Doctor, dict]]:
    specs = [Specialization(name=n, description=d) for n, d, _ in SPECIALIZATIONS]
    session.add_all(specs)
    # One password hash for all staff accounts: bcrypt is slow on purpose
    staff_hash = hash_password(DEMO_PASSWORDS["doctor"])
    doctors = []
    for i, spec_index in enumerate(DOCTOR_SPECS):
        last, first, middle = _names(fake, rnd)
        email = "doctor@medbook.example" if i == 0 else f"doctor{i + 1:02d}@medbook.example"
        schedule = (
            SCHEDULES["full"] if i == 0 else SCHEDULES[rnd.choice(["morning", "evening", "full"])]
        )
        doctor = Doctor(
            user=User(email=email, password_hash=staff_hash, role=Role.DOCTOR, created_at=now),
            specialization=specs[spec_index],
            last_name=last,
            first_name=first,
            middle_name=middle,
            room=str(100 + i * 3),
            bio=f"{SPECIALIZATIONS[spec_index][0]}, стаж {rnd.randint(4, 30)} років.",
            slot_minutes=SPECIALIZATIONS[spec_index][2],
        )
        for weekday, intervals in schedule.items():
            for start, end in intervals:
                doctor.working_hours.append(
                    WorkingHours(weekday=weekday, start_time=start, end_time=end)
                )
        doctors.append((doctor, schedule))
    session.add_all(d for d, _ in doctors)
    return doctors


def _add_days_off(doctors: list[tuple[Doctor, dict]], rnd: random.Random, today: date) -> None:
    for i, (doctor, _) in enumerate(doctors):
        vacation = today - timedelta(days=rnd.randint(20, HISTORY_DAYS - 10))
        for k in range(7):
            doctor.days_off.append(DayOff(day=vacation + timedelta(days=k), reason="Відпустка"))
        if i % 3 == 1:
            doctor.days_off.append(
                DayOff(
                    day=today + timedelta(days=rnd.randint(3, FUTURE_DAYS)), reason="Конференція"
                )
            )


def _create_patients(fake: Faker, rnd: random.Random, now: datetime) -> list[Patient]:
    # A base registered before the history window plus new registrations
    # that grow towards today – gives the "new patients" report a trend.
    moments = [now - timedelta(days=rnd.randint(HISTORY_DAYS, 365)) for _ in range(120)]
    offsets = list(range(HISTORY_DAYS))
    weights = [1 + (HISTORY_DAYS - d) / 60 for d in offsets]
    moments += [
        now - timedelta(days=d, hours=rnd.randint(0, 23), minutes=rnd.randint(0, 59))
        for d in rnd.choices(offsets, weights, k=280)
    ]
    moments.sort()
    # Seeded people get notifications disabled: their e-mails and phones are
    # invented, and live mode must never message a real stranger.
    patient_hash = hash_password(DEMO_PASSWORDS["patient"])
    patients = []
    for n, created in enumerate(moments, start=1):
        last, first, middle = _names(fake, rnd)
        patients.append(
            Patient(
                user=User(
                    email=f"patient{n:03d}@example.com",
                    password_hash=patient_hash,
                    role=Role.PATIENT,
                    created_at=created,
                ),
                last_name=last,
                first_name=first,
                middle_name=middle,
                phone=_phone(rnd),
                birth_date=fake.date_between(date(1945, 1, 1), date(2020, 12, 31)),
                notify_email=False,
                notify_sms=False,
                created_at=created,
            )
        )
    return patients


def _history(appt: Appointment, patient: Patient, doctor: Doctor, rnd: random.Random) -> None:
    appt.history.append(
        AppointmentStatusChange(
            from_status=None,
            to_status=S.SCHEDULED,
            changed_by=patient.user,
            changed_at=appt.created_at,
        )
    )
    if appt.status == S.SCHEDULED:
        return
    if appt.status == S.CANCELLED:
        span = max((appt.starts_at - appt.created_at).total_seconds(), 60)
        at, by, reason = (
            appt.created_at + timedelta(seconds=rnd.uniform(0, span)),
            patient.user,
            "Змінилися плани",
        )
    elif appt.status == S.CONFIRMED:
        at, by, reason = appt.created_at + timedelta(hours=1), None, None
    else:
        at, by, reason = appt.ends_at, doctor.user, None
    appt.history.append(
        AppointmentStatusChange(
            from_status=S.SCHEDULED,
            to_status=appt.status,
            changed_by=by,
            reason=reason,
            changed_at=at,
        )
    )


def _demo_notifications(appt: Appointment) -> None:
    def sent(channel, kind, at):
        appt.notifications.append(
            Notification(
                channel=channel,
                kind=kind,
                send_at=at,
                status=NotificationStatus.SENT,
                attempts=1,
                sent_at=at,
                created_at=appt.created_at,
            )
        )

    sent(NotificationChannel.EMAIL, NotificationKind.CONFIRMATION, appt.created_at)
    if appt.status == S.CANCELLED:
        sent(NotificationChannel.EMAIL, NotificationKind.CANCELLATION, appt.history[-1].changed_at)
        return
    sent(NotificationChannel.EMAIL, NotificationKind.REMINDER, appt.starts_at - timedelta(hours=24))
    sent(NotificationChannel.SMS, NotificationKind.REMINDER, appt.starts_at - timedelta(hours=2))


def _create_appointments(
    doctors: list[tuple[Doctor, dict]],
    patients: list[Patient],
    demo: Patient,
    rnd: random.Random,
    now: datetime,
    today: date,
) -> list[Appointment]:
    registered = [to_local(p.created_at).date() for p in patients]
    busy: set[tuple[int, date]] = set()
    appointments = []
    for doctor, schedule in doctors:
        popularity = rnd.uniform(0.35, 0.65)
        days_off = {d.day for d in doctor.days_off}
        step = timedelta(minutes=doctor.slot_minutes)
        for offset in range(-HISTORY_DAYS, FUTURE_DAYS + 1):
            day = today + timedelta(days=offset)
            if day.weekday() not in schedule or day in days_off:
                continue
            pool = patients[: bisect.bisect_right(registered, day)]
            for start in slot_starts(schedule[day.weekday()], day, doctor.slot_minutes):
                future = start >= now
                chance = popularity * max(0.15, 1 - offset / FUTURE_DAYS) if future else popularity
                if rnd.random() > chance:
                    continue
                patient = demo if rnd.random() < (0.01 if future else 0.001) else rnd.choice(pool)
                if (id(patient), day) in busy or patient.created_at > start:
                    continue
                busy.add((id(patient), day))
                if start + step <= now:
                    status = rnd.choices([S.COMPLETED, S.CANCELLED, S.NO_SHOW], [85, 10, 5])[0]
                else:
                    status = rnd.choices([S.SCHEDULED, S.CONFIRMED, S.CANCELLED], [62, 30, 8])[0]
                booked = start - timedelta(days=rnd.randint(1, 14), hours=rnd.randint(0, 23))
                appt = Appointment(
                    patient=patient,
                    doctor=doctor,
                    starts_at=start,
                    ends_at=start + step,
                    status=status,
                    reason=rnd.choice(REASONS) if rnd.random() < 0.7 else None,
                    doctor_notes=rnd.choice(NOTES) if status == S.COMPLETED else None,
                    created_at=min(max(booked, patient.created_at), now),
                )
                _history(appt, patient, doctor, rnd)
                if patient is demo and not future:
                    _demo_notifications(appt)
                appointments.append(appt)
    return appointments


def seed(session: Session, force: bool = False) -> bool:
    if session.scalar(select(func.count()).select_from(User)):
        if not force:
            return False
        _wipe(session)

    rnd = random.Random(42)
    fake = Faker("uk_UA")
    fake.seed_instance(42)
    now, today = utc_now(), local_today()

    session.add(ClinicSettings(id=1))
    session.add(_user("admin@medbook.example", DEMO_PASSWORDS["admin"], Role.ADMIN, now))
    doctors = _create_doctors(session, fake, rnd, now)
    _add_days_off(doctors, rnd, today)

    patients = _create_patients(fake, rnd, now)
    demo = Patient(
        user=_user(
            "patient@medbook.example",
            DEMO_PASSWORDS["patient"],
            Role.PATIENT,
            patients[5].created_at,
        ),
        last_name="Мельник",
        first_name="Ірина",
        middle_name="Петрівна",
        phone="+380671112233",
        birth_date=date(1994, 3, 12),
        created_at=patients[5].created_at,
    )
    session.add_all([*patients, demo])
    session.add_all(_create_appointments(doctors, patients, demo, rnd, now, today))
    session.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill the database with demo data")
    parser.add_argument("--force", action="store_true", help="wipe existing data first")
    args = parser.parse_args()
    with SessionLocal() as session:
        if not seed(session, force=args.force):
            print("Database already has data – skipping seed (use --force to recreate).")
            return
        counts = {
            m.__tablename__: session.scalar(select(func.count()).select_from(m))
            for m in (User, Doctor, Patient, Appointment, Notification)
        }
        print("Seeded:", ", ".join(f"{k}={v}" for k, v in counts.items()))
        print(
            "Demo logins:",
            ", ".join(f"{r}@medbook.example / {p}" for r, p in DEMO_PASSWORDS.items()),
        )


if __name__ == "__main__":
    main()
