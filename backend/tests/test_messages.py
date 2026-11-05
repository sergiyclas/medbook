from datetime import date, time

import pytest
from sqlalchemy.orm import Session

from app.core.clock import local_to_utc
from app.domain.enums import AppointmentStatus, NotificationKind
from app.models import AppointmentStatusChange
from app.notifications.messages import (
    SMS_MAX_LENGTH,
    EmailMessageBuilder,
    MessageComposer,
    SmsMessageBuilder,
)
from tests.factories import make_appointment, make_doctor, make_patient

SLOT = local_to_utc(date(2026, 11, 18), time(9))
composer = MessageComposer("Клініка MedBook", "http://localhost:8080/")


@pytest.fixture
def appt(session: Session):
    doctor = make_doctor(
        session, last_name="Коваленко", first_name="Андрій", middle_name="Іванович"
    )
    doctor.room = "103"
    patient = make_patient(session, email="olena@clinic.example", phone="+380671234567")
    return make_appointment(session, patient, doctor, SLOT)


def email(kind: NotificationKind, appt):
    builder = EmailMessageBuilder()
    composer.compose(kind, appt, builder)
    return builder.get_result()


def sms(kind: NotificationKind, appt):
    builder = SmsMessageBuilder("MedBook")
    composer.compose(kind, appt, builder)
    return builder.get_result()


def test_same_steps_give_two_different_representations(appt) -> None:
    mail = email(NotificationKind.REMINDER, appt)
    text = sms(NotificationKind.REMINDER, appt)

    assert mail.to == "olena@clinic.example"
    assert mail.subject == "Нагадування про прийом"
    assert "середа, 18 листопада 2026, 09:00" in mail.text
    assert "Коваленко Андрій Іванович" in mail.html
    assert 'href="http://localhost:8080/my"' in mail.html

    assert text.to == "+380671234567"
    assert text.text.startswith("MedBook. Нагадування про прийом: 18.11 о 09:00")
    assert "Коваленко А. І." in text.text
    assert "каб. 103" in text.text
    assert "Доброго дня" not in text.text  # the SMS builder skips the greeting step
    assert len(text.text) <= SMS_MAX_LENGTH


def test_director_varies_steps_by_kind(appt) -> None:
    assert "приходьте за 10 хвилин" in email(NotificationKind.REMINDER, appt).text
    assert "приходьте за 10 хвилин" not in email(NotificationKind.CONFIRMATION, appt).text
    assert email(NotificationKind.CONFIRMATION, appt).subject == "Ви записані на прийом"


def test_cancellation_carries_the_reason_escaped_in_html(appt) -> None:
    appt.status = AppointmentStatus.CANCELLED
    appt.history.append(
        AppointmentStatusChange(to_status=AppointmentStatus.CANCELLED, reason="Лікар <хворіє>")
    )
    mail = email(NotificationKind.CANCELLATION, appt)
    assert "Причина: Лікар <хворіє>" in mail.text
    assert "Лікар &lt;хворіє&gt;" in mail.html
    assert "<хворіє>" not in mail.html
    assert sms(NotificationKind.CANCELLATION, appt).text.startswith("MedBook. Прийом скасовано")


def test_long_sms_is_cut_to_two_segments(session: Session, appt) -> None:
    appt.doctor.specialization.name = "Дуже-дуже довга назва спеціалізації " * 4
    assert len(sms(NotificationKind.REMINDER, appt).text) == SMS_MAX_LENGTH
