from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# One session per request acts as the Unit of Work: services flush as they go,
# the caller commits once at the end of the use case.
def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
