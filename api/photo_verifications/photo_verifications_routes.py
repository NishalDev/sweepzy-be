from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.photo_verifications.photo_verifications_schema import (
    PhotoVerificationIn, PhotoVerificationOut, PhotoVerificationReview
)
from api.photo_verifications.photo_verifications_controller import PhotoVerificationController
from api.uploads.uploads_controller import create_upload_controller

router = APIRouter(prefix="/photo-verifications", tags=["photo-verifications"])

@router.post(
    "/events/{event_id}",
    response_model=PhotoVerificationOut,
    summary="Capture before/after photos for an event"
)
async def create_verification(
    event_id: UUID,
    report_id: UUID = Form(...),                # ← report_id from form
    phase: str = Form(...),                     # ← phase from form
    photos: List[UploadFile] = File(...),       # ← your files
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> PhotoVerificationOut:
    user_id = current_user["id"]
    photo_urls: List[str] = []

    # 1️⃣ Save each upload and collect the URLs
    for file in photos:
        upload = create_upload_controller(
            file       = file,
            db         = db,
            latitude   = None,
            longitude  = None,
            user_id    = user_id,
            session_id = None,
        )
        photo_urls.append(upload.file_url)

    # 2️⃣ Build your Pydantic payload
    payload = PhotoVerificationIn(
        report_id  = report_id,
        phase      = phase,
        photo_urls = photo_urls
    )

    # 3️⃣ Delegate to your controller
    return PhotoVerificationController.create(
        event_id         = event_id,
        payload          = payload,
        db               = db,
        current_user_id  = user_id
    )
@router.get(
    "/events/{event_id}",
    response_model=List[PhotoVerificationOut],
    summary="List photo verifications by event"
)
def list_event_verifications(
    event_id: UUID,
    phase: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> List[PhotoVerificationOut]:
    return PhotoVerificationController.list_event(event_id, phase, status, db)

@router.get(
    "/{id}",
    response_model=PhotoVerificationOut,
    summary="Get a single photo verification record"
)
def get_verification(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> PhotoVerificationOut:
    return PhotoVerificationController.get(id, db)

@router.put(
    "/{id}/review",
    response_model=PhotoVerificationOut,
    summary="Approve or reject a photo verification record"
)
def review_verification(
    id: UUID,
    payload: PhotoVerificationReview,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> PhotoVerificationOut:
    return PhotoVerificationController.review(id, payload, db, current_user['id'])
