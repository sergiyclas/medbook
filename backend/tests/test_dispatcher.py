from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.bootstrap import build_bus
from app.core.clock import local_to_utc
from app.domain.enums import NotificationChannel as Ch
from app.domain.enums import NotificationKind as K
from app.domain.enums import NotificationStatus as N
from app.models import Notification
from app.notifications.dispatcher import NotificationDispatcher
from app.notifications.factory import TransportFactory
from app.notifications.messages import MessageComposer
from app.notifications.ports import DeliveryError
from app.services.booking_facade import BookingFacade
from tests.factories import make_doctor, make_patient

BOOKED_AT = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)  # Monday 08:00 in Kyiv
SLOT = local_to_utc(date(2026, 11, 18), time(9))  # Wednesday 09:00


class Recorder:
    def __init__(self) -> None:
        self.sent: list = []
        self.errors: list[DeliveryError] = []

    def send(self, message) -> None:
        if self.errors:
            raise self.errors.pop(0)
        self.sent.append(message)


class RecordingFactory(TransportFactory):
    def __init__(self) -> None:
        self.email, self.sms = Recorder(), Recorder()

    def create_email_sender(self):
        return self.email

    def create_sms_sender(self):
        return self.sms


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def setup(engine: Engine, session: Session):
    clock = Clock(BOOKED_AT)
    facade = BookingFacade(session, build_bus(session), clock=clock)
    patient, doctor = make_patient(session), make_doctor(session)
    session.commit()
    transports = RecordingFactory()
    dispatcher = NotificationDispatcher(
        sessionmaker(bind=engine, expire_on_commit=False),
        transports,
        MessageComposer("Клініка", "http://localhost"),
        sender_name="MedBook",
        max_attempts=3,
        clock=clock,
    )
    return facade, patient, doctor, transports, dispatcher, clock


# The dispatcher writes through its own sessions; drop this session's cached
# copies so the test reads what is actually in the database
def confirmation(session: Session) -> Notification:
    session.expire_all()
    return session.scalar(select(Notification).where(Notification.kind == K.CONFIRMATION))


def statuses(session: Session) -> dict[tuple[Ch, K], N]:
    session.expire_all()
    return {(n.channel, n.kind): n.status for n in session.scalars(select(Notification))}


def test_confirmation_goes_now_reminders_when_due(session, setup) -> None:
    facade, patient, doctor, transports, dispatcher, clock = setup
    facade.book(patient.user, doctor.id, SLOT)

    assert dispatcher.process_due() == {N.SENT: 1}
    assert [m.subject for m in transports.email.sent] == ["Ви записані на прийом"]

    clock.now = SLOT - timedelta(hours=23)  # e-mail reminder (24 h before) is due
    assert dispatcher.process_due() == {N.SENT: 1}
    clock.now = SLOT - timedelta(minutes=90)  # SMS reminder (2 h before) is due
    assert dispatcher.process_due() == {N.SENT: 1}
    assert transports.sms.sent[0].text.startswith("MedBook. Нагадування про прийом")
    assert set(statuses(session).values()) == {N.SENT}
    assert dispatcher.process_due() == {}  # nothing is sent twice


def test_reminder_for_a_cancelled_visit_is_not_sent(session, setup) -> None:
    facade, patient, doctor, transports, dispatcher, clock = setup
    appt = facade.book(patient.user, doctor.id, SLOT)
    # The worker was down; by the time it runs the visit was cancelled and the
    # reminders became due. The canceller already withdrew them.
    facade.cancel(patient.user, appt.id)
    clock.now = SLOT - timedelta(hours=1)
    dispatcher.process_due()

    result = statuses(session)
    assert result[(Ch.EMAIL, K.REMINDER)] == N.CANCELLED
    assert result[(Ch.SMS, K.REMINDER)] == N.CANCELLED
    assert result[(Ch.EMAIL, K.CANCELLATION)] == N.SENT
    # "You are booked" right before "cancelled" would only confuse the patient
    assert result[(Ch.EMAIL, K.CONFIRMATION)] == N.CANCELLED
    assert [m.subject for m in transports.email.sent] == ["Прийом скасовано"]


def test_channel_switched_off_after_booking_is_skipped(session, setup) -> None:
    facade, patient, doctor, transports, dispatcher, clock = setup
    facade.book(patient.user, doctor.id, SLOT)
    patient.notify_sms = False
    session.commit()
    clock.now = SLOT - timedelta(hours=1)
    dispatcher.process_due()
    assert statuses(session)[(Ch.SMS, K.REMINDER)] == N.SKIPPED
    assert transports.sms.sent == []


def test_temporary_failure_is_retried_later_then_gives_up(session, setup) -> None:
    facade, patient, doctor, transports, dispatcher, clock = setup
    facade.book(patient.user, doctor.id, SLOT)
    transports.email.errors = [DeliveryError("timeout", transient=True)] * 3

    assert dispatcher.process_due() == {N.PENDING: 1}
    row = confirmation(session)
    assert (row.attempts, row.send_at, row.last_error) == (
        1,
        BOOKED_AT + timedelta(minutes=1),
        "timeout",
    )
    assert dispatcher.process_due() == {}  # not due yet

    clock.now += timedelta(minutes=1)
    assert dispatcher.process_due() == {N.PENDING: 1}
    clock.now += timedelta(minutes=5)
    assert dispatcher.process_due() == {N.FAILED: 1}  # third and last attempt


def test_permanent_failure_fails_at_once(session, setup) -> None:
    facade, patient, doctor, transports, dispatcher, _ = setup
    facade.book(patient.user, doctor.id, SLOT)
    transports.email.errors = [DeliveryError("mailbox does not exist", transient=False)]
    assert dispatcher.process_due() == {N.FAILED: 1}


def test_row_stuck_in_sending_is_released(session, setup) -> None:
    facade, patient, doctor, transports, dispatcher, clock = setup
    facade.book(patient.user, doctor.id, SLOT)
    row = confirmation(session)
    row.status, row.claimed_at = N.SENDING, BOOKED_AT  # a worker died mid-delivery
    session.commit()

    assert dispatcher.process_due() == {}
    clock.now += timedelta(minutes=11)
    assert dispatcher.process_due() == {N.SENT: 1}


def test_unexpected_error_fails_one_message_and_the_batch_goes_on(session, setup) -> None:
    facade, patient, doctor, transports, dispatcher, clock = setup
    facade.book(patient.user, doctor.id, SLOT)
    other = make_patient(session, notify_email=False)  # gets an SMS confirmation
    session.commit()
    facade.book(other.user, doctor.id, SLOT + timedelta(hours=1))

    def broken(message):
        raise ValueError("bad header")

    transports.email.send = broken
    assert dispatcher.process_due() == {N.FAILED: 1, N.SENT: 1}
    row = confirmation(session)
    assert row.last_error == "ValueError: bad header"


def test_message_reclaimed_by_another_worker_is_not_sent_twice(session, setup) -> None:
    facade, patient, doctor, transports, dispatcher, clock = setup
    facade.book(patient.user, doctor.id, SLOT)
    claimed_at, ids = dispatcher._claim()
    # meanwhile the row went stale and another worker took it over
    row = confirmation(session)
    row.claimed_at = claimed_at + timedelta(minutes=11)
    session.commit()
    assert dispatcher._deliver(ids[0], claimed_at) is None
    assert transports.email.sent == []
