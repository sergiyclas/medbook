from pydantic import BaseModel, ConfigDict, Field


class ClinicSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reminder_email_hours_before: int
    reminder_sms_hours_before: int
    max_daily_bookings_per_patient: int
    booking_horizon_days: int
    patient_cancel_cutoff_hours: int


class ClinicSettingsUpdate(BaseModel):
    reminder_email_hours_before: int | None = Field(default=None, ge=1, le=168)
    reminder_sms_hours_before: int | None = Field(default=None, ge=1, le=72)
    max_daily_bookings_per_patient: int | None = Field(default=None, ge=1, le=10)
    booking_horizon_days: int | None = Field(default=None, ge=1, le=365)
    patient_cancel_cutoff_hours: int | None = Field(default=None, ge=0, le=72)
