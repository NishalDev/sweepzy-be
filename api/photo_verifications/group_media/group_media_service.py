import os
import uuid
import mimetypes
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path

from sqlalchemy.orm import Session
from PIL import Image

from api.photo_verifications.group_media.group_media_model import GroupMedia  # adapt to your project path

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
BASE_MEDIA_URL = os.getenv("BASE_MEDIA_URL", "/media")  # mount this with StaticFiles in your app
IMAGE_WHITELIST = ("image/jpeg", "image/png", "image/webp")
VIDEO_WHITELIST = ("video/mp4", "video/webm", "video/quicktime")
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", 15 * 1024 * 1024))   # 15 MB
MAX_VIDEO_BYTES = int(os.getenv("MAX_VIDEO_BYTES", 100 * 1024 * 1024))  # 100 MB

# Ensure upload dir exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in name)


def _make_public_url(path: Path) -> str:
    """
    Given an absolute path under UPLOAD_DIR, return the public URL using BASE_MEDIA_URL.
    """
    # Ensure path is under UPLOAD_DIR
    rel = path.relative_to(UPLOAD_DIR)
    return f"{BASE_MEDIA_URL.rstrip('/')}/{rel.as_posix()}"


def _save_bytes_to_disk(b: bytes, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(b)


def _create_image_thumbnail(src_path: Path, thumb_path: Path, max_size=(640, 360)) -> Optional[Path]:
    try:
        img = Image.open(src_path)
        img.thumbnail(max_size)
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(thumb_path, format="JPEG", quality=75)
        return thumb_path
    except Exception:
        return None


def _create_video_poster(src_path: Path, thumb_path: Path, at_seconds: int = 1) -> Optional[Path]:
    """
    Try to use ffmpeg (must be installed) to extract one frame.
    """
    try:
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(at_seconds),
            "-i", str(src_path),
            "-vframes", "1",
            "-q:v", "2",
            str(thumb_path)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return thumb_path
    except Exception:
        return None


class GroupMediaService:
    def __init__(self, db: Session):
        self.db = db

    async def upload_and_create(
        self,
        event_id: str,
        upload_files,
        latitude: Optional[float],
        longitude: Optional[float],
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        upload_files: list of FastAPI UploadFile objects
        Returns list of created items
        """
        created = []

        for upload in upload_files:
            # read bytes
            try:
                contents = await upload.read()
            except Exception:
                # if read fails skip this file
                continue

            if not contents:
                continue

            # detect mime
            mime = (upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or "application/octet-stream").lower()
            is_image = mime.startswith("image/")
            is_video = mime.startswith("video/")

            # basic size validation
            size_bytes = len(contents)
            if is_image and size_bytes > MAX_IMAGE_BYTES:
                # skip and continue
                continue
            if is_video and size_bytes > MAX_VIDEO_BYTES:
                continue

            # prepare storage path: uploads/events/{event_id}/group/{uuid}_{safe_filename}
            safe_name = _safe_filename(upload.filename or "file")
            filename = f"{uuid.uuid4().hex}_{safe_name}"
            relative_folder = Path("events") / str(event_id) / "group"
            dest_rel = relative_folder / filename
            dest_abs = UPLOAD_DIR / dest_rel

            # write file
            try:
                _save_bytes_to_disk(contents, dest_abs)
            except Exception:
                # if saving fails, skip
                continue

            # generate thumbnail/poster if possible
            thumb_rel: Optional[Path] = None
            if is_image:
                thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
                candidate = relative_folder / "thumbs" / thumb_name
                thumb_abs = UPLOAD_DIR / candidate
                if _create_image_thumbnail(dest_abs, thumb_abs):
                    thumb_rel = candidate
            elif is_video:
                thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
                candidate = relative_folder / "thumbs" / thumb_name
                thumb_abs = UPLOAD_DIR / candidate
                if _create_video_poster(dest_abs, thumb_abs):
                    thumb_rel = candidate

            # public URLs
            try:
                public_url = _make_public_url(dest_abs)
            except Exception:
                # fallback to storing a relative path as URL
                public_url = f"{BASE_MEDIA_URL.rstrip('/')}/{dest_rel.as_posix()}"

            public_thumb = None
            if thumb_rel:
                thumb_abs_path = UPLOAD_DIR / thumb_rel
                try:
                    public_thumb = _make_public_url(thumb_abs_path)
                except Exception:
                    public_thumb = f"{BASE_MEDIA_URL.rstrip('/')}/{thumb_rel.as_posix()}"

            # create DB row
            gm = GroupMedia(
                event_id=str(event_id),
                uploaded_by=user_id,
                object_key=str(dest_rel.as_posix()),  # store path relative to upload dir
                file_url=public_url,
                thumb_url=public_thumb,
                mime_type=mime,
                media_type="video" if is_video else "image",
                size_bytes=size_bytes,
                latitude=latitude,
                longitude=longitude,
                metadata_json=None,   # no extracted metadata yet; set later if you extract EXIF/duration
            )

            try:
                self.db.add(gm)
                self.db.commit()
                self.db.refresh(gm)
                created.append({
                    "id": gm.id,
                    "file_url": gm.file_url,
                    "thumb_url": gm.thumb_url,
                    "mime_type": gm.mime_type,
                    "media_type": gm.media_type,
                    "size_bytes": gm.size_bytes,
                    "created_at": gm.created_at,
                })
            except Exception:
                # rollback and cleanup files if DB insert fails
                self.db.rollback()
                try:
                    if dest_abs.exists():
                        dest_abs.unlink()
                    if thumb_rel:
                        thumb_abs_any = UPLOAD_DIR / thumb_rel
                        if thumb_abs_any.exists():
                            thumb_abs_any.unlink()
                except Exception:
                    pass
                continue

        return created

    def list_by_event(self, event_id: str, media_type: Optional[str], limit: int, offset: int):
        q = self.db.query(GroupMedia).filter(GroupMedia.event_id == str(event_id)).order_by(GroupMedia.created_at.desc())
        if media_type in ("image", "video"):
            q = q.filter(GroupMedia.media_type == media_type)
        rows = q.limit(limit).offset(offset).all()
        return [
            {
                "id": r.id,
                "file_url": r.file_url,
                "thumb_url": r.thumb_url,
                "mime_type": r.mime_type,
                "media_type": r.media_type,
                "size_bytes": r.size_bytes,
                "created_at": r.created_at,
                "metadata": getattr(r, "metadata_json", None),
            }
            for r in rows
        ]

    def delete_media(self, event_id: str, media_id: int, current_user_id: int):
        row = self.db.query(GroupMedia).get(media_id)
        if not row or str(row.event_id) != str(event_id):
            raise LookupError("Media not found")

        # permission: uploader or admin — adapt to your user system
        if row.uploaded_by != current_user_id:
            raise PermissionError("Only uploader (or admin) can delete")

        # delete files from disk
        try:
            if row.object_key:
                obj_path = UPLOAD_DIR / Path(row.object_key)
                if obj_path.exists():
                    obj_path.unlink()
            if row.thumb_url:
                # thumb_url is a public url like /media/events/...
                # convert to relative path under UPLOAD_DIR
                try:
                    prefix = BASE_MEDIA_URL.rstrip("/")
                    rel_path = row.thumb_url
                    # If thumb_url included domain or scheme, you may need to strip that first.
                    # We handle the common case where thumb_url starts with BASE_MEDIA_URL.
                    if rel_path.startswith(prefix):
                        rel_path = rel_path[len(prefix):].lstrip("/")
                    thumb_abs = UPLOAD_DIR / Path(rel_path)
                    if thumb_abs.exists():
                        thumb_abs.unlink()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self.db.delete(row)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
