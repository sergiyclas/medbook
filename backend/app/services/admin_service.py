from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domain.enums import Role
from app.domain.errors import Conflict, NotFound
from app.models import (
    Appointment,
    ClinicSettings,
    DayOff,
    Doctor,
    Patient,
    Specialization,
    User,
    WorkingHours,
)
from app.repositories.doctors import DayOffRepository, DoctorRepository, SpecializationRepository
from app.repositories.patients import PatientRepository
from app.repositories.settings import ClinicSettingsRepository
from app.repositories.users import UserRepository
from app.schemas.doctors import (
    DayOffIn,
    DoctorCreate,
    DoctorUpdate,
    SpecializationIn,
    WeeklySchedule,
    WorkingHoursIn,
)
from app.schemas.patients import PatientUpdate
from app.schemas.settings import ClinicSettingsUpdate
from app.services.booking_facade import BookingFacade


def _apply(entity: object, changes: dict) -> None:
    for field, value in changes.items():
        setattr(entity, field, value)


def _hours(rows: list[WorkingHoursIn]) -> list[WorkingHours]:
    return [WorkingHours(**r.model_dump()) for r in rows]


class AdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.specializations = SpecializationRepository(session)
        self.doctors = DoctorRepository(session)
        self.days_off = DayOffRepository(session)
        self.patients = PatientRepository(session)
        self.settings = ClinicSettingsRepository(session)

    # ---------- specializations ----------
    def create_specialization(self, data: SpecializationIn) -> Specialization:
        self._ensure_unique_specialization(data.name)
        spec = self.specializations.add(Specialization(**data.model_dump()))
        self.session.commit()
        return spec

    def update_specialization(self, spec_id: int, data: SpecializationIn) -> Specialization:
        spec = self._specialization(spec_id)
        if data.name != spec.name:
            self._ensure_unique_specialization(data.name)
        _apply(spec, data.model_dump())
        self.session.commit()
        return spec

    def delete_specialization(self, spec_id: int) -> None:
        spec = self._specialization(spec_id)
        if spec.doctors:
            raise Conflict("Спеціалізацію не можна видалити, поки до неї прив'язані лікарі")
        self.specializations.delete(spec)
        self.session.commit()

    # ---------- doctors ----------
    # Account and profile are created in one transaction: no doctor without a login
    def create_doctor(self, data: DoctorCreate) -> Doctor:
        if self.users.by_email(data.email):
            raise Conflict("Користувач з таким e-mail уже зареєстрований", "email_taken")
        self._specialization(data.specialization_id)
        user = User(
            email=data.email.lower(), password_hash=hash_password(data.password), role=Role.DOCTOR
        )
        doctor = Doctor(
            user=user,
            working_hours=_hours(data.working_hours),
            **data.model_dump(exclude={"email", "password", "working_hours"}),
        )
        self.doctors.add(doctor)
        self.session.commit()
        return doctor

    def update_doctor(self, doctor_id: int, data: DoctorUpdate) -> Doctor:
        doctor = self.doctor(doctor_id)
        # null clears optional fields but is ignored for required ones
        changes = {
            k: v
            for k, v in data.model_dump(exclude_unset=True).items()
            if v is not None or k in {"middle_name", "room", "bio"}
        }
        if "specialization_id" in changes:
            self._specialization(changes["specialization_id"])
        _apply(doctor, changes)
        doctor.user.is_active = doctor.is_active
        self.session.commit()
        return doctor

    # Replaces the whole weekly template. Booked visits outside the new hours stay
    # valid – the administrator reschedules them explicitly if needed.
    def set_working_hours(self, doctor_id: int, schedule: WeeklySchedule) -> Doctor:
        doctor = self.doctor(doctor_id)
        doctor.working_hours = _hours(schedule.working_hours)
        self.session.commit()
        return doctor

    # Visits already booked on that day are cancelled through BookingFacade in
    # the same transaction, so patients are notified like for any cancellation.
    def add_day_off(
        self, actor: User, doctor_id: int, data: DayOffIn, booking: BookingFacade
    ) -> tuple[DayOff, list[Appointment]]:
        doctor = self.doctor(doctor_id)
        if any(d.day == data.day for d in doctor.days_off):
            raise Conflict("Цей день уже позначено як вихідний")
        day_off = self.days_off.add(DayOff(doctor=doctor, **data.model_dump()))
        reason = "Лікар не працює в цей день" + (f": {data.reason}" if data.reason else "")
        cancelled = booking.cancel_doctor_day(actor, doctor, data.day, reason)
        return day_off, cancelled

    def remove_day_off(self, day_off_id: int) -> None:
        day_off = self.days_off.get(day_off_id)
        if day_off is None:
            raise NotFound("Вихідний не знайдено")
        self.days_off.delete(day_off)
        self.session.commit()

    def doctor(self, doctor_id: int) -> Doctor:
        doctor = self.doctors.get(doctor_id)
        if doctor is None:
            raise NotFound("Лікаря не знайдено")
        return doctor

    # ---------- patients ----------
    def update_patient(self, patient_id: int, data: PatientUpdate) -> Patient:
        patient = self.patient(patient_id)
        _apply(patient, data.model_dump(exclude_unset=True, exclude_none=True))
        self.session.commit()
        return patient

    def patient(self, patient_id: int) -> Patient:
        patient = self.patients.get(patient_id)
        if patient is None:
            raise NotFound("Пацієнта не знайдено")
        return patient

    # ---------- clinic settings ----------
    def update_settings(self, data: ClinicSettingsUpdate) -> ClinicSettings:
        settings = self.settings.current()
        _apply(settings, data.model_dump(exclude_unset=True, exclude_none=True))
        self.session.commit()
        return settings

    def _specialization(self, spec_id: int) -> Specialization:
        spec = self.specializations.get(spec_id)
        if spec is None:
            raise NotFound("Спеціалізацію не знайдено")
        return spec

    def _ensure_unique_specialization(self, name: str) -> None:
        if self.specializations.by_name(name):
            raise Conflict("Така спеціалізація вже існує")
