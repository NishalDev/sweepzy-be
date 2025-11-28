from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.photo_verifications.group_media.group_media_controller import GroupMediaController

router = APIRouter(prefix="/events/{event_id}/group-media", tags=["group-media"])


@router.post("/upload", summary="Upload files for group media (images or videos)")
async def upload_media(
    event_id: UUID,
    files: List[UploadFile] = File(...),
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    """
    Direct upload endpoint. Saves files on disk, creates DB rows and returns created items.
    """
    return await GroupMediaController.direct_upload(
        event_id=event_id,
        upload_files=files,
        latitude=latitude,
        longitude=longitude,
        db=db,
        current_user_id=current_user["id"],
    )


@router.get("", summary="List media for an event")
def list_media(
    event_id: UUID,
    media_type: Optional[str] = Query(None, description="Filter by 'image' or 'video'"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    return GroupMediaController.list_event(event_id, media_type, limit, offset, db)


@router.delete("/{media_id}", summary="Delete a media item (uploader or admin)")
def delete_media(
    event_id: UUID,
    media_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    return GroupMediaController.delete(event_id, media_id, db, current_user["id"])
