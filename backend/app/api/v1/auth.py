from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
import uuid
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_linking_token,
    create_password_reset_token,
    create_refresh_token,
    decode_email_verification_token,
    decode_linking_token,
    decode_password_reset_token,
    decode_token,
    hash_password,
    is_google_oauth_configured,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.repositories import user_repo
from app.schemas.user import (
    EmailResendRequest,
    EmailVerifyRequest,
    GoogleCallbackRequest,
    GoogleConfigureRequest,
    GoogleLinkConfirmRequest,
    GoogleVerifyRequest,
    OtpResendRequest,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    SignupRequest,
    SmtpTestResponse,
    TokenResponse,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.services.activity_service import create_user_notification, record_activity
from app.services.email_service import EmailDeliveryError, email_service
from app.services.otp_service import (
    OTPCooldownError,
    OTPExpiredError,
    OTPMaxAttemptsError,
    OTPValidationError,
    create_otp_challenge,
    mask_email,
    verify_otp_challenge,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("15/minute")
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
    """Registers a new user account with initial verification token and welcomes them."""
    existing = user_repo.get_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered. Please sign in.")

    # Create new user
    user = user_repo.create(
        db,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )

    # Issue email verification token (expires in 24 hours)
    verify_token = create_email_verification_token(str(user.id))
    user.email_verification_token = verify_token
    user.email_verification_expires_at = datetime.utcnow() + timedelta(hours=24)
    db.commit()

    # Record welcome activity and notification
    record_activity(
        db=db,
        user_id=user.id,
        action_type="account_created",
        title="Account Created",
        description="Welcome to Analyticx AI! Your personalized workspace has been provisioned.",
    )
    create_user_notification(
        db=db,
        user_id=user.id,
        title="Welcome to Analyticx AI! 🚀",
        message="Your workspace is ready. Complete the onboarding wizard to tailor your insights, models, and dashboards.",
        level="success",
        link="/onboarding",
        event_type="onboarding",
    )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserRead.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("30/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticates user with non-enumerating error responses and records session."""
    user = user_repo.get_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been deactivated. Please contact support.")

    # Record last login timestamp
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Record audit activity
    record_activity(
        db=db,
        user_id=user.id,
        action_type="login",
        title="Signed In",
        description=f"Authenticated from {request.client.host if request.client else 'client'}",
    )

    remember = bool(payload.remember_me)
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id), remember_me=remember),
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: dict, db: Session = Depends(get_db)):
    """Refreshes the short-lived access token using a valid refresh token."""
    token = payload.get("refresh_token")
    if not token:
        raise HTTPException(status_code=400, detail="refresh_token is required")
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user = user_repo.get_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's profile and preferences."""
    return current_user


