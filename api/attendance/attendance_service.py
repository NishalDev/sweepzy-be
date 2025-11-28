# api/attendance/attendance_service.py

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from api.attendance.attendance_tokens_model import AttendanceToken
from api.attendance.attendance_records_model import AttendanceRecord, AttendanceMethod
from api.cleanup_events.cleanup_events_model import CleanupEvent  # to fetch start/end
from api.attendance.attendance_tokens_model import AttendanceToken as TokenModel
from api.attendance.attendance_records_model import AttendanceRecord as RecordModel

class AttendanceService:
    def __init__(self, db: Session):
        self.db = db

    def generate_token(
        self,
        event_id: UUID,
        user_id: int,
        length: int = 4
    ) -> TokenModel:
        event = self.db.query(CleanupEvent).get(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        self.db.query(AttendanceToken).filter_by(
            event_id=event_id, user_id=user_id
        ).delete()

        import secrets, string
        alphabet = string.ascii_uppercase + string.digits
        token_str = ''.join(secrets.choice(alphabet) for _ in range(length))

        token = AttendanceToken(
            event_id         = event_id,
            user_id          = user_id,
            token            = token_str,
            not_valid_before = event.scheduled_date,
            expires_at       = event.scheduled_date + timedelta(hours=2),
        )

        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

 
    def fetch_token_and_checkin(
    self,
    event_id: UUID,
    user_id: int
) -> Optional[dict]:
        now = datetime.now(timezone.utc)

        token = (
        self.db.query(TokenModel)
        .filter_by(event_id=event_id, user_id=user_id)
        .filter(TokenModel.not_valid_before <= now)
        .filter(TokenModel.expires_at >= now)
        .one_or_none()
    )

        if not token:
            return None

        checked_in = (
            self.db.query(
            self.db.query(AttendanceRecord)
            .filter_by(event_id=event_id, user_id=user_id)
            .exists()
        )
        .scalar()
        )

        return {
            "token": token,
            "checked_in": checked_in
        }
        
    def record_attendance(
        self,
        event_id: UUID,
        user_id: int,
        token_str: str,
        recorder_id: int,
        method: AttendanceMethod = AttendanceMethod.token,
        details: dict | None = None
    ) -> RecordModel:
        now = datetime.now(timezone.utc)
        tok = (
            self.db.query(AttendanceToken)
            .filter_by(event_id=event_id, user_id=user_id, token=token_str)
            .one_or_none()
        )
        if not tok:
            raise HTTPException(status_code=400, detail="Invalid token")
        if now < tok.not_valid_before:
            raise HTTPException(status_code=400, detail="Too early to check in")
        if now > tok.expires_at:
            raise HTTPException(status_code=400, detail="Token expired")
        if tok.used_at:
            raise HTTPException(status_code=400, detail="Token already used")

        tok.used_at = now

        rec = AttendanceRecord(
            event_id    = event_id,
            user_id     = user_id,
            recorded_by = recorder_id,
            method      = method,
            details     = details
        )
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def list_event_records(self, event_id: UUID) -> List[RecordModel]:
        return (
            self.db.query(AttendanceRecord)
                .filter_by(event_id=event_id)
                .order_by(AttendanceRecord.checked_in_at.asc())
                .all()
        )

    def list_user_records(self, user_id: int) -> List[RecordModel]:
        return (
            self.db.query(AttendanceRecord)
                .filter_by(user_id=user_id)
                .order_by(AttendanceRecord.checked_in_at.desc())
                .all()
        )
