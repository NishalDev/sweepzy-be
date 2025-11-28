import os
import uuid
import json
import threading
import logging
from urllib.parse import urlparse, urljoin
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import cv2
import numpy as np
import requests
import onnxruntime as ort
import time
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
import platform
from config.settings import settings
from api.litter_detections.litter_detections_model import LitterDetection
from api.litter_reports.litter_reports_model import LitterReport
from api.uploads.uploads_model import Upload

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_session = getattr(globals(), "_requests_session", None) or requests.Session()
# Environment-configurable model path (download into this path in container start)
if platform.system() == "Windows":
    MODEL_PATH = os.getenv(
        "MODEL_PATH",
        r"E:\ecoCity\EcoCity\weights\best_classes.onnx"  # local Windows path
    )
else:
    MODEL_PATH = os.getenv(
        "MODEL_PATH",
        "/home/appuser/app/weights/best_classes.onnx"  # Fly container path
    )

# Expect the ONNX export to already include NMS (yolo export with include-nms=True).
MODEL_SOURCE = os.getenv("MODEL_SOURCE", "onnx")  # for metadata only

# HTTP settings for fetching images
UPLOAD_URL = os.getenv("UPLOAD_URL") or getattr(settings, "UPLOAD_URL", "http://localhost:8000")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))

# ONNX Runtime session global + lock (lazy init)
_ORT_SESSION: Optional[ort.InferenceSession] = None
_SESSION_LOCK = threading.Lock()

# requests session (reuse TCP connections)
_requests_session = requests.Session()
_requests_session.headers.update({"User-Agent": "litter-detector/1.0"})


def _load_onnx_session(model_path: str) -> ort.InferenceSession:
    """Create and return an ONNX Runtime session for the given path (CPU)."""
    providers = ["CPUExecutionProvider"]
    logger.info("Loading ONNX model from %s", model_path)
    sess = ort.InferenceSession(model_path, providers=providers)
    return sess


def get_ort_session() -> ort.InferenceSession:
    """Lazy-load and return the shared ONNX Runtime session."""
    global _ORT_SESSION
    if _ORT_SESSION is None:
        with _SESSION_LOCK:
            if _ORT_SESSION is None:
                if not os.path.exists(MODEL_PATH):
                    logger.error("Model file missing at %s", MODEL_PATH)
                    raise RuntimeError(f"Model not found at {MODEL_PATH}")
                _ORT_SESSION = _load_onnx_session(MODEL_PATH)
    return _ORT_SESSION


def determine_severity(
    total_count: int,
    bounding_boxes: List[List[float]],
    image_size: Tuple[int, int] = None
) -> str:
    if total_count == 0:
        return "none"
    if total_count < 5:
        severity = "low"
    elif total_count < 15:
        severity = "medium"
    else:
        severity = "high"

    if image_size and bounding_boxes:
        img_w, img_h = image_size
        img_area = img_w * img_h
        if img_area > 0:
            boxes_area = 0.0
            for box in bounding_boxes:
                if len(box) >= 4:
                    x1, y1, x2, y2 = box[:4]
                    # clamp values and ensure positive area
                    w = max(0.0, float(x2) - float(x1))
                    h = max(0.0, float(y2) - float(y1))
                    boxes_area += w * h
            density = boxes_area / img_area
            if density > 0.10 and severity != "high":
                severity = "high"
            elif density > 0.05 and severity == "low":
                severity = "medium"

    return severity


