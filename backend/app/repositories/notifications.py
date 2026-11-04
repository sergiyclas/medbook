from collections.abc import Iterable

from sqlalchemy import select

from app.domain.enums import NotificationKind, NotificationStatus
from app.models import Notification
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
