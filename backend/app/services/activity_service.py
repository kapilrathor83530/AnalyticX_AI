from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.activity import UserActivity
from app.models.notification import Notification


def record_activity(
    db: Session,
    user_id: int,
    action_type: str,
    title: str,
    description: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    workspace_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> UserActivity:
    """Records an empirical user activity event for auditing, workspace continuity, and history."""
    activity = UserActivity(
        user_id=user_id,
        workspace_id=workspace_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        description=description,
        details=details or {},
        created_at=datetime.utcnow(),
    )
    db.add(activity)
    try:
        db.commit()
        db.refresh(activity)
    except Exception:
        db.rollback()
    return activity


def list_user_activities(
    db: Session,
    user_id: int,
    limit: int = 30,
) -> List[UserActivity]:
    """Retrieves recent activities for a user ordered by timestamp descending."""
    return (
        db.query(UserActivity)
        .filter(UserActivity.user_id == user_id)
        .order_by(UserActivity.created_at.desc())
        .limit(limit)
        .all()
    )


def create_user_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    level: str = "info",
    link: Optional[str] = None,
    event_type: str = "general",
) -> Notification:
    """Creates a persistent in-app notification for a user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        level=level,
        is_read=False,
        link=link,
        event_type=event_type,
        created_at=datetime.utcnow(),
    )
    db.add(notif)
    try:
        db.commit()
        db.refresh(notif)
    except Exception:
        db.rollback()
    return notif


def list_user_notifications(
    db: Session,
    user_id: int,
    limit: int = 50,
    unread_only: bool = False,
) -> List[Notification]:
    """Retrieves notifications for a user."""
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    return q.order_by(Notification.created_at.desc()).limit(limit).all()


def mark_notification_as_read(db: Session, notification_id: int, user_id: int) -> bool:
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if notif:
        notif.is_read = True
        db.commit()
        return True
    return False


def mark_all_notifications_as_read(db: Session, user_id: int) -> int:
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({"is_read": True})
    )
    db.commit()
    return updated
