from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.dashboard_chat_message import DashboardChatMessage
from app.models.dashboard_conversation import DashboardConversation


def list_conversations(db: Session, dashboard_id: int) -> list[DashboardConversation]:
    return db.query(DashboardConversation).filter(DashboardConversation.dashboard_id == dashboard_id).order_by(DashboardConversation.updated_at.desc()).all()


def get_conversation(db: Session, conversation_id: int) -> Optional[DashboardConversation]:
    return db.query(DashboardConversation).filter(DashboardConversation.id == conversation_id).first()


def create_conversation(db: Session, dashboard_id: int, title: str, mode: str) -> DashboardConversation:
    item = DashboardConversation(dashboard_id=dashboard_id, title=title[:255] or "Dashboard conversation", mode=mode)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_messages(db: Session, conversation_id: int) -> list[DashboardChatMessage]:
    return db.query(DashboardChatMessage).filter(DashboardChatMessage.conversation_id == conversation_id).order_by(DashboardChatMessage.created_at.asc(), DashboardChatMessage.id.asc()).all()


def create_message(db: Session, conversation_id: int, role: str, content: str, details: dict | None = None) -> DashboardChatMessage:
    item = DashboardChatMessage(conversation_id=conversation_id, role=role, content=content, details=details or {})
    db.add(item)
    conversation = get_conversation(db, conversation_id)
    if conversation:
        # ``created_at`` is populated only during flush; use an explicit value so
        # the parent can be updated in the same transaction on SQLite.
        conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


def delete_conversation_messages(db: Session, conversation_id: int) -> None:
    db.query(DashboardChatMessage).filter(DashboardChatMessage.conversation_id == conversation_id).delete()
    db.commit()
