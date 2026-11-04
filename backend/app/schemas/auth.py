from pydantic import BaseModel

from app.domain.enums import Role
from app.schemas.doctors import DoctorOut
from app.schemas.patients import PatientOut


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class MeOut(BaseModel):
    id: int
    email: str
    role: Role
    patient: PatientOut | None = None
    doctor: DoctorOut | None = None
