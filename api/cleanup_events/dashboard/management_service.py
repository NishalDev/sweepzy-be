from typing import List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from api.attendance.attendance_records_model import AttendanceRecord
from api.user.user_model import User  # <-- import your User model
from api.cleanup_events.cleanup_events_model import CleanupEvent
from api.photo_verifications.photo_verifications_model import PhotoVerification, PhotoPhase
from api.litter_reports.litter_reports_model import LitterReport

class ManagementService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(self, event_id: UUID) -> Tuple[dict, List[dict]]:
        # 1) Total litter reports
        total_reports = (
            self.db.query(func.count(LitterReport.id))
              .join(CleanupEvent, CleanupEvent.litter_group_id == LitterReport.group_id)
              .filter(CleanupEvent.id == event_id)
              .scalar()
        ) or 0

        # 2) Verified reports = has both before & after
        before_sq = (
            select(PhotoVerification.report_id)
              .where(
                  PhotoVerification.event_id == event_id,
                  PhotoVerification.phase == PhotoPhase.before
              )
              .distinct()
              .subquery()
        )
        after_sq = (
            select(PhotoVerification.report_id)
              .where(
                  PhotoVerification.event_id == event_id,
                  PhotoVerification.phase == PhotoPhase.after
              )
              .distinct()
              .subquery()
        )

        verified_count = (
            self.db.query(func.count())
              .select_from(
                before_sq.join(after_sq, before_sq.c.report_id == after_sq.c.report_id)
              )
              .scalar()
        ) or 0

        percent = (verified_count / total_reports * 100) if total_reports else 0.0

        progress = {
            "total_reports": total_reports,
            "verified_reports": verified_count,
            "percent": round(percent, 1),
        }

        # 3) Attendance list: join AttendanceRecord -> User to fetch username
        rows = (
            self.db.query(
                AttendanceRecord.checked_in_at,
                AttendanceRecord.method,
                User.username
            )
            .join(User, User.id == AttendanceRecord.user_id)
            .filter(AttendanceRecord.event_id == event_id)
            .order_by(AttendanceRecord.checked_in_at.asc())
            .all()
        )

        # Map into dicts matching AttendanceOut schema
        attendance = [
            {
                "username": username,
                "checked_in_at": checked_in_at,
                "method": method,
            }
            for checked_in_at, method, username in rows
        ]

        return progress, attendance

    def get_final_summary(self, event_id: UUID) -> dict:
        # Dummy area covered (km²). Replace with your real calculation if available.
        area_covered = 1.2

        return {
            "area_covered": round(area_covered, 2)
        }
