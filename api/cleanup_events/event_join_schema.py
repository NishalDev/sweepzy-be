from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

from api.cleanup_events.event_join_model import EventJoinRole, EventJoinStatus


# Shared base for internal usage
class EventJoinBase(BaseModel):
    cleanup_event_id: UUID
    user_id: int
    role: EventJoinRole
    status: EventJoinStatus
    notes: Optional[str] = None


# Client-side join creation (just needs event ID)
class EventJoinCreate(BaseModel):
    cleanup_event_id: UUID


# Update schema
class EventJoinUpdate(BaseModel):
    status: Optional[EventJoinStatus] = None
    notes: Optional[str] = None
    role: Optional[EventJoinRole] = None


# Internal DB response structure
class EventJoinInDBBase(EventJoinBase):
    id: int
    joined_at: datetime
    auto_approved: bool
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Final response model
class EventJoin(EventJoinInDBBase):
    pass


# Public participant listing
class EventParticipantResponse(BaseModel):
    user_id: int
    username: str
    role: EventJoinRole
    status: EventJoinStatus
    checked_in: bool
    
    model_config = ConfigDict(from_attributes=True)

class UsernameOnlyResponse(BaseModel):
    username: str
