import logging
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import utc_now
from app.domain.enums import (
    NotificationChannel,
    NotificationKind,
    NotificationStatus,
)
from app.models import Notification
from app.notifications.factory import TransportFactory
from app.notifications.messages import (
    EmailMessageBuilder,
    MessageBuilder,
    MessageComposer,
    SmsMessageBuilder,
)
from app.notifications.ports import DeliveryError

log = logging.getLogger("medbook.worker")

STALE_AFTER = timedelta(minutes=10)
# Delay before the next try after a temporary failure: 1, 5, 15, 60 minutes
BACKOFF = [timedelta(minutes=m) for m in (1, 5, 15, 60)]


# The relay half of the transactional outbox. Runs in the worker process:
# claims due rows in a short transaction of its own, then delivers each one in
# a separate transaction, so a slow SMTP server never holds database locks.
class NotificationDispatcher:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        transports: TransportFactory,
        composer: MessageComposer,
        sender_name: str,
        max_attempts: int = 5,
        batch_size: int = 50,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.session_factory = session_factory
        self.composer = composer
        self.sender_name = sender_name
        self.max_attempts = max_attempts
        self.batch_size = batch_size
        self.clock = clock
        self.senders = {
            NotificationChannel.EMAIL: transports.create_email_sender(),
            NotificationChannel.SMS: transports.create_sms_sender(),
        }

    def process_due(self) -> Counter[NotificationStatus]:
        self._release_stale()
        results: Counter[NotificationStatus] = Counter()
        claimed_at, ids = self._claim()
        for notification_id in ids:
            status = self._deliver(notification_id, claimed_at)
            if status is not None:
                results[status] += 1
        return results

    # Stuck rows go back to the queue; the patient may get a duplicate, never nothing
    def _release_stale(self) -> None:
        with self.session_factory() as session:
            session.execute(
                update(Notification)
                .where(
                    Notification.status == NotificationStatus.SENDING,
                    Notification.claimed_at < self.clock() - STALE_AFTER,
                )
                .values(status=NotificationStatus.PENDING)
            )
            session.commit()

    # SKIP LOCKED lets several workers run side by side without taking the
    # same rows (PostgreSQL; SQLite has no row locks and ignores the clause)
    def _claim(self) -> tuple[datetime, list[int]]:
        now = self.clock()
        with self.session_factory() as session:
            due = session.scalars(
                select(Notification)
                .where(
                    Notification.status == NotificationStatus.PENDING,
                    Notification.send_at <= now,
                )
                .order_by(Notification.send_at)
                .limit(self.batch_size)
                .with_for_update(skip_locked=True)
            ).all()
            for notification in due:
                notification.status = NotificationStatus.SENDING
                notification.claimed_at = now
                notification.attempts += 1
            session.commit()
            return now, [n.id for n in due]

    # claimed_at works as an ownership token: if a slow batch outlived STALE_AFTER
    # and another worker re-claimed the row, this worker must not send it as well
    def _deliver(self, notification_id: int, claimed_at: datetime) -> NotificationStatus | None:
        with self.session_factory() as session:
            notification = session.get(Notification, notification_id)
            assert notification is not None
            if (
                notification.status != NotificationStatus.SENDING
                or notification.claimed_at != claimed_at
            ):
                return None
            now = self.clock()
            reason = self._skip_reason(notification, now)
            if reason:
                notification.status = NotificationStatus.SKIPPED
                notification.last_error = reason
            else:
                try:
                    self._send(notification, now)
                except Exception as exc:
                    # System boundary: a broken template or a library bug fails this
                    # one message instead of stalling the rest of the outbox
                    log.exception("notification %s failed", notification_id)
                    notification.status = NotificationStatus.FAILED
                    notification.last_error = f"{type(exc).__name__}: {exc}"[:500]
            session.commit()
            return notification.status

    def _send(self, notification: Notification, now: datetime) -> None:
        builder = self._builder_for(notification.channel)
        self.composer.compose(notification.kind, notification.appointment, builder)
        try:
            self.senders[notification.channel].send(builder.get_result())
        except DeliveryError as exc:
            notification.last_error = str(exc)[:500]
            if exc.transient and notification.attempts < self.max_attempts:
                delay = BACKOFF[min(notification.attempts, len(BACKOFF)) - 1]
                notification.status = NotificationStatus.PENDING
                notification.send_at = now + delay
            else:
                notification.status = NotificationStatus.FAILED
            return
        notification.status = NotificationStatus.SENT
        notification.sent_at = now
        notification.last_error = None

    def _builder_for(self, channel: NotificationChannel) -> MessageBuilder:
        if channel == NotificationChannel.EMAIL:
            return EmailMessageBuilder()
        return SmsMessageBuilder(self.sender_name)

    # Things may have changed between scheduling and sending
    @staticmethod
    def _skip_reason(notification: Notification, now: datetime) -> str | None:
        appt, patient = notification.appointment, notification.appointment.patient
        enabled = {
            NotificationChannel.EMAIL: patient.notify_email,
            NotificationChannel.SMS: patient.notify_sms,
        }
        if not enabled[notification.channel]:
            return "Пацієнт вимкнув цей канал"
        if notification.kind != NotificationKind.CANCELLATION and not appt.state.is_active:
            return "Прийом уже не активний"
        if notification.kind == NotificationKind.REMINDER and appt.starts_at <= now:
            return "Прийом уже почався"
        return None
