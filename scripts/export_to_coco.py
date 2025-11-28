"""
Export detections stored in `litter_reports.detection_results` to COCO JSON.

Usage (from repo root):
  python -m .scripts.export_to_coco --out coco_annotations.json

The script will:
 - query all litter_reports rows with non-empty detection_results
 - resolve the upload row to find the image file URL/path
 - attempt to open local files under the project's uploads directory or download remote images
 - construct a COCO dict with images, annotations and categories

Notes:
 - category ids are derived from the union of detected labels; if your model uses a known
   fixed label list, pass it via DEFAULT_LABELS inside the file.
 - image and annotation ids are integers assigned sequentially.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple
from io import BytesIO
import argparse

from PIL import Image
import requests
import sys
from pathlib import Path

# If the package imports fail when the script is executed directly (python <path>),
_pkg_root = Path(__file__).resolve().parents[1]
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from config.database import SessionLocal, UPLOAD_DIR, engine
from sqlalchemy import text


DEFAULT_LABELS = ["plastic_bag", "plastic_bottle", "paper_waste", "food_wrapper"]


def _parse_detection_results(raw) -> Dict:
    """Return parsed detection_results as a dict (handles double-encoded JSON)."""
    if raw is None:
        return {}
    # If DB returned a list (JSON array) or dict already, return as-is
    if isinstance(raw, dict) or isinstance(raw, (list, tuple)):
        return raw
    # sometimes stored as JSON string
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _open_image_get_size(path_or_url: str) -> Tuple[int, int]:
    """Try to open local file first (relative to UPLOAD_DIR), else fetch over HTTP.

    Returns (width, height) or (0,0) if it cannot be opened.
    """
    # Absolute or relative path on disk?
    # If path_or_url is a local path under uploads, resolve it
    candidates = []
    if os.path.isabs(path_or_url) and os.path.exists(path_or_url):
        candidates.append(path_or_url)
    # common storage pattern: uploads/<filename>
    rel = path_or_url.lstrip("/\\")
    local = os.path.join(str(UPLOAD_DIR), os.path.basename(rel))
    if os.path.exists(local):
        candidates.append(local)

    for c in candidates:
        try:
            with Image.open(c) as img:
                return img.width, img.height
        except Exception:
            continue

    # otherwise try HTTP fetch
    try:
        resp = requests.get(path_or_url, timeout=20)
        if resp.status_code == 200:
            with Image.open(BytesIO(resp.content)) as img:
                return img.width, img.height
    except Exception:
        pass

    return 0, 0


def _flatten_polygons(polygons) -> List[List[float]]:
    """Convert list of polygons ([[[x,y],...], ...]) to COCO segmentation format [[x1,y1,x2,y2,...], ...].

    This function will remove consecutive duplicate points, strip a closing point if it
    is identical to the first point, and remove repeated points (using a small rounding
    tolerance) so the resulting segmentation contains at least 3 unique points.
    """
    segs: List[List[float]] = []
    if not polygons:
        return segs

    for poly in polygons:
        try:
            cleaned: List[Tuple[float, float]] = []
            for p in poly:
                if not (isinstance(p, (list, tuple)) and len(p) >= 2):
                    continue
                x = float(p[0])
                y = float(p[1])
                # skip consecutive duplicates
                if cleaned and abs(x - cleaned[-1][0]) < 1e-9 and abs(y - cleaned[-1][1]) < 1e-9:
                    continue
                cleaned.append((x, y))

            if len(cleaned) < 3:
                continue

            # if polygon is closed (last == first), remove the last point
            if len(cleaned) >= 2 and abs(cleaned[0][0] - cleaned[-1][0]) < 1e-9 and abs(cleaned[0][1] - cleaned[-1][1]) < 1e-9:
                cleaned.pop()

            # remove any duplicate points while preserving order, using rounded keys
            unique: List[Tuple[float, float]] = []
            seen = set()
            for x, y in cleaned:
                key = (round(x, 6), round(y, 6))
                if key in seen:
                    continue
                seen.add(key)
                unique.append((x, y))

            if len(unique) < 3:
                continue

            flat = [coord for pt in unique for coord in pt]
            segs.append(flat)
        except Exception:
            continue

    return segs


def _polygon_area(poly: List[Tuple[float, float]]) -> float:
    """Compute polygon area (absolute) using shoelace formula. poly is list of (x,y)."""
    if not poly or len(poly) < 3:
        return 0.0
    area = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def export_to_coco(output_path: str, detection_status: str | None = None, include_no_litter: bool = False, source: str = "auto", verbose: bool = False) -> None:
    """Export COCO JSON containing detections from litter_detections or litter_reports.

    - detection_status: optional filter on status field (applies when falling back to report-level JSON)
    - include_no_litter: include reports with zero detections
    - source: "detections", "reports", or "auto" (try detections first, then reports)
    - verbose: print debug info
    """
    conn = engine.connect()
    try:
        # Prefer authoritative rows from litter_detections (one per detection run).
        sql = text("""
            SELECT ld.id::text AS detection_id,
                   ld.litter_report_id::text AS report_id,
                   lr.upload_id::text AS upload_id,
                   ld.bounding_boxes::text AS bounding_boxes,
                   ld.detected_objects::text AS detected_objects,
                   ld.total_litter_count AS total_litter_count,
                   u.file_name AS file_name,
                   u.file_url AS file_url
            FROM litter_detections ld
            JOIN litter_reports lr ON lr.id = ld.litter_report_id
            LEFT JOIN uploads u ON u.id = lr.upload_id
            WHERE ld.bounding_boxes IS NOT NULL OR ld.detected_objects IS NOT NULL
        """)

        images: List[Dict] = []
        annotations: List[Dict] = []
        category_name_to_id: Dict[str, int] = {}

        img_id = 1
        ann_id = 1
        upload_to_image_id: Dict[str, int] = {}

        if source in ("auto", "detections"):
            res = conn.execute(sql).mappings()
            if verbose:
                print("query returned rows from litter_detections")

            for row in res:
                boxes = _parse_detection_results(row["bounding_boxes"]) or []
                detected = _parse_detection_results(row["detected_objects"]) or []
                total = row.get("total_litter_count") or (len(boxes) if boxes else 0)
                if not include_no_litter and (total is None or total == 0):
                    continue

                upload_id = row.get("upload_id")
                report_id = row.get("report_id")
                file_name = row["file_name"] or (f"{report_id}.jpg")
                file_url = row["file_url"]

                img_key = upload_id if upload_id else f"report:{report_id}"

                if img_key in upload_to_image_id:
                    current_img_id = upload_to_image_id[img_key]
                else:
                    w, h = (0, 0)
                    if file_url:
                        w, h = _open_image_get_size(file_url)
                    current_img_id = img_id
                    images.append({"id": current_img_id, "file_name": file_name, "width": w, "height": h})
                    upload_to_image_id[img_key] = current_img_id
                    img_id += 1

                for idx, box in enumerate(boxes):
                    try:
                        label = None
                        if idx < len(detected) and isinstance(detected[idx], dict):
                            label = detected[idx].get("label")
                        if label is None:
                            if detected and isinstance(detected[0], dict):
                                label = detected[0].get("label")
                            else:
                                label = DEFAULT_LABELS[0]

                        if label not in category_name_to_id:
                            category_name_to_id[label] = len(category_name_to_id) + 1

                        cat_id = category_name_to_id[label]
                        x1, y1, x2, y2 = [float(v) for v in box[:4]]
                        bw = max(0.0, x2 - x1)
                        bh = max(0.0, y2 - y1)
                        # try to get polygon segmentation & area if provided alongside detection
                        segmentation = []
                        poly_area = None
                        if isinstance(detected, list) and idx < len(detected) and isinstance(detected[idx], dict):
                            # some records include bounding_polygons near the detected_objects
                            poly = detected[idx].get("bounding_polygons") or detected[idx].get("bounding_polygon")
                            if poly:
                                segmentation = _flatten_polygons(poly)
                                if segmentation:
                                    # use first polygon to compute area
                                    pts = [(segmentation[0][i], segmentation[0][i+1]) for i in range(0, len(segmentation[0]), 2)]
                                    poly_area = _polygon_area(pts)

                        area = poly_area if poly_area is not None else (bw * bh)

                        annotations.append({
                            "id": ann_id,
                            "image_id": current_img_id,
                            "category_id": cat_id,
                            "bbox": [x1, y1, bw, bh],
                            "area": area,
                            "iscrowd": 0,
                            "segmentation": segmentation,
                        })
                        ann_id += 1
                    except Exception:
                        continue

            if verbose:
                print(f"after litter_detections pass: images={len(images)}, annotations={len(annotations)}")

        # fallback to report-level detection_results if nothing found
        if (source in ("auto", "reports")) and len(images) == 0:
            if verbose:
                print("no images from litter_detections — falling back to litter_reports.detection_results")
            reports_sql = text("""
                SELECT lr.id::text AS report_id,
                       lr.upload_id::text AS upload_id,
                       lr.detection_results::text AS detection_results,
                       u.file_name AS file_name,
                       u.file_url AS file_url
                FROM litter_reports lr
                LEFT JOIN uploads u ON u.id = lr.upload_id
                WHERE lr.detection_results IS NOT NULL
            """)
            rep_res = conn.execute(reports_sql).mappings()

            for row in rep_res:
                raw = row["detection_results"]
                dr = _parse_detection_results(raw)
                if not dr:
                    continue
                status = dr.get("status") or dr.get("review_status")
                if detection_status and status != detection_status:
                    continue

                upload_id = row.get("upload_id")
                report_id = row.get("report_id")
                file_name = row["file_name"] or (f"{report_id}.jpg")
                file_url = row["file_url"]

                img_key = upload_id if upload_id else f"report:{report_id}"
                if img_key in upload_to_image_id:
                    current_img_id = upload_to_image_id[img_key]
                else:
                    w, h = (0, 0)
                    if file_url:
                        w, h = _open_image_get_size(file_url)
                    current_img_id = img_id
                    images.append({"id": current_img_id, "file_name": file_name, "width": w, "height": h})
                    upload_to_image_id[img_key] = current_img_id
                    img_id += 1

                # If detection_results contains a 'detections' list, iterate through it.
                detections_list = dr.get("detections") if isinstance(dr, dict) else None
                if detections_list and isinstance(detections_list, list):
                    for det in detections_list:
                        boxes_det = det.get("bounding_boxes") or []
                        detected_det = det.get("detected_objects") or []
                        for idx, box in enumerate(boxes_det):
                            try:
                                label = None
                                if idx < len(detected_det) and isinstance(detected_det[idx], dict):
                                    label = detected_det[idx].get("label")
                                if label is None:
                                    if detected_det and isinstance(detected_det[0], dict):
                                        label = detected_det[0].get("label")
                                    else:
                                        label = DEFAULT_LABELS[0]

                                if label not in category_name_to_id:
                                    category_name_to_id[label] = len(category_name_to_id) + 1

                                cat_id = category_name_to_id[label]
                                x1, y1, x2, y2 = [float(v) for v in box[:4]]
                                bw = max(0.0, x2 - x1)
                                bh = max(0.0, y2 - y1)
                                segmentation = []
                                poly_area = None
                                poly = det.get("bounding_polygons") or det.get("bounding_polygon")
                                if poly:
                                    segmentation = _flatten_polygons(poly)
                                    if segmentation:
                                        pts = [(segmentation[0][i], segmentation[0][i+1]) for i in range(0, len(segmentation[0]), 2)]
                                        poly_area = _polygon_area(pts)

                                area = poly_area if poly_area is not None else (bw * bh)

                                annotations.append({
                                    "id": ann_id,
                                    "image_id": current_img_id,
                                    "category_id": cat_id,
                                    "bbox": [x1, y1, bw, bh],
                                    "area": area,
                                    "iscrowd": 0,
                                    "segmentation": segmentation,
                                })
                                ann_id += 1
                            except Exception:
                                continue
                    continue

                # otherwise fall back to top-level fields if present
                boxes = dr.get("bounding_boxes") or []
                detected = dr.get("detected_objects") or []
                for idx, box in enumerate(boxes):
                    try:
                        label = None
                        if idx < len(detected) and isinstance(detected[idx], dict):
                            label = detected[idx].get("label")
                        if label is None:
                            if detected and isinstance(detected[0], dict):
                                label = detected[0].get("label")
                            else:
                                label = DEFAULT_LABELS[0]

                        if label not in category_name_to_id:
                            category_name_to_id[label] = len(category_name_to_id) + 1

                        cat_id = category_name_to_id[label]
                        x1, y1, x2, y2 = [float(v) for v in box[:4]]
                        bw = max(0.0, x2 - x1)
                        bh = max(0.0, y2 - y1)
                        area = bw * bh

                        annotations.append({
                            "id": ann_id,
                            "image_id": current_img_id,
                            "category_id": cat_id,
                            "bbox": [x1, y1, bw, bh],
                            "area": area,
                            "iscrowd": 0,
                            "segmentation": [],
                        })
                        ann_id += 1
                    except Exception:
                        continue

        # categories list
        if category_name_to_id:
            categories = [{"id": cid, "name": name} for name, cid in category_name_to_id.items()]
        else:
            categories = [{"id": i + 1, "name": name} for i, name in enumerate(DEFAULT_LABELS)]

        coco = {"images": images, "annotations": annotations, "categories": categories}

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(coco, fh, indent=2)

        print(f"Wrote COCO json to {output_path}: {len(images)} images, {len(annotations)} annotations, {len(categories)} categories")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Export litter_report detections to COCO JSON")
    parser.add_argument("--out", required=True, help="output JSON file path")
    parser.add_argument("--status", required=False, help="filter detection_results.status value")
    parser.add_argument("--include-no-litter", action="store_true", help="include reports with zero detections")
    parser.add_argument("--source", choices=["auto", "detections", "reports"], default="auto", help="which DB table to source detections from (default: auto)")
    parser.add_argument("--verbose", action="store_true", help="print debug info")
    args = parser.parse_args()

    export_to_coco(args.out, detection_status=args.status, include_no_litter=args.include_no_litter, source=args.source, verbose=args.verbose)


if __name__ == "__main__":
    main()
