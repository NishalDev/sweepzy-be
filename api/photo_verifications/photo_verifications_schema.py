# api/photo_verifications/photo_verifications_schema.py

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from api.photo_verifications.photo_verifications_model import PhotoPhase, VerificationStatus


class PhotoVerificationIn(BaseModel):
    """
    Payload for creating a photo verification record.
    """
    report_id: UUID  
    phase: PhotoPhase
    photo_urls: List[str] = Field(..., description="List of S3 URLs for uploaded photos")


class PhotoVerificationOut(BaseModel):
    id: UUID
    event_id: UUID
    report_id: UUID
    captured_by: int
    phase: PhotoPhase
    photo_urls: List[str]
    captured_at: datetime
    status: VerificationStatus
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PhotoVerificationReview(BaseModel):
    """
    Payload for approving or rejecting a photo verification.
    """
    status: VerificationStatus
