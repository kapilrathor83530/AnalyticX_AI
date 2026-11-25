from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_and_login_flow():
    email = "test_auth_user@example.com"
    password = "strongpassword123"

    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Auth Tester"},
    )
    assert register.status_code in (201, 400)
    if register.status_code == 201:
        token = register.json()["access_token"]
        assert token

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["access_token"]
    assert body["user"]["email"] == email


def test_login_wrong_password():
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrong_pw@example.com", "password": "correct-password"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong_pw@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_me_requires_token():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_token():
    email = "me_user@example.com"
    password = "password-1234"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == email
