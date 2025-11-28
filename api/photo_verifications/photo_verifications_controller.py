
from uuid import UUID
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.photo_verifications.photo_verifications_schema import (
    PhotoVerificationIn, PhotoVerificationOut, PhotoVerificationReview
)
from api.photo_verifications.photo_verifications_model import PhotoPhase, VerificationStatus
from api.photo_verifications.photo_verifications_service import PhotoVerificationService

class PhotoVerificationController:
    @staticmethod
    def create(
        event_id: UUID,
        payload: PhotoVerificationIn,
        db: Session,
        current_user_id: int
    ) -> PhotoVerificationOut:
        svc = PhotoVerificationService(db)
        pv = svc.create_verification(
            event_id=event_id,
            report_id   = payload.report_id,    
            captured_by=current_user_id,     
            phase=PhotoPhase(payload.phase),
            photo_urls=payload.photo_urls
        )
        return PhotoVerificationOut.model_validate({
            **pv.__dict__
        })

    @staticmethod
    def list_event(
        event_id: UUID,
        phase: Optional[str],
        status: Optional[str],
        db: Session
    ) -> List[PhotoVerificationOut]:
        svc = PhotoVerificationService(db)
        phase_enum = PhotoPhase(phase) if phase else None
        status_enum = VerificationStatus(status) if status else None
        rows = svc.list_by_event(event_id, phase_enum, status_enum)
        return [PhotoVerificationOut.model_validate(r.__dict__) for r in rows]

    @staticmethod
    def get(
        id: UUID,
        db: Session
    ) -> PhotoVerificationOut:
        svc = PhotoVerificationService(db)
        pv = svc.get_by_id(id)
        return PhotoVerificationOut.model_validate(pv.__dict__)

    @staticmethod
    def review(
        id: UUID,
        payload: PhotoVerificationReview,
        db: Session,
        current_user_id: int
    ) -> PhotoVerificationOut:
        svc = PhotoVerificationService(db)
        try:
            pv = svc.review_verification(
                id=id,
                reviewer_id=current_user_id,
                status=VerificationStatus(payload.status)
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return PhotoVerificationOut.model_validate(pv.__dict__)