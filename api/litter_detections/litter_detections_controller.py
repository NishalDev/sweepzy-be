import uuid
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from config.database import get_db
from api.litter_detections.litter_detections_service import (
    create_litter_detection,
    get_detections_for_report
)
from api.litter_detections.litter_detections_schema import LitterDetectionResponse

def get_detections_controller(litter_report_id: uuid.UUID, db: Session = Depends(get_db)):
    detections = get_detections_for_report(db, litter_report_id)
    if not detections:
        raise HTTPException(status_code=404, detail="No detections found for this litter report")
    return detections

def create_detection_controller(litter_report_id: uuid.UUID, db: Session = Depends(get_db)) -> LitterDetectionResponse:
    try:
        detection = create_litter_detection(db, litter_report_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not detection:
        raise HTTPException(status_code=400, detail="Failed to create detection record")
    return detection
