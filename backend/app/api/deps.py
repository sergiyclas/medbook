from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.bootstrap import build_bus
from app.core.security import decode_access_token
from app.db.session import get_session
from app.domain.enums import Role
from app.models import Doctor, Patient, User
from app.services.booking_facade import BookingFacade

SessionDep = Annotated[Session, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    session: SessionDep, token: Annotated[str | None, Depends(oauth2_scheme)]
) -> User:
    user_id = decode_access_token(token) if token else None
    user = session.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Потрібна авторизація",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role) -> Callable[[User], User]:
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостатньо прав")
        return user

    return checker


def current_patient(user: Annotated[User, Depends(require_role(Role.PATIENT))]) -> Patient:
    assert user.patient is not None
    return user.patient


def current_doctor(user: Annotated[User, Depends(require_role(Role.DOCTOR))]) -> Doctor:
    assert user.doctor is not None
    return user.doctor


CurrentPatient = Annotated[Patient, Depends(current_patient)]
CurrentDoctor = Annotated[Doctor, Depends(current_doctor)]
AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]


def get_booking(session: SessionDep) -> BookingFacade:
    return BookingFacade(session, build_bus(session))


Booking = Annotated[BookingFacade, Depends(get_booking)]
