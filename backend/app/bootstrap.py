from sqlalchemy.orm import Session

from app.domain.events import AppointmentBooked, AppointmentRescheduled, AppointmentStatusChanged
from app.repositories.notifications import NotificationRepository
from app.repositories.settings import ClinicSettingsRepository
from app.services.event_bus import EventBus
from app.services.event_handlers import (
    PendingNotificationCanceller,
    ReminderScheduler,
    StatusHistoryRecorder,
)


# Composition root for the event bus. A new bus per session/request: handlers
# capture that session, so a module-level bus would leak them across requests.
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
