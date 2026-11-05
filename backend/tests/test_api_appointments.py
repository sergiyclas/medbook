from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.clock import local_to_utc, local_today
from app.domain.enums import NotificationStatus
from app.models import Notification
from tests.conftest import login
from tests.factories import make_doctor, make_patient


def next_monday() -> date:
    day = local_today() + timedelta(days=2)
    while day.weekday() != 0:
        day += timedelta(days=1)
    return day


DAY = next_monday()
SLOT = local_to_utc(DAY, time(9)).isoformat()


@pytest.fixture
def people(session: Session, client: TestClient):
    doctor = make_doctor(session, email="doc@clinic.example", password="doctor1")
    other_doctor = make_doctor(session, email="doc2@clinic.example", password="doctor2")
    anna = make_patient(session, email="anna@clinic.example", password="secret1")
    make_patient(session, email="boris@clinic.example", password="secret2")
    session.commit()
    return {
        "doctor": doctor,
        "other_doctor": other_doctor,
        "anna_id": anna.id,
        "anna": login(client, "anna@clinic.example", "secret1"),
        "boris": login(client, "boris@clinic.example", "secret2"),
        "doc": login(client, "doc@clinic.example", "doctor1"),
        "doc2": login(client, "doc2@clinic.example", "doctor2"),
    }


def book(client: TestClient, headers: dict, doctor_id: int, starts_at: str = SLOT, **extra):
    return client.post(
        "/api/v1/appointments",
        json={"doctor_id": doctor_id, "starts_at": starts_at, **extra},
        headers=headers,
    )


def test_public_slots_hide_booked_time(client: TestClient, people) -> None:
    doctor_id = people["doctor"].id
    before = client.get(f"/api/v1/doctors/{doctor_id}/slots?day={DAY}").json()
    assert book(client, people["anna"], doctor_id).status_code == 201
    after = client.get(f"/api/v1/doctors/{doctor_id}/slots?day={DAY}").json()
    assert len(after) == len(before) - 1
    assert all(s["starts_at"] != before[0]["starts_at"] for s in after)


def test_slot_cannot_be_booked_twice(client: TestClient, people) -> None:
    book(client, people["anna"], people["doctor"].id)
    response = book(client, people["boris"], people["doctor"].id)
    assert response.status_code == 409
    assert response.json()["code"] == "slot_taken"


def test_rule_violation_returns_its_code(client: TestClient, people) -> None:
    off_grid = local_to_utc(DAY, time(9, 10)).isoformat()
    response = book(client, people["anna"], people["doctor"].id, off_grid)
    assert response.status_code == 422
    assert response.json()["code"] == "not_on_grid"


def test_patient_sees_own_visits_others_get_404(client: TestClient, people) -> None:
    appt_id = book(client, people["anna"], people["doctor"].id, reason="Огляд").json()["id"]

    mine = client.get("/api/v1/appointments/my", headers=people["anna"]).json()
    assert [a["id"] for a in mine] == [appt_id]
    history = client.get(f"/api/v1/appointments/{appt_id}/history", headers=people["anna"])
    assert [h["to_status"] for h in history.json()] == ["scheduled"]

    assert client.get(f"/api/v1/appointments/{appt_id}", headers=people["boris"]).status_code == 404
    cancel = client.post(f"/api/v1/appointments/{appt_id}/cancel", json={}, headers=people["boris"])
    assert cancel.status_code == 404


def test_patient_cancels_and_reschedules(client: TestClient, people) -> None:
    appt_id = book(client, people["anna"], people["doctor"].id).json()["id"]
    later = local_to_utc(DAY, time(14)).isoformat()
    moved = client.post(
        f"/api/v1/appointments/{appt_id}/reschedule",
        json={"starts_at": later},
        headers=people["anna"],
    )
    assert moved.status_code == 200
    assert moved.json()["starts_at"].startswith(local_to_utc(DAY, time(14)).strftime("%Y-%m-%dT%H"))

    cancelled = client.post(
        f"/api/v1/appointments/{appt_id}/cancel", json={"reason": "Одужала"}, headers=people["anna"]
    )
    assert cancelled.json()["status"] == "cancelled"
    again = client.post(f"/api/v1/appointments/{appt_id}/cancel", json={}, headers=people["anna"])
    assert again.status_code == 409
    assert again.json()["code"] == "invalid_transition"


def test_doctor_cabinet_shows_only_own_visits(client: TestClient, people) -> None:
    book(client, people["anna"], people["doctor"].id)
    book(client, people["boris"], people["other_doctor"].id)

    mine = client.get(f"/api/v1/doctor/schedule?date_from={DAY}", headers=people["doc"]).json()
    assert len(mine) == 1
    assert mine[0]["doctor"]["id"] == people["doctor"].id
    assert mine[0]["patient"]["email"] == "anna@clinic.example"


def test_doctor_cannot_book_or_touch_foreign_visits(client: TestClient, people) -> None:
    appt_id = book(client, people["anna"], people["doctor"].id).json()["id"]
    assert book(client, people["doc"], people["doctor"].id).status_code == 403
    foreign = client.post(f"/api/v1/appointments/{appt_id}/confirm", headers=people["doc2"])
    assert foreign.status_code == 404
    own = client.post(f"/api/v1/appointments/{appt_id}/confirm", headers=people["doc"])
    assert own.json()["status"] == "confirmed"


def test_reception_books_for_a_patient(client: TestClient, people, admin_headers) -> None:
    missing = book(client, admin_headers, people["doctor"].id)
    assert missing.status_code == 422
    assert missing.json()["code"] == "patient_required"

    ok = book(client, admin_headers, people["doctor"].id, patient_id=people["anna_id"])
    assert ok.status_code == 201
    listed = client.get("/api/v1/admin/appointments?status=scheduled", headers=admin_headers)
    assert [a["id"] for a in listed.json()] == [ok.json()["id"]]


def test_day_off_over_bookings_cancels_them(client: TestClient, people, admin_headers) -> None:
    appt_id = book(client, people["anna"], people["doctor"].id).json()["id"]
    response = client.post(
        f"/api/v1/admin/doctors/{people['doctor'].id}/days-off",
        json={"day": DAY.isoformat(), "reason": "Конференція"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["cancelled_appointments"] == 1
    visit = client.get(f"/api/v1/appointments/{appt_id}", headers=people["anna"]).json()
    assert visit["status"] == "cancelled"
    slots = client.get(f"/api/v1/doctors/{people['doctor'].id}/slots?day={DAY}").json()
    assert slots == []


def test_admin_sees_notification_log_and_retries_failed(
    client: TestClient, session: Session, people, admin_headers
) -> None:
    appt_id = book(client, people["anna"], people["doctor"].id).json()["id"]
    log = client.get("/api/v1/admin/notifications", headers=admin_headers).json()
    assert {n["kind"] for n in log} == {"confirmation", "reminder"}
    assert all(n["appointment"]["id"] == appt_id for n in log)

    pending_id = log[0]["id"]
    refused = client.post(f"/api/v1/admin/notifications/{pending_id}/retry", headers=admin_headers)
    assert refused.status_code == 409

    failed = session.get(Notification, pending_id)
    failed.status, failed.attempts = NotificationStatus.FAILED, 5
    session.commit()
    retried = client.post(f"/api/v1/admin/notifications/{pending_id}/retry", headers=admin_headers)
    assert retried.json()["status"] == "pending"
    assert retried.json()["attempts"] == 0
