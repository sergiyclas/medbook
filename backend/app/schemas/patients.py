from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.phone import normalize_phone

Name = Field(min_length=1, max_length=100)


def _check_birth_date(value: date) -> date:
    if not date(1900, 1, 1) <= value < date.today():
        raise ValueError("Дата народження має бути в минулому")
    return value


class PatientRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    last_name: str = Name
    first_name: str = Name
    middle_name: str | None = Field(default=None, max_length=100)
    phone: str
    birth_date: date

    _phone = field_validator("phone")(normalize_phone)
    _birth = field_validator("birth_date")(_check_birth_date)


# What a patient may change about themselves
class PatientSelfUpdate(BaseModel):
    phone: str | None = None
    notify_email: bool | None = None
    notify_sms: bool | None = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return None if value is None else normalize_phone(value)


# What an administrator may change
class PatientUpdate(PatientSelfUpdate):
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None

    @field_validator("birth_date")
    @classmethod
    def _birth(cls, value: date | None) -> date | None:
        return None if value is None else _check_birth_date(value)


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    last_name: str
    first_name: str
    middle_name: str | None
    full_name: str
    phone: str
    birth_date: date
    notify_email: bool
    notify_sms: bool
    created_at: datetime
