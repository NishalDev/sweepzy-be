from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


class NearbyLitterOut(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    before_image_url: Optional[str]
    after_image_url: Optional[str]
    distance_km: float
    status: str

    class Config:
        orm_mode = True


class EventOut(BaseModel):
    id: UUID
    name: str
    date: datetime
    location: Optional[str]
    centroid_lat: Optional[float] = None
    centroid_lng: Optional[float] = None
    event_status: Optional[str] = None

    class Config:
        orm_mode = True


class AnalyticsOut(BaseModel):
    avg_participants_per_event: float
    percent_events_verified: float


class LitterTypeBreakdownOut(BaseModel):
    plastic_bottle: int
    plastic_bag: int
    paper_waste: int
    food_wrapper: int

    class Config:
        orm_mode = True


class DashboardResponse(BaseModel):
    # ─── User Dashboard ──────────────────────────────────────────────────
    total_reports: Optional[int] = None
    cleaned_reports: Optional[int] = None
    points: Optional[int] = None
    nearby_litter: List[NearbyLitterOut] = []
    upcoming_events: List[EventOut] = []
    registered_events: List[EventOut] = []
    # ─── Host Dashboard ──────────────────────────────────────────────────
    total_events: Optional[int] = None
    participants_engaged: Optional[int] = None
    pending_approvals: Optional[int] = None
    verified_cleanups: Optional[int] = None
    analytics: Optional[AnalyticsOut] = None
    breakdown: Optional[LitterTypeBreakdownOut] = None
    next_event: Optional[EventOut] = None
    my_events: List[EventOut] = []
    participant_names: List[str] = []

    class Config:
        orm_mode = True