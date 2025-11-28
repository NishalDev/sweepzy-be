from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class UploadBase(BaseModel):
    """
    Shared attributes for an upload record.
    """
    user_id: int
    session_id : str
    file_name: str
    file_url: str
    content_type: Optional[str] = None
    size: Optional[int] = None  # in bytes
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class UploadCreate(UploadBase):
    """
    Attributes required to create a new upload record.
    """
    pass

class UploadResponse(UploadBase):
    """
    Attributes returned in responses for an upload record.
    """
    id: UUID
    uploaded_at: datetime

    class Config:
        orm_mode = True
