from copy import deepcopy
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.database import get_db
from app.models.dataset import Dataset
from app.models.user import User
from app.repositories import dashboard_chat_repo
from app.repositories import dashboard_repo
from app.services.activity_service import create_user_notification, record_activity
from app.schemas.dashboard_chat import (
    DashboardChatMessageRead, DashboardChatRequest, DashboardChatResponse, DashboardConversationRead,
    DashboardRestoreRequest,
)
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardRead,
    DashboardUpdate,
    LayoutUpdate,
    WidgetCreate,
    WidgetRead,
    WidgetUpdate,
)
from app.services.business_chat_service import answer_business_chat
from app.services.dashboard_context_service import dashboard_context
from app.services.data_service import load_dataset_df

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _get_dashboard_or_404(db: Session, dashboard_id: int):
    dashboard = dashboard_repo.get_dashboard(db, dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard


@router.get("", response_model=list[DashboardRead])
def list_dashboards(
    dataset_id: int | None = None,
    search: str | None = None,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    return dashboard_repo.list_dashboards(
        db,
        dataset_id=dataset_id,
        search=search,
        user_id=user.id if user else None,
    )


@router.post("", response_model=DashboardRead)
def create_dashboard(
    payload: DashboardCreate,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    data = payload.model_dump()
    if user:
        data["user_id"] = user.id
    dashboard = dashboard_repo.create_dashboard(db, data)
    if user:
        record_activity(
            db=db,
            user_id=user.id,
            action_type="dashboard_created",
            title=f"Created Dashboard '{dashboard.name}'",
            description=f"Dashboard created for dataset #{payload.dataset_id}",
            entity_type="dashboard",
            entity_id=dashboard.id,
        )
        create_user_notification(
            db=db,
            user_id=user.id,
            title="Dashboard Saved",
            message=f"Dashboard '{dashboard.name}' was created.",
            level="success",
            link=f"/dashboard/{dashboard.id}/edit",
            event_type="dashboard",
        )
    return dashboard


@router.get("/{dashboard_id}", response_model=DashboardRead)
def get_dashboard(dashboard_id: int, db: Session = Depends(get_db)):
    return _get_dashboard_or_404(db, dashboard_id)


@router.post("/{dashboard_id}/duplicate", response_model=DashboardRead)
def duplicate_dashboard(dashboard_id: int, payload: DashboardUpdate | None = None, db: Session = Depends(get_db)):
    dashboard = _get_dashboard_or_404(db, dashboard_id)
    return dashboard_repo.duplicate_dashboard(db, dashboard, (payload.name if payload else None))


@router.get("/{dashboard_id}/export")
def export_dashboard(dashboard_id: int, db: Session = Depends(get_db)):
    dashboard = _get_dashboard_or_404(db, dashboard_id)
    return {
        "version": 1,
        "dashboard": {
            "dataset_id": dashboard.dataset_id,
            "workspace_id": dashboard.workspace_id,
            "name": dashboard.name,
            "description": dashboard.description,
            "layout_config": dashboard.layout_config or {},
        },
        "widgets": [
            {"chart_type": item.chart_type, "title": item.title, "config": item.config or {}, "data_mapping": item.data_mapping or {}, "position": item.position or {}, "size": item.size or {}}
            for item in dashboard_repo.list_widgets(db, dashboard_id)
        ],
    }


@router.post("/restore", response_model=DashboardRead)
def restore_dashboard(payload: DashboardRestoreRequest, db: Session = Depends(get_db)):
    source = payload.configuration
    dashboard_data = source.get("dashboard", source)
    dataset_id = dashboard_data.get("dataset_id")
    if not isinstance(dataset_id, int) or not db.query(Dataset).filter(Dataset.id == dataset_id).first():
        raise HTTPException(status_code=400, detail="The saved dashboard references a dataset that is not available.")
    dashboard = dashboard_repo.create_dashboard(db, {
        "dataset_id": dataset_id,
        "workspace_id": dashboard_data.get("workspace_id"),
        "name": payload.name or dashboard_data.get("name") or "Restored dashboard",
        "description": dashboard_data.get("description"),
        "layout_config": dashboard_data.get("layout_config") or {},
    })
    for widget in source.get("widgets", []):
        if isinstance(widget, dict) and widget.get("chart_type"):
            dashboard_repo.create_widget(db, {**widget, "dashboard_id": dashboard.id})
    return dashboard


@router.put("/{dashboard_id}", response_model=DashboardRead)
def update_dashboard(dashboard_id: int, payload: DashboardUpdate, db: Session = Depends(get_db)):
    dashboard = _get_dashboard_or_404(db, dashboard_id)
    return dashboard_repo.update_dashboard(db, dashboard, payload.model_dump(exclude_unset=True))


@router.delete("/{dashboard_id}")
def delete_dashboard(dashboard_id: int, db: Session = Depends(get_db)):
    dashboard = _get_dashboard_or_404(db, dashboard_id)
    dashboard_repo.delete_dashboard(db, dashboard)
    return {"deleted": True, "dashboard_id": dashboard_id}


@router.put("/{dashboard_id}/layout", response_model=DashboardRead)
def update_layout(dashboard_id: int, payload: LayoutUpdate, db: Session = Depends(get_db)):
    dashboard = _get_dashboard_or_404(db, dashboard_id)
    return dashboard_repo.update_dashboard(db, dashboard, {"layout_config": payload.layout_config})


@router.get("/{dashboard_id}/widgets", response_model=list[WidgetRead])
def list_widgets(dashboard_id: int, db: Session = Depends(get_db)):
    _get_dashboard_or_404(db, dashboard_id)
    return dashboard_repo.list_widgets(db, dashboard_id)


@router.post("/{dashboard_id}/widgets", response_model=WidgetRead)
def create_widget(dashboard_id: int, payload: WidgetCreate, db: Session = Depends(get_db)):
    _get_dashboard_or_404(db, dashboard_id)
    data = payload.model_dump()
    data["dashboard_id"] = dashboard_id
    return dashboard_repo.create_widget(db, data)


@router.put("/{dashboard_id}/widgets/{widget_id}", response_model=WidgetRead)
def update_widget(dashboard_id: int, widget_id: int, payload: WidgetUpdate, db: Session = Depends(get_db)):
    widget = dashboard_repo.get_widget(db, widget_id)
    if not widget or widget.dashboard_id != dashboard_id:
        raise HTTPException(status_code=404, detail="Widget not found")
    return dashboard_repo.update_widget(db, widget, payload.model_dump(exclude_unset=True))


@router.delete("/{dashboard_id}/widgets/{widget_id}")
def delete_widget(dashboard_id: int, widget_id: int, db: Session = Depends(get_db)):
    widget = dashboard_repo.get_widget(db, widget_id)
    if not widget or widget.dashboard_id != dashboard_id:
        raise HTTPException(status_code=404, detail="Widget not found")
    dashboard_repo.delete_widget(db, widget)
    return {"deleted": True, "widget_id": widget_id}


@router.get("/{dashboard_id}/conversations", response_model=list[DashboardConversationRead])
def list_conversations(dashboard_id: int, db: Session = Depends(get_db)):
    _get_dashboard_or_404(db, dashboard_id)
    return dashboard_chat_repo.list_conversations(db, dashboard_id)


@router.get("/{dashboard_id}/conversations/{conversation_id}/messages", response_model=list[DashboardChatMessageRead])
def list_conversation_messages(dashboard_id: int, conversation_id: int, db: Session = Depends(get_db)):
    _get_dashboard_or_404(db, dashboard_id)
    conversation = dashboard_chat_repo.get_conversation(db, conversation_id)
    if not conversation or conversation.dashboard_id != dashboard_id:
        raise HTTPException(status_code=404, detail="Conversation not found for this dashboard")
    return dashboard_chat_repo.list_messages(db, conversation_id)


@router.delete("/{dashboard_id}/conversations/{conversation_id}/messages")
def clear_conversation_messages(dashboard_id: int, conversation_id: int, db: Session = Depends(get_db)):
    _get_dashboard_or_404(db, dashboard_id)
    conversation = dashboard_chat_repo.get_conversation(db, conversation_id)
    if not conversation or conversation.dashboard_id != dashboard_id:
        raise HTTPException(status_code=404, detail="Conversation not found for this dashboard")
    dashboard_chat_repo.delete_conversation_messages(db, conversation_id)
    return {"cleared": True, "conversation_id": conversation_id}


@router.post("/{dashboard_id}/chat", response_model=DashboardChatResponse)
async def dashboard_chat(dashboard_id: int, payload: DashboardChatRequest, db: Session = Depends(get_db)):
    dashboard = _get_dashboard_or_404(db, dashboard_id)
    if payload.conversation_id:
        conversation = dashboard_chat_repo.get_conversation(db, payload.conversation_id)
        if not conversation or conversation.dashboard_id != dashboard.id:
            raise HTTPException(status_code=404, detail="Conversation not found for this dashboard")
    else:
        conversation = dashboard_chat_repo.create_conversation(db, dashboard.id, payload.message[:72], payload.mode)

    user_message = dashboard_chat_repo.create_message(db, conversation.id, "user", payload.message)
    dataset = db.query(Dataset).filter(Dataset.id == dashboard.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=409, detail="This dashboard's source dataset is no longer available.")
    df = load_dataset_df(dataset)
    context = dashboard_context(db, dashboard, df)
    history = [
        {"role": message.role, "content": message.content}
        for message in dashboard_chat_repo.list_messages(db, conversation.id)[-12:]
    ]
    # The workflow receives calculated data, while this compact object lets it describe the active dashboard.
    result = await answer_business_chat(df, history, dashboard_context=context)
    assistant_message = dashboard_chat_repo.create_message(
        db, conversation.id, "assistant", result["answer"],
        {key: result.get(key, []) for key in ("verified_facts", "limitations", "tools_used")},
    )
    return {"conversation": conversation, "message": assistant_message, "dashboard_context": context, **result}
