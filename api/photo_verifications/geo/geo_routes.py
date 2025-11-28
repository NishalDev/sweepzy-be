# api/geo/geo_routes.py

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.photo_verifications.geo.geo_controller import GeoController
from api.photo_verifications.geo.geo_schema import ReportCoordsOut, GeoValidateIn, GeoValidateOut

router = APIRouter(prefix="/geo", tags=["geo"])

@router.get(
    "/events/{event_id}/reports",
    response_model=List[ReportCoordsOut],
    summary="List all report coordinates for an event"
)
def list_reports(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> List[ReportCoordsOut]:
    return GeoController.list_report_coords(event_id, db)

@router.post(
    "/validate",
    response_model=GeoValidateOut,
    summary="Validate user proximity to a report"
)
def validate_location(
    payload: GeoValidateIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> GeoValidateOut:
    return GeoController.validate_location(payload, db)
