# landmark_schema.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from api.location.city.city_schema import CityRead

class LandmarkBase(BaseModel):
    name: str
    city_id: int

class LandmarkCreate(LandmarkBase):
    pass

class LandmarkRead(LandmarkBase):
    id: int
    created_at: datetime
    # optional nested city for convenience in responses
    city: Optional[CityRead] = None

    class Config:
        orm_mode = True
