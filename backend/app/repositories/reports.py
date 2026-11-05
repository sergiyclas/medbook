from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import AppointmentStatus
from app.models import Appointment, Doctor, Patient

# Read side for reports: plain column tuples instead of full entities – a year
# of visits is tens of thousands of rows and needs no relationships.


class ReportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def appointments(
        self, start: datetime, end: datetime, doctor_id: int | None
    ) -> list[tuple[datetime, datetime, int, AppointmentStatus]]:
        query = select(
            Appointment.starts_at, Appointment.ends_at, Appointment.doctor_id, Appointment.status
        ).where(Appointment.starts_at >= start, Appointment.starts_at < end)
        if doctor_id is not None:
            query = query.where(Appointment.doctor_id == doctor_id)
        return [tuple(row) for row in self.session.execute(query)]

    def patient_registrations(self, start: datetime, end: datetime) -> list[datetime]:
        query = select(Patient.created_at).where(
            Patient.created_at >= start, Patient.created_at < end
        )
        return list(self.session.scalars(query))

    def patients_registered_before(self, moment: datetime) -> int:
        query = select(func.count()).select_from(Patient).where(Patient.created_at < moment)
        return self.session.scalar(query) or 0

    def doctors(self, doctor_id: int | None = None) -> list[Doctor]:
        query = select(Doctor).options(
            selectinload(Doctor.specialization),
            selectinload(Doctor.working_hours),
            selectinload(Doctor.days_off),
        )
        if doctor_id is not None:
            query = query.where(Doctor.id == doctor_id)
        return list(self.session.scalars(query.order_by(Doctor.last_name, Doctor.first_name)))
