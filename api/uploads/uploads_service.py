# api/uploads/uploads_service.py

import uuid
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import UploadFile
from config.database import UPLOAD_DIR  # assume you’ve defined this
from api.uploads.uploads_model import Upload
from api.user.user_service import award_points
from config.points_config import PointReason

# Ensure upload directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def create_upload_with_file(
    db: Session,
    file: UploadFile,
    latitude: float | None = None,
    longitude: float | None = None,
    user_id: int | None = None,
    session_id: str | None = None,
) -> Upload:
    """
    Save uploaded file to disk, record metadata in DB including user_id,
    optional geolocation, and optional session_id. Then award points.
    """
    # 1️⃣ Write file to disk
    ext = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / unique_name
    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_url = f"/uploads/{unique_name}"

    # 2️⃣ Persist Upload record
    upload = Upload(
        user_id=user_id,
        session_id=session_id,
        file_name=file.filename,
        file_url=file_url,
        content_type=file.content_type,
        size=dest.stat().st_size,
        latitude=latitude,
        longitude=longitude
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def get_all_uploads(db: Session):
    return db.query(Upload).order_by(Upload.uploaded_at.desc()).all()


def get_upload(db: Session, upload_id: uuid.UUID):
    return db.query(Upload).filter(Upload.id == upload_id).first()


def delete_upload(db: Session, upload_id: uuid.UUID):
    upload = get_upload(db, upload_id)
    if upload:
        # optionally delete file on disk
        try:
            Path(UPLOAD_DIR / Path(upload.file_url).name).unlink()
        except Exception:
            pass
        db.delete(upload)
        db.commit()
        return True
    return False
