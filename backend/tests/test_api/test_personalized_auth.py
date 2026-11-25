import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_registration_and_duplicate_handling():
    uid = uuid.uuid4().hex[:8]
    email = f"user_{uid}@analyticx.ai"
    pwd = "SecurePassword123!"

    # 1. Successful registration
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "full_name": "SaaS Tester"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["access_token"]
    assert data["user"]["email"] == email
    assert data["user"]["full_name"] == "SaaS Tester"
    assert data["user"]["role"] == "Data Analyst"
    assert data["user"]["onboarding_completed"] is False
    assert data["user"]["is_verified"] is False

    # 2. Duplicate registration returns 400
    res_dup = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "full_name": "Duplicate Tester"},
    )
    assert res_dup.status_code == 400
    assert "already registered" in res_dup.json()["detail"].lower()


def test_email_verification_lifecycle():
    uid = uuid.uuid4().hex[:8]
    email = f"verify_{uid}@analyticx.ai"
    pwd = "Password456!"

    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "full_name": "Verify Me"},
    )
    assert res.status_code == 201

    # Resend verification token (returns token in dev mode)
    res_resend = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )
    assert res_resend.status_code == 200
    dev_token = res_resend.json().get("dev_token")
    assert dev_token is not None

    # Verify email with token
    res_verify = client.post(
        "/api/v1/auth/verify-email",
        json={"token": dev_token},
    )
    assert res_verify.status_code == 200
    assert res_verify.json()["verified"] is True

    # Check /me to confirm is_verified is True
    login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["is_verified"] is True


def test_password_reset_lifecycle():
    uid = uuid.uuid4().hex[:8]
    email = f"reset_{uid}@analyticx.ai"
    old_pwd = "OldPassword123!"
    new_pwd = "NewPassword456!"

    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": old_pwd, "full_name": "Reset Tester"},
    )

    # 1. Request reset link
    req = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": email},
    )
    assert req.status_code == 200
    reset_token = req.json().get("reset_token")
    assert reset_token is not None

    # 2. Confirm reset
    conf = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": new_pwd},
    )
    assert conf.status_code == 200
    assert conf.json()["updated"] is True

    # 3. Single-use invalidation: using same token again fails
    conf_reuse = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "AnotherPassword789!"},
    )
    assert conf_reuse.status_code == 400

    # 4. Old password cannot login, new password succeeds
    fail_login = client.post("/api/v1/auth/login", json={"email": email, "password": old_pwd})
    assert fail_login.status_code == 401

    ok_login = client.post("/api/v1/auth/login", json={"email": email, "password": new_pwd})
    assert ok_login.status_code == 200


def test_onboarding_and_preferences_persistence():
    uid = uuid.uuid4().hex[:8]
    email = f"onboard_{uid}@analyticx.ai"
    pwd = "Password987!"

    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "full_name": "Onboard Me"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Complete onboarding
    onboard_payload = {
        "role": "Data Scientist / ML Engineer",
        "primary_goal": ["Forecast future metrics", "Automate exploratory data analysis"],
        "experience_level": "Advanced",
        "preferences": {
            "theme": "dark",
            "language": "es",
            "explanation_level": "technical",
        },
    }
    res = client.post("/api/v1/users/onboarding", json=onboard_payload, headers=headers)
    assert res.status_code == 200
    user_data = res.json()
    assert user_data["onboarding_completed"] is True
    assert user_data["role"] == "Data Scientist / ML Engineer"
    assert user_data["experience_level"] == "Advanced"
    assert user_data["primary_goal"] == ["Forecast future metrics", "Automate exploratory data analysis"]
    assert user_data["preferences"]["language"] == "es"
    assert user_data["preferences"]["explanation_level"] == "technical"

    # Profile endpoint returns stats and user
    profile_res = client.get("/api/v1/users/profile", headers=headers)
    assert profile_res.status_code == 200
    pdata = profile_res.json()
    assert pdata["user"]["role"] == "Data Scientist / ML Engineer"
    assert "stats" in pdata


