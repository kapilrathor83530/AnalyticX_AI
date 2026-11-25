import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.models.activity import UserActivity
from app.models.dashboard import Dashboard
from app.models.dataset import Dataset
from app.models.forecast import ForecastRun
from app.models.notification import Notification
from app.models.report import ReportRecord
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories import user_repo
from app.schemas.user import (
    ChangePasswordRequest,
    OnboardingRequest,
    UserActivityRead,
    UserPreferencesUpdate,
    UserProfileUpdate,
    UserRead,
)
from app.services.activity_service import (
    create_user_notification,
    list_user_activities,
    list_user_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
    record_activity,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile")
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns rich user profile with workspace inventory statistics."""
    dataset_count = db.query(Dataset).filter(Dataset.user_id == current_user.id).count()
    dashboard_count = db.query(Dashboard).filter(Dashboard.user_id == current_user.id).count()
    report_count = db.query(ReportRecord).filter(ReportRecord.user_id == current_user.id).count()
    unread_notifs = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )

    return {
        "user": UserRead.model_validate(current_user),
        "stats": {
            "dataset_count": dataset_count,
            "dashboard_count": dashboard_count,
            "report_count": report_count,
            "unread_notifications": unread_notifs,
        },
    }


@router.put("/profile", response_model=UserRead)
def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates basic profile fields (name, role, experience level, avatar)."""
    updated = user_repo.update_profile(
        db=db,
        user=current_user,
        full_name=payload.full_name,
        role=payload.role,
        experience_level=payload.experience_level,
        avatar_url=payload.avatar_url,
    )
    record_activity(
        db=db,
        user_id=current_user.id,
        action_type="profile_updated",
        title="Profile Updated",
        description="Display name or professional title was updated.",
    )
    return updated


@router.put("/preferences", response_model=UserRead)
def update_preferences(
    payload: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates personalized user preferences (theme, language, explanation depth, notifications)."""
    updated = user_repo.update_preferences(
        db=db,
        user=current_user,
        new_prefs=payload.model_dump(exclude_unset=True),
    )
    record_activity(
        db=db,
        user_id=current_user.id,
        action_type="preferences_updated",
        title="Preferences Saved",
        description="Application preferences were updated.",
    )
    return updated


@router.post("/onboarding", response_model=UserRead)
def complete_onboarding(
    payload: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Saves personalized onboarding survey responses and activates personalized workspace."""
    updated = user_repo.save_onboarding(
        db=db,
        user=current_user,
        role=payload.role,
        primary_goal=payload.primary_goal,
        experience_level=payload.experience_level,
        preferences=payload.preferences,
    )
    record_activity(
        db=db,
        user_id=current_user.id,
        action_type="onboarding_completed",
        title="Onboarding Completed",
        description=f"Personalized configuration set: {payload.role} ({payload.experience_level}).",
    )
    create_user_notification(
        db=db,
        user_id=current_user.id,
        title="Personalized Experience Ready ✨",
        message=f"We tailored Analyticx AI for your goals: {', '.join(payload.primary_goal[:2]) or 'General Analytics'}.",
        level="success",
        link="/workspace",
        event_type="onboarding",
    )
    return updated


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Changes password with verification of the current password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password does not match.")

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()

    record_activity(
        db=db,
        user_id=current_user.id,
        action_type="password_changed",
        title="Password Changed",
        description="Password was updated from Account Settings.",
    )
    create_user_notification(
        db=db,
        user_id=current_user.id,
        title="Security Notice: Password Updated",
        message="Your password was successfully updated from Account Settings.",
        level="info",
        event_type="security",
    )
    return {"updated": True, "message": "Password changed successfully."}


@router.get("/activity", response_model=List[UserActivityRead])
def get_user_activity(
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the authenticated user's recent activity stream."""
    return list_user_activities(db=db, user_id=current_user.id, limit=limit)


@router.get("/notifications")
def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns persistent in-app notifications for the authenticated user."""
    items = list_user_notifications(db=db, user_id=current_user.id, limit=limit, unread_only=unread_only)
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )
    return {
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "level": n.level,
                "is_read": n.is_read,
                "link": n.link,
                "event_type": n.event_type,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
        "unread_count": unread_count,
    }


@router.post("/notifications/{notification_id}/read")
def read_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks a single notification as read."""
    success = mark_notification_as_read(db=db, notification_id=notification_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"marked": True}


@router.post("/notifications/read-all")
def read_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks all user notifications as read."""
    count = mark_all_notifications_as_read(db=db, user_id=current_user.id)
    return {"marked_count": count}


@router.get("/export-data")
def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exports all personal account data, preferences, project metadata, and activity history in machine-readable JSON."""
    user_dict = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "experience_level": current_user.experience_level,
        "primary_goal": current_user.primary_goal,
        "preferences": current_user.preferences,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }

    datasets = (
        db.query(Dataset)
        .filter(Dataset.user_id == current_user.id)
        .all()
    )
    dataset_records = [
        {
            "id": d.id,
            "name": d.name,
            "original_filename": d.original_filename,
            "rows": d.row_count,
            "columns": d.column_count,
            "status": d.status,
            "quality_score": d.quality_score,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in datasets
    ]

    dashboards = (
        db.query(Dashboard)
        .filter(Dashboard.user_id == current_user.id)
        .all()
    )
    dashboard_records = [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in dashboards
    ]

    activities = list_user_activities(db=db, user_id=current_user.id, limit=200)
    activity_records = [
        {
            "id": a.id,
            "action_type": a.action_type,
            "title": a.title,
            "description": a.description,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]

    export_bundle = {
        "export_metadata": {
            "application": "Analyticx AI",
            "version": "2.0",
            "exported_at": datetime.utcnow().isoformat(),
        },
        "user_profile": user_dict,
        "datasets": dataset_records,
        "dashboards": dashboard_records,
        "activity_history": activity_records,
    }

    content = json.dumps(export_bundle, indent=2).encode("utf-8")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="analyticx_account_export_{current_user.id}.json"'},
    )


@router.delete("/account")
def delete_user_account(
    confirmation: str = Query(..., description="Must equal 'DELETE' to confirm deletion"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently deletes user account, owned resources, and personal history."""
    if confirmation.strip() != "DELETE":
        raise HTTPException(
            status_code=400,
            detail="Confirmation text must be 'DELETE' to permanently delete your account.",
        )

    # Clean up owned datasets
    db.query(Dataset).filter(Dataset.user_id == current_user.id).delete()
    # Clean up owned dashboards
    db.query(Dashboard).filter(Dashboard.user_id == current_user.id).delete()
    # Clean up owned reports
    db.query(ReportRecord).filter(ReportRecord.user_id == current_user.id).delete()
    # Clean up activities and notifications
    db.query(UserActivity).filter(UserActivity.user_id == current_user.id).delete()
    db.query(Notification).filter(Notification.user_id == current_user.id).delete()
    # Delete user
    db.delete(current_user)
    db.commit()

    return {"deleted": True, "message": "Your Analyticx AI account and all associated data have been permanently deleted."}
