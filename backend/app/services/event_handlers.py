from datetime import datetime, timedelta

from app.core.clock import to_local
from app.domain.enums import (
    AppointmentStatus,
    NotificationChannel,
    NotificationKind,
    NotificationStatus,
)
from app.domain.events import (
    AppointmentBooked,
    AppointmentRescheduled,
    AppointmentStatusChanged,
    DomainEvent,
)
from app.models import Appointment, AppointmentStatusChange, Notification
from app.repositories.notifications import NotificationRepository
from app.repositories.settings import ClinicSettingsRepository

# Observers subscribed to appointment events in app/bootstrap.py. Each one has a
# single concern; none of them depends on another, so their order does not matter.

_UPCOMING_KINDS = (NotificationKind.CONFIRMATION, NotificationKind.REMINDER)
_FINAL_STATUSES = (
    AppointmentStatus.CANCELLED,
    AppointmentStatus.COMPLETED,
    AppointmentStatus.NO_SHOW,
)


# Keeps the audit trail shown in the appointment history
class StatusHistoryRecorder:
    def handle(self, event: DomainEvent) -> None:
        appt = event.appointment
        match event:
            case AppointmentBooked():
                change = AppointmentStatusChange(to_status=AppointmentStatus.SCHEDULED)
            case AppointmentStatusChanged():
                change = AppointmentStatusChange(
                    from_status=event.old, to_status=event.new, reason=event.reason
                )
            case AppointmentRescheduled():
                moved_from = to_local(event.old_starts_at).strftime("%d.%m.%Y %H:%M")
                change = AppointmentStatusChange(
                    from_status=event.old_status,
                    to_status=AppointmentStatus.SCHEDULED,
                    reason=f"Перенесено з {moved_from}",
                )
        change.changed_by_id = event.actor_id
        change.changed_at = event.at
        appt.history.append(change)


# GRASP Creator for Notification: decides which messages a patient will get and
# when, from the clinic settings and the patient's channel preferences.
class ReminderScheduler:
    def __init__(
        self, notifications: NotificationRepository, settings: ClinicSettingsRepository
    ) -> None:
        self.notifications = notifications
        self.settings = settings

    def handle(self, event: DomainEvent) -> None:
        appt = event.appointment
        match event:
            case AppointmentBooked():
                self._schedule(appt, event.at)
            case AppointmentRescheduled():
                for old in self.notifications.pending_for(appt.id, _UPCOMING_KINDS):
                    old.status = NotificationStatus.CANCELLED
                self.notifications.session.flush()
                self._schedule(appt, event.at)
            case AppointmentStatusChanged(new=AppointmentStatus.CANCELLED):
                self._one_off(appt, NotificationKind.CANCELLATION, event.at)

    def _schedule(self, appt: Appointment, now: datetime) -> None:
        self._one_off(appt, NotificationKind.CONFIRMATION, now)
        settings = self.settings.current()
        lead_hours = {
            NotificationChannel.EMAIL: settings.reminder_email_hours_before,
            NotificationChannel.SMS: settings.reminder_sms_hours_before,
        }
        for channel in self._channels(appt):
            send_at = appt.starts_at - timedelta(hours=lead_hours[channel])
            if send_at > now:  # booked too late for this reminder – skip it
                self._add(appt, channel, NotificationKind.REMINDER, send_at)

    # Confirmations and cancellations go out once: by e-mail when the patient
    # accepts e-mail, otherwise by SMS
    def _one_off(self, appt: Appointment, kind: NotificationKind, now: datetime) -> None:
        channels = self._channels(appt)
        if channels:
            self._add(appt, channels[0], kind, now)

    @staticmethod
    def _channels(appt: Appointment) -> list[NotificationChannel]:
        patient = appt.patient
        return [
            channel
            for channel, enabled in (
                (NotificationChannel.EMAIL, patient.notify_email),
                (NotificationChannel.SMS, patient.notify_sms),
            )
            if enabled
        ]

    def _add(
        self,
        appt: Appointment,
        channel: NotificationChannel,
        kind: NotificationKind,
        send_at: datetime,
    ) -> None:
        appt.notifications.append(Notification(channel=channel, kind=kind, send_at=send_at))


# A visit that is over or called off must not trigger reminders any more
class PendingNotificationCanceller:
    def __init__(self, notifications: NotificationRepository) -> None:
        self.notifications = notifications

    def handle(self, event: DomainEvent) -> None:
        if isinstance(event, AppointmentStatusChanged) and event.new in _FINAL_STATUSES:
            for pending in self.notifications.pending_for(event.appointment.id, _UPCOMING_KINDS):
                pending.status = NotificationStatus.CANCELLED
