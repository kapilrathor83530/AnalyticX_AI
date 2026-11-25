from datetime import datetime, timedelta
from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.user import EmailOtpChallenge, User
from app.services.email_service import EmailDeliveryError, email_service
from app.services.otp_service import mask_email, verify_otp_hash

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_email_test_mode(monkeypatch):
    """Ensures email service captures emails in memory and clears queue between tests."""
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "test")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-google-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-google-secret")
    email_service.clear_sent_emails()
    yield
    email_service.clear_sent_emails()


# ===========================================================================
# TEST GROUP A — GOOGLE AUTHENTICATION & OPENID CONNECT
# ===========================================================================


def test_google_login_valid_token():
    """Tests successful Google registration and login with a cryptographically verified ID token."""
    uid = uuid.uuid4().hex[:8]
    sub = f"google_sub_{uid}"
    email = f"analyst_{uid}@gmail.com"
    name = "Dr. Analyst"

    mock_id_info = {
        "iss": "https://accounts.google.com",
        "aud": settings.GOOGLE_CLIENT_ID,
        "sub": sub,
        "email": email,
        "email_verified": True,
        "name": name,
        "picture": "https://lh3.googleusercontent.com/avatar.png",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        # 1. First-time registration with Google
        res = client.post("/api/v1/auth/oauth/google/verify", json={"credential": "valid.google.jwt"})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == email
        assert data["user"]["full_name"] == name
        assert data["user"]["is_verified"] is True

        # 2. Re-login with same Google token maps to same user
        res_repeat = client.post("/api/v1/auth/oauth/google/verify", json={"credential": "valid.google.jwt"})
        assert res_repeat.status_code == 200
        assert res_repeat.json()["user"]["id"] == data["user"]["id"]


def test_google_login_rejection_without_token():
    """Verify that Google authentication is NOT simulated by accepting client-supplied email without a token."""
    res = client.post("/api/v1/auth/oauth/google/verify", json={"email": "attacker@fake.com"})
    assert res.status_code == 400
    assert "credential" in res.json()["detail"].lower()


def test_google_login_invalid_signature():
    """Rejects Google ID token when signature validation fails."""
    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Token signature is invalid")):
        res = client.post("/api/v1/auth/oauth/google/verify", json={"credential": "tampered.jwt.token"})
        assert res.status_code == 401
        assert "signature is invalid" in res.json()["detail"].lower()


def test_google_login_unverified_email():
    """Rejects Google ID token if Google has not marked the email verified."""
    mock_id_info = {
        "iss": "https://accounts.google.com",
        "aud": settings.GOOGLE_CLIENT_ID,
        "sub": "sub_unverified_123",
        "email": "unverified@gmail.com",
        "email_verified": False,
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        res = client.post("/api/v1/auth/oauth/google/verify", json={"credential": "unverified.jwt"})
        assert res.status_code == 400
        assert "not verified" in res.json()["detail"].lower()


def test_google_login_missing_config(monkeypatch):
    """When GOOGLE_CLIENT_ID is not configured, returns clear actionable guidance."""
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    res = client.post("/api/v1/auth/oauth/google/verify", json={"credential": "some.token"})
    assert res.status_code == 400
    assert "not configured" in res.json()["detail"].lower()


def test_safe_account_linking_policy():
    """
    If a user already has an account with the same email, require proof of ownership
    (password or OTP) before combining identities.
    """
    uid = uuid.uuid4().hex[:8]
    email = f"existing_{uid}@analyticx.ai"
    pwd = "ExistingPassword123!"

    # 1. User registers with email & password first
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "full_name": "Original User"})
    assert reg.status_code == 201

    # 2. Later, someone attempts to sign in via Google with that same email
    google_sub = f"google_sub_{uid}"
    mock_id_info = {
        "iss": "https://accounts.google.com",
        "aud": settings.GOOGLE_CLIENT_ID,
        "sub": google_sub,
        "email": email,
        "email_verified": True,
        "name": "Google User",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        res = client.post("/api/v1/auth/oauth/google/verify", json={"credential": "some.token"})
        assert res.status_code == 200
        data = res.json()
        assert data.get("account_linking_required") is True
        assert "linking_token" in data
        assert data["email"] == email

        linking_token = data["linking_token"]

        # 3. Incorrect password fails linking
        fail_link = client.post(
            "/api/v1/auth/oauth/google/confirm-link",
            json={"linking_token": linking_token, "password": "WrongPassword999!"},
        )
        assert fail_link.status_code == 401

        # 4. Correct password confirms linking and establishes session
        good_link = client.post(
            "/api/v1/auth/oauth/google/confirm-link",
            json={"linking_token": linking_token, "password": pwd},
        )
        assert good_link.status_code == 200
        link_data = good_link.json()
        assert "access_token" in link_data
        assert link_data["user"]["email"] == email

        # 5. Subsequent Google login now succeeds directly without re-prompting
        direct_login = client.post("/api/v1/auth/oauth/google/verify", json={"credential": "some.token"})
        assert direct_login.status_code == 200
        assert direct_login.json().get("account_linking_required") is not True
        assert "access_token" in direct_login.json()


# ===========================================================================
# TEST GROUP B — EMAIL OTP DELIVERY & VERIFICATION
# ===========================================================================


def test_otp_lifecycle_success():
    """Generates 6-digit OTP, sends branded email, verifies challenge, and logs in."""
    uid = uuid.uuid4().hex[:8]
    email = f"otp_user_{uid}@example.com"

    # 1. Send OTP
    send_res = client.post("/api/v1/auth/otp/send", json={"email": email, "purpose": "login"})
    assert send_res.status_code == 200
    send_data = send_res.json()
    assert send_data["success"] is True
    assert "challenge_id" in send_data
    assert "code" not in send_data  # OTP code MUST NOT be exposed in API response!
    assert "masked_email" in send_data
    challenge_id = send_data["challenge_id"]

    # 2. Check email delivery service captured the email
    sent = email_service.get_sent_emails()
    assert len(sent) == 1
    assert sent[0]["to"] == email
    assert "Verification Code" in sent[0]["subject"]

    # Extract 6-digit OTP from captured email body for testing
    import re
    match = re.search(r"\b(\d{6})\b", sent[0]["text"])
    assert match is not None
    otp_code = match.group(1)

    # 3. Verify OTP
    verify_res = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "email": email, "code": otp_code, "full_name": "OTP User"},
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert "access_token" in verify_data
    assert verify_data["user"]["email"] == email
    assert verify_data["user"]["is_verified"] is True


