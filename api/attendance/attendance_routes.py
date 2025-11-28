# api/attendance/attendance_routes.py

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.attendance.attendance_schema import TokenOut, AttendanceIn, AttendanceOut
from api.attendance.attendance_controller import AttendanceController

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get(
    "/events/{event_id}/token",
    response_model=TokenOut,
    summary="Fetch existing attendance token (if still valid)",
)
def fetch_token(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
) -> TokenOut:
    user_id = current_user["id"]
    return AttendanceController.fetch_token(event_id, db, user_id)


@router.post(
    "/events/{event_id}/checkin",
    response_model=AttendanceOut,
    summary="Field recorder checks in a user by validating their token",
)
def check_in(
    event_id: UUID,
    payload: AttendanceIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
) -> AttendanceOut:
    recorder_id = current_user["id"]
    return AttendanceController.check_in(event_id, payload, db, recorder_id)


@router.get(
    "/events/{event_id}/records",
    response_model=List[AttendanceOut],
    summary="List all attendance records for an event",
)
def list_event_records(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
) -> List[AttendanceOut]:
    user_id = current_user["id"]
    return AttendanceController.list_event_records(event_id, db, user_id)


@router.get(
    "/users/me/records",
    response_model=List[AttendanceOut],
    summary="List my own attendance records",
)
def list_my_records(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
) -> List[AttendanceOut]:
    user_id = current_user["id"]
    return AttendanceController.list_my_records(db, user_id)
