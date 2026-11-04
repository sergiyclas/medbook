from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.domain.enums import Role
from app.domain.errors import Conflict
from app.models import Patient, User
from app.repositories.patients import PatientRepository
from app.repositories.users import UserRepository
from app.schemas.patients import PatientRegister, PatientSelfUpdate


class AccountService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.patients = PatientRepository(session)

    # Used both for self-registration and by the administrator for walk-in patients
    def register_patient(self, data: PatientRegister) -> Patient:
        if self.users.by_email(data.email):
            raise Conflict("Користувач з таким e-mail уже зареєстрований", "email_taken")
        user = User(
            email=data.email.lower(), password_hash=hash_password(data.password), role=Role.PATIENT
        )
        patient = self.patients.add(
            Patient(user=user, **data.model_dump(exclude={"email", "password"}))
        )
        self.session.commit()
        return patient

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.users.by_email(email)
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            return None
        return user

    def update_profile(self, patient: Patient, data: PatientSelfUpdate) -> Patient:
        for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(patient, field, value)
        self.session.commit()
        return patient
