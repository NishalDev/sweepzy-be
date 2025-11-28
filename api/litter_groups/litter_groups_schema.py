# Pydantic schemas for LitterGroup (schemas/litter_group.py)
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any, List
from uuid import UUID as UUIDType
from datetime import datetime
from api.litter_reports.litter_reports_schema import LitterReportResponse

# ─── Base Model ───────────────────────────────────────────────────────────────
class LitterGroupBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., max_length=100, description="Name of the litter group")
    description: Optional[str] = Field(None, description="Optional description of the group")
    location: Optional[str] = Field(None, max_length=100, description="Optional textual location of the group")
    severity: Optional[str] = Field(None, description="Severity level: low | medium | high")
# ─── Create / Update Schemas ──────────────────────────────────────────────────
class LitterGroupCreate(LitterGroupBase):
    # Provide lat/lng for automatic geom computation
    lat: float = Field(..., description="Latitude of group center")
    lng: float = Field(..., description="Longitude of group center")
    group_type: Optional[str] = Field("public", description="Group visibility: public | private")

class LitterGroupUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=100)
    lat: Optional[float] = Field(None, description="New latitude for group center")
    lng: Optional[float] = Field(None, description="New longitude for group center")
    group_type: Optional[str] = Field(None, description="Change visibility: public | private")
    severity: Optional[str] = Field(None, description="Update severity level") 
    
# ─── Read / Response Schema ───────────────────────────────────────────────────
class LitterGroupRead(LitterGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUIDType
    created_by: int
    group_type: str
    status: str
    verification_status: str
    member_count: int
    report_count: int
    geom: Optional[Dict[str, Any]] = Field(
        None, description="GeoJSON geometry of the group center"
    )
    coverage_area: Optional[Dict[str, Any]] = Field(
        None, description="GeoJSON polygon of group coverage area"
    )
    created_at: datetime
    updated_at: datetime
    event_id: Optional[UUIDType] = None
    is_locked: bool
    litter_reports: List[LitterReportResponse] = []
    # Map thumbnails
    centroid_lat: Optional[float] = Field(
        None, description="Latitude of the event's cluster centroid"
    )
    centroid_lng: Optional[float] = Field(
        None, description="Longitude of the event's cluster centroid"
    )

    @field_validator('geom', mode='before')
    @classmethod
    def _validate_geom(cls, v):
        """
        Convert raw WKBElement from SQLAlchemy into GeoJSON dict.
        """
        from geoalchemy2.shape import to_shape
        from shapely.geometry import mapping
        from geoalchemy2.elements import WKBElement
        if isinstance(v, WKBElement):
            return mapping(to_shape(v))
        return v

    @field_validator('coverage_area', mode='before')
    @classmethod
    def _validate_coverage_area(cls, v):
        """
        Convert raw WKBElement (Polygon) into GeoJSON dict.
        """
        from geoalchemy2.shape import to_shape
        from shapely.geometry import mapping
        from geoalchemy2.elements import WKBElement
        if isinstance(v, WKBElement):
            return mapping(to_shape(v))
        return v
# ─── Cluster Suggestion Schema ───────────────────────────────────────────────
class ClusterSuggestion(BaseModel):
    cluster_id: int
    report_count: int
    avg_severity: str
    hull: Optional[Dict[str, Any]]   = None
    bbox: Optional[Dict[str, Any]]   = None
    members: Optional[List[Dict]]    = None

    class Config:
        schema_extra = {
            "example": {
                "cluster_id": 5,
                "report_count": 12,
                "avg_severity": "low",
                "hull": {
                    "type": "Polygon",
                    "coordinates": [
                        [[77.59,12.96],[77.61,12.96],[77.61,12.99],[77.59,12.99],[77.59,12.96]]
                    ]
                },
                "bbox": {
                    "type": "Polygon",
                    "coordinates": [
                        [[77.59,12.96],[77.61,12.96],[77.61,12.99],[77.59,12.99],[77.59,12.96]]
                    ]
                },
                "members": [
                    {
                        "id": "uuid-1234",
                        "point": {"type":"Point","coordinates":[77.5987,12.9719]},
                        "severity": "high"
                    },
                  
                ]
            }
        }