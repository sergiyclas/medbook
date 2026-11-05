from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.domain.enums import NotificationChannel, NotificationKind, NotificationStatus
from app.models import Appointment, Notification
from app.repositories.base import Repository


class NotificationRepository(Repository[Notification]):
    model = Notification

    # Pending rows only: a row already claimed by the worker ("sending") is in flight
    def pending_for(
        self, appointment_id: int, kinds: Iterable[NotificationKind]
    ) -> list[Notification]:
        query = select(Notification).where(
            Notification.appointment_id == appointment_id,
            Notification.status == NotificationStatus.PENDING,
            Notification.kind.in_(list(kinds)),
        )
        return list(self.session.scalars(query))

    def search(
        self,
        status: NotificationStatus | None,
        channel: NotificationChannel | None,
        limit: int,
        offset: int,
    ) -> list[Notification]:
        query = select(Notification).options(
            joinedload(Notification.appointment).joinedload(Appointment.patient),
            joinedload(Notification.appointment).joinedload(Appointment.doctor),
        )
        if status is not None:
            query = query.where(Notification.status == status)
        if channel is not None:
            query = query.where(Notification.channel == channel)
        query = query.order_by(Notification.send_at.desc(), Notification.id.desc())
        return list(self.session.scalars(query.limit(limit).offset(offset)))
