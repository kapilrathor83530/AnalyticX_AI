from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    title: str
    message: str
    level: str
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    title: str
    message: str
    level: str = "info"
