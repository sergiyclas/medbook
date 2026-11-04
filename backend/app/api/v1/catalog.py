from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.repositories.doctors import DoctorRepository, SpecializationRepository
from app.schemas.doctors import DoctorOut, SpecializationOut

# Public read side: anyone can browse specializations and doctors before signing in
router = APIRouter(tags=["catalog"])


@router.get("/specializations", response_model=list[SpecializationOut])
def specializations(session: SessionDep):
    return SpecializationRepository(session).all()


@router.get("/doctors", response_model=list[DoctorOut])
def doctors(session: SessionDep, specialization_id: int | None = None):
    return DoctorRepository(session).find(specialization_id=specialization_id)


@router.get("/doctors/{doctor_id}", response_model=DoctorOut)
def doctor(doctor_id: int, session: SessionDep):
    found = DoctorRepository(session).get(doctor_id)
    if found is None or not found.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Лікаря не знайдено")
    return found
