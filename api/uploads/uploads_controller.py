# api/uploads/uploads_controller.py
import uuid
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from api.uploads.uploads_service import (
    create_upload_with_file,
    get_all_uploads,
    get_upload,
    delete_upload
)
from api.uploads.uploads_schema import UploadResponse


def create_upload_controller(
    file: UploadFile,
    db: Session,
    latitude: float | None = None,
    longitude: float | None = None,
    user_id: uuid.UUID = None,
    session_id: str | None = None
) -> UploadResponse:
    """
    Controller now requires user_id (and optional session_id) and passes both to the service layer.
    """
    upload = create_upload_with_file(
        db,
        file,
        latitude,
        longitude,
        user_id=user_id,
        session_id=session_id
    )
    if not upload:
        raise HTTPException(status_code=400, detail="Failed to save upload")
    return upload

# list, get, delete controllers unchanged

def list_uploads_controller(db: Session):
    return get_all_uploads(db)


def get_upload_controller(upload_id: uuid.UUID, db: Session) -> UploadResponse:
    upload = get_upload(db, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


def delete_upload_controller(upload_id: uuid.UUID, db: Session):
    success = delete_upload(db, upload_id)
    if not success:
        raise HTTPException(status_code=404, detail="Upload not found")
    return {"detail": "Upload deleted successfully"}