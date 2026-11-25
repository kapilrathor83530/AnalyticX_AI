from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    query = db.query(Notification)
    if user:
        query = query.filter((Notification.user_id == user.id) | (Notification.user_id.is_(None)))
    return query.order_by(Notification.created_at.desc()).limit(50).all()


@router.post("", response_model=NotificationRead)
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    notification = Notification(
        user_id=user.id if user else None,
        title=payload.title,
        message=payload.message,
        level=payload.level,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    return {"updated": True}


@router.delete("/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notification)
    db.commit()
    return {"deleted": True}
