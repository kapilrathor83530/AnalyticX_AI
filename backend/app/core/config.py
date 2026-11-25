from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Analyticx AI"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./analyticx.db"
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_MB: int = 200
    CORS_ORIGINS: str = "http://localhost:5173"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # Qwen3 4B Instruct is the supported local default.  It is intentionally
    # a local Ollama identifier: the application never falls back to a paid API.
    DEFAULT_MODEL: str = "qwen3:4b-instruct"
    LLM_REQUEST_TIMEOUT_SECONDS: float = 90.0
    LLM_CONTEXT_TOKENS: int = 8192
    LLM_MAX_CONCURRENT_REQUESTS: int = 1
    LLM_KEEP_ALIVE: str = "10m"
    # Tool plans are short and schema constrained; explicit reasoning tokens are
    # unnecessary on a CPU-only runtime and increase latency substantially.
    LLM_ENABLE_THINKING: bool = False

    JWT_SECRET: str = "change-me-in-production-use-a-long-random-string"
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # When True, protected endpoints require a valid Bearer token.
    REQUIRE_AUTH: bool = False

    # Optional Google OAuth Credentials
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # SMTP & Gmail Delivery Settings
    EMAIL_PROVIDER: str = "smtp"  # "smtp", "console", "test"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_SECURE: bool = False
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = "Analyticx AI <auth@analyticx.ai>"

    # Aliases / compatibility fallback
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    APP_BASE_URL: str = "http://localhost:5173"

    # OTP Security Parameters
    OTP_EXPIRY_MINUTES: int = 5
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    @property
    def resolved_smtp_user(self) -> str:
        return (self.SMTP_USER or self.SMTP_USERNAME or "").strip()

    @property
    def resolved_smtp_pass(self) -> str:
        return (self.SMTP_PASS or self.SMTP_PASSWORD or "").strip()

    @property
    def resolved_smtp_from(self) -> str:
        if self.SMTP_FROM and self.SMTP_FROM != "Analyticx AI <auth@analyticx.ai>":
            return self.SMTP_FROM
        if self.EMAIL_FROM:
            return self.EMAIL_FROM
        if self.resolved_smtp_user:
            return f"Analyticx AI <{self.resolved_smtp_user}>"
        return self.SMTP_FROM

    @property
    def resolved_smtp_secure(self) -> bool:
        return bool(self.SMTP_SECURE or self.SMTP_USE_SSL or self.SMTP_PORT == 465)

    @property
    def resolved_otp_expiry_minutes(self) -> int:
        return self.OTP_EXPIRY_MINUTES or self.OTP_EXPIRE_MINUTES or 5

    class Config:
        env_file = (
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
            ".env",
        )
        extra = "ignore"


settings = Settings()

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
