# api/litter_detections/litter_detections_schema.py

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class LitterDetectionBase(BaseModel):
    litter_report_id: UUID
    detected_objects: Optional[List[Dict[str, Any]]] = None
    bounding_boxes: Optional[List[List[float]]] = None
    total_litter_count: Optional[int] = None
    severity_level: Optional[str] = None
    detection_source: Optional[str] = None
    detection_confidence: Optional[float] = None
    review_status: str = "pending"
    reviewed_by: Optional[int] = None
    review_notes: Optional[str] = None

class LitterDetectionCreate(LitterDetectionBase):
    pass

class LitterDetectionUpdate(BaseModel):
    detected_objects: Optional[List[Dict[str, Any]]] = None
    bounding_boxes: Optional[List[List[float]]] = None
    total_litter_count: Optional[int] = None
    severity_level: Optional[str] = None
    detection_source: Optional[str] = None
    detection_confidence: Optional[float] = None
    review_status: Optional[str] = None
    reviewed_by: Optional[int] = None
    review_notes: Optional[str] = None

class LitterDetectionResponse(LitterDetectionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
class LitterDetectionCreateInput(BaseModel):
    litter_report_id: UUID