from pydantic import BaseModel
from datetime import datetime

class BadgeBase(BaseModel):
    name: str
    icon_key: str
    description: str

class BadgeCreate(BadgeBase):
    pass

class BadgeRead(BadgeBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class UserBadgeRead(BaseModel):
    badge: BadgeRead
    earned_at: datetime

    class Config:
        orm_mode = True
        
