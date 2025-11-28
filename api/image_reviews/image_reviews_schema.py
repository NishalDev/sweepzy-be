from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ImageReviewBase(BaseModel):
    litter_report_id: UUID
    reviewed_by: Optional[int] = None
    review_status: Optional[str] = "pending"
    review_notes: Optional[str] = None
    is_duplicate: Optional[bool] = False
    reviewed_at: Optional[datetime] = None

class ImageReviewCreate(ImageReviewBase):
    pass

class ImageReviewResponse(ImageReviewBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
