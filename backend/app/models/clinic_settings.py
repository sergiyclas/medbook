from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Business settings the administrator edits at runtime. A single typed row instead
# of a key/value table: each field is validated and has a sane default.
class ClinicSettings(Base):
    __tablename__ = "clinic_settings"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    reminder_email_hours_before: Mapped[int] = mapped_column(default=24)
    reminder_sms_hours_before: Mapped[int] = mapped_column(default=2)
    max_daily_bookings_per_patient: Mapped[int] = mapped_column(default=2)
    booking_horizon_days: Mapped[int] = mapped_column(default=30)
    patient_cancel_cutoff_hours: Mapped[int] = mapped_column(default=2)
