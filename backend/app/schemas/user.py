from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool = False
    email_verified: bool = False
    auth_provider: str = "password"
    account_status: str = "active"
    role: str = "Data Analyst"
    primary_goal: List[str] = []
    experience_level: str = "Intermediate"
    preferences: Dict[str, Any] = {}
    onboarding_completed: bool = False
    avatar_url: Optional[str] = None
    profile_image_url: Optional[str] = None
    last_login_at: Optional[datetime] = None
    last_login_method: Optional[str] = None
    timezone: str = "UTC"
    preferred_language: str = "en"
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class EmailVerifyRequest(BaseModel):
    token: str


class EmailResendRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    experience_level: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPreferencesUpdate(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    explanation_level: Optional[str] = None
    email_notifications: Optional[bool] = None
    date_format: Optional[str] = None


class OnboardingRequest(BaseModel):
    role: str = "Data Analyst"
    primary_goal: List[str] = []
    experience_level: str = "Intermediate"
    preferences: Optional[Dict[str, Any]] = None


class UserActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    workspace_id: Optional[int] = None
    action_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class GoogleCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


class GoogleVerifyRequest(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    credential: Optional[str] = None


class GoogleConfigureRequest(BaseModel):
    client_id: str
    client_secret: str


class OtpSendRequest(BaseModel):
    email: EmailStr
    purpose: Optional[str] = "login"
    challenge_id: Optional[str] = None


class OtpResendRequest(BaseModel):
    email: EmailStr
    purpose: Optional[str] = "login"
    challenge_id: Optional[str] = None


class OtpSendResponse(BaseModel):
    success: bool
    challenge_id: str
    masked_email: str
    expires_in: int
    cooldown: int
    message: str


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    code: str
    challenge_id: Optional[str] = None
    full_name: Optional[str] = None


class GoogleLinkConfirmRequest(BaseModel):
    linking_token: str
    password: Optional[str] = None
    challenge_id: Optional[str] = None
    code: Optional[str] = None


class SignupRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None
    agree_terms: Optional[bool] = True


class SmtpTestResponse(BaseModel):
    connected: bool
    host: str
    port: int
    tls_active: bool
    sender_configured: bool
    message: str
    error_detail: Optional[str] = None
