from enum import StrEnum


class Role(StrEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class AppointmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# Statuses that occupy a slot in the doctor's schedule
ACTIVE_STATUSES = (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED)


class NotificationChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"


class NotificationKind(StrEnum):
    CONFIRMATION = "confirmation"
    REMINDER = "reminder"
    CANCELLATION = "cancellation"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
