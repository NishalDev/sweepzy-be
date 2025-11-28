# city_schema.py
from pydantic import BaseModel
from datetime import datetime

class CityBase(BaseModel):
    name: str

class CityCreate(CityBase):
    pass

class CityRead(CityBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
