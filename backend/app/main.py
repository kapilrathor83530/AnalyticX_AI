from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import health
from app.api.v1 import (
    agents as agents_router,
    analytics as analytics_router,
    auth as auth_router,
    context as context_router,
    copilot as copilot_router,
    dashboards as dashboards_router,
    datasets as datasets_router,
    forecasting as forecasting_router,
    llm as llm_router,
    reports as reports_router,
    simulation as simulation_router,
    tasks as tasks_router,
    users as users_router,
    visualizations as visualizations_router,
    workspaces as workspaces_router,
    ws as ws_router,
    project_insights as project_insights_router,
)
from app.api.v1 import notifications as notifications_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.database import Base, engine
from app.models import (  # noqa: F401
    Dashboard, DashboardConversation, DashboardChatMessage, Dataset, ForecastRun, Notification, Scenario, Transformation,
    User, EmailOtpChallenge, Widget, Workspace, ProjectAnalysisRun, ProjectInsight, ReportRecord, UserActivity,
)

Base.metadata.create_all(bind=engine)

def _migrate_db_columns():
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            # Migrate users table columns if missing
            u_info = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            u_existing = {row[1] for row in u_info}
            user_cols = [
                ("google_sub", "VARCHAR(255)"),
                ("email_verified", "BOOLEAN DEFAULT 0"),
                ("auth_provider", "VARCHAR(64) DEFAULT 'password'"),
                ("account_status", "VARCHAR(32) DEFAULT 'active'"),
                ("profile_image_url", "VARCHAR(255)"),
                ("last_login_method", "VARCHAR(64)"),
                ("last_login_ip", "VARCHAR(64)"),
                ("timezone", "VARCHAR(64) DEFAULT 'UTC'"),
                ("preferred_language", "VARCHAR(32) DEFAULT 'en'"),
            ]
            for col_name, col_type in user_cols:
                if col_name not in u_existing:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))

            # Migrate email_otp_challenges table columns if missing
            otp_info = conn.execute(text("PRAGMA table_info(email_otp_challenges)")).fetchall()
            otp_existing = {row[1] for row in otp_info}
            otp_cols = [
                ("status", "VARCHAR(32) DEFAULT 'pending'"),
                ("ip_address", "VARCHAR(64)"),
            ]
            for col_name, col_type in otp_cols:
                if col_name not in otp_existing:
                    conn.execute(text(f"ALTER TABLE email_otp_challenges ADD COLUMN {col_name} {col_type}"))

            conn.commit()
    except Exception:
        pass

_migrate_db_columns()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import SessionLocal
    from app.repositories import user_repo
    from app.core.security import hash_password
    db = SessionLocal()
    try:
        user = user_repo.get_by_email(db, "demo@analyticx.ai")
        if not user:
            user = user_repo.create(
                db,
                email="demo@analyticx.ai",
                hashed_password=hash_password("analyticx123"),
                full_name="Kapil",
            )
            user.is_verified = True
            user.email_verified = True
            db.commit()
        else:
            user.full_name = "Kapil"
            user.is_verified = True
            user.email_verified = True
            db.commit()

        # Check and migrate SQLite forecast_runs and users columns if missing
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                # Migrate users table columns if missing
                u_info = conn.execute(text("PRAGMA table_info(users)")).fetchall()
                u_existing = {row[1] for row in u_info}
                if "google_sub" not in u_existing:
                    conn.execute(text("ALTER TABLE users ADD COLUMN google_sub VARCHAR(255)"))
                    try:
                        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub ON users(google_sub)"))
                    except Exception:
                        pass

                info = conn.execute(text("PRAGMA table_info(forecast_runs)")).fetchall()
                existing_cols = {row[1] for row in info}
                new_cols = [
                    ('group_dimension', 'TEXT'),
                    ('group_value', 'TEXT'),
                    ('candidate_models', 'JSON'),
                    ('backtest_results', 'JSON'),
                    ('confidence_intervals', 'JSON'),
                    ('scenarios', 'JSON'),
                    ('insights', 'JSON'),
                    ('data_validation', 'JSON'),
                    ('training_time_ms', 'REAL'),
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE forecast_runs ADD COLUMN {col_name} {col_type}"))
                conn.commit()
        except Exception:
            pass
    except Exception:
        pass
    finally:
        db.close()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in [
    health.router, auth_router.router, users_router.router, workspaces_router.router, datasets_router.router,
    dashboards_router.router, visualizations_router.router, llm_router.router,
    agents_router.router, analytics_router.router, forecasting_router.router,
    simulation_router.router, reports_router.router, notifications_router.router,
    tasks_router.router, ws_router.router, copilot_router.router, context_router.router,
    project_insights_router.router,
]:
    app.include_router(r, prefix=settings.API_V1_PREFIX)
    # Also support /api/* alias for standard routing conventions
    app.include_router(r, prefix="/api")


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "status": "ok"}


@app.get("/health", tags=["health"])
def root_health_check():
    return {"status": "ok", "app": settings.APP_NAME}
