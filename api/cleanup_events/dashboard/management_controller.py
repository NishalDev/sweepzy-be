from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from api.cleanup_events.cleanup_events_model import CleanupEvent
from api.cleanup_events.cleanup_events_schema import EventStatus
from api.cleanup_events.dashboard.management_service import ManagementService
from api.cleanup_events.dashboard.dashboard_schema import DashboardOut
from api.cleanup_events.dashboard.dashboard_schema import AttendanceOut

class ManagementController:
    @staticmethod
    def get_dashboard(event_id: UUID, db: Session) -> DashboardOut:
        # Check if event exists
        event = db.query(CleanupEvent).get(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Get progress and attendance from service
        svc = ManagementService(db)
        progress, attendance_dicts = svc.get_dashboard(event_id)

        # Convert each dict to AttendanceOut (username, checked_in_at, method)
        attendance = [
            AttendanceOut.model_validate(item)
            for item in attendance_dicts
        ]

        # Fetch final summary if completed
        final_summary = None
        if event.event_status == EventStatus.completed.value:
            final_summary = svc.get_final_summary(event_id)

        return DashboardOut(
            progress=progress,
            attendance=attendance,
            final_summary=final_summary
        )
