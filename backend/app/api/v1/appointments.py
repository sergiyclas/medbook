from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, status

from app.api.deps import Booking, CurrentPatient, CurrentUser, SessionDep, require_role
from app.core.clock import utc_now
from app.domain.enums import Role
from app.repositories.appointments import AppointmentRepository
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentOut,
    CancelIn,
    CompleteIn,
    RescheduleIn,
    SlotOut,
    StatusChangeOut,
)

router = APIRouter(tags=["appointments"])

staff_only = [Depends(require_role(Role.DOCTOR, Role.ADMIN))]


@router.get("/doctors/{doctor_id}/slots", response_model=list[SlotOut])
def free_slots(doctor_id: int, day: date, booking: Booking):
    return [SlotOut(starts_at=s, ends_at=e) for s, e in booking.available_slots(doctor_id, day)]


@router.post(
    "/appointments",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.PATIENT, Role.ADMIN))],
)
def book(data: AppointmentCreate, user: CurrentUser, booking: Booking):
    return booking.book(user, data.doctor_id, data.starts_at, data.reason, data.patient_id)


@router.get("/appointments/my", response_model=list[AppointmentOut])
def my_appointments(
    patient: CurrentPatient,
    session: SessionDep,
    scope: Literal["upcoming", "past"] = "upcoming",
):
    return AppointmentRepository(session).for_patient(patient.id, scope == "upcoming", utc_now())


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int, user: CurrentUser, booking: Booking):
    return booking.appointment_for(user, appointment_id)


@router.get("/appointments/{appointment_id}/history", response_model=list[StatusChangeOut])
def appointment_history(appointment_id: int, user: CurrentUser, booking: Booking):
    history = [
        StatusChangeOut.model_validate(change)
        for change in booking.appointment_for(user, appointment_id).history
    ]
    if user.role == Role.PATIENT:
        history = [change.model_copy(update={"changed_by_email": None}) for change in history]
    return history


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(appointment_id: int, data: CancelIn, user: CurrentUser, booking: Booking):
    return booking.cancel(user, appointment_id, data.reason)


@router.post("/appointments/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule(appointment_id: int, data: RescheduleIn, user: CurrentUser, booking: Booking):
    return booking.reschedule(user, appointment_id, data.starts_at)


@router.post(
    "/appointments/{appointment_id}/confirm",
    response_model=AppointmentOut,
    dependencies=staff_only,
)
def confirm(appointment_id: int, user: CurrentUser, booking: Booking):
    return booking.confirm(user, appointment_id)


@router.post(
    "/appointments/{appointment_id}/complete",
    response_model=AppointmentOut,
    dependencies=staff_only,
)
def complete(appointment_id: int, data: CompleteIn, user: CurrentUser, booking: Booking):
    return booking.complete(user, appointment_id, data.notes)


@router.post(
    "/appointments/{appointment_id}/no-show",
    response_model=AppointmentOut,
    dependencies=staff_only,
)
def mark_no_show(appointment_id: int, user: CurrentUser, booking: Booking):
    return booking.mark_no_show(user, appointment_id)
