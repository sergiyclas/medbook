from datetime import date, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.domain.availability import overlapping_weekdays


class SpecializationIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


class SpecializationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None


class WorkingHoursIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def _ordered(self) -> "WorkingHoursIn":
        if self.start_time >= self.end_time:
            raise ValueError("Початок зміни має бути раніше за кінець")
        return self


class WorkingHoursOut(WorkingHoursIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


def _no_overlaps(rows: list[WorkingHoursIn]) -> list[WorkingHoursIn]:
    clashes = overlapping_weekdays((r.weekday, r.start_time, r.end_time) for r in rows)
    if clashes:
        raise ValueError(f"Інтервали перетинаються у дні тижня: {sorted(clashes)}")
    return rows


class WeeklySchedule(BaseModel):
    working_hours: list[WorkingHoursIn]

    _check = field_validator("working_hours")(_no_overlaps)


class DoctorCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    last_name: str = Field(min_length=1, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    specialization_id: int
    room: str | None = Field(default=None, max_length=20)
    bio: str | None = None
    slot_minutes: int = Field(default=20, ge=10, le=120)
    working_hours: list[WorkingHoursIn] = []

    _check = field_validator("working_hours")(_no_overlaps)


class DoctorUpdate(BaseModel):
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    specialization_id: int | None = None
    room: str | None = Field(default=None, max_length=20)
    bio: str | None = None
    slot_minutes: int | None = Field(default=None, ge=10, le=120)
    is_active: bool | None = None


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_name: str
    first_name: str
    middle_name: str | None
    full_name: str
    specialization: SpecializationOut
    room: str | None
    bio: str | None
    slot_minutes: int
    is_active: bool
    working_hours: list[WorkingHoursOut]


class DoctorAdminOut(DoctorOut):
    email: str


class DayOffIn(BaseModel):
    day: date
    reason: str | None = Field(default=None, max_length=200)


class DayOffOut(DayOffIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int


class DayOffCreated(DayOffOut):
    cancelled_appointments: int
