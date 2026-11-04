from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_session
from app.domain.enums import Role
from app.main import app as fastapi_app
from app.models import User


# Makes SQLite behave like PostgreSQL where the code relies on it: enforced
# foreign keys and Unicode-aware lower() (SQLite's own folds ASCII only,
# so case-insensitive search for Cyrillic names would silently fail).
def _configure_sqlite(conn, _record) -> None:
    conn.execute("PRAGMA foreign_keys=ON")
    conn.create_function("lower", 1, lambda s: s.lower() if s is not None else None)


@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    event.listen(eng, "connect", _configure_sqlite)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as s:
        yield s


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    fastapi_app.dependency_overrides[get_session] = lambda: session
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client: TestClient, session: Session) -> dict[str, str]:
    session.add(
        User(email="admin@clinic.example", password_hash=hash_password("admin123"), role=Role.ADMIN)
    )
    session.commit()
    return login(client, "admin@clinic.example", "admin123")
