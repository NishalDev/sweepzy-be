# api/photo_verifications/photo_verification_service.py

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from api.photo_verifications.photo_verifications_model import (
    PhotoVerification, PhotoPhase, VerificationStatus
)

class PhotoVerificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_verification(
        self,
        event_id: UUID,
        report_id: UUID,
        captured_by: int,
        phase: PhotoPhase,
        photo_urls: List[str]
    ) -> PhotoVerification:
        # 1️⃣ Try to find an existing record for this event/report/user/phase
        existing = (
            self.db.query(PhotoVerification)
            .filter_by(
                event_id=event_id,
                report_id=report_id,        # include report in filter
                captured_by=captured_by,
                phase=phase
            )
            .one_or_none()
        )

        if existing:
            # 2️⃣ Append new URLs to the JSON array
            existing.photo_urls = existing.photo_urls + photo_urls
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # 3️⃣ Otherwise create a new record
        pv = PhotoVerification(
            event_id    = event_id,
            report_id   = report_id,
            captured_by = captured_by,
            phase       = phase,
            photo_urls  = photo_urls
        )
        self.db.add(pv)
        self.db.commit()
        self.db.refresh(pv)
        return pv

    def list_by_event(
        self,
        event_id: UUID,
        phase: Optional[PhotoPhase] = None,
        status: Optional[VerificationStatus] = None
    ) -> List[PhotoVerification]:
        query = self.db.query(PhotoVerification).filter_by(event_id=event_id)
        if phase:
            query = query.filter_by(phase=phase)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(PhotoVerification.captured_at.asc()).all()

    def get_by_id(self, id: UUID) -> PhotoVerification:
        pv = self.db.query(PhotoVerification).get(id)
        if not pv:
            raise HTTPException(status_code=404, detail="Photo verification not found")
        return pv

    def review_verification(
        self,
        id: UUID,
        reviewer_id: int,
        status: VerificationStatus
    ) -> PhotoVerification:
        pv = self.get_by_id(id)
        pv.status = status
        pv.reviewed_by = reviewer_id
        from datetime import datetime
        pv.reviewed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(pv)
        return pv