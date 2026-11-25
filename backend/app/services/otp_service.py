from datetime import datetime, timedelta
import hashlib
import hmac
import logging
import secrets
from typing import Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import EmailOtpChallenge

logger = logging.getLogger(__name__)


class OTPValidationError(Exception):
    """Raised when submitted code does not match or challenge is invalid."""
    pass


class OTPExpiredError(Exception):
    """Raised when challenge has passed its expiry window."""
    pass


class OTPMaxAttemptsError(Exception):
    """Raised when user exceeds maximum allowed verification attempts."""
    pass


class OTPCooldownError(Exception):
    """Raised when user requests a new code before the resend cooldown expires."""
    def __init__(self, message: str, seconds_left: int):
        super().__init__(message)
        self.seconds_left = seconds_left


def generate_secure_otp() -> str:
    """Generates a cryptographically secure 6-digit numeric OTP code."""
    # secrets.randbelow ensures uniform distribution [0, 999999]
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str, challenge_id: str) -> str:
    """
    Computes keyed HMAC-SHA256 hash using the server secret key
    combined with the unique per-challenge identifier.
    Plaintext OTP is never stored on disk or database.
    """
    secret = getattr(settings, "SECRET_KEY", None) or getattr(settings, "JWT_SECRET", "analyticx-default-secret-key")
    key = (secret + ":" + challenge_id).encode("utf-8")
    return hmac.new(key, code.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def verify_otp_hash(code: str, stored_hash: str, challenge_id: str) -> bool:
    """Constant-time verification of submitted OTP."""
    expected_hash = hash_otp(code, challenge_id)
    return hmac.compare_digest(expected_hash, stored_hash)


def mask_email(email: str) -> str:
    """Masks email address for secure UI display (e.g. j***e@example.com)."""
    if not email or "@" not in email:
        return "***"
    parts = email.split("@")
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "***"
    else:
        masked_user = user[0] + "***" + user[-1]
    return f"{masked_user}@{domain}"


def create_otp_challenge(
    db: Session,
    email: str,
    purpose: str = "login",
    ip_address: Optional[str] = None,
) -> Tuple[EmailOtpChallenge, str]:
    """
    Creates a new challenge and secure 6-digit code.
    Enforces resend cooldowns and invalidates previous active challenges for the email.
    """
    norm_email = email.strip().lower()
    now = datetime.utcnow()

    # 1. Check active cooldown
    recent_active = (
        db.query(EmailOtpChallenge)
        .filter(
            EmailOtpChallenge.email == norm_email,
            EmailOtpChallenge.consumed_at.is_(None),
            EmailOtpChallenge.cooldown_until > now,
        )
        .order_by(EmailOtpChallenge.created_at.desc())
        .first()
    )
    if recent_active:
        seconds_left = max(1, int((recent_active.cooldown_until - now).total_seconds()))
        raise OTPCooldownError(
            f"Please wait {seconds_left} seconds before requesting another verification code.",
            seconds_left=seconds_left,
        )

    # 2. Invalidate previous active unconsumed challenges for this email
    db.query(EmailOtpChallenge).filter(
        EmailOtpChallenge.email == norm_email,
        EmailOtpChallenge.consumed_at.is_(None),
    ).update({"consumed_at": now, "status": "expired"})
    db.commit()

    # 3. Generate cryptographic OTP and challenge
    plain_otp = generate_secure_otp()
    challenge_id = uuid.uuid4().hex
    hashed = hash_otp(plain_otp, challenge_id)
    expiry_minutes = settings.resolved_otp_expiry_minutes

    challenge = EmailOtpChallenge(
        email=norm_email,
        challenge_id=challenge_id,
        hashed_code=hashed,
        purpose=purpose,
        attempts=0,
        max_attempts=settings.OTP_MAX_ATTEMPTS,
        status="pending",
        ip_address=ip_address,
        expires_at=now + timedelta(minutes=expiry_minutes),
        cooldown_until=now + timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS),
        created_at=now,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    return challenge, plain_otp


def verify_otp_challenge(
    db: Session,
    email: str,
    code: str,
    challenge_id: Optional[str] = None,
) -> EmailOtpChallenge:
    """
    Verifies the submitted OTP against the challenge.
    Enforces expiration, attempt bounds, single-use consumption, and constant-time check.
    """
    norm_email = email.strip().lower()
    clean_code = code.strip()
    now = datetime.utcnow()

    query = db.query(EmailOtpChallenge).filter(EmailOtpChallenge.email == norm_email)
    if challenge_id and challenge_id.strip():
        query = query.filter(EmailOtpChallenge.challenge_id == challenge_id.strip())
    else:
        query = query.filter(EmailOtpChallenge.consumed_at.is_(None)).order_by(
            EmailOtpChallenge.created_at.desc()
        )

    challenge = query.first()

    if not challenge:
        raise OTPValidationError("Invalid or expired verification session.")

    if challenge.consumed_at is not None:
        raise OTPValidationError("This verification code has already been used.")

    if challenge.expires_at < now:
        challenge.status = "expired"
        db.commit()
        raise OTPExpiredError("This verification code has expired. Please request a new code.")

    if challenge.attempts >= challenge.max_attempts:
        challenge.status = "exhausted"
        db.commit()
        raise OTPMaxAttemptsError(
            "Maximum verification attempts exceeded. This code is invalidated. Please request a new code."
        )

    # Verify cryptographic hash
    if not verify_otp_hash(clean_code, challenge.hashed_code, challenge.challenge_id):
        challenge.attempts += 1
        remaining = challenge.max_attempts - challenge.attempts
        if remaining <= 0:
            challenge.status = "exhausted"
            db.commit()
            raise OTPMaxAttemptsError(
                "Incorrect code. Maximum verification attempts exceeded. Please request a new code."
            )
        db.commit()
        raise OTPValidationError(f"Invalid verification code. {remaining} attempt(s) remaining.")

    # Mark consumed atomically
    challenge.consumed_at = now
    challenge.status = "consumed"
    db.commit()
    db.refresh(challenge)
    return challenge
