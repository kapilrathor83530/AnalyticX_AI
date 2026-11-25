import os
import shutil
import time
from fastapi import APIRouter
from sqlalchemy import text
from app.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    db_status = "connected"
    latency_ms = 0.0
    try:
        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    disk_info = {}
    try:
        total, used, free = shutil.disk_usage(os.getcwd())
        disk_info = {
            "total_gb": round(total / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "status": "healthy" if free > 500 * 1024 * 1024 else "warning_low_disk",
        }
    except Exception:
        disk_info = {"status": "unavailable"}

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "app": "Analyticx AI",
        "version": "1.0.0",
        "database": {
            "status": db_status,
            "latency_ms": latency_ms,
        },
        "storage": disk_info,
    }
