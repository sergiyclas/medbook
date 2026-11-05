from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.api.deps import CurrentDoctor, SessionDep
from app.core.clock import local_today, utc_now
from app.repositories.appointments import AppointmentRepository
from app.schemas.appointments import AppointmentOut
from app.services.availability import AvailabilityCalendar

# A doctor only ever sees their own appointments: the doctor id comes from the
# token, never from the request.
router = APIRouter(prefix="/doctor", tags=["doctor cabinet"])


@router.get("/schedule", response_model=list[AppointmentOut])
def schedule(
    doctor: CurrentDoctor,
    session: SessionDep,
    date_from: date | None = None,
    date_to: date | None = None,
):
    first = date_from or local_today()
    last = date_to or first + timedelta(days=6)
    start, _ = AvailabilityCalendar.day_bounds(first)
    _, end = AvailabilityCalendar.day_bounds(last)
    # Bounded by the dates; a busy week is well over the default page of 100
    return AppointmentRepository(session).search(
        doctor_id=doctor.id, start=start, end=end, limit=1000
    )


@router.get("/history", response_model=list[AppointmentOut])
def history(
    doctor: CurrentDoctor,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return AppointmentRepository(session).search(
        doctor_id=doctor.id, end=utc_now(), newest_first=True, limit=limit, offset=offset
    )
