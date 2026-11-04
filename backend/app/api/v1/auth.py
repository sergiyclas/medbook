from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep
from app.core.security import create_access_token
from app.schemas.auth import MeOut, TokenOut
from app.schemas.patients import PatientRegister
from app.services.accounts import AccountService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: PatientRegister, session: SessionDep) -> TokenOut:
    patient = AccountService(session).register_patient(data)
    return TokenOut(
        access_token=create_access_token(patient.user_id, patient.user.role), role=patient.user.role
    )


# OAuth2 password form (username = e-mail) – the same endpoint powers the
# "Authorize" button in Swagger UI and the SPA login screen.
@router.post("/login", response_model=TokenOut)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep) -> TokenOut:
    user = AccountService(session).authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невірний e-mail або пароль")
    return TokenOut(access_token=create_access_token(user.id, user.role), role=user.role)


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser) -> MeOut:
    return MeOut.model_validate(user, from_attributes=True)
