from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.photo_verifications.group_media.group_media_service import GroupMediaService


class GroupMediaController:
    @staticmethod
    async def direct_upload(event_id, upload_files, latitude: Optional[float], longitude: Optional[float], db: Session, current_user_id: int):
        svc = GroupMediaService(db)
        try:
            return await svc.upload_and_create(event_id, upload_files, latitude, longitude, current_user_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail="Upload failed")

    @staticmethod
    def list_event(event_id, media_type: Optional[str], limit: int, offset: int, db: Session):
        svc = GroupMediaService(db)
        return svc.list_by_event(event_id, media_type, limit, offset)

    @staticmethod
    def delete(event_id, media_id: int, db: Session, current_user_id: int):
        svc = GroupMediaService(db)
        try:
            svc.delete_media(event_id, media_id, current_user_id)
            return {"ok": True}
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception:
            raise HTTPException(status_code=500, detail="Delete failed")
