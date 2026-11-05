from fastapi import APIRouter, HTTPException, status

from app.api.deps import Booking, SessionDep
from app.repositories.doctors import DoctorRepository, SpecializationRepository
from app.schemas.appointments import NextSlotOut
from app.schemas.doctors import DoctorOut, SpecializationOut

# Public read side: anyone can browse specializations and doctors before signing in
router = APIRouter(tags=["catalog"])


@router.get("/specializations", response_model=list[SpecializationOut])
def specializations(session: SessionDep):
    return SpecializationRepository(session).all()


@router.get("/doctors", response_model=list[DoctorOut])
def doctors(session: SessionDep, specialization_id: int | None = None):
    return DoctorRepository(session).find(specialization_id=specialization_id)


# Must stay above /doctors/{doctor_id}, otherwise "next-free" is parsed as an id
@router.get("/doctors/next-free", response_model=list[NextSlotOut])
def next_free(booking: Booking, specialization_id: int | None = None):
    return [
        NextSlotOut(doctor_id=d.id, starts_at=s)
        for d, s in booking.next_free_slots(specialization_id)
    ]


@router.get("/doctors/{doctor_id}", response_model=DoctorOut)
def doctor(doctor_id: int, session: SessionDep):
    found = DoctorRepository(session).get(doctor_id)
    if found is None or not found.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Лікаря не знайдено")
    return found