def fetch_image_bytes(path_or_url: str) -> bytes:
    """
    Robust image fetcher:
      - Accepts either a full http(s) URL or a path relative to settings.UPLOAD_URL
      - Attaches Authorization: Bearer <UPLOAD_ACCESS_TOKEN> when fetching from uploads
      - Logs headers, redirect chain, and response codes
      - Retries on server errors (5xx) but not client errors (4xx)
    """
    parsed = urlparse(path_or_url)
    if parsed.scheme in ("http", "https"):
        file_url = path_or_url
    else:
        upload_base = getattr(settings, "UPLOAD_URL", None) or getattr(settings, "UPLOAD_BASE_URL", None)
        if not upload_base:
            logger.error("fetch_image_bytes: UPLOAD_URL not configured in settings")
            raise HTTPException(500, detail="Server misconfiguration: UPLOAD_URL not set")
        file_url = f"{upload_base.rstrip('/')}/{path_or_url.lstrip('/')}"

    headers = {}
    upload_token = getattr(settings, "UPLOAD_ACCESS_TOKEN", None)
    # If we are fetching from the uploads service, include the token
    # Check either the path contains '/uploads/' OR the URL host equals configured upload host
    try:
        parsed_file = urlparse(file_url)
        if upload_token and ("/uploads/" in parsed_file.path or parsed_file.netloc == urlparse(getattr(settings, "UPLOAD_URL")).netloc):
            headers["Authorization"] = f"Bearer {upload_token}"
            logger.info("fetch_image_bytes: adding Authorization header (redacted) for %s", file_url)
    except Exception:
        # fallback: attach if token present and '/uploads/' in url
        if upload_token and "/uploads/" in file_url:
            headers["Authorization"] = f"Bearer {upload_token}"
            logger.info("fetch_image_bytes: adding Authorization header (redacted) for %s", file_url)

    # Log what we will send (redact token)
    logger.info(
        "fetch_image_bytes: requesting %s with headers %s",
        file_url,
        {k: ("<REDACTED>" if k.lower() == "authorization" else v) for k, v in headers.items()},
    )

    # Attempt download with retries for 5xx
    max_attempts = 3
    backoff = 1.5
    resp = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = _session.get(file_url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            logger.info("fetch_image_bytes: attempt %d status=%s", attempt, resp.status_code)
            if resp.history:
                logger.info("fetch_image_bytes: redirect chain: %s", [r.status_code for r in resp.history])
            # success
            if resp.status_code == 200:
                break
            # client error -> don't retry
            if 400 <= resp.status_code < 500:
                logger.warning("fetch_image_bytes: client error %s when downloading %s", resp.status_code, file_url)
                break
            # otherwise (5xx) will retry
        except requests.RequestException as exc:
            logger.warning("fetch_image_bytes: attempt %d failed: %s", attempt, exc)
            resp = None

        if attempt < max_attempts:
            time.sleep(backoff * attempt)

    if resp is None:
        logger.exception("Failed to download image from %s: no response", file_url)
        raise HTTPException(500, detail="Failed to download image: no response")

    # If final response is a redirect (non-200) but has location, try manual re-request (to preserve auth)
    if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("location"):
        final = urljoin(file_url, resp.headers["location"])
        logger.info("fetch_image_bytes: following manual redirect to %s", final)
        try:
            resp2 = _session.get(final, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            logger.info("fetch_image_bytes: manual redirect status=%s", resp2.status_code)
            resp = resp2
        except requests.RequestException as exc:
            logger.warning("fetch_image_bytes: manual redirect failed: %s", exc)

    if resp.status_code != 200:
        logger.error("Failed to download image, status=%s url=%s", resp.status_code, file_url)
        raise HTTPException(502, detail=f"Failed to download image, status={resp.status_code}")

    return resp.content

def _letterbox_resize(img: np.ndarray, new_shape: int = 640) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """
    Resize + pad to square (new_shape x new_shape) while keeping aspect ratio.
    Returns resized image, scale, (pad_w, pad_h).
    """
    h, w = img.shape[:2]
    if isinstance(new_shape, (tuple, list)):
        nx, ny = new_shape
        target_w, target_h = nx, ny
    else:
        target_w = target_h = int(new_shape)
    # scale
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    pad_w = target_w - new_w
    pad_h = target_h - new_h
    top = pad_h // 2
    bottom = pad_h - top
    left = pad_w // 2
    right = pad_w - left
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return padded, scale, (left, top)


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float = 0.45) -> List[int]:
    """Simple NMS (boxes are x1,y1,x2,y2). Returns kept indices."""
    if boxes.size == 0:
        return []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep: List[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        inds = np.where(iou <= iou_thresh)[0]
        order = order[inds + 1]
    return keep


def run_detection_on_image_bytes(img_bytes: bytes, conf_thresh: float = 0.25, iou_thresh: float = 0.45, input_size: int = 640) -> Dict[str, Any]:
    """
    Runs inference using ONNX Runtime. 
    NOTE: This implementation expects the ONNX export to include NMS and to produce
    a final detection output with rows like [x1, y1, x2, y2, conf, class].
    If your ONNX export produces raw predictions (like many YOLO exports without `include-nms`),
    you'll need a different postprocessing decode step.
    """
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise RuntimeError("BAD_DECODE")
    h0, w0 = img_bgr.shape[:2]

    # prepare input
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    resized, scale, (pad_x, pad_y) = _letterbox_resize(img_rgb, new_shape=input_size)
    tensor = resized.astype(np.float32) / 255.0
    # CHW
    tensor = np.transpose(tensor, (2, 0, 1))
    tensor = np.expand_dims(tensor, 0).astype(np.float32)

    session = get_ort_session()
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: tensor})
    preds = outputs[0]

    # Normalize output shape: many exports are (1, N, 6) or (N,6)
    if preds is None or (isinstance(preds, np.ndarray) and preds.size == 0):
        # nothing detected
        return {
            "detected_objects": [],
            "bounding_boxes": [],
            "total_litter_count": 0,
            "severity_level": "none",
            "detection_source": "onnx",
            "detection_confidence": 0.0,
            "review_status": "pending",
            "reviewed_by": None,
            "review_notes": None,
        }

    preds = np.asarray(preds)
    if preds.ndim == 3 and preds.shape[0] == 1:
        preds = preds[0]

    # Expect each row: [x1, y1, x2, y2, conf, class]
    if preds.ndim != 2 or preds.shape[1] < 6:
        # Not the expected layout — fail fast with actionable message.
        logger.error("Unexpected ONNX output shape %s — expected (N,6) with NMS included.", preds.shape)
        raise RuntimeError("Unexpected ONNX output shape; export your model with include-nms=True giving outputs (N,6) [x1,y1,x2,y2,conf,class]")

    boxes = preds[:, :4].astype(float)
    scores = preds[:, 4].astype(float)
    classes = preds[:, 5].astype(int)

    # filter by confidence
    keep_mask = scores >= conf_thresh
    if not np.any(keep_mask):
        return {
            "detected_objects": [],
            "bounding_boxes": [],
            "total_litter_count": 0,
            "severity_level": "none",
            "detection_source": "onnx",
            "detection_confidence": 0.0,
            "review_status": "pending",
            "reviewed_by": None,
            "review_notes": None,
        }

    boxes = boxes[keep_mask]
    scores = scores[keep_mask]
    classes = classes[keep_mask]

    # scale boxes back to original image coords: undo letterbox
    # boxes currently in pixel coords of padded/resized image; need to remove padding and scale
    # We know: resized image = original * scale with padding (pad_x, pad_y)
    # So first subtract pad, then divide by scale.
    boxes[:, [0, 2]] = (boxes[:, [0, 2]] - pad_x) / (scale + 1e-9)
    boxes[:, [1, 3]] = (boxes[:, [1, 3]] - pad_y) / (scale + 1e-9)

    # clamp to image size
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, w0)
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, h0)

    # run NMS again as a safety (some exports include NMS but duplicates can remain)
    keep_idx = _nms(boxes, scores, iou_thresh)
    final_boxes = boxes[keep_idx].tolist()
    final_scores = scores[keep_idx].tolist()
    final_classes = classes[keep_idx].tolist()

    # Map classes -> label strings: you should provide your label map near the model,
    # or embed it in the model metadata. Here we use numeric labels (stringified).
    LABELS = ["plastic_bag","plastic_bottle", "paper_waste", "food_wrapper"]

    detections = []
    for cls_idx, conf in zip(final_classes, final_scores):
        label = LABELS[int(cls_idx)]
        detections.append({"label": label, "confidence": float(conf)})

    avg_conf = float(np.mean(final_scores)) if final_scores else 0.0
    total = len(detections)
    severity = determine_severity(total, final_boxes, (w0, h0))

    return {
        "detected_objects": detections,
        "bounding_boxes": final_boxes,
        "total_litter_count": total,
        "severity_level": severity,
        "detection_source": "onnx",
        "detection_confidence": avg_conf,
        "review_status": "pending",
        "reviewed_by": None,
        "review_notes": None,
    }