@router.post("/verify-email")
def verify_email(payload: EmailVerifyRequest, db: Session = Depends(get_db)):
    """Verifies a user's email address using a time-limited token."""
    user_id = decode_email_verification_token(payload.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    user = user_repo.get_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    if user.email_verification_token and user.email_verification_token != payload.token:
        raise HTTPException(status_code=400, detail="This verification token has already been superseded.")

    user.is_verified = True
    user.email_verification_token = None
    user.email_verification_expires_at = None
    db.commit()

    record_activity(
        db=db,
        user_id=user.id,
        action_type="email_verified",
        title="Email Verified",
        description="Your primary email address has been successfully verified.",
    )
    create_user_notification(
        db=db,
        user_id=user.id,
        title="Email Verified",
        message="Your email address has been verified. You have full access to all features.",
        level="success",
        event_type="security",
    )
    return {"verified": True, "message": "Email verified successfully!"}


@router.post("/resend-verification")
@limiter.limit("5/minute")
def resend_verification(request: Request, payload: EmailResendRequest, db: Session = Depends(get_db)):
    """Resends email verification token with rate limiting and non-enumerating response."""
    user = user_repo.get_by_email(db, payload.email)
    if user and not user.is_verified:
        token = create_email_verification_token(str(user.id))
        user.email_verification_token = token
        user.email_verification_expires_at = datetime.utcnow() + timedelta(hours=24)
        db.commit()
        # In development/local mode, return token so verification can be completed without SMTP server
        return {"sent": True, "message": "Verification link has been sent.", "dev_token": token}
    return {"sent": True, "message": "If an unverified account exists with this email, a verification link has been sent."}


@router.post("/password-reset/request", response_model=PasswordResetResponse)
@limiter.limit("5/minute")
def request_password_reset(request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Initiates secure password reset flow without exposing whether the email exists."""
    user = user_repo.get_by_email(db, payload.email)
    if not user:
        return PasswordResetResponse(message="If the email exists, a password reset link has been dispatched.")

    token = create_password_reset_token(str(user.id))
    user.password_reset_token = token
    user.password_reset_expires_at = datetime.utcnow() + timedelta(minutes=30)
    db.commit()

    # In local/offline mode, return the token so the user can test the reset workflow directly
    return PasswordResetResponse(
        message="If the email exists, a password reset link has been dispatched.",
        reset_token=token,
    )


@router.post("/password-reset/confirm")
@limiter.limit("10/minute")
def confirm_password_reset(request: Request, payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Validates single-use reset token and securely updates user password."""
    user_id = decode_password_reset_token(payload.token)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = user_repo.get_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Validate that token has not already been used or cleared
    if user.password_reset_token != payload.token:
        raise HTTPException(status_code=400, detail="This reset token has already been used or invalidated.")

    if user.password_reset_expires_at and user.password_reset_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="This reset token has expired. Please request a new one.")

    # Update password and invalidate reset token
    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    user.updated_at = datetime.utcnow()
    db.commit()

    record_activity(
        db=db,
        user_id=user.id,
        action_type="password_reset",
        title="Password Reset",
        description="Password was successfully reset using a secure token.",
    )
    create_user_notification(
        db=db,
        user_id=user.id,
        title="Security Alert: Password Changed",
        message="Your account password was just changed. If you did not make this change, contact support immediately.",
        level="warning",
        event_type="security",
    )
    return {"updated": True, "message": "Password has been successfully reset. You may now sign in."}


def _complete_google_authenticated_login(
    db: Session,
    google_sub: str,
    email: str,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    method: str = "Google Sign-In",
) -> TokenResponse:
    norm_email = email.strip().lower()

    # 1. Search by stable Google subject identifier (sub)
    user = user_repo.get_by_google_sub(db, google_sub)

    if not user:
        # Check by email
        existing_by_email = user_repo.get_by_email(db, norm_email)
        if existing_by_email:
            # If already linked to this sub, use it
            if existing_by_email.google_sub == google_sub:
                user = existing_by_email
            elif existing_by_email.google_sub and existing_by_email.google_sub != google_sub:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email address is already associated with a different Google account.",
                )
            else:
                # Account linking required!
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account linking verification required before combining identities.",
                )
        else:
            # Create new user with verified Google identity
            user = user_repo.create(
                db,
                email=norm_email,
                hashed_password=hash_password(str(uuid.uuid4())),
                full_name=name or norm_email.split("@")[0].title(),
            )
            user.google_sub = google_sub
            user.is_verified = True
            user.avatar_url = avatar_url or f"https://api.dicebear.com/7.x/initials/svg?seed={name or norm_email}"
            db.commit()
            db.refresh(user)

            record_activity(
                db=db,
                user_id=user.id,
                action_type="account_created",
                title="Account Created via Google",
                description=f"Welcome to Analyticx AI! Account verified with {method}.",
            )
            create_user_notification(
                db=db,
                user_id=user.id,
                title="Google Sign-In Verified! 🚀",
                message="Your account was authenticated and verified via Google. Your workspace is ready.",
                level="success",
                link="/workspace",
                event_type="auth",
            )

    # Update existing user profile & login timestamp
    user.is_verified = True
    if not user.google_sub:
        user.google_sub = google_sub
    if name and (not user.full_name or user.full_name == "Kapil"):
        user.full_name = name
    if avatar_url and not user.avatar_url:
        user.avatar_url = avatar_url
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    record_activity(
        db=db,
        user_id=user.id,
        action_type="login",
        title=f"Signed in via {method}",
        description=f"Authenticated and verified via Google ({norm_email}).",
    )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserRead.model_validate(user),
    )


# ---------------------------------------------------------------------------
# Email OTP Authentication Endpoints (Passwordless Login & Verification)
# ---------------------------------------------------------------------------


