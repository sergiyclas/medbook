from fastapi.testclient import TestClient

from tests.conftest import login

REGISTRATION = {
    "email": "Olena.Shevchenko@Example.com",
    "password": "secret12",
    "last_name": "Шевченко",
    "first_name": "Олена",
    "middle_name": "Іванівна",
    "phone": "067 123-45-67",
    "birth_date": "1990-05-17",
}


def test_patient_registers_and_sees_own_profile(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=REGISTRATION)
    assert response.status_code == 201
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["role"] == "patient"
    assert me["email"] == "olena.shevchenko@example.com"
    assert me["patient"]["phone"] == "+380671234567"
    assert me["patient"]["full_name"] == "Шевченко Олена Іванівна"


def test_duplicate_email_is_rejected(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=REGISTRATION)
    response = client.post(
        "/api/v1/auth/register", json=REGISTRATION | {"email": "olena.shevchenko@example.com"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


def test_registration_validates_phone_and_birth_date(client: TestClient) -> None:
    bad_phone = client.post("/api/v1/auth/register", json=REGISTRATION | {"phone": "12345"})
    future_birth = client.post(
        "/api/v1/auth/register", json=REGISTRATION | {"birth_date": "2999-01-01"}
    )
    assert bad_phone.status_code == 422
    assert future_birth.status_code == 422


def test_login_with_wrong_password_fails(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=REGISTRATION)
    response = client.post(
        "/api/v1/auth/login", data={"username": REGISTRATION["email"], "password": "wrong"}
    )
    assert response.status_code == 401


def test_patient_updates_notification_preferences(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=REGISTRATION)
    headers = login(client, REGISTRATION["email"], REGISTRATION["password"])
    response = client.patch("/api/v1/patients/me", json={"notify_sms": False}, headers=headers)
    assert response.status_code == 200
    assert response.json()["notify_sms"] is False
    assert response.json()["notify_email"] is True


def test_protected_endpoints_require_token_and_role(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    client.post("/api/v1/auth/register", json=REGISTRATION)
    headers = login(client, REGISTRATION["email"], REGISTRATION["password"])
    assert client.get("/api/v1/admin/patients", headers=headers).status_code == 403
