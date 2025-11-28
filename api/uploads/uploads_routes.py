from fastapi import APIRouter, UploadFile, status, File, Form, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from uuid import UUID
import uuid
import qrcode
from io import BytesIO
import io
import logging
import base64
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime, timedelta
from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.uploads.uploads_controller import (
    create_upload_controller,
    list_uploads_controller,
    get_upload_controller,
    delete_upload_controller
)
from api.litter_reports.image_fingerprints_model import ImageFingerprint
from api.litter_reports.litter_reports_model import LitterReport
from api.litter_reports.litter_reports_schema import LitterReportResponse, LitterReportCreate
from api.litter_reports.litter_reports_controller import create_report_controller
from api.litter_detections.litter_detections_service import create_litter_detection
from api.uploads.uploads_schema import UploadResponse
from api.user.user_service import award_points
from api.litter_detections.litter_detections_service import run_detection_on_image_bytes
from config.points_config import PointReason
import os
import imagehash
from imagehash import hex_to_hash
import numpy as np
from PIL import Image
from utils.geoutils import (
    distance_meters,
    find_spatio_temporal
)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
router = APIRouter(
    prefix="/uploads",
    tags=["uploads"]
)

# thresholds
SPATIAL_RADIUS_M = 50        # meters
TEMPORAL_WINDOW_S = 30 * 60   # seconds
PHASH_THRESHOLD = 8           # Hamming bits
EMBED_SIM_THRESHOLD = 0.90    # cosine similarity


# @router.post(
#     "/{session_id}/full",
#     response_model=LitterReportResponse,
#     status_code=status.HTTP_201_CREATED,
#     summary="Upload image → dedupe → create report → run detection"
# )
# def upload_create_report_and_detect(
#     session_id: str,
#     file: UploadFile = File(...),
#     latitude: float | None = Form(None),
#     longitude: float | None = Form(None),
#     db: Session = Depends(get_db),
#     current_user=Depends(auth_middleware)
# ):
#     user_id = current_user["id"]
#     ts = datetime.utcnow()

#     # 1. Spatio-temporal dedupe
#     spatio_ids = find_spatio_temporal(
#         db=db,
#         model=LitterReport,
#         lat=latitude,
#         lng=longitude,
#         ts=ts,
#         radius_m=SPATIAL_RADIUS_M,
#         window_s=TEMPORAL_WINDOW_S,
#     )
#     if spatio_ids:
#         raise HTTPException(
#             status_code=409,
#             detail={"reason": "spatio-temporal", "ids": [str(r) for r in spatio_ids]}
#         )

#     # 2. Perceptual-hash dedupe
#     file.file.seek(0)
#     img_bytes = file.file.read()
#     img = Image.open(BytesIO(img_bytes))
#     ph = imagehash.phash(img)

#     one_week_ago = ts - timedelta(days=7)
#     recent_hashes = db.execute(
#         select(ImageFingerprint.report_id, ImageFingerprint.phash)
#         .join(LitterReport, ImageFingerprint.report_id == LitterReport.id)
#         .where(LitterReport.created_at >= one_week_ago)
#     ).fetchall()

#     phash_dups = [rid for rid, old_hex in recent_hashes
#                   if (ph - hex_to_hash(old_hex)) <= PHASH_THRESHOLD]
#     if phash_dups:
#         raise HTTPException(
#             status_code=409,
#             detail={"reason": "phash", "ids": [str(r) for r in phash_dups]}
#         )

#     # 3. Embedding-similarity dedupe
#     file.file.seek(0)
#     file_bytes = file.file.read()
#     emb_model = load_embedding_model()
#     arr = preprocess_image(file_bytes)
#     emb = emb_model.predict(np.expand_dims(arr, 0))[0]
#     emb = emb / np.linalg.norm(emb)

#     idx = load_faiss_index()
#     print(f"[FAISS DEBUG] idx.d = {getattr(idx, 'd', None)}")
#     print(f"[FAISS DEBUG] raw emb shape = {emb.shape}, dtype = {emb.dtype}")
#     query_emb = emb.astype('float32').reshape(1, -1)
#     print(f"[FAISS DEBUG] query_emb shape = {query_emb.shape}, dtype = {query_emb.dtype}")

#     dists, rep_ids = idx.search(query_emb, k=5)

#     emb_dups = [int(rep_id) for dist, rep_id in zip(dists[0], rep_ids[0])
#                 if rep_id >= 0 and dist >= EMBED_SIM_THRESHOLD]
#     if emb_dups:
#         raise HTTPException(
#             status_code=409,
#             detail={"reason": "embedding", "ids": [str(r) for r in emb_dups]}
#         )

#     # 4. Save upload & report
#     file.file.seek(0)
#     upload = create_upload_controller(
#         db=db,
#         file=file,
#         latitude=latitude,
#         longitude=longitude,
#         user_id=user_id,
#         session_id=session_id,
#     )
#     if not upload:
#         raise HTTPException(500, "Failed to save upload")

#     report_in = LitterReportCreate(
#         user_id=user_id,
#         upload_id=UUID(str(upload.id)),
#         latitude=latitude,
#         longitude=longitude,
#         status="pending",
#         severity=None,
#         detection_results=None,
#         reward_points=0,
#     )
#     report = create_report_controller(report_in, db, user_id)
#     if not report:
#         db.delete(upload)
#         db.commit()
#         raise HTTPException(500, "Failed to create litter report")

