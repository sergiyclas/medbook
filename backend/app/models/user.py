from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime, str_enum
from app.domain.enums import Role

if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.patient import Patient


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(str_enum(Role))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    patient: Mapped[Patient | None] = relationship(back_populates="user")
    doctor: Mapped[Doctor | None] = relationship(back_populates="user")