def test_multi_tenant_data_isolation():
    uid_a = uuid.uuid4().hex[:8]
    email_a = f"usera_{uid_a}@analyticx.ai"
    pwd_a = "PasswordA123!"
    reg_a = client.post("/api/v1/auth/register", json={"email": email_a, "password": pwd_a})
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    uid_b = uuid.uuid4().hex[:8]
    email_b = f"userb_{uid_b}@analyticx.ai"
    pwd_b = "PasswordB123!"
    reg_b = client.post("/api/v1/auth/register", json={"email": email_b, "password": pwd_b})
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A uploads a private CSV
    csv_content = b"client_id,secret_revenue\n1,50000\n2,85000\n"
    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": (f"user_a_secret_{uid_a}.csv", io.BytesIO(csv_content), "text/csv")},
        headers=headers_a,
    )
    assert upload_res.status_code == 200
    dataset_a_id = upload_res.json()["id"]

    # User A can access dataset A
    get_a = client.get(f"/api/v1/datasets/{dataset_a_id}", headers=headers_a)
    assert get_a.status_code == 200

    # User B CANNOT access User A's private dataset (returns 403 Forbidden!)
    get_b = client.get(f"/api/v1/datasets/{dataset_a_id}", headers=headers_b)
    assert get_b.status_code == 403
    assert "permission" in get_b.json()["detail"].lower() or "denied" in get_b.json()["detail"].lower()

    # User B cannot delete User A's dataset
    del_b = client.delete(f"/api/v1/datasets/{dataset_a_id}", headers=headers_b)
    assert del_b.status_code == 403

    # User A can safely delete their own dataset
    del_a = client.delete(f"/api/v1/datasets/{dataset_a_id}", headers=headers_a)
    assert del_a.status_code == 200
    assert del_a.json()["deleted"] is True


def test_activity_stream_and_notifications():
    uid = uuid.uuid4().hex[:8]
    email = f"activity_{uid}@analyticx.ai"
    pwd = "PasswordAct123!"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch recent activities
    act_res = client.get("/api/v1/users/activity", headers=headers)
    assert act_res.status_code == 200
    acts = act_res.json()
    assert len(acts) >= 1
    assert any(a["action_type"] == "account_created" for a in acts)

    # Fetch notifications
    notif_res = client.get("/api/v1/users/notifications", headers=headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert notifs["unread_count"] >= 1
    assert len(notifs["items"]) >= 1

    # Mark all read
    read_all = client.post("/api/v1/users/notifications/read-all", headers=headers)
    assert read_all.status_code == 200

    notif_res2 = client.get("/api/v1/users/notifications", headers=headers)
    assert notif_res2.json()["unread_count"] == 0


def test_user_data_export():
    uid = uuid.uuid4().hex[:8]
    email = f"export_{uid}@analyticx.ai"
    pwd = "PasswordExp123!"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "full_name": "Export Guy"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/users/export-data", headers=headers)
    assert res.status_code == 200
    export_json = res.json()
    assert "user_profile" in export_json
    assert export_json["user_profile"]["email"] == email
    assert "activity_history" in export_json
    assert "datasets" in export_json


def test_google_oauth_workflow(monkeypatch):
    from unittest.mock import patch
    from app.core.config import settings

    # Ensure client_id is set for verification
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret")

    # 1. Config check
    cfg = client.get("/api/v1/auth/oauth/google/config")
    assert cfg.status_code == 200
    cfg_data = cfg.json()
    assert cfg_data["configured"] is True
    assert cfg_data["client_id"] == "test-client-id.apps.googleusercontent.com"

    # 2. Rejection of unauthenticated client-supplied email without token
    rej = client.post("/api/v1/auth/oauth/google/verify", json={"email": "hacker@example.com"})
    assert rej.status_code == 400
    assert "credential" in rej.json()["detail"].lower()

    # 3. Real Google ID Token Verification with sub mapping & auto-verification
    uid = uuid.uuid4().hex[:8]
    google_sub = f"sub_{uid}"
    google_email = f"google_user_{uid}@gmail.com"
    google_name = "Google Verified Analyst"

    mock_id_info = {
        "iss": "https://accounts.google.com",
        "sub": google_sub,
        "email": google_email,
        "email_verified": True,
        "name": google_name,
        "picture": "https://lh3.googleusercontent.com/test",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        res = client.post(
            "/api/v1/auth/oauth/google/verify",
            json={"credential": "mock.google.id.token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        user_info = data["user"]
        assert user_info["email"] == google_email
        assert user_info["full_name"] == google_name
        assert user_info["is_verified"] is True

        token = data["access_token"]
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == google_email

        # 4. Subsequent Google Login with same sub logs in directly
        res_repeat = client.post(
            "/api/v1/auth/oauth/google/verify",
            json={"credential": "mock.google.id.token"},
        )
        assert res_repeat.status_code == 200
        assert res_repeat.json()["user"]["email"] == google_email