#     # 5. Run detection
#     detection = create_litter_detection(db, report.id)
#     if detection.total_litter_count == 0:
#         db.delete(detection)
#         db.delete(report)
#         db.delete(upload)
#         db.commit()
#         raise HTTPException(400, "No litter detected; upload discarded.")

#     # 6. Save fingerprint
#     fingerprint = ImageFingerprint(
#         report_id=report.id,
#         phash=str(ph),
#         embedding=emb.tobytes()
#     )
#     db.add(fingerprint)
#     db.commit()

#     # 7. Award points
#     award_points(
#         db=db,
#         current_user=current_user,
#         user_id=user_id,
#         reason=PointReason.uploaded_litter_report
#     )

#     # 8. Async FAISS indexing
#     index_embedding_async(report.id, emb)

#     return report
@router.post(
    "/{session_id}/full",
    response_model=LitterReportCreate,
    status_code=status.HTTP_201_CREATED,
    summary="Upload image → dedupe → create report"
)
async def upload_create_report_and_detect(
    session_id: str,
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(auth_middleware)
):
    user_id = current_user["id"]
    now = datetime.utcnow()

    # ─── 1. Read & hash image ───────────────────────────────────────────────────
    img_bytes = await file.read()
    img = Image.open(BytesIO(img_bytes))
    ph = imagehash.phash(img)

    # ─── 2. Global pHash dedupe (last week only) ───────────────────────────────
    one_week_ago = now - timedelta(days=7)
    rows = db.execute(
        select(ImageFingerprint.report_id, ImageFingerprint.phash)
        .join(LitterReport, ImageFingerprint.report_id == LitterReport.id)
        .where(LitterReport.created_at >= one_week_ago)
    ).fetchall()

    dup_ids = []
    for rid, old_hex in rows:
        old_hash = hex_to_hash(old_hex)
        if (ph - old_hash) <= PHASH_THRESHOLD:
            dup_ids.append(str(rid))

    if dup_ids:
        # true visual duplicate
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "phash", "ids": dup_ids}
        )

    # ─── 3. Save upload ────────────────────────────────────────────────────────
    file.file.seek(0)
    upload = create_upload_controller(
        db=db,
        file=file,
        latitude=latitude,
        longitude=longitude,
        user_id=user_id,
        session_id=session_id
    )
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save upload"
        )

    # ─── 4. Create report ─────────────────────────────────────────────────────
    report_in = LitterReportCreate(
        user_id=user_id,
        upload_id=UUID(str(upload.id)),
        latitude=latitude,
        longitude=longitude,
        status="pending",
        severity=None,
        detection_results=None,
        reward_points=0,
    )
    report = create_report_controller(report_in, db, user_id)
    if not report:
        # cleanup upload
        db.delete(upload)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create report"
        )

    # ─── 5. Persist pHash and spatial data ─────────────────────────
    # Store empty bytes for embedding to maintain database compatibility
    fp = ImageFingerprint(
        report_id=report.id,
        phash=str(ph),
        embedding=b''  # empty bytes for embedding since we're not using it
    )
    db.add(fp)

    # set spatial field
    report.geom = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

    db.commit()

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"id": str(report.id)}
    )
@router.post(
    "/{session_id}",
    response_model=UploadResponse,
    summary="Upload a file tied to a session"
)
async def upload_file_with_session_endpoint(
    request: Request,
    session_id: str,
    file: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(auth_middleware),
):
    form = await request.form()
    print("🚨 Raw form keys:", list(form.keys()))
    upload = create_upload_controller(
        file=file,
        db=db,
        latitude=latitude,
        longitude=longitude,
        user_id=current_user["id"],
        session_id=session_id,
    )
    return upload


@router.post(
    "/",
    response_model=UploadResponse,
    summary="Upload a file and store its metadata"
)
async def upload_file_endpoint(
    file: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(auth_middleware),
):
    print(f"Latitude: {latitude}, Longitude: {longitude}, User ID: {current_user['id']}")
    return create_upload_controller(file, db, latitude, longitude, current_user['id'])


@router.get(
    "/",
    response_model=List[UploadResponse],
    summary="List all uploads"
)
def list_uploads_endpoint(
    db: Session = Depends(get_db)
):
    return list_uploads_controller(db)


@router.get(
    "/session/create",
    summary="Create an upload session and generate a QR code"
)
async def create_upload_session():
    session_id = str(uuid.uuid4())
    base_url = os.getenv("NGROK_URL", "http://localhost:3000")
    upload_url = f"{base_url}/upload/{session_id}"

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(upload_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_data = base64.b64encode(buffer.getvalue()).decode()
    qr_data_url = f"data:image/png;base64,{qr_data}"

    return JSONResponse(content={
        "sessionId": session_id,
        "qrDataUrl": qr_data_url
    })


@router.get(
    "/{upload_id}",
    response_model=UploadResponse,
    summary="Get a single upload by ID"
)
def get_upload_endpoint(
    upload_id: UUID,
    db: Session = Depends(get_db)
):
    return get_upload_controller(upload_id, db)


@router.delete(
    "/{upload_id}",
    summary="Delete an upload"
)
def delete_upload_endpoint(
    upload_id: UUID,
    db: Session = Depends(get_db)
):
    return delete_upload_controller(upload_id, db)