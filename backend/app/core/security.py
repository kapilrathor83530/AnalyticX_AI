from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# pbkdf2_sha256 avoids the bcrypt backend incompatibility present with the
# Python 3.13 runtime while retaining a salted, adaptive password hash.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: Dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def create_refresh_token(subject: str, remember_me: bool = False) -> str:
    # 30 days if remember_me, 7 days otherwise
    days = 30 if remember_me else 7
    return create_access_token(subject, expires_minutes=60 * 24 * days)


def create_password_reset_token(subject: str) -> str:
    return create_access_token(subject, expires_minutes=30)


def decode_password_reset_token(token: str) -> Optional[str]:
    return decode_token(token)


def create_email_verification_token(subject: str) -> str:
    return create_access_token(subject, expires_minutes=60 * 24)  # 24 hours


def decode_email_verification_token(token: str) -> Optional[str]:
    return decode_token(token)


def create_linking_token(
    google_sub: str,
    email: str,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> str:
    """Signs a short-lived token (10 minutes) for safe Google account linking challenges."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload: Dict[str, Any] = {
        "sub": google_sub,
        "email": email.strip().lower(),
        "name": name,
        "avatar_url": avatar_url,
        "type": "google_link",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_linking_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a Google account linking token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "google_link":
            return None
        return payload
    except JWTError:
        return None


def is_google_oauth_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
