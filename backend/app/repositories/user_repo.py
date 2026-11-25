from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email.ilike(email.strip())).first()


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_by_google_sub(db: Session, google_sub: str) -> Optional[User]:
    if not google_sub:
        return None
    return db.query(User).filter(User.google_sub == google_sub).first()


def create(
    db: Session,
    email: str,
    hashed_password: str,
    full_name: Optional[str] = None,
    role: str = "Data Analyst",
    experience_level: str = "Intermediate",
    preferences: Optional[Dict[str, Any]] = None,
) -> User:
    user = User(
        email=email.strip().lower(),
        hashed_password=hashed_password,
        full_name=full_name.strip() if full_name else None,
        role=role,
        experience_level=experience_level,
        preferences=preferences or {
            "theme": "dark",
            "language": "en",
            "explanation_level": "standard",
            "email_notifications": True,
        },
        primary_goal=[],
        onboarding_completed=False,
        is_verified=False,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_profile(
    db: Session,
    user: User,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    experience_level: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> User:
    if full_name is not None:
        user.full_name = full_name.strip()
    if role is not None:
        user.role = role
    if experience_level is not None:
        user.experience_level = experience_level
    if avatar_url is not None:
        user.avatar_url = avatar_url
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def update_preferences(
    db: Session,
    user: User,
    new_prefs: Dict[str, Any],
) -> User:
    current = dict(user.preferences or {})
    current.update({k: v for k, v in new_prefs.items() if v is not None})
    user.preferences = current
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def save_onboarding(
    db: Session,
    user: User,
    role: str,
    primary_goal: List[str],
    experience_level: str,
    preferences: Optional[Dict[str, Any]] = None,
) -> User:
    user.role = role
    user.primary_goal = primary_goal
    user.experience_level = experience_level
    if preferences:
        cur = dict(user.preferences or {})
        cur.update(preferences)
        user.preferences = cur
    user.onboarding_completed = True
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user
