# api/geo/geo_schema.py

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class ReportCoordsOut(BaseModel):
    report_id: UUID = Field(..., description="Unique ID of the litter report")
    latitude: float = Field(..., description="Latitude of the reported litter location")
    longitude: float = Field(..., description="Longitude of the reported litter location")
    image_url: Optional[str] = Field(
        None, description="URL of the image associated with the report"
    )
    class Config:
        orm_mode = True


class GeoValidateIn(BaseModel):
    report_id: UUID = Field(..., description="ID of the litter report to validate against")
    user_lat: float = Field(..., description="Latitude of the user's current position")
    user_lon: float = Field(..., description="Longitude of the user's current position")
    threshold: Optional[float] = Field(
        10.0,
        description="Distance threshold in meters to consider user 'in range'"
    )


class GeoValidateOut(BaseModel):
    report_id: UUID = Field(..., description="ID of the litter report validated")
    distance: float = Field(..., description="Computed distance in meters between user and report")
    bearing: float = Field(..., description="Computed bearing in degrees from user to report")
    in_range: bool = Field(..., description="Whether the user is within the threshold distance")
