from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Appointment, Patient, User
from app.seed import seed


def test_seed_fills_an_empty_database_once(session: Session) -> None:
    assert seed(session) is True
    assert session.scalar(select(func.count()).select_from(Appointment)) > 1000
    assert session.scalar(select(User).where(User.email == "admin@medbook.example")) is not None
    assert seed(session) is False


def test_seeded_strangers_never_receive_notifications(session: Session) -> None:
    seed(session)
    noisy = session.scalars(
        select(Patient)
        .join(User)
        .where(User.email != "patient@medbook.example")
        .where(Patient.notify_email | Patient.notify_sms)
    ).all()
    assert noisy == []
