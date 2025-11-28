# api/geo/geo_service.py

from typing import List, Tuple, Dict, Any
from math import radians, sin, cos, atan2, sqrt
from uuid import UUID
from sqlalchemy.orm import Session, joinedload   
from fastapi import HTTPException

from api.litter_reports.litter_reports_model import LitterReport
from api.cleanup_events.cleanup_events_model import CleanupEvent

class GeoService:
    def __init__(self, db: Session):
        self.db = db

    def list_reports_by_event(self, event_id: UUID) -> List[Dict[str, Any]]:
        """
        Return all litter reports for the given event via the event's litter_group_id,
        including each report’s uploaded image URL.
        """
        # 1) Fetch the event and its linked group
        event = self.db.query(CleanupEvent).get(event_id)
        if not event or not event.litter_group_id:
            raise HTTPException(status_code=404, detail="Event or linked group not found")

        # 2) Query reports with eager loading of upload
        reports = (
            self.db
            .query(LitterReport)
            .options(joinedload(LitterReport.upload))
            .filter_by(group_id=event.litter_group_id)
            .all()
        )
        if not reports:
            raise HTTPException(status_code=404, detail="No reports found for event")

        # 3) Build a simple dict list including file_url
        response: List[Dict[str, Any]] = []
        for r in reports:
            response.append({
                "id":         r.id,
                "latitude":   r.latitude,
                "longitude":  r.longitude,
                "status":     r.status,
                "created_at": r.created_at,
                "image_url":  getattr(r.upload, "file_url", None),
            })
        return response

    def compute_distance_bearing(
        self,
        user_lat: float,
        user_lon: float,
        target_lat: float,
        target_lon: float
    ) -> Tuple[float, float]:
        """
        Returns (distance_in_meters, bearing_in_degrees_from_north) between user and target.
        """
        R = 6371000.0  # Earth radius in meters
        φ1, φ2 = radians(user_lat), radians(target_lat)
        Δφ = radians(target_lat - user_lat)
        Δλ = radians(target_lon - user_lon)

        a = sin(Δφ / 2) ** 2 + cos(φ1) * cos(φ2) * sin(Δλ / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c

        y = sin(Δλ) * cos(φ2)
        x = cos(φ1) * sin(φ2) - sin(φ1) * cos(φ2) * cos(Δλ)
        bearing = (atan2(y, x) * 180.0 / 3.141592653589793 + 360) % 360

        return distance, bearing

    def validate_proximity(
        self,
        report_id: UUID,
        user_lat: float,
        user_lon: float,
        threshold: float = 10.0
    ) -> Dict[str, Any]:
        """
        Validate that the user is within `threshold` meters of the report.
        Returns a dict with keys: report_id, distance, bearing, in_range.
        """
        report = self.db.query(LitterReport).get(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        distance, bearing = self.compute_distance_bearing(
            user_lat, user_lon, report.latitude, report.longitude
        )
        in_range = distance <= threshold

        return {
            "report_id": str(report_id),
            "distance": distance,
            "bearing": bearing,
            "in_range": in_range
        }
