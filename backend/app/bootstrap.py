from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domain.events import AppointmentBooked, AppointmentRescheduled, AppointmentStatusChanged
from app.notifications.dispatcher import NotificationDispatcher
from app.notifications.factory import get_transport_factory
from app.notifications.messages import MessageComposer
from app.repositories.notifications import NotificationRepository
from app.repositories.settings import ClinicSettingsRepository
from app.services.event_bus import EventBus
from app.services.event_handlers import (
    PendingNotificationCanceller,
    ReminderScheduler,
    StatusHistoryRecorder,
)

# Composition root: the only place that knows which concrete classes are wired
# together. The API (per request) and the worker (once) both build from here.


# A new bus per session/request: handlers capture that session, so a
# module-level bus would leak them across requests.
def build_bus(session: Session) -> EventBus:
    notifications = NotificationRepository(session)
    history = StatusHistoryRecorder()
    reminders = ReminderScheduler(notifications, ClinicSettingsRepository(session))
    canceller = PendingNotificationCanceller(notifications)

    bus = EventBus()
    for event_type in (AppointmentBooked, AppointmentStatusChanged, AppointmentRescheduled):
        bus.subscribe(event_type, history)
        bus.subscribe(event_type, reminders)
    bus.subscribe(AppointmentStatusChanged, canceller)
    return bus


def build_dispatcher() -> NotificationDispatcher:
    settings = get_settings()
    return NotificationDispatcher(
        SessionLocal,
        get_transport_factory(),
        MessageComposer(settings.clinic_name, settings.app_url),
        sender_name=settings.app_name,
        max_attempts=settings.notification_max_attempts,
    )
