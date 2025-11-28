# api/notifications/notifications_schema.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Literal, Optional

class NotificationRead(BaseModel):
    id: int
    user_id: int
    message: str
    type: Literal["info", "alert", "reminder"]
    read: bool = Field(..., alias="read_status")
    link: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