def test_otp_cooldown_enforcement():
    """Requesting an OTP within the resend cooldown window triggers HTTP 429."""
    uid = uuid.uuid4().hex[:8]
    email = f"cooldown_{uid}@example.com"

    # First send is fine
    res1 = client.post("/api/v1/auth/otp/send", json={"email": email})
    assert res1.status_code == 200

    # Immediate second send must trigger 429 Too Many Requests
    res2 = client.post("/api/v1/auth/otp/send", json={"email": email})
    assert res2.status_code == 429
    assert "wait" in res2.json()["detail"].lower()


def test_otp_invalid_code_and_max_attempts():
    """Incorrect code increments attempts; exceeding max attempts permanently locks the code."""
    uid = uuid.uuid4().hex[:8]
    email = f"attempts_{uid}@example.com"

    res = client.post("/api/v1/auth/otp/send", json={"email": email})
    challenge_id = res.json()["challenge_id"]

    # Attempt 1: wrong code
    v1 = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "email": email, "code": "000000"},
    )
    assert v1.status_code == 400
    assert "attempt(s) remaining" in v1.json()["detail"]

    # Repeatedly submit wrong code until max attempts
    for _ in range(4):
        v = client.post(
            "/api/v1/auth/otp/verify",
            json={"challenge_id": challenge_id, "email": email, "code": "111111"},
        )
    assert v.status_code == 429
    assert "maximum" in v.json()["detail"].lower()


def test_otp_reused_code_prevention():
    """A consumed OTP code cannot be reused."""
    uid = uuid.uuid4().hex[:8]
    email = f"reused_{uid}@example.com"

    res = client.post("/api/v1/auth/otp/send", json={"email": email})
    challenge_id = res.json()["challenge_id"]

    import re
    match = re.search(r"\b(\d{6})\b", email_service.get_sent_emails()[0]["text"])
    otp_code = match.group(1)

    # First verification succeeds
    v1 = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "email": email, "code": otp_code},
    )
    assert v1.status_code == 200

    # Second verification fails
    v2 = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "email": email, "code": otp_code},
    )
    assert v2.status_code == 400
    assert "already been used" in v2.json()["detail"].lower()


def test_otp_email_mismatch():
    """Submitting challenge_id for email A with email B must be rejected."""
    uid_a = uuid.uuid4().hex[:8]
    uid_b = uuid.uuid4().hex[:8]
    email_a = f"a_{uid_a}@example.com"
    email_b = f"b_{uid_b}@example.com"

    res = client.post("/api/v1/auth/otp/send", json={"email": email_a})
    challenge_id = res.json()["challenge_id"]

    v = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "email": email_b, "code": "123456"},
    )
    assert v.status_code == 400
    assert "invalid" in v.json()["detail"].lower()


# ===========================================================================
# TEST GROUP D — SECURITY & PRIVACY
# ===========================================================================


def test_email_masking_utility():
    assert mask_email("kapil@analyticx.ai") == "k***l@analyticx.ai"
    assert mask_email("a@b.com") == "a***@b.com"
    assert mask_email("alexander.smith@gmail.com") == "a***h@gmail.com"


def test_otp_cryptographic_hash():
    from app.services.otp_service import hash_otp, verify_otp_hash
    code = "729401"
    salt = "challenge_salt_123"
    hashed = hash_otp(code, salt)
    assert hashed != code
    assert len(hashed) == 64  # SHA-256 hex string
    assert verify_otp_hash(code, hashed, salt) is True
    assert verify_otp_hash("729402", hashed, salt) is False
