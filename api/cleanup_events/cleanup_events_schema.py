# api/cleanup_events/cleanup_events_schema.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from enum import Enum
from datetime import datetime
from decimal import Decimal

from api.litter_reports.litter_reports_schema import LitterReportResponse
from api.attendance.attendance_schema import AttendanceOut


# ─── Core Enums ────────────────────────────────────────────────────────────────
class EventStatus(str, Enum):
    upcoming   = "upcoming"
    ongoing    = "ongoing"
    completed  = "completed"
    cancelled  = "cancelled"

class VerificationStatus(str, Enum):
    pending   = "pending"
    submitted = "submitted"
    verified  = "verified"
    rejected  = "rejected"


# ─── Base / Create / Update ────────────────────────────────────────────────────
class CleanupEventBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_name: str
    description: Optional[str]
    location: Optional[str]
    scheduled_date: datetime
    participant_limit: Optional[int] = None
    funding_required: Optional[Decimal] = None
    needs_approval: bool

class CleanupEventCreate(CleanupEventBase):
    litter_group_id: Optional[UUID] = None
    litter_report_ids: Optional[List[UUID]] = None

    @classmethod
    def validate(cls, values):
        if not values.get('litter_group_id') and not values.get('litter_report_ids'):
            raise ValueError('Either litter_group_id or litter_report_ids must be provided')
        return values

class CleanupEventUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    participant_limit: Optional[int] = None
    funding_required: Optional[Decimal] = None
    needs_approval: Optional[bool] = None
    event_status: Optional[EventStatus] = None
    verification_status: Optional[VerificationStatus] = None


# ─── “Read” Schema for Everyone ───────────────────────────────────────────────
class CleanupEventRead(CleanupEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    litter_group_id: Optional[UUID]
    organized_by: int
    registered_participants: int
    funds_raised: Decimal
    event_status: EventStatus
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime

    # extras
    severity: Optional[str] = None
    organizer_name: Optional[str] = None
    reports: List[LitterReportResponse] = Field(default_factory=list)
    centroid_lat: Optional[float] = None
    centroid_lng: Optional[float] = None

    joined: bool = Field(False, description="Whether current user joined")
    user_role: Optional[str] = Field(None, description="Current user’s role for this event")
    approval_status: Optional[str] = Field(None, description="Approval status if needs approval")


# ─── Admin “Submitted” Endpoints ──────────────────────────────────────────────
class CleanupEventSummary(BaseModel):
    """
    Minimal fields for listing all submitted‑for‑review events.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_name: str
    scheduled_date: datetime
    location: Optional[str]
    organized_by: int
    event_status: EventStatus
    verification_status: VerificationStatus

class ReportWithVerifications(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: UUID
    original_image: Optional[str]
    before_photos: List[str] = Field(default_factory=list)
    after_photos:  List[str] = Field(default_factory=list)

class CleanupEventDetail(BaseModel):
    """
    One submitted event with its reports (orig + before/after) and attendance.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_name: str
    description: Optional[str]
    scheduled_date: datetime
    location: Optional[str]
    organized_by: int
    event_status: EventStatus
    verification_status: VerificationStatus

    reports: List[ReportWithVerifications] = Field(
        default_factory=list,
        description="Each litter report + its before/after captures"
    )
    attendance: List[AttendanceOut] = Field(
        default_factory=list,
        description="Attendance check‑ins for this event"
    )

class UserJoinedEventOut(BaseModel):
    """
    Minimal schema for events that the current user has signed up for.
    """
    model_config = ConfigDict(from_attributes=True, orm_mode=True)

    id: UUID
    event_name: str
    scheduled_date: datetime
    event_status: EventStatus
