from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict
from datetime import datetime

class GroupMediaOut(BaseModel):
    id: int
    event_id: str
    uploaded_by: Optional[int]
    object_key: str
    file_url: HttpUrl
    thumb_url: Optional[HttpUrl]
    mime_type: Optional[str]
    media_type: str
    size_bytes: Optional[int]
    latitude: Optional[float]
    longitude: Optional[float]
    metadata: Optional[Dict]
    verified: bool
    created_at: datetime

    class Config:
        orm_mode = True

class PresignRequest(BaseModel):
    filenames: list[str]

class PresignEntry(BaseModel):
    key: str
    upload_url: str
    public_url: str
