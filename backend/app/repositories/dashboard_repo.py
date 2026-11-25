from copy import deepcopy
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.dashboard import Dashboard
from app.models.widget import Widget


def list_dashboards(
    db: Session,
    dataset_id: Optional[int] = None,
    search: Optional[str] = None,
    user_id: Optional[int] = None,
) -> List[Dashboard]:
    query = db.query(Dashboard)
    if user_id is not None:
        query = query.filter((Dashboard.user_id == user_id) | (Dashboard.user_id.is_(None)))
    if dataset_id is not None:
        query = query.filter(Dashboard.dataset_id == dataset_id)
    if search:
        needle = f"%{search.strip()}%"
        query = query.filter((Dashboard.name.ilike(needle)) | (Dashboard.description.ilike(needle)))
    return query.order_by(Dashboard.updated_at.desc(), Dashboard.created_at.desc()).all()


def get_dashboard(db: Session, dashboard_id: int) -> Optional[Dashboard]:
    return db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()


def create_dashboard(db: Session, data: dict) -> Dashboard:
    dashboard = Dashboard(**data)
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return dashboard


def update_dashboard(db: Session, dashboard: Dashboard, data: dict) -> Dashboard:
    for key, value in data.items():
        if value is not None:
            setattr(dashboard, key, value)
    db.commit()
    db.refresh(dashboard)
    return dashboard


def delete_dashboard(db: Session, dashboard: Dashboard) -> None:
    db.delete(dashboard)
    db.commit()


def list_widgets(db: Session, dashboard_id: int) -> List[Widget]:
    return db.query(Widget).filter(Widget.dashboard_id == dashboard_id).order_by(Widget.id.asc()).all()


def get_widget(db: Session, widget_id: int) -> Optional[Widget]:
    return db.query(Widget).filter(Widget.id == widget_id).first()


def create_widget(db: Session, data: dict) -> Widget:
    widget = Widget(**data)
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


def update_widget(db: Session, widget: Widget, data: dict) -> Widget:
    for key, value in data.items():
        if value is not None:
            setattr(widget, key, value)
    db.commit()
    db.refresh(widget)
    return widget


def delete_widget(db: Session, widget: Widget) -> None:
    db.delete(widget)
    db.commit()


def duplicate_dashboard(db: Session, dashboard: Dashboard, name: str | None = None) -> Dashboard:
    copy = Dashboard(
        dataset_id=dashboard.dataset_id,
        workspace_id=dashboard.workspace_id,
        name=name or f"{dashboard.name} (copy)",
        description=dashboard.description,
        layout_config=deepcopy(dashboard.layout_config or {}),
        is_default=False,
    )
    db.add(copy)
    db.flush()
    for widget in list_widgets(db, dashboard.id):
        db.add(Widget(
            dashboard_id=copy.id,
            chart_type=widget.chart_type,
            title=widget.title,
            config=deepcopy(widget.config or {}),
            data_mapping=deepcopy(widget.data_mapping or {}),
            position=deepcopy(widget.position or {}),
            size=deepcopy(widget.size or {}),
        ))
    db.commit()
    db.refresh(copy)
    return copy
