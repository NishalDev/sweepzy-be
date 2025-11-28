from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from shapely import wkb
from shapely.geometry import mapping
from json import loads

class LitterReportBase(BaseModel):
    user_id: int
    upload_id: UUID
    latitude: float
    longitude: float
    is_detected: bool = False
    is_mapped: bool = False
    is_grouped: bool = False
    detection_results: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None       # low, medium, high
    reviewed_by: Optional[int] = None
    reward_points: int = 0              # default zero
    status: str = "pending"
    geom: Optional[Dict[str, Any]] = None
    city_id: Optional[int] = None
    landmark_id: Optional[int] = None

    @validator("detection_results", pre=True, always=True)
    def parse_detection_results(cls, v):
        """
        Ensure detection_results is a dict, parsing from JSON string if necessary.
        """
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return loads(v)
            except ValueError:
                raise ValueError("Invalid JSON for detection_results")
        return v
class LitterReportCreate(LitterReportBase):
    pass

class LitterReportUpdate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_detected: Optional[bool] = None
    is_mapped: Optional[bool] = None
    is_grouped: Optional[bool] = None
    detection_results: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None
    reviewed_by: Optional[int] = None
    reward_points: Optional[int] = None
    status: Optional[str] = None
    geom: Optional[Dict[str, Any]] = None
    city_id: Optional[int] = None
    landmark_id: Optional[int] = None

class LitterReportResponse(LitterReportBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    image_url: Optional[str] = None
    detection_id: Optional[UUID] = None
    
    @validator("geom", pre=True, always=True)
    def parse_geom(cls, v):
        """
        Convert raw WKBElement or bytes into GeoJSON dict.
        """
        if v is None:
            return None
        try:
            data = bytes(v.data) if hasattr(v, 'data') else bytes(v)
            geom_obj = wkb.loads(data)
            return mapping(geom_obj)
        except Exception:
            if isinstance(v, dict):
                return v
            raise

    class Config:
        from_attributes = True
        orm_mode = True

class GroupSummary(BaseModel):
    id: UUID
    name: str
    coverage_area: Optional[Dict[str, Any]] = None

    @validator("coverage_area", pre=True, always=True)
    def parse_coverage(cls, v):
        if v is None:
            return None
        try:
            data = bytes(v.data) if hasattr(v, "data") else bytes(v)
            shape = wkb.loads(data)
            return mapping(shape)
        except Exception:
            return None

class LitterReportListResponse(BaseModel):
    total_count: int
    total_litter_count: int
    reports: List[LitterReportResponse]
    groups: List[GroupSummary]          # now returns multiple clusters
    group: Optional[GroupSummary] = None  # optional single for legacy

    class Config:
        orm_mode = True