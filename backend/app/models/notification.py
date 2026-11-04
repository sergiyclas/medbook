from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime, str_enum
from app.domain.enums import NotificationChannel, NotificationKind, NotificationStatus

if TYPE_CHECKING:
    from app.models.appointment import Appointment

_OPEN = text("status IN ('pending', 'sending')")


# Transactional outbox: rows are written in the same transaction as the booking
# and delivered later by the worker, so a failed SMTP call never rolls back a visit.
class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "uq_notifications_open_per_kind",
            "appointment_id",
            "kind",
            "channel",
            unique=True,
            postgresql_where=_OPEN,
            sqlite_where=_OPEN,
        ),
        Index("ix_notifications_due", "status", "send_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(str_enum(NotificationChannel))
    kind: Mapped[NotificationKind] = mapped_column(str_enum(NotificationKind))
    send_at: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[NotificationStatus] = mapped_column(
        str_enum(NotificationStatus), default=NotificationStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(String(500))
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    appointment: Mapped[Appointment] = relationship(back_populates="notifications")
