from collections.abc import Callable
from datetime import date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.domain.appointment_state import TransitionContext
from app.domain.enums import Role
from app.domain.errors import Forbidden, InvalidData, NotFound
from app.models import Appointment, Doctor, Patient, User
from app.repositories.appointments import AppointmentRepository
from app.repositories.doctors import DoctorRepository
from app.repositories.patients import PatientRepository
from app.repositories.settings import ClinicSettingsRepository
from app.services.availability import AvailabilityCalendar
from app.services.booking_rules import (
    BookingRequest,
    SlotTaken,
    build_admin_chain,
    build_patient_chain,
)
from app.services.event_bus import EventBus


# GoF Facade (and GRASP Controller) for everything that changes an appointment.
# API routes see one object with use-case methods; behind it the validation
# chain, the state machine, repositories and the event bus cooperate. The
# facade only coordinates – rules live in the chain, transitions in the states,
# side effects in the event handlers – and it owns the single commit.
class BookingFacade:
    def __init__(
        self, session: Session, bus: EventBus, clock: Callable[[], datetime] = utc_now
    ) -> None:
        self.session = session
        self.bus = bus
        self.clock = clock
        self.appointments = AppointmentRepository(session)
        self.doctors = DoctorRepository(session)
        self.patients = PatientRepository(session)
        self.settings = ClinicSettingsRepository(session)
        self.calendar = AvailabilityCalendar(self.appointments)

    # ---------- queries ----------
    def available_slots(self, doctor_id: int, day: date) -> list[tuple[datetime, datetime]]:
        doctor = self._doctor(doctor_id)
        if not doctor.is_active:
            return []
        step = timedelta(minutes=doctor.slot_minutes)
        return [(s, s + step) for s in self.calendar.free_slots(doctor, day, self.clock())]

    def appointment_for(self, actor: User, appointment_id: int) -> Appointment:
        appt = self.appointments.get(appointment_id)
        if appt is None or not self._can_see(actor, appt):
            raise NotFound("Прийом не знайдено")
        return appt

    # ---------- commands ----------
    def book(
        self,
        actor: User,
        doctor_id: int,
        starts_at: datetime,
        reason: str | None = None,
        patient_id: int | None = None,
    ) -> Appointment:
        patient = self._patient_for(actor, patient_id)
        doctor = self._doctor(doctor_id)
        now = self.clock()
        self._chain_for(actor).check(
            BookingRequest(doctor, patient, starts_at, now, self.settings.current())
        )
        appt = Appointment.book(patient, doctor, starts_at, reason, actor, now)
        self.session.add(appt)
        return self._finish(appt)

    def reschedule(self, actor: User, appointment_id: int, starts_at: datetime) -> Appointment:
        appt = self.appointment_for(actor, appointment_id)
        now = self.clock()
        self._chain_for(actor).check(
            BookingRequest(
                appt.doctor, appt.patient, starts_at, now, self.settings.current(), appt.id
            )
        )
        appt.reschedule(self._ctx(actor), starts_at)
        return self._finish(appt)

    def cancel(self, actor: User, appointment_id: int, reason: str | None = None) -> Appointment:
        appt = self.appointment_for(actor, appointment_id)
        appt.cancel(self._ctx(actor), reason)
        return self._finish(appt)

    def confirm(self, actor: User, appointment_id: int) -> Appointment:
        appt = self.appointment_for(actor, appointment_id)
        appt.confirm(self._ctx(actor))
        return self._finish(appt)

    def complete(self, actor: User, appointment_id: int, notes: str | None) -> Appointment:
        appt = self.appointment_for(actor, appointment_id)
        appt.complete(self._ctx(actor), notes)
        return self._finish(appt)

    def mark_no_show(self, actor: User, appointment_id: int) -> Appointment:
        appt = self.appointment_for(actor, appointment_id)
        appt.mark_no_show(self._ctx(actor))
        return self._finish(appt)

    # Used when the administrator marks a day off over existing bookings: every
    # active visit that day is cancelled through the regular state machine, so
    # patients get the same cancellation notices as for any other cancel.
    def cancel_doctor_day(
        self, actor: User, doctor: Doctor, day: date, reason: str
    ) -> list[Appointment]:
        start, end = self.calendar.day_bounds(day)
        ctx = self._ctx(actor)
        cancelled = self.appointments.doctor_active_between(doctor.id, start, end)
        for appt in cancelled:
            appt.cancel(ctx, reason)
        self._flush_and_publish(cancelled)
        self.session.commit()
        return cancelled

    # ---------- internals ----------
    def _finish(self, appt: Appointment) -> Appointment:
        self._flush_and_publish([appt])
        self.session.commit()
        return appt

    # Flush first so new rows have ids and the unique slot index has spoken;
    # then let observers add their rows to the same transaction.
    def _flush_and_publish(self, appointments: list[Appointment]) -> None:
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise SlotTaken("Цей час щойно зайняли – оберіть інший слот") from None
        for appt in appointments:
            for event in appt.pull_events():
                self.bus.publish(event)
        self.session.flush()

    def _ctx(self, actor: User) -> TransitionContext:
        return TransitionContext(
            actor=actor,
            now=self.clock(),
            patient_cancel_cutoff_hours=self.settings.current().patient_cancel_cutoff_hours,
        )

    def _chain_for(self, actor: User):
        if actor.role == Role.PATIENT:
            return build_patient_chain(self.calendar, self.appointments)
        if actor.role == Role.ADMIN:
            return build_admin_chain(self.calendar, self.appointments)
        raise Forbidden("Записувати пацієнтів можуть лише пацієнти та адміністратори")

    def _patient_for(self, actor: User, patient_id: int | None) -> Patient:
        if actor.role == Role.PATIENT:
            assert actor.patient is not None
            return actor.patient
        if patient_id is None:
            raise InvalidData("Вкажіть пацієнта, якого записуєте", "patient_required")
        patient = self.patients.get(patient_id)
        if patient is None:
            raise NotFound("Пацієнта не знайдено")
        return patient

    def _doctor(self, doctor_id: int) -> Doctor:
        doctor = self.doctors.get(doctor_id)
        if doctor is None:
            raise NotFound("Лікаря не знайдено")
        return doctor

    @staticmethod
    def _can_see(actor: User, appt: Appointment) -> bool:
        if actor.role == Role.ADMIN:
            return True
        if actor.role == Role.DOCTOR:
            return appt.doctor.user_id == actor.id
        return appt.patient.user_id == actor.id
