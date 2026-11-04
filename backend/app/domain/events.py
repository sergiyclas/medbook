from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from app.domain.enums import AppointmentStatus

if TYPE_CHECKING:
    from app.models import Appointment

# Domain events: facts about appointments that other parts of the system react to.
# Appointment records them; BookingFacade publishes them after the change is flushed.


@dataclass(frozen=True)
class AppointmentBooked:
    appointment: Appointment
    actor_id: int | None
    at: datetime


@dataclass(frozen=True)
class AppointmentStatusChanged:
    appointment: Appointment
    old: AppointmentStatus
    new: AppointmentStatus
    actor_id: int | None
    reason: str | None
    at: datetime


@dataclass(frozen=True)
class AppointmentRescheduled:
    appointment: Appointment
    old_status: AppointmentStatus
    old_starts_at: datetime
    actor_id: int | None
    at: datetime


DomainEvent = AppointmentBooked | AppointmentStatusChanged | AppointmentRescheduled
