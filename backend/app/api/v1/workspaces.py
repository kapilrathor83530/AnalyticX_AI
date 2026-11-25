from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.database import get_db
from app.models.user import User
from app.repositories import workspace_repo
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    return workspace_repo.list_for_user(db, user.id if user else None)


@router.post("", response_model=WorkspaceRead)
def create_workspace(
    payload: WorkspaceCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    data = payload.model_dump()
    data["user_id"] = user.id if user else None
    return workspace_repo.create(db, data)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = workspace_repo.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.put("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(workspace_id: int, payload: WorkspaceUpdate, db: Session = Depends(get_db)):
    workspace = workspace_repo.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace_repo.update(db, workspace, payload.model_dump(exclude_unset=True))


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = workspace_repo.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace_repo.delete(db, workspace)
    return {"deleted": True, "workspace_id": workspace_id}
