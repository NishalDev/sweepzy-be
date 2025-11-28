from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from api.litter_detections.litter_detections_controller import (
    create_detection_controller,
    get_detections_controller
)
from api.litter_detections.litter_detections_schema import (
    LitterDetectionResponse,
    LitterDetectionCreateInput
)
from config.database import get_db

router = APIRouter(prefix="/litter_detections", tags=["Litter Detections"])

@router.post("/", response_model=LitterDetectionResponse, summary="Run AI model & create litter detection")
def create_litter_detection_endpoint(
    input_data: LitterDetectionCreateInput,
    db: Session = Depends(get_db)
):
    """
    Run AI model on the image of an existing litter report and store detection result.

    - **litter_report_id**: UUID of the litter report (in request body)
    """
    return create_detection_controller(input_data.litter_report_id, db)

@router.get("/report/{litter_report_id}", response_model=List[LitterDetectionResponse], summary="Get detections for a litter report")
def get_detections_for_report_endpoint(
    litter_report_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve all detection records associated with a given litter report.
    
    - **litter_report_id**: UUID of the litter report (as path param)
    """
    return get_detections_controller(litter_report_id, db)
