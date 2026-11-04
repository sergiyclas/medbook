from fastapi.testclient import TestClient

from tests.conftest import login

SCHEDULE = [
    {"weekday": 0, "start_time": "09:00", "end_time": "13:00"},
    {"weekday": 0, "start_time": "14:00", "end_time": "18:00"},
]


def _doctor_payload(spec_id: int, **overrides) -> dict:
    return {
        "email": "doc@clinic.example",
        "password": "doctor1",
        "last_name": "Коваленко",
        "first_name": "Андрій",
        "specialization_id": spec_id,
        "slot_minutes": 30,
        "working_hours": SCHEDULE,
    } | overrides


def _specialization(client: TestClient, headers: dict, name: str = "Кардіолог") -> int:
    response = client.post("/api/v1/admin/specializations", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_admin_creates_doctor_visible_in_public_catalog(
    client: TestClient, admin_headers: dict
) -> None:
    cardio = _specialization(client, admin_headers)
    other = _specialization(client, admin_headers, "Невролог")
    response = client.post(
        "/api/v1/admin/doctors", json=_doctor_payload(cardio), headers=admin_headers
    )
    assert response.status_code == 201
    assert response.json()["email"] == "doc@clinic.example"
    assert len(response.json()["working_hours"]) == 2

    assert len(client.get(f"/api/v1/doctors?specialization_id={cardio}").json()) == 1
    assert client.get(f"/api/v1/doctors?specialization_id={other}").json() == []
    # the new doctor can sign in straight away
    login(client, "doc@clinic.example", "doctor1")


def test_overlapping_working_hours_are_rejected(client: TestClient, admin_headers: dict) -> None:
    spec = _specialization(client, admin_headers)
    clash = [*SCHEDULE, {"weekday": 0, "start_time": "12:00", "end_time": "15:00"}]
    response = client.post(
        "/api/v1/admin/doctors",
        json=_doctor_payload(spec, working_hours=clash),
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_deactivated_doctor_disappears_and_cannot_log_in(
    client: TestClient, admin_headers: dict
) -> None:
    spec = _specialization(client, admin_headers)
    doctor_id = client.post(
        "/api/v1/admin/doctors", json=_doctor_payload(spec), headers=admin_headers
    ).json()["id"]
    client.patch(
        f"/api/v1/admin/doctors/{doctor_id}", json={"is_active": False}, headers=admin_headers
    )

    assert client.get("/api/v1/doctors").json() == []
    assert client.get(f"/api/v1/doctors/{doctor_id}").status_code == 404
    response = client.post(
        "/api/v1/auth/login", data={"username": "doc@clinic.example", "password": "doctor1"}
    )
    assert response.status_code == 401


def test_specialization_with_doctors_cannot_be_deleted(
    client: TestClient, admin_headers: dict
) -> None:
    spec = _specialization(client, admin_headers)
    client.post("/api/v1/admin/doctors", json=_doctor_payload(spec), headers=admin_headers)
    response = client.delete(f"/api/v1/admin/specializations/{spec}", headers=admin_headers)
    assert response.status_code == 409


def test_working_hours_and_days_off_management(client: TestClient, admin_headers: dict) -> None:
    spec = _specialization(client, admin_headers)
    doctor_id = client.post(
        "/api/v1/admin/doctors", json=_doctor_payload(spec), headers=admin_headers
    ).json()["id"]

    replaced = client.put(
        f"/api/v1/admin/doctors/{doctor_id}/working-hours",
        json={"working_hours": [{"weekday": 2, "start_time": "08:00", "end_time": "12:00"}]},
        headers=admin_headers,
    )
    assert [h["weekday"] for h in replaced.json()["working_hours"]] == [2]

    day_off = client.post(
        f"/api/v1/admin/doctors/{doctor_id}/days-off",
        json={"day": "2026-12-31", "reason": "Свято"},
        headers=admin_headers,
    )
    assert day_off.status_code == 201
    duplicate = client.post(
        f"/api/v1/admin/doctors/{doctor_id}/days-off",
        json={"day": "2026-12-31"},
        headers=admin_headers,
    )
    assert duplicate.status_code == 409
    removed = client.delete(f"/api/v1/admin/days-off/{day_off.json()['id']}", headers=admin_headers)
    assert removed.status_code == 204


def test_admin_updates_clinic_settings_within_bounds(
    client: TestClient, admin_headers: dict
) -> None:
    assert (
        client.get("/api/v1/admin/settings", headers=admin_headers).json()["booking_horizon_days"]
        == 30
    )
    ok = client.patch(
        "/api/v1/admin/settings", json={"booking_horizon_days": 60}, headers=admin_headers
    )
    too_big = client.patch(
        "/api/v1/admin/settings", json={"booking_horizon_days": 1000}, headers=admin_headers
    )
    assert ok.json()["booking_horizon_days"] == 60
    assert too_big.status_code == 422


def test_admin_registers_and_finds_walk_in_patient(client: TestClient, admin_headers: dict) -> None:
    payload = {
        "email": "walkin@clinic.example",
        "password": "secret12",
        "last_name": "Бондар",
        "first_name": "Петро",
        "phone": "+380501112233",
        "birth_date": "1960-02-02",
    }
    assert (
        client.post("/api/v1/admin/patients", json=payload, headers=admin_headers).status_code
        == 201
    )
    found = client.get("/api/v1/admin/patients?search=бонд", headers=admin_headers).json()
    assert [p["email"] for p in found] == ["walkin@clinic.example"]
