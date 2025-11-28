# File: api/user_details/user_details_schema.py

from pydantic import BaseModel, AnyUrl
from typing import Optional, List, Dict
from datetime import datetime

class Availability(BaseModel):
    weekends: bool
    weekdays: List[str]

class UserDetailsBase(BaseModel):
    full_name: Optional[str] = None
    profile_photo: Optional[str] = None
    bio: Optional[str] = None

    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

    phone: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None  # e.g. {"instagram": "...", "twitter": "..."}

    cleanup_types: Optional[List[str]] = None
    availability: Optional[Availability] = None
    skills: Optional[List[str]] = None

class UserDetailsCreate(UserDetailsBase):
    pass

class UserDetailsUpdate(BaseModel):
    full_name: Optional[str] = None
    profile_photo: Optional[str] = None
    bio: Optional[str] = None

    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

    phone: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None

    cleanup_types: Optional[List[str]] = None
    availability: Optional[Availability] = None
    skills: Optional[List[str]] = None

class UserInfo(BaseModel):
    username: str
    email: str

    model_config = {
        "from_attributes": True
    }

class UserDetailsResponse(UserDetailsBase):
    id: int
    user_id: Optional[int] = None 
    user: Optional[UserInfo] = None  # Related use
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
