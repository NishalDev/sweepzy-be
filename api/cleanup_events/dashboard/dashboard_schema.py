from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class AttendanceOut(BaseModel):
    username: str = Field(..., description="The volunteer's username")
    checked_in_at: datetime = Field(
        ...,
        description="Timestamp when the volunteer checked in"
    )
    method: str = Field(
        ...,
        description="How the volunteer checked in (e.g. 'token', 'photo')"
    )

class Progress(BaseModel):
    total_reports: int = Field(..., description="Total number of litter reports in this event")
    verified_reports: int = Field(..., description="Number of reports with both BEFORE & AFTER photos")
    percent: float = Field(..., description="verified_reports/total_reports * 100")

class FinalSummaryOut(BaseModel):
    # total_weight: float
    area_covered: float
    # funds_raised: float

class DashboardOut(BaseModel):
    progress: Progress
    attendance: List[AttendanceOut]
    final_summary: Optional[FinalSummaryOut] = None
