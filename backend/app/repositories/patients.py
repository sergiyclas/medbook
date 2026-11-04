from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from app.models import Patient, User
from app.repositories.base import Repository


class PatientRepository(Repository[Patient]):
    model = Patient

    def by_user(self, user_id: int) -> Patient | None:
        return self.session.scalar(select(Patient).where(Patient.user_id == user_id))

    def search(self, text: str | None, limit: int, offset: int) -> list[Patient]:
        query = select(Patient).join(Patient.user).options(joinedload(Patient.user))
        if text:
            like = f"%{text.strip()}%"
            query = query.where(
                or_(
                    Patient.last_name.ilike(like),
                    Patient.first_name.ilike(like),
                    Patient.phone.ilike(like),
                    User.email.ilike(like),
                )
            )
        query = query.order_by(Patient.last_name, Patient.first_name).limit(limit).offset(offset)
        return list(self.session.scalars(query))
