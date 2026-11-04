from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import DayOff, Doctor, Specialization
from app.repositories.base import Repository


class SpecializationRepository(Repository[Specialization]):
    model = Specialization

    def all(self) -> list[Specialization]:
        return list(self.session.scalars(select(Specialization).order_by(Specialization.name)))

    def by_name(self, name: str) -> Specialization | None:
        return self.session.scalar(select(Specialization).where(Specialization.name == name))


class DoctorRepository(Repository[Doctor]):
    model = Doctor

    def find(self, specialization_id: int | None = None, active_only: bool = True) -> list[Doctor]:
        query = select(Doctor).options(
            selectinload(Doctor.specialization), selectinload(Doctor.working_hours)
        )
        if specialization_id is not None:
            query = query.where(Doctor.specialization_id == specialization_id)
        if active_only:
            query = query.where(Doctor.is_active.is_(True))
        return list(self.session.scalars(query.order_by(Doctor.last_name, Doctor.first_name)))

    def by_user(self, user_id: int) -> Doctor | None:
        return self.session.scalar(select(Doctor).where(Doctor.user_id == user_id))


class DayOffRepository(Repository[DayOff]):
    model = DayOff
