from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AdminUser, Booking, SessionDep, require_role
from app.domain.enums import AppointmentStatus, Role
from app.repositories.appointments import AppointmentRepository
from app.repositories.doctors import DoctorRepository
from app.repositories.patients import PatientRepository
from app.repositories.settings import ClinicSettingsRepository
from app.schemas.appointments import AppointmentOut
from app.schemas.doctors import (
    DayOffCreated,
    DayOffIn,
    DayOffOut,
    DoctorAdminOut,
    DoctorCreate,
    DoctorUpdate,
    SpecializationIn,
    SpecializationOut,
    WeeklySchedule,
)
from app.schemas.patients import PatientOut, PatientRegister, PatientUpdate
from app.schemas.settings import ClinicSettingsOut, ClinicSettingsUpdate
from app.services.accounts import AccountService
from app.services.admin_service import AdminService
from app.services.availability import AvailabilityCalendar

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(Role.ADMIN))]
)


# ---------- specializations ----------
@router.post("/specializations", response_model=SpecializationOut, status_code=201)
def create_specialization(data: SpecializationIn, session: SessionDep):
    return AdminService(session).create_specialization(data)


@router.put("/specializations/{spec_id}", response_model=SpecializationOut)
def update_specialization(spec_id: int, data: SpecializationIn, session: SessionDep):
    return AdminService(session).update_specialization(spec_id, data)


@router.delete("/specializations/{spec_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_specialization(spec_id: int, session: SessionDep) -> None:
    AdminService(session).delete_specialization(spec_id)


# ---------- doctors ----------
@router.get("/doctors", response_model=list[DoctorAdminOut])
def list_doctors(session: SessionDep, specialization_id: int | None = None):
    return DoctorRepository(session).find(specialization_id, active_only=False)


@router.post("/doctors", response_model=DoctorAdminOut, status_code=201)
def create_doctor(data: DoctorCreate, session: SessionDep):
    return AdminService(session).create_doctor(data)


@router.get("/doctors/{doctor_id}", response_model=DoctorAdminOut)
def get_doctor(doctor_id: int, session: SessionDep):
    return AdminService(session).doctor(doctor_id)


@router.patch("/doctors/{doctor_id}", response_model=DoctorAdminOut)
def update_doctor(doctor_id: int, data: DoctorUpdate, session: SessionDep):
    return AdminService(session).update_doctor(doctor_id, data)


@router.put("/doctors/{doctor_id}/working-hours", response_model=DoctorAdminOut)
def set_working_hours(doctor_id: int, schedule: WeeklySchedule, session: SessionDep):
    return AdminService(session).set_working_hours(doctor_id, schedule)


@router.get("/doctors/{doctor_id}/days-off", response_model=list[DayOffOut])
def list_days_off(doctor_id: int, session: SessionDep):
    return AdminService(session).doctor(doctor_id).days_off


@router.post("/doctors/{doctor_id}/days-off", response_model=DayOffCreated, status_code=201)
def add_day_off(
    doctor_id: int, data: DayOffIn, admin: AdminUser, session: SessionDep, booking: Booking
):
    day_off, cancelled = AdminService(session).add_day_off(admin, doctor_id, data, booking)
    return DayOffCreated(
        **DayOffOut.model_validate(day_off).model_dump(), cancelled_appointments=len(cancelled)
    )


@router.delete("/days-off/{day_off_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_day_off(day_off_id: int, session: SessionDep) -> None:
    AdminService(session).remove_day_off(day_off_id)


# ---------- appointments ----------
@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(
    session: SessionDep,
    doctor_id: int | None = None,
    patient_id: int | None = None,
    status_filter: Annotated[AppointmentStatus | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    start = AvailabilityCalendar.day_bounds(date_from)[0] if date_from else None
    end = AvailabilityCalendar.day_bounds(date_to)[1] if date_to else None
    return AppointmentRepository(session).search(
        doctor_id, patient_id, status_filter, start, end, limit=limit, offset=offset
    )


# ---------- patients ----------
@router.get("/patients", response_model=list[PatientOut])
def list_patients(
    session: SessionDep,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return PatientRepository(session).search(search, limit, offset)


@router.post("/patients", response_model=PatientOut, status_code=201)
def create_patient(data: PatientRegister, session: SessionDep):
    return AccountService(session).register_patient(data)


@router.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, session: SessionDep):
    return AdminService(session).patient(patient_id)


@router.patch("/patients/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, data: PatientUpdate, session: SessionDep):
    return AdminService(session).update_patient(patient_id, data)


# ---------- clinic settings ----------
@router.get("/settings", response_model=ClinicSettingsOut)
def get_settings(session: SessionDep):
    return ClinicSettingsRepository(session).current()


@router.patch("/settings", response_model=ClinicSettingsOut)
def update_settings(data: ClinicSettingsUpdate, session: SessionDep):
    return AdminService(session).update_settings(data)
