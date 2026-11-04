from fastapi import APIRouter

from app.api.deps import CurrentPatient, SessionDep
from app.schemas.patients import PatientOut, PatientSelfUpdate
from app.services.accounts import AccountService

router = APIRouter(prefix="/patients", tags=["patient"])


@router.get("/me", response_model=PatientOut)
def my_profile(patient: CurrentPatient):
    return patient


@router.patch("/me", response_model=PatientOut)
def update_my_profile(data: PatientSelfUpdate, patient: CurrentPatient, session: SessionDep):
    return AccountService(session).update_profile(patient, data)