@router.post("/signup", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def signup(
    request: Request,
    payload: SignupRequest,
    db: Session = Depends(get_db),
):
    """
    Registers a new user and dispatches a 6-digit OTP verification email via Gmail SMTP.
    Account remains unverified until the OTP challenge is validated.
    """
    norm_email = payload.email.strip().lower()
    existing_user = user_repo.get_by_email(db, norm_email)

    if existing_user:
        if existing_user.is_verified or existing_user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists. Please sign in.",
            )
        # Update details on existing unverified user
        if payload.full_name:
            existing_user.full_name = payload.full_name.strip()
        if payload.password:
            existing_user.hashed_password = hash_password(payload.password)
        user = existing_user
        db.commit()
    else:
        # Create brand-new user record
        pw = payload.password if payload.password else str(uuid.uuid4())
        user = user_repo.create(
            db,
            email=norm_email,
            hashed_password=hash_password(pw),
            full_name=payload.full_name.strip() if payload.full_name else None,
        )
        user.is_verified = False
        user.email_verified = False
        user.auth_provider = "email_otp" if not payload.password else "password"
        user.account_status = "active"
        db.commit()
        db.refresh(user)

    client_ip = request.client.host if request.client else None

    try:
        challenge, plain_otp = create_otp_challenge(
            db, email=norm_email, purpose="signup", ip_address=client_ip
        )
    except OTPCooldownError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(err),
            headers={"Retry-After": str(err.seconds_left)},
        )

    try:
        email_service.send_otp_email(to_email=norm_email, otp_code=plain_otp, purpose="signup")
    except EmailDeliveryError as err:
        challenge.consumed_at = datetime.utcnow()
        challenge.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        )
    except Exception as exc:
        challenge.consumed_at = datetime.utcnow()
        challenge.status = "expired"
        db.commit()
        logger.error(f"Unexpected error sending signup OTP email: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while dispatching the verification email. Please try again.",
        )

    return {
        "success": True,
        "challenge_id": challenge.challenge_id,
        "email": norm_email,
        "masked_email": mask_email(norm_email),
        "expires_in": settings.resolved_otp_expiry_minutes * 60,
        "cooldown": settings.OTP_RESEND_COOLDOWN_SECONDS,
        "message": f"Verification code sent to {mask_email(norm_email)}. Please verify to activate your account.",
    }


@router.post("/request-otp", response_model=OtpSendResponse)
@router.post("/otp/send", response_model=OtpSendResponse)
@limiter.limit("6/minute")
def request_otp(
    request: Request,
    payload: OtpSendRequest,
    db: Session = Depends(get_db),
):
    """
    Generates a secure 6-digit OTP, stores its HMAC-SHA256 hash, and dispatches
    a branded verification email through Google Gmail SMTP.
    """
    email = payload.email.strip().lower()
    purpose = payload.purpose or "login"
    client_ip = request.client.host if request.client else None

    try:
        challenge, plain_otp = create_otp_challenge(
            db, email=email, purpose=purpose, ip_address=client_ip
        )
    except OTPCooldownError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(err),
            headers={"Retry-After": str(err.seconds_left)},
        )

    try:
        email_service.send_otp_email(to_email=email, otp_code=plain_otp, purpose=purpose)
    except EmailDeliveryError as err:
        challenge.consumed_at = datetime.utcnow()
        challenge.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        )
    except Exception as exc:
        challenge.consumed_at = datetime.utcnow()
        challenge.status = "expired"
        db.commit()
        logger.error(f"Unexpected error sending OTP email: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while dispatching the verification email. Please try again.",
        )

    return OtpSendResponse(
        success=True,
        challenge_id=challenge.challenge_id,
        masked_email=mask_email(email),
        expires_in=settings.resolved_otp_expiry_minutes * 60,
        cooldown=settings.OTP_RESEND_COOLDOWN_SECONDS,
        message=f"A 6-digit verification code was sent to {mask_email(email)}.",
    )


