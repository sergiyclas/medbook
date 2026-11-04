from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.enums import AppointmentStatus
from app.schemas.doctors import SpecializationOut


class SlotOut(BaseModel):
    starts_at: datetime
    ends_at: datetime


class AppointmentCreate(BaseModel):
    doctor_id: int
    starts_at: AwareDatetime
    reason: str | None = Field(default=None, max_length=500)
    # Required when an administrator books for a patient, ignored for patients
    patient_id: int | None = None


class RescheduleIn(BaseModel):
    starts_at: AwareDatetime


class CancelIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class CompleteIn(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class DoctorBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    specialization: SpecializationOut
    room: str | None


class PatientBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str
    email: str
    birth_date: date


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    reason: str | None
    doctor_notes: str | None
    created_at: datetime
    doctor: DoctorBrief
    patient: PatientBrief


class StatusChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: AppointmentStatus | None
    to_status: AppointmentStatus
    reason: str | None
    changed_at: datetime
    changed_by_email: str | None
