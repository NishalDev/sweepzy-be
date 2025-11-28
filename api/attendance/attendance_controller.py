# api/attendance/attendance_controller.py

from typing import List
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.attendance.attendance_service import AttendanceService
from api.attendance.attendance_tokens_model import AttendanceToken
from api.attendance.attendance_records_model import AttendanceRecord, AttendanceMethod
from api.attendance.attendance_schema import (
    TokenOut,
    AttendanceIn,
    AttendanceOut,
)

class AttendanceController:
    @staticmethod
    def generate_token(
        event_id: UUID,
        db: Session,
        current_user_id: int,
    ) -> TokenOut:
        svc = AttendanceService(db)
        token = svc.generate_token(event_id, current_user_id)
        return TokenOut.model_validate({
            "token": token.token,
            "not_valid_before": token.not_valid_before,
            "expires_at": token.expires_at,
        })

    @staticmethod
    def fetch_token(
    event_id: UUID,
    db: Session,
    current_user_id: int,
) -> TokenOut:
        svc = AttendanceService(db)

        result = svc.fetch_token_and_checkin(event_id, current_user_id)

        if not result:
            raise HTTPException(status_code=404, detail="No valid token found")

        token = result["token"]
        checked_in = result["checked_in"]

        return TokenOut(
        token=token.token,
        not_valid_before=token.not_valid_before,
        expires_at=token.expires_at,
        checked_in=checked_in
    )
    
    @staticmethod
    def check_in(
        event_id: UUID,
        payload: AttendanceIn,
        db: Session,
        current_user_id: int,
    ) -> AttendanceOut:
        svc = AttendanceService(db)
        try:
            rec = svc.record_attendance(
                event_id=event_id,
                user_id=payload.user_id,
                token_str=payload.token,
                recorder_id=current_user_id,
                method=AttendanceMethod.token,
                details=None,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return AttendanceOut.model_validate({
            "event_id": rec.event_id,
            "user_id": rec.user_id,
            "checked_in_at": rec.checked_in_at,
            "recorded_by": rec.recorded_by,
            "method": rec.method,
            "details": rec.details,
        })

    @staticmethod
    def list_event_records(
        event_id: UUID,
        db: Session,
        current_user_id: int,
    ) -> List[AttendanceOut]:
        svc = AttendanceService(db)
        rows = svc.list_event_records(event_id)
        return [
            AttendanceOut.model_validate({
                "event_id": r.event_id,
                "user_id": r.user_id,
                "checked_in_at": r.checked_in_at,
                "recorded_by": r.recorded_by,
                "method": r.method,
                "details": r.details,
            })
            for r in rows
        ]

    @staticmethod
    def list_my_records(
        db: Session,
        current_user_id: int,
    ) -> List[AttendanceOut]:
        svc = AttendanceService(db)
        rows = svc.list_user_records(current_user_id)
        return [
            AttendanceOut.model_validate({
                "event_id": r.event_id,
                "user_id": r.user_id,
                "checked_in_at": r.checked_in_at,
                "recorded_by": r.recorded_by,
                "method": r.method,
                "details": r.details,
            })
            for r in rows
        ]
