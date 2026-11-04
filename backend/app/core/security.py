from datetime import timedelta

import bcrypt
import jwt

from app.core.clock import utc_now
from app.core.config import get_settings
from app.domain.enums import Role


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: int, role: Role) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": utc_now() + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# Returns the user id or None when the token is invalid or expired
def decode_access_token(token: str) -> int | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    return int(payload["sub"])
