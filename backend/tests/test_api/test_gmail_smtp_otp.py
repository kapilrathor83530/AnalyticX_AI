from datetime import datetime, timedelta
import re
import smtplib
from unittest.mock import MagicMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database import SessionLocal
from app.main import app
from app.models.user import EmailOtpChallenge, User
from app.services.email_service import email_service
from app.services.otp_service import mask_email

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Sets test provider for email delivery and resets sent emails."""
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "test")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_SECURE", False)
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASS", "")
    email_service.clear_sent_emails()
    yield
    email_service.clear_sent_emails()


# ===========================================================================
# 1. GMAIL SMTP CONNECTION DIAGNOSTICS TESTS
# ===========================================================================


def test_smtp_test_connection_unconfigured():
    """Returns safe diagnostic notice when credentials are not yet set."""
    res = client.post("/api/v1/auth/smtp/test-connection")
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is False
    assert data["sender_configured"] is False
    assert "backend/.env" in data["message"]


def test_smtp_test_connection_success_mocked(monkeypatch):
    """Verifies SMTP handshake on port 587 with STARTTLS and login."""
    monkeypatch.setattr(settings, "SMTP_USER", "analyst@gmail.com")
    monkeypatch.setattr(settings, "SMTP_PASS", "abcd-efgh-ijkl-mnop")

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_instance = MagicMock()
        mock_smtp_cls.return_value = mock_instance

        res = client.post("/api/v1/auth/smtp/test-connection")
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is True
        assert data["sender_configured"] is True
        assert data["tls_active"] is True
        assert "ana***@gmail.com" in data["message"]

        mock_instance.ehlo.assert_called()
        mock_instance.starttls.assert_called_once()
        mock_instance.login.assert_called_once_with("analyst@gmail.com", "abcd-efgh-ijkl-mnop")
        mock_instance.quit.assert_called_once()


def test_smtp_test_connection_auth_failure_mocked(monkeypatch):
    """Verifies safe error reporting on Google SMTP auth failure without password leakage."""
    monkeypatch.setattr(settings, "SMTP_USER", "analyst@gmail.com")
    monkeypatch.setattr(settings, "SMTP_PASS", "invalid_password")

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_instance = MagicMock()
        mock_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
        mock_smtp_cls.return_value = mock_instance

        res = client.post("/api/v1/auth/smtp/test-connection")
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is False
        assert data["sender_configured"] is True
        assert "App Password" in data["message"]
        # Ensure password is not leaked in response
        assert "invalid_password" not in str(data)


# ===========================================================================
# 2. SIGNUP & EMAIL VERIFICATION VIA GMAIL OTP LIFECYCLE
# ===========================================================================


def test_signup_and_verify_otp_flow():
    """
    Complete lifecycle:
    1. Register user via /auth/signup.
    2. Verification code is delivered via branded email.
    3. Verify OTP code via /auth/verify-otp.
    4. Account is activated and email_verified=True.
    5. Access token accesses /auth/me.
    """
    uid = uuid.uuid4().hex[:8]
    email = f"signup_{uid}@gmail.com"
    full_name = f"Analyst {uid}"
    password = f"SecurePass123!{uid}"

    # 1. Signup
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": full_name,
            "password": password,
        },
    )
    assert signup_res.status_code == 201
    signup_data = signup_res.json()
    assert signup_data["success"] is True
    challenge_id = signup_data["challenge_id"]
    assert "masked_email" in signup_data

    # Verify email was dispatched
    sent = email_service.get_sent_emails()
    assert len(sent) == 1
    assert sent[0]["to"] == email
    match = re.search(r"\b(\d{6})\b", sent[0]["text"])
    assert match is not None
    otp_code = match.group(1)

    # Verify user exists in DB but is unverified
    db = SessionLocal()
    try:
        user_in_db = db.query(User).filter(User.email == email).first()
        assert user_in_db is not None
        assert user_in_db.email_verified is False
    finally:
        db.close()

    # 2. Submit wrong OTP -> 400
    wrong_res = client.post(
        "/api/v1/auth/verify-otp",
        json={
            "challenge_id": challenge_id,
            "email": email,
            "code": "000000" if otp_code != "000000" else "111111",
        },
    )
    assert wrong_res.status_code == 400
    assert "Invalid verification code" in wrong_res.json()["detail"]

    # 3. Submit valid OTP -> 200
    verify_res = client.post(
        "/api/v1/auth/verify-otp",
        json={
            "challenge_id": challenge_id,
            "email": email,
            "code": otp_code,
        },
    )
    assert verify_res.status_code == 200
    token_data = verify_res.json()
    assert "access_token" in token_data
    assert token_data["user"]["email"] == email
    assert token_data["user"]["email_verified"] is True
    assert token_data["user"]["is_verified"] is True
    access_token = token_data["access_token"]

    # 4. Access /auth/me using token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == email
    assert me_data["full_name"] == full_name
    assert me_data["email_verified"] is True


def test_api_prefix_alias_support():
    """Verifies that both /api/v1/auth/... and /api/auth/... work identically."""
    uid = uuid.uuid4().hex[:8]
    email = f"alias_{uid}@example.com"

    # Request via /api/auth/request-otp
    req_res = client.post("/api/auth/request-otp", json={"email": email, "purpose": "login"})
    assert req_res.status_code == 200
    data = req_res.json()
    assert data["success"] is True
    challenge_id = data["challenge_id"]

    sent = email_service.get_sent_emails()
    match = re.search(r"\b(\d{6})\b", sent[-1]["text"])
    assert match is not None
    otp_code = match.group(1)

    # Verify via /api/auth/verify-otp
    ver_res = client.post(
        "/api/auth/verify-otp",
        json={"challenge_id": challenge_id, "email": email, "code": otp_code},
    )
    assert ver_res.status_code == 200
    assert "access_token" in ver_res.json()


# ===========================================================================
# 3. COOLDOWN & RESEND BEHAVIOR
# ===========================================================================


def test_otp_resend_cooldown_enforcement():
    """Requests OTP, attempts immediate resend, gets 429, cools down, succeeds."""
    uid = uuid.uuid4().hex[:8]
    email = f"cooldown_{uid}@gmail.com"

    # First request
    res1 = client.post("/api/v1/auth/request-otp", json={"email": email})
    assert res1.status_code == 200

    # Immediate second request triggers 429 cooldown
    res2 = client.post("/api/v1/auth/resend-otp", json={"email": email})
    assert res2.status_code == 429
    assert "Retry-After" in res2.headers
    assert "Please wait" in res2.json()["detail"]

    # Fast forward cooldown in DB
    db = SessionLocal()
    try:
        db.query(EmailOtpChallenge).filter(EmailOtpChallenge.email == email).update(
            {"cooldown_until": datetime.utcnow() - timedelta(seconds=1)}
        )
        db.commit()
    finally:
        db.close()

    # Resend after cooldown succeeds
    res3 = client.post("/api/v1/auth/resend-otp", json={"email": email})
    assert res3.status_code == 200
    assert res3.json()["success"] is True


# ===========================================================================
# 4. MAX ATTEMPTS & SINGLE-USE REPLAY ATTACK PREVENTION
# ===========================================================================


def test_otp_max_attempts_lockout():
    """Enforces account protection by exhausting code after 5 bad attempts."""
    uid = uuid.uuid4().hex[:8]
    email = f"lockout_{uid}@gmail.com"

    req_res = client.post("/api/v1/auth/request-otp", json={"email": email})
    assert req_res.status_code == 200
    challenge_id = req_res.json()["challenge_id"]

    # 4 invalid attempts return 400 with remaining count
    for i in range(1, 5):
        bad_res = client.post(
            "/api/v1/auth/verify-otp",
            json={"challenge_id": challenge_id, "email": email, "code": "000000"},
        )
        assert bad_res.status_code == 400
        assert f"{5 - i} attempt(s) remaining" in bad_res.json()["detail"]

    # 5th invalid attempt locks out challenge
    lockout_res = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": challenge_id, "email": email, "code": "000000"},
    )
    assert lockout_res.status_code == 429
    assert "Maximum verification attempts exceeded" in lockout_res.json()["detail"]


def test_otp_single_use_consumption():
    """Prevents replaying a previously consumed OTP."""
    uid = uuid.uuid4().hex[:8]
    email = f"singleuse_{uid}@gmail.com"

    req_res = client.post("/api/v1/auth/request-otp", json={"email": email})
    challenge_id = req_res.json()["challenge_id"]

    sent = email_service.get_sent_emails()
    match = re.search(r"\b(\d{6})\b", sent[-1]["text"])
    otp_code = match.group(1)

    # First verification succeeds
    res1 = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": challenge_id, "email": email, "code": otp_code},
    )
    assert res1.status_code == 200

    # Second verification with same code fails
    res2 = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": challenge_id, "email": email, "code": otp_code},
    )
    assert res2.status_code == 400
    assert "already been used" in res2.json()["detail"]


# ===========================================================================
# 5. USER PERSISTENCE & DATA ISOLATION
# ===========================================================================


def test_user_session_isolation_and_persistence():
    """Verifies that multiple users maintain completely isolated persistent identities."""
    uid1 = uuid.uuid4().hex[:8]
    uid2 = uuid.uuid4().hex[:8]
    email1 = f"user1_{uid1}@gmail.com"
    email2 = f"user2_{uid2}@gmail.com"

    # User 1 sign up & verify
    client.post("/api/v1/auth/signup", json={"email": email1, "full_name": "Alice Analyst"})
    otp1 = re.search(r"\b(\d{6})\b", email_service.get_sent_emails()[-1]["text"]).group(1)
    tok1 = client.post("/api/v1/auth/verify-otp", json={"email": email1, "code": otp1}).json()["access_token"]

    # User 2 sign up & verify
    client.post("/api/v1/auth/signup", json={"email": email2, "full_name": "Bob DataScientist"})
    otp2 = re.search(r"\b(\d{6})\b", email_service.get_sent_emails()[-1]["text"]).group(1)
    tok2 = client.post("/api/v1/auth/verify-otp", json={"email": email2, "code": otp2}).json()["access_token"]

    # Verify User 1 cannot see User 2's identity
    u1_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok1}"}).json()
    u2_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok2}"}).json()

    assert u1_me["email"] == email1
    assert u1_me["full_name"] == "Alice Analyst"
    assert u2_me["email"] == email2
    assert u2_me["full_name"] == "Bob DataScientist"
    assert u1_me["id"] != u2_me["id"]


# ===========================================================================
# 6. NEGATIVE TESTS: LOGIN BYPASS PREVENTION & SMTP REALITY ENFORCEMENT
# ===========================================================================


def test_unconfigured_smtp_raises_error_not_fake_success(monkeypatch):
    """
    Proves that when Gmail SMTP is not configured in .env, OTP request fails
    with clear error response rather than silently returning fake success.
    """
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASS", "")

    res = client.post("/api/v1/auth/request-otp", json={"email": "nobody@example.com"})
    assert res.status_code in (502, 503)
    data = res.json()
    assert "detail" in data
    assert "Gmail SMTP credentials are not configured" in data["detail"]
    assert "backend/.env" in data["detail"]


def test_otp_request_never_returns_session_tokens_or_logs_user_in():
    """
    Proves that requesting an OTP challenge NEVER grants an authenticated session.
    No access_token or refresh_token is issued until valid OTP code is verified.
    """
    uid = uuid.uuid4().hex[:8]
    email = f"no_bypass_{uid}@example.com"

    res = client.post("/api/v1/auth/request-otp", json={"email": email})
    assert res.status_code == 200
    data = res.json()

    # Must contain challenge info but ZERO tokens
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "token" not in data
    assert data["success"] is True
    assert "challenge_id" in data

    # Attempting to access protected endpoints without token must return 401
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 401


def test_signup_requires_otp_verification_for_session():
    """
    Proves that submitting signup requests an OTP challenge but does NOT log the user in.
    Session tokens are only issued upon successful server-side OTP validation.
    """
    uid = uuid.uuid4().hex[:8]
    email = f"signup_otp_{uid}@example.com"
    pwd = "StrongSecurePassword123!"

    # 1. User signs up
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pwd, "full_name": "OTP User"},
    )
    assert signup_res.status_code == 201
    signup_data = signup_res.json()
    assert "access_token" not in signup_data
    assert "refresh_token" not in signup_data
    assert signup_data["success"] is True
    assert "challenge_id" in signup_data

    # 2. Before OTP verification, unauthenticated access to /auth/me returns 401
    assert client.get("/api/v1/auth/me").status_code == 401

    # 3. Retrieve OTP from email service and verify
    sent = email_service.get_sent_emails()
    match = re.search(r"\b(\d{6})\b", sent[-1]["text"])
    assert match is not None
    otp_code = match.group(1)

    # 4. Valid OTP verification grants authenticated session
    verify_res = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": signup_data["challenge_id"], "email": email, "code": otp_code},
    )
    assert verify_res.status_code == 200
    token = verify_res.json()["access_token"]
    assert token

    # 5. Token now successfully accesses /auth/me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