def create_litter_detection(db: Session, report_id: uuid.UUID) -> LitterDetection:
    """
    Runs detection and persists both the LitterDetection and report update.
    Guarantees the report.status is updated on any failure.
    """
    report = None
    try:
        # 1) fetch report + upload
        report = db.get(LitterReport, report_id)
        if not report:
            raise HTTPException(404, detail=f"Report {report_id} not found")

        upload = db.get(Upload, report.upload_id)
        if not upload or not upload.file_url:
            raise HTTPException(400, detail="No upload or file_url")

        # 2) fetch image
        img_bytes = fetch_image_bytes(upload.file_url)

        # 3) run detection
        detection_results = run_detection_on_image_bytes(img_bytes)
        total = detection_results["total_litter_count"]
        if total == 0:
            # Mark report as no-litter and keep record
            report.status = "no-litter"
            report.is_detected = False
            report.detection_results = json.dumps({
                **detection_results,
                "status": "no-litter",
                "error_message": "No litter detected"
            })
            db.commit()
            raise HTTPException(400, detail="No litter detected.")

        # 4) persist detection row
        # add metadata about model used
        detection_results_meta = {**detection_results}
        payload = {"litter_report_id": report_id, **detection_results_meta}
        
        detection = LitterDetection(**jsonable_encoder(payload))
        db.add(detection)

        # 5) update report
        report.severity = detection_results_meta["severity_level"]
        report.is_detected = True
        report.detection_results = json.dumps(detection_results_meta)
        db.commit()
        db.refresh(detection)
        return detection

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Detection failed for report %s: %s", report_id, e)
        if report:
            report.status = "error"
            report.detection_results = json.dumps({"error": str(e)})
            db.commit()
        raise HTTPException(500, detail="Detection service error")


def get_detections_for_report(db: Session, report_id: uuid.UUID) -> List[LitterDetection]:
    return db.query(LitterDetection).filter_by(litter_report_id=report_id).all()


def update_litter_report_with_detection(
    db: Session, litter_report_id: uuid.UUID, detection_results: Dict[str, Any]
) -> LitterReport:
    """
    Update the LitterReport table with detection payload.
    """
    report = db.query(LitterReport).filter(LitterReport.id == litter_report_id).first()
    if not report:
        raise HTTPException(404, detail="Report not found")

    report.severity = detection_results.get("severity_level")
    report.is_detected = True
    report.detection_results = jsonable_encoder(detection_results)

    db.commit()
    db.refresh(report)

    return report
