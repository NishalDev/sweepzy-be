import os
import sys
import time
import logging
from uuid import UUID
from urllib.parse import urlparse
from fastapi import HTTPException

import requests
import numpy as np
from redis import Redis
from rq import Queue
from rq.decorators import job
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from api.litter_detections.litter_detections_service import (
    create_litter_detection,
    update_litter_report_with_detection,
)
from api.litter_detections.litter_detections_model import LitterDetection
from utils.geoutils import (
    load_embedding_model,
    preprocess_image,
    index_embedding_async,
)

# Logging setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.handlers.clear()
logger.addHandler(handler)

# Redis + RQ setup
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
logger.info(f"▶️ report_worker connecting to Redis at {REDIS_URL}")
redis_conn = Redis.from_url(REDIS_URL, decode_responses=False)
queue = Queue("reports", connection=redis_conn)

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Embedding model loaded once
_EMBED_MODEL = load_embedding_model()

# Constants
REQUEST_TIMEOUT = 60  # seconds for HTTP fetch

# place this function in your worker file (replace existing process_report implementation)
@job("reports", connection=redis_conn, timeout=600)
def process_report(report_id: UUID, upload_path: str, latitude: float, longitude: float):
    """
    RQ job: process a single litter report, always fetching images via public URL.
    This version will send an Authorization header if settings.UPLOAD_ACCESS_TOKEN is configured.
    """
    logger.info(f"▶️ process_report called for report_id={report_id}")
    db = SessionLocal()
    try:
        # Build public URL to fetch image
        parsed = urlparse(upload_path)
        if parsed.scheme in ("http", "https"):
            file_url = upload_path
        else:
            # ensure settings.UPLOAD_URL is set to your public uploads base
            file_url = f"{settings.UPLOAD_URL.rstrip('/')}/{upload_path.lstrip('/')}"
        logger.info(f"▶️ downloading from URL: {file_url}")

        # Prepare headers / auth for download
        headers = {}
        # Use a dedicated backend/service token for worker downloads (recommended)
        access_token = getattr(settings, "UPLOAD_ACCESS_TOKEN", None)
        logger.info("▶️ process_report debug: UPLOAD_URL=%s, UPLOAD_ACCESS_TOKEN present=%s",
                    getattr(settings, "UPLOAD_URL", None), bool(access_token))
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            logger.info("▶️ process_report debug: will send Authorization header (redacted)")
        else:
            logger.warning("▶️ process_report debug: UPLOAD_ACCESS_TOKEN missing in settings")
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
                logger.info("▶️ using UPLOAD_ACCESS_TOKEN for authenticated download")

        # Download image bytes with simple retry/backoff
        max_attempts = 3
        backoff_seconds = 1.5
        resp = None
        for attempt in range(1, max_attempts + 1):
            try:
                resp = requests.get(file_url, timeout=REQUEST_TIMEOUT, headers=headers)
                logger.info(f"▶️ download response code: {resp.status_code} (attempt {attempt})")
                # if successful or client error, break (client errors shouldn't be retried)
                if resp.status_code == 200:
                    break
                if 400 <= resp.status_code < 500:
                    # client error (403 etc.) - don't retry
                    logger.warning(f"▶️ client error while downloading (status={resp.status_code})")
                    break
                # otherwise (5xx) we'll retry
            except requests.exceptions.RequestException as e:
                logger.warning(f"▶️ download attempt {attempt} failed: {e}")
                resp = None

            # simple backoff before next attempt
            if attempt < max_attempts:
                time.sleep(backoff_seconds * attempt)

        # Validate response
        if resp is None:
            msg = "Failed to download image: no response"
            logger.warning(msg)
            update_litter_report_with_detection(db, report_id, {"status": "error", "error_message": msg})
            return

        if resp.status_code != 200:
            msg = f"Failed to download image, status={resp.status_code}"
            logger.warning(msg)
            update_litter_report_with_detection(db, report_id, {"status": "error", "error_message": msg})
            return

        image_bytes = resp.content
        logger.info(f"▶️ received {len(image_bytes)} bytes")

        # Preprocess for embedding
        arr = preprocess_image(image_bytes)
        logger.info(f"▶️ preprocessed image shape: {arr.shape}")

        # Embedding
        logger.info("▶️ calling _EMBED_MODEL.predict_on_batch()")
        start = time.time()
        try:
            emb = _EMBED_MODEL.predict_on_batch(np.expand_dims(arr, 0))[0]
            elapsed = time.time() - start
            logger.info(f"▶️ predict_on_batch returned in {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start
            logger.exception(f"ERROR in predict_on_batch after {elapsed:.2f}s: {e}")
            update_litter_report_with_detection(db, report_id, {"status": "error", "error_message": str(e)})
            return

        # Normalize & index
        emb = emb / (np.linalg.norm(emb) + 1e-10)
        logger.info("▶️ calling index_embedding_async()")
        try:
            index_embedding_async(report_id, emb)
            logger.info("▶️ index_embedding_async() returned")
        except Exception as e:
            logger.exception(f"ERROR in index_embedding_async: {e}")
            update_litter_report_with_detection(db, report_id, {"status": "error", "error_message": str(e)})
            return

        # Detection
        logger.info("▶️ calling create_litter_detection()")
        try:
            create_litter_detection(db, report_id)
            logger.info("▶️ create_litter_detection() returned")
        except HTTPException as he:
            if getattr(he, "detail", None) == "NO_LITTER_DETECTED_DELETE":
                logger.info(f"Report {report_id} deleted: no litter detected.")
                return
            logger.exception(f"ERROR in create_litter_detection: {he}")
            update_litter_report_with_detection(db, report_id, {"status": "error", "error_message": str(he)})
            return

        # Query detections
        detections = (
            db.query(LitterDetection)
              .filter_by(litter_report_id=report_id)
              .filter(LitterDetection.total_litter_count > 0)
              .all()
        )
        logger.info(f"▶️ found {len(detections)} detection rows")
        if not detections:
            update_litter_report_with_detection(db, report_id, {
                "status": "no-litter",
                "detections": [],
                "severity_level": None,
                "error_message": "No litter detected"
            })
            return

        # Serialize & update
        serialized = [{
            "id": str(d.id),
            "detected_objects": d.detected_objects,
            "bounding_boxes": d.bounding_boxes,
            "total_litter_count": d.total_litter_count,
            "severity_level": d.severity_level,
            "detection_confidence": d.detection_confidence,
            "detection_source": d.detection_source,
            "review_status": d.review_status,
            "review_notes": d.review_notes,
        } for d in detections]
        severity_level = serialized[0].get("severity_level")

        update_litter_report_with_detection(db, report_id, {
            "status": "completed",
            "detections": serialized,
            "severity_level": severity_level,
        })
        logger.info(f"Completed report {report_id}, {len(detections)} detections")

    except Exception as e:
        logger.exception(f"Error processing report {report_id}: {e}")
        try:
            update_litter_report_with_detection(db, report_id, {"status": "error", "error_message": str(e)})
        except:
            logger.exception("Failed to mark report as error")
    finally:
        db.close()