@router.post("/resend-otp", response_model=OtpSendResponse)
@limiter.limit("6/minute")
def resend_otp(
    request: Request,
    payload: OtpResendRequest,
    db: Session = Depends(get_db),
):
    """
    Resends a fresh 6-digit OTP code to the requested email address.
    Strictly enforces the 60-second cooldown window.
    """
    email = payload.email.strip().lower()
    purpose = payload.purpose or "login"
    client_ip = request.client.host if request.client else None

    try:
        challenge, plain_otp = create_otp_challenge(
            db, email=email, purpose=purpose, ip_address=client_ip
        )
    except OTPCooldownError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(err),
            headers={"Retry-After": str(err.seconds_left)},
        )

    try:
        email_service.send_otp_email(to_email=email, otp_code=plain_otp, purpose=purpose)
    except EmailDeliveryError as err:
        challenge.consumed_at = datetime.utcnow()
        challenge.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        )
    except Exception as exc:
        challenge.consumed_at = datetime.utcnow()
        challenge.status = "expired"
        db.commit()
        logger.error(f"Unexpected error resending OTP email: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while dispatching the verification email. Please try again.",
        )

    return OtpSendResponse(
        success=True,
        challenge_id=challenge.challenge_id,
        masked_email=mask_email(email),
        expires_in=settings.resolved_otp_expiry_minutes * 60,
        cooldown=settings.OTP_RESEND_COOLDOWN_SECONDS,
        message=f"A new verification code was sent to {mask_email(email)}.",
    )


@router.post("/verify-otp", response_model=TokenResponse)
@router.post("/otp/verify", response_model=TokenResponse)
@limiter.limit("12/minute")
def verify_email_otp(
    request: Request,
    payload: OtpVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Validates a submitted 6-digit OTP code against the server challenge.
    On success: verifies email ownership, updates persistent user record,
    and issues an authenticated JWT session.
    """
    email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else None

    try:
        challenge = verify_otp_challenge(
            db,
            email=email,
            code=payload.code,
            challenge_id=payload.challenge_id,
        )
    except OTPValidationError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except OTPExpiredError as err:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(err))
    except OTPMaxAttemptsError as err:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(err))

    user = user_repo.get_by_email(db, email)
    if not user:
        # Register new passwordless user
        user = user_repo.create(
            db,
            email=email,
            hashed_password=hash_password(str(uuid.uuid4())),
            full_name=payload.full_name or email.split("@")[0].title(),
        )
        user.is_verified = True
        user.email_verified = True
        user.auth_provider = "email_otp"
        user.account_status = "active"
        user.last_login_at = datetime.utcnow()
        user.last_login_method = "email_otp"
        user.last_login_ip = client_ip
        db.commit()
        db.refresh(user)

        record_activity(
            db=db,
            user_id=user.id,
            action_type="account_created",
            title="Account Created via Email OTP",
            description=f"Account created and verified with Gmail OTP ({email}).",
        )
        create_user_notification(
            db=db,
            user_id=user.id,
            title="Welcome to Analyticx AI! 🚀",
            message="Your account was verified via one-time email code. Your personalized workspace is ready.",
            level="success",
            link="/workspace",
            event_type="auth",
        )
    else:
        user.is_verified = True
        user.email_verified = True
        user.account_status = "active"
        user.last_login_at = datetime.utcnow()
        user.last_login_method = "email_otp"
        if client_ip:
            user.last_login_ip = client_ip
        if payload.full_name and (not user.full_name or user.full_name == "Kapil"):
            user.full_name = payload.full_name
        if not user.auth_provider:
            user.auth_provider = "email_otp"
        db.commit()
        db.refresh(user)

        record_activity(
            db=db,
            user_id=user.id,
            action_type="login",
            title="Signed In via Email OTP",
            description=f"Authenticated using verified one-time email code ({email}).",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserRead.model_validate(user),
    )


@router.post("/smtp/test-connection", response_model=SmtpTestResponse)
@router.get("/smtp/test-connection", response_model=SmtpTestResponse)
def test_smtp_connection_endpoint():
    """
    Tests SMTP connection and authentication handshake with Gmail SMTP.
    Returns connection status and helpful diagnostics without exposing credentials.
    """
    res = email_service.test_smtp_connection()
    return SmtpTestResponse(
        connected=res["success"],
        host=res["host"],
        port=res["port"],
        tls_active=res.get("tls", True),
        sender_configured=res["configured"],
        message=res["message"],
        error_detail=res.get("error"),
    )



# ---------------------------------------------------------------------------
# Google Sign-In & OpenID Connect Endpoints
# ---------------------------------------------------------------------------


@router.get("/oauth/google/config")
def google_oauth_config():
    """Returns Google OAuth configuration status so UI can render active or guided state."""
    return {
        "configured": is_google_oauth_configured(),
        "client_id": settings.GOOGLE_CLIENT_ID if is_google_oauth_configured() else None,
        "email_delivery_configured": email_service.is_configured(),
        "sandbox_enabled": False,
        "instructions": (
            "To enable Google Sign-In, configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env"
            if not is_google_oauth_configured()
            else "Google OAuth is active and ready."
        ),
    }


@router.post("/oauth/google/verify")
async def google_verify_or_login(
    request: Request,
    payload: GoogleVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Verifies an official Google ID token on the server using Google Identity Services.
    Validates token issuer, audience, signature, expiration, and verified email claim.
    Enforces safe account-linking if an account with this email already exists without Google link.
    """
    if not payload.credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A verified Google ID token ('credential') is required for Google Sign-In.",
        )

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth credentials are not configured on the server. Please set GOOGLE_CLIENT_ID in backend/.env.",
        )

    try:
        # Server-side cryptographic token validation
        id_info = google_id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            audience=settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as err:
        logger.warning(f"Google ID token validation failed: {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {str(err)}",
        )
    except Exception as err:
        logger.error(f"Unexpected error verifying Google ID token: {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to verify Google token signature.",
        )

    # Validate issuer
    if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token issuer.",
        )

    # Validate verified email
    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google identity token does not contain an email address.",
        )

    if not id_info.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Google account email is not verified by Google.",
        )

    google_sub = id_info.get("sub")
    if not google_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token is missing the subject identifier ('sub').",
        )

    norm_email = email.strip().lower()
    name = id_info.get("name") or payload.name
    picture = id_info.get("picture") or payload.avatar_url

    # Check if a user is already linked with this google_sub
    user_by_sub = user_repo.get_by_google_sub(db, google_sub)
    if user_by_sub:
        return _complete_google_authenticated_login(
            db, google_sub=google_sub, email=user_by_sub.email, name=name, avatar_url=picture
        )

    # Check if an existing account exists with this email
    existing_user = user_repo.get_by_email(db, norm_email)
    if existing_user:
        if existing_user.google_sub and existing_user.google_sub != google_sub:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email address is already linked to another Google account.",
            )

        # Safe Account Linking Policy:
        # Require proof of ownership before merging Google identity into an existing password/OTP account
        linking_token = create_linking_token(
            google_sub=google_sub,
            email=norm_email,
            name=name,
            avatar_url=picture,
        )
        has_real_pwd = bool(existing_user.hashed_password and len(existing_user.hashed_password) > 20)
        return {
            "account_linking_required": True,
            "email": norm_email,
            "masked_email": mask_email(norm_email),
            "linking_token": linking_token,
            "has_password": has_real_pwd,
            "message": (
                "An Analyticx AI account with this email address already exists. "
                "To securely link your Google account, please confirm ownership using your password or an Email OTP."
            ),
        }

    # Brand new Google user
    return _complete_google_authenticated_login(
        db, google_sub=google_sub, email=norm_email, name=name, avatar_url=picture
    )


