from datetime import date, datetime, time, timedelta

from app.core.clock import local_to_utc
from app.domain.availability import slot_starts
from app.models import Doctor
from app.repositories.appointments import AppointmentRepository


# GRASP Information Expert for "when can this doctor see a patient". Booking rules
# and the public slots endpoint ask the same object, so they can never disagree.
class AvailabilityCalendar:
    def __init__(self, appointments: AppointmentRepository) -> None:
        self.appointments = appointments

    @staticmethod
    def is_day_off(doctor: Doctor, day: date) -> bool:
        return any(d.day == day for d in doctor.days_off)

    @staticmethod
    def intervals(doctor: Doctor, day: date) -> list[tuple[time, time]]:
        return [
            (h.start_time, h.end_time) for h in doctor.working_hours if h.weekday == day.weekday()
        ]

    # Needs no stored appointments, so the doctor-load report uses it for capacity
    @classmethod
    def grid(cls, doctor: Doctor, day: date) -> list[datetime]:
        if cls.is_day_off(doctor, day):
            return []
        return slot_starts(cls.intervals(doctor, day), day, doctor.slot_minutes)

    @staticmethod
    def day_bounds(day: date) -> tuple[datetime, datetime]:
        return local_to_utc(day, time(0)), local_to_utc(day + timedelta(days=1), time(0))

    def free_slots(
        self, doctor: Doctor, day: date, now: datetime, exclude_id: int | None = None
    ) -> list[datetime]:
        start, end = self.day_bounds(day)
        busy = self.appointments.doctor_busy_starts(doctor.id, start, end, exclude_id)
        return [s for s in self.grid(doctor, day) if s > now and s not in busy]
