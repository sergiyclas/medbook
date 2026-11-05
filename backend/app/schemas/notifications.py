from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import (
    AppointmentStatus,
    NotificationChannel,
    NotificationKind,
    NotificationStatus,
)


class PersonName(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class NotificationAppointment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    starts_at: datetime
    status: AppointmentStatus
    patient: PersonName
    doctor: PersonName


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: NotificationChannel
    kind: NotificationKind
    status: NotificationStatus
    send_at: datetime
    sent_at: datetime | None
    attempts: int
    last_error: str | None
    appointment: NotificationAppointment
