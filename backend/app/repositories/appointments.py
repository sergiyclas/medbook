from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import joinedload

from app.domain.enums import ACTIVE_STATUSES, AppointmentStatus
from app.models import Appointment, Doctor, Patient
from app.repositories.base import Repository


def _with_people(query: Select) -> Select:
    return query.options(
        joinedload(Appointment.patient).joinedload(Patient.user),
        joinedload(Appointment.doctor).joinedload(Doctor.specialization),
    )


def _active() -> object:
    return Appointment.status.in_(ACTIVE_STATUSES)


class AppointmentRepository(Repository[Appointment]):
    model = Appointment

    # ---------- queries used by booking rules and the calendar ----------
    def doctor_busy_starts(
        self, doctor_id: int, start: datetime, end: datetime, exclude_id: int | None = None
    ) -> set[datetime]:
        query = select(Appointment.starts_at).where(
            Appointment.doctor_id == doctor_id,
            Appointment.starts_at >= start,
            Appointment.starts_at < end,
            _active(),
        )
        if exclude_id is not None:
            query = query.where(Appointment.id != exclude_id)
        return set(self.session.scalars(query))

    def patient_overlapping(
        self, patient_id: int, start: datetime, end: datetime, exclude_id: int | None = None
    ) -> list[Appointment]:
        query = select(Appointment).where(
            Appointment.patient_id == patient_id,
            Appointment.starts_at < end,
            Appointment.ends_at > start,
            _active(),
        )
        if exclude_id is not None:
            query = query.where(Appointment.id != exclude_id)
        return list(self.session.scalars(query))

    def patient_active_count(
        self, patient_id: int, start: datetime, end: datetime, exclude_id: int | None = None
    ) -> int:
        query = select(func.count()).where(
            Appointment.patient_id == patient_id,
            Appointment.starts_at >= start,
            Appointment.starts_at < end,
            _active(),
        )
        if exclude_id is not None:
            query = query.where(Appointment.id != exclude_id)
        return self.session.scalar(query) or 0

    def doctor_active_between(
        self, doctor_id: int, start: datetime, end: datetime
    ) -> list[Appointment]:
        query = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.starts_at >= start,
            Appointment.starts_at < end,
            _active(),
        )
        return list(self.session.scalars(_with_people(query)))

    # ---------- cabinet and admin lists ----------
    def for_patient(self, patient_id: int, upcoming: bool, now: datetime) -> list[Appointment]:
        query = select(Appointment).where(Appointment.patient_id == patient_id)
        if upcoming:
            query = query.where(Appointment.ends_at > now).order_by(Appointment.starts_at)
        else:
            query = query.where(Appointment.ends_at <= now).order_by(Appointment.starts_at.desc())
        return list(self.session.scalars(_with_people(query)))

    def search(
        self,
        doctor_id: int | None = None,
        patient_id: int | None = None,
        status: AppointmentStatus | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        newest_first: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Appointment]:
        query = select(Appointment)
        if doctor_id is not None:
            query = query.where(Appointment.doctor_id == doctor_id)
        if patient_id is not None:
            query = query.where(Appointment.patient_id == patient_id)
        if status is not None:
            query = query.where(Appointment.status == status)
        if start is not None:
            query = query.where(Appointment.starts_at >= start)
        if end is not None:
            query = query.where(Appointment.starts_at < end)
        order = Appointment.starts_at.desc() if newest_first else Appointment.starts_at
        query = query.order_by(order).limit(limit).offset(offset)
        return list(self.session.scalars(_with_people(query)))
