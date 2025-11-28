from uuid import UUID
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.cleanup_events.dashboard.management_controller import ManagementController
from api.cleanup_events.dashboard.dashboard_schema import DashboardOut
from api.cleanup_events.cleanup_events_model import CleanupEvent

router = APIRouter(prefix="/cleanup_events", tags=["cleanup_events"])

@router.get(
    "/{event_id}/dashboard",
    response_model=DashboardOut,
    summary="Host dashboard: photo-verification progress + attendance list"
)
def get_event_dashboard(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> Any:
    # Optional: Only allow host to view dashboard
    event = db.query(CleanupEvent).get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if current_user["id"] != event.organized_by:
        raise HTTPException(status_code=403, detail="Not authorized to access this dashboard")

    return ManagementController.get_dashboard(event_id, db)