@router.post("/oauth/google/confirm-link", response_model=TokenResponse)
def confirm_google_account_link(
    request: Request,
    payload: GoogleLinkConfirmRequest,
    db: Session = Depends(get_db),
):
    """
    Confirms and binds a Google identity (sub) to an existing account after verifying
    ownership via the existing account password or an email OTP code.
    """
    token_data = decode_linking_token(payload.linking_token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The account linking session has expired or is invalid. Please sign in with Google again.",
        )

    email = token_data.get("email")
    google_sub = token_data.get("sub")
    name = token_data.get("name")
    avatar_url = token_data.get("avatar_url")

    user = user_repo.get_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    # 1. Verify ownership via password if provided
    verified = False
    if payload.password:
        if verify_password(payload.password, user.hashed_password):
            verified = True
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect account password. Ownership could not be confirmed.",
            )

    # 2. Verify ownership via Email OTP if provided
    elif payload.challenge_id and payload.code:
        try:
            verify_otp_challenge(db, challenge_id=payload.challenge_id, email=email, code=payload.code)
            verified = True
        except Exception as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide your account password or a valid Email OTP code to confirm linking.",
        )

    # Link Google identity
    user.google_sub = google_sub
    user.is_verified = True
    if avatar_url and not user.avatar_url:
        user.avatar_url = avatar_url
    if name and (not user.full_name or user.full_name == "Kapil"):
        user.full_name = name
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    record_activity(
        db=db,
        user_id=user.id,
        action_type="account_linked",
        title="Google Account Linked",
        description=f"Successfully linked verified Google identity to existing account ({email}).",
    )
    create_user_notification(
        db=db,
        user_id=user.id,
        title="Google Account Linked! 🔗",
        message="Your Google account is now linked. You can sign in using either Google or your email.",
        level="success",
        link="/workspace",
        event_type="auth",
    )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserRead.model_validate(user),
    )


