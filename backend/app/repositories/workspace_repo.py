from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.workspace import Workspace


def list_for_user(db: Session, user_id: Optional[int]) -> List[Workspace]:
    query = db.query(Workspace)
    if user_id is not None:
        query = query.filter(Workspace.user_id == user_id)
    return query.order_by(Workspace.created_at.desc()).all()


def get(db: Session, workspace_id: int) -> Optional[Workspace]:
    return db.query(Workspace).filter(Workspace.id == workspace_id).first()


def create(db: Session, data: dict) -> Workspace:
    workspace = Workspace(**data)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def update(db: Session, workspace: Workspace, data: dict) -> Workspace:
    for key, value in data.items():
        if value is not None:
            setattr(workspace, key, value)
    db.commit()
    db.refresh(workspace)
    return workspace


def delete(db: Session, workspace: Workspace) -> None:
    db.delete(workspace)
    db.commit()
