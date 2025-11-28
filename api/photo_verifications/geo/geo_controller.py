# api/geo/geo_controller.py

from uuid import UUID
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.photo_verifications.geo.geo_service import GeoService
from api.photo_verifications.geo.geo_schema import (
    ReportCoordsOut,
    GeoValidateIn,
    GeoValidateOut
)

class GeoController:
    @staticmethod
    def list_report_coords(
        event_id: UUID,
        db: Session
    ) -> List[ReportCoordsOut]:
        svc = GeoService(db)
        # Now returns List[dict] with keys: id, latitude, longitude, image_url
        reports = svc.list_reports_by_event(event_id)
        return [
            ReportCoordsOut(
                report_id= r["id"],
                latitude=  r["latitude"],
                longitude= r["longitude"],
                image_url= r.get("image_url")
            )
            for r in reports
        ]

    @staticmethod
    def validate_location(
        payload: GeoValidateIn,
        db: Session
    ) -> GeoValidateOut:
        svc = GeoService(db)
        try:
            result = svc.validate_proximity(
                payload.report_id,
                payload.user_lat,
                payload.user_lon,
                payload.threshold
            )
        except HTTPException as e:
            raise e

        return GeoValidateOut(
            report_id=payload.report_id,
            distance=result["distance"],
            bearing=result["bearing"],
            in_range=result["in_range"]
        )