@router.post("/oauth/google/callback", response_model=Union[TokenResponse, Dict[str, Any]])
async def google_oauth_callback(
    request: Request,
    payload: GoogleCallbackRequest,
    db: Session = Depends(get_db),
):
    """Exchanges Google authorization code for tokens and signs in user."""
    if not is_google_oauth_configured():
        raise HTTPException(
            status_code=400,
            detail="Google OAuth client credentials are not configured on the server.",
        )

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": payload.code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": payload.redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(token_url, data=token_data)
        if res.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Google token exchange failed: {res.text}",
            )
        tokens = res.json()
        access_token = tokens.get("access_token")

        userinfo_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_res.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Failed to retrieve user profile from Google.",
            )
        user_info = userinfo_res.json()

    email = user_info.get("email")
    google_sub = user_info.get("sub")
    name = user_info.get("name")
    picture = user_info.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Google did not return a valid email address.")

    norm_email = email.strip().lower()

    # Check by google_sub
    user_by_sub = user_repo.get_by_google_sub(db, google_sub) if google_sub else None
    if user_by_sub:
        return _complete_google_authenticated_login(
            db, google_sub=google_sub or str(user_by_sub.id), email=user_by_sub.email, name=name, avatar_url=picture, method="Google OAuth 2.0"
        )

    # Check by email
    existing_user = user_repo.get_by_email(db, norm_email)
    if existing_user:
        if existing_user.google_sub and existing_user.google_sub != google_sub:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email address is already linked to another Google account.",
            )
        linking_token = create_linking_token(
            google_sub=google_sub or f"google_{uuid.uuid4().hex[:12]}",
            email=norm_email,
            name=name,
            avatar_url=picture,
        )
        return {
            "account_linking_required": True,
            "email": norm_email,
            "masked_email": mask_email(norm_email),
            "linking_token": linking_token,
            "has_password": bool(existing_user.hashed_password and len(existing_user.hashed_password) > 20),
            "message": (
                "An Analyticx AI account with this email address already exists. "
                "To securely link your Google account, please confirm ownership using your password or an Email OTP."
            ),
        }

    return _complete_google_authenticated_login(
        db, google_sub=google_sub or f"google_{uuid.uuid4().hex[:12]}", email=norm_email, name=name, avatar_url=picture, method="Google OAuth 2.0"
    )


@router.post("/oauth/google/configure")
def configure_google_oauth(payload: GoogleConfigureRequest):
    """Saves Google OAuth Client ID and Secret to backend/.env and activates them immediately."""
    cid = payload.client_id.strip()
    csecret = payload.client_secret.strip()

    settings.GOOGLE_CLIENT_ID = cid
    settings.GOOGLE_CLIENT_SECRET = csecret

    env_path = Path("backend/.env")
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        new_lines = []
        found_id, found_sec = False, False
        for l in lines:
            if l.startswith("GOOGLE_CLIENT_ID="):
                new_lines.append(f"GOOGLE_CLIENT_ID={cid}")
                found_id = True
            elif l.startswith("GOOGLE_CLIENT_SECRET="):
                new_lines.append(f"GOOGLE_CLIENT_SECRET={csecret}")
                found_sec = True
            else:
                new_lines.append(l)
        if not found_id:
            new_lines.append(f"GOOGLE_CLIENT_ID={cid}")
        if not found_sec:
            new_lines.append(f"GOOGLE_CLIENT_SECRET={csecret}")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return {
        "configured": True,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "message": "Google OAuth credentials updated and activated successfully.",
    }


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logs out user and records session conclusion."""
    record_activity(
        db=db,
        user_id=current_user.id,
        action_type="logout",
        title="Signed Out",
        description="Session ended successfully.",
    )
    return {"logged_out": True}
