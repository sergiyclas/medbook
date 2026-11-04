from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.core.clock import to_local
from app.domain.errors import Conflict, InvalidData
from app.models import ClinicSettings, Doctor, Patient
from app.repositories.appointments import AppointmentRepository
from app.services.availability import AvailabilityCalendar


class BookingRejected(InvalidData):
    code = "booking_rejected"


class SlotTaken(Conflict):
    code = "slot_taken"


@dataclass(frozen=True)
class BookingRequest:
    doctor: Doctor
    patient: Patient
    starts_at: datetime
    now: datetime
    settings: ClinicSettings
    # Set when an existing appointment is being moved: it must not clash with itself
    exclude_id: int | None = None

    @property
    def ends_at(self) -> datetime:
        return self.starts_at + timedelta(minutes=self.doctor.slot_minutes)

    @property
    def local_day(self) -> date:
        return to_local(self.starts_at).date()


# GoF Chain of Responsibility. Each handler checks one rule and either rejects
# the request or passes it on. Different use cases assemble different chains
# from the same handlers (see the build_* functions at the bottom).
class BookingRule(ABC):
    def __init__(self) -> None:
        self._next: BookingRule | None = None

    def then(self, nxt: BookingRule) -> BookingRule:
        self._next = nxt
        return nxt

    def check(self, request: BookingRequest) -> None:
        self.validate(request)
        if self._next is not None:
            self._next.check(request)

    @abstractmethod
    def validate(self, request: BookingRequest) -> None: ...


class DoctorIsActive(BookingRule):
    def validate(self, request: BookingRequest) -> None:
        if not request.doctor.is_active:
            raise BookingRejected("Лікар зараз не приймає пацієнтів", "doctor_inactive")


class NotInPast(BookingRule):
    def validate(self, request: BookingRequest) -> None:
        if request.starts_at <= request.now:
            raise BookingRejected("Не можна записатися на час, що вже минув", "in_past")


class WithinHorizon(BookingRule):
    def validate(self, request: BookingRequest) -> None:
        days = request.settings.booking_horizon_days
        if request.starts_at > request.now + timedelta(days=days):
            raise BookingRejected(
                f"Записатися можна не більше ніж на {days} днів наперед", "beyond_horizon"
            )


class NotOnDayOff(BookingRule):
    def __init__(self, calendar: AvailabilityCalendar) -> None:
        super().__init__()
        self.calendar = calendar

    def validate(self, request: BookingRequest) -> None:
        if self.calendar.is_day_off(request.doctor, request.local_day):
            raise BookingRejected("У цей день лікар не працює", "day_off")


class WithinWorkingHours(BookingRule):
    def __init__(self, calendar: AvailabilityCalendar) -> None:
        super().__init__()
        self.calendar = calendar

    def validate(self, request: BookingRequest) -> None:
        start = to_local(request.starts_at).time()
        end = to_local(request.ends_at).time()
        intervals = self.calendar.intervals(request.doctor, request.local_day)
        if not any(a <= start and end <= b for a, b in intervals):
            raise BookingRejected("Цей час поза графіком роботи лікаря", "outside_hours")


class SlotAligned(BookingRule):
    def __init__(self, calendar: AvailabilityCalendar) -> None:
        super().__init__()
        self.calendar = calendar

    # Starts must sit on the doctor's slot grid – this is what makes the
    # (doctor, starts_at) unique index a complete guard against overlaps.
    def validate(self, request: BookingRequest) -> None:
        if request.starts_at not in self.calendar.grid(request.doctor, request.local_day):
            raise BookingRejected("Оберіть один із запропонованих слотів", "not_on_grid")


class SlotFree(BookingRule):
    def __init__(self, calendar: AvailabilityCalendar, appointments: AppointmentRepository) -> None:
        super().__init__()
        self.calendar = calendar
        self.appointments = appointments

    def validate(self, request: BookingRequest) -> None:
        start, end = self.calendar.day_bounds(request.local_day)
        busy = self.appointments.doctor_busy_starts(
            request.doctor.id, start, end, request.exclude_id
        )
        if request.starts_at in busy:
            raise SlotTaken("Цей час уже зайнятий – оберіть інший слот")


class PatientNoOverlap(BookingRule):
    def __init__(self, appointments: AppointmentRepository) -> None:
        super().__init__()
        self.appointments = appointments

    def validate(self, request: BookingRequest) -> None:
        if self.appointments.patient_overlapping(
            request.patient.id, request.starts_at, request.ends_at, request.exclude_id
        ):
            raise BookingRejected("На цей час у пацієнта вже є інший прийом", "patient_overlap")


class PatientDailyLimit(BookingRule):
    def __init__(self, calendar: AvailabilityCalendar, appointments: AppointmentRepository) -> None:
        super().__init__()
        self.calendar = calendar
        self.appointments = appointments

    def validate(self, request: BookingRequest) -> None:
        limit = request.settings.max_daily_bookings_per_patient
        start, end = self.calendar.day_bounds(request.local_day)
        count = self.appointments.patient_active_count(
            request.patient.id, start, end, request.exclude_id
        )
        if count >= limit:
            raise BookingRejected(f"Не більше {limit} записів на один день", "daily_limit")


def _link(*rules: BookingRule) -> BookingRule:
    for current, nxt in zip(rules, rules[1:], strict=False):
        current.then(nxt)
    return rules[0]


# Patients self-booking online: every rule applies
def build_patient_chain(
    calendar: AvailabilityCalendar, appointments: AppointmentRepository
) -> BookingRule:
    return _link(
        DoctorIsActive(),
        NotInPast(),
        WithinHorizon(),
        NotOnDayOff(calendar),
        WithinWorkingHours(calendar),
        SlotAligned(calendar),
        SlotFree(calendar, appointments),
        PatientNoOverlap(appointments),
        PatientDailyLimit(calendar, appointments),
    )


# Reception staff booking on a patient's behalf: may book beyond the online
# horizon and ignore the per-day limit (e.g. a referral to two specialists)
def build_admin_chain(
    calendar: AvailabilityCalendar, appointments: AppointmentRepository
) -> BookingRule:
    return _link(
        DoctorIsActive(),
        NotInPast(),
        NotOnDayOff(calendar),
        WithinWorkingHours(calendar),
        SlotAligned(calendar),
        SlotFree(calendar, appointments),
        PatientNoOverlap(appointments),
    )
