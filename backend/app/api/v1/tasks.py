from fastapi import APIRouter, HTTPException

from app.services.task_service import get_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
def task_status(task_id: str):
    task = get_task(task_id)
    if task.get("status") == "missing":
        raise HTTPException(status_code=404, detail="Task not found")
    return task
