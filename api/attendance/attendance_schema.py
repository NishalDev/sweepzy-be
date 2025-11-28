# api/attendance/attendance_schema.py

from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from api.attendance.attendance_records_model import AttendanceMethod


class TokenOut(BaseModel):
    token: str
    not_valid_before: datetime
    expires_at: datetime
    checked_in: bool = False

class AttendanceIn(BaseModel):
    """
    Payload for a field recorder to check in a user.
    """
    user_id: int
    token: str


class AttendanceOut(BaseModel):
    event_id: UUID
    user_id: int
    checked_in_at: datetime
    recorded_by: int
    method: AttendanceMethod
    details: Optional[Dict[str, Any]] = None
    
    
    model_config = ConfigDict(from_attributes=True)
