import os
import uuid
import json
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, asc, desc, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from api.litter_reports.litter_reports_schema import LitterReportResponse
from api.litter_reports.litter_reports_model import LitterReport
from api.uploads.uploads_model import Upload
from api.litter_detections.litter_detections_model import LitterDetection
from fastapi import HTTPException
from typing import Any, Dict, List, Optional # Import Group model
from api.litter_groups.litter_groups_service import LitterGroupService
from shapely import wkb
from shapely.geometry import Point
from shapely.geometry import shape
from geoalchemy2.shape import from_shape
from utils.query_params import QueryParams

UPLOADS_DIR = os.path.join(os.getcwd(), "uploads")

# Utility: save uploaded file

def save_uploaded_file(uploaded_file) -> str:
    """
    Save the uploaded file to the 'uploads' directory and return its path.
    """
    if not os.path.exists(UPLOADS_DIR):
        os.makedirs(UPLOADS_DIR)

    # Generate unique filename and preserve extension
    ext = os.path.splitext(uploaded_file.filename)[1]
    fname = f"{uuid.uuid4()}{ext}"
    fpath = os.path.join(UPLOADS_DIR, fname)

    with open(fpath, "wb") as buf:
        buf.write(uploaded_file.file.read())

    return fpath


def create_litter_report(db: Session, report_data: dict) -> LitterReport:
    """
    Create a new LitterReport with latitude/longitude, populate its geom,
    then attempt immediate radius-based grouping.
    """
    serializable = jsonable_encoder(report_data)
    try:
        # 1) Insert new report row
        new_report = LitterReport(**serializable)
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

        # 2) Populate geom from latitude & longitude
        db.execute(text("""
            UPDATE litter_reports
               SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
             WHERE id = :rid
        """), {
            "lng": new_report.longitude,
            "lat": new_report.latitude,
            "rid": str(new_report.id)
        })
        db.commit()
        db.refresh(new_report)

        # 3) Attempt immediate radius-based grouping (within 500 m)
        _assign_to_nearest_group(
            db,
            new_report.id,
            new_report.latitude,
            new_report.longitude,
            radius_m=500
        )
        
        return new_report

    except Exception as e:
        db.rollback()
        print("❌ create_litter_report failed with payload:", serializable)
        print("❌ Exception:", e)
        return None

def get_user_litter_reports(
    db: Session,
    params: QueryParams[LitterReport],     # pagination params first
    user_id: int,
    status: Optional[str] = None,
    detection_status: Optional[str] = None,  # new filter
) -> Dict[str, Any]:
    """
    Fetch paginated litter reports uploaded by a given user (optionally filtered by status and detection_status),
    attach image URLs, sum total litter, and collect unique groups.
    """
    # 1. Base query with optional status filter
    query = (
        db.query(LitterReport)
          .options(joinedload(LitterReport.group))
          .filter(LitterReport.user_id == user_id)
    )
    if status:
        query = query.filter(LitterReport.status == status)

    # 2. Total count before pagination
    total_count = query.count()

    # 3. Apply sorting & pagination via params
    try:
        paged_query = params.apply(query, LitterReport)
    except ValueError as e:
        raise ValueError(f"Invalid pagination parameters: {e}")

    # 4. Fetch paginated reports
    reports: List[LitterReport] = paged_query.all()

    # 5. In-memory detection_status filter
    if detection_status:
        filtered = []
        for r in reports:
            dr = r.detection_results
            if isinstance(dr, str):
                try:
                    dr = json.loads(dr)
                except Exception:
                    continue
            if isinstance(dr, dict) and dr.get("status") == detection_status:
                filtered.append(r)
        reports = filtered

    # 6. Sum total_litter_count for this page
    report_ids = [r.id for r in reports]
    if report_ids:
        total_litter_count = db.execute(
            text("""
                SELECT COALESCE(SUM(total_litter_count), 0)
                  FROM litter_detections
                 WHERE litter_report_id = ANY(:ids)
            """),
            {"ids": report_ids}
        ).scalar()
    else:
        total_litter_count = 0

    # 7. Attach image URLs
    for r in reports:
        if r.upload_id:
            row = db.execute(
                text("SELECT file_url FROM uploads WHERE id = :u"),
                {"u": str(r.upload_id)}
            ).fetchone()
            if row:
                r.image_url = row.file_url

    # 8. Collect unique groups
    group_map: Dict[Any, Any] = {}
    for r in reports:
        if r.group:
            group_map[r.group.id] = {
                "id": r.group.id,
                "name": r.group.name,
                "coverage_area": r.group.coverage_area,
            }

    return {
        "total_count": total_count,
        "total_litter_count": total_litter_count,
        "reports": reports,
        "groups": list(group_map.values()),
    }
    


def get_all_litter_reports(
    db: Session,
    params: Optional[QueryParams[LitterReport]] = None,
    status: Optional[str] = None,
    city: Optional[str] = None,
    landmark: Optional[str] = None,
    detection_status: Optional[str] = None,  # expects values like "completed"
) -> Dict[str, Any]:
    """
    Returns filtered & optionally paginated litter reports.
    For double-encoded detection_results we use detection_results::text::json->>'status'
    which reliably extracts the inner JSON's status before pagination.
    """

    # --- 1) Base query & static filters ---
    base_q = db.query(LitterReport).options(joinedload(LitterReport.group))
    base_q = base_q.filter(LitterReport.is_grouped.is_(False))

    if status:
        base_q = base_q.filter(LitterReport.status == status)

    if city:
        base_q = base_q.filter(LitterReport.city.ilike(f"%{city}%"))
    
    if landmark:
        base_q = base_q.filter(LitterReport.landmark.ilike(f"%{landmark}%"))

    if detection_status:
        status_filter = cast(LitterReport.detection_results, JSONB)["status"].astext == detection_status
        base_q = base_q.filter(status_filter)

    # --- 2) total_count after filtering (before pagination) ---
    total_count = int(base_q.with_entities(func.count(LitterReport.id)).scalar() or 0)

    # --- 3) Sorting ---
    # choose sort_by/sort_order from params if present, otherwise sensible defaults
    sort_by = params.sort_by if params and getattr(params, "sort_by", None) else "id"
    sort_order = params.sort_order if params and getattr(params, "sort_order", None) else "desc"

    sort_col = getattr(LitterReport, sort_by, None)
    if not sort_col:
        raise ValueError(f"Invalid sort_by field: {sort_by}")

    ordered_q = base_q.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))

    # --- 4) Pagination (only if params provided) ---
    q = ordered_q
    if params:
        # guard if offset/limit are Optional in QueryParams
        offset = getattr(params, "offset", None)
        limit = getattr(params, "limit", None)

        if offset is not None:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)

    reports: List[LitterReport] = q.all()

    # --- 5) total_litter_count (parallel aggregate query) ---
    det_sum_q = (
        db.query(func.coalesce(func.sum(LitterDetection.total_litter_count), 0))
        .join(LitterReport, LitterReport.id == LitterDetection.litter_report_id)
        .filter(LitterReport.is_grouped.is_(False))
    )

    if status:
        det_sum_q = det_sum_q.filter(LitterReport.status == status)

    if city:
        det_sum_q = det_sum_q.filter(LitterReport.city.ilike(f"%{city}%"))

    if detection_status:
        status_filter = cast(LitterReport.detection_results, JSONB)["status"].astext == detection_status
        det_sum_q = det_sum_q.filter(status_filter)

    total_litter_count = int(det_sum_q.scalar() or 0)

    # --- 6) Attach image URLs (unchanged) ---
    for r in reports:
        if getattr(r, "upload_id", None):
            row = db.execute(
                text("SELECT file_url FROM uploads WHERE id = :u"),
                {"u": str(r.upload_id)}
            ).fetchone()
            if row:
                r.image_url = row.file_url

    # --- 7) Collect unique groups from current page ---
    group_map: Dict[int, Group] = {}
    for r in reports:
        if r.group:
            group_map[r.group.id] = r.group

    groups = [
        {"id": g.id, "name": g.name, "coverage_area": g.coverage_area}
        for g in group_map.values()
    ]

    return {
        "total_count": total_count,
        "total_litter_count": total_litter_count,
        "items": reports,
        "clusters": groups,
    }
    
def get_litter_report(
    db: Session,
    report_id: uuid.UUID,
    user_id: int,
    status: str | None = None
) -> Dict[str, Any]:
    """
    Fetch exactly one litter report by ID (and user).
    Mirrors the logic in `get_user_litter_reports` / `get_all_litter_reports`:
     1) base query with joinedload(group)
     2) sum total_litter_count
     3) attach image_url
     4) collect unique groups
    Returns a dict with total_count, total_litter_count, reports[], groups[].
    """

    # 1) Base query (filtering by report_id + user_id, optionally status)
    query = db.query(LitterReport).options(joinedload(LitterReport.group))
    query = query.filter(
        LitterReport.id == report_id,
        LitterReport.user_id == user_id
    )
    if status:
        query = query.filter(LitterReport.status == status)

    reports: List[LitterReport] = query.all()
    if not reports:
        raise HTTPException(status_code=404, detail="Report not found")
    total_count = len(reports)  # will be 1

    # 2) Sum total_litter_count from litter_detections
    report_ids = [r.id for r in reports]
    total_litter_count = 0
    if report_ids:
        total_litter_count = db.execute(
            text("""
              SELECT COALESCE(SUM(total_litter_count), 0)
                FROM litter_detections
               WHERE litter_report_id = ANY(:ids)
            """),
            {"ids": report_ids}
        ).scalar() or 0

    # 3) Attach image_urls from uploads
    for r in reports:
        if r.upload_id:
            row = db.execute(
                text("SELECT file_url FROM uploads WHERE id = :u"),
                {"u": str(r.upload_id)}
            ).fetchone()
            if row:
                # row[0] contains the file_url string
                r.image_url = row[0]

        # also attach the sum for this single report
        setattr(r, "total_litter_count", total_litter_count)

    # 4) Collect unique groups
    group_map: Dict[int, Dict[str, Any]] = {}
    for r in reports:
        if r.group:
            grp = r.group
            group_map[grp.id] = {
                "id": grp.id,
                "name": grp.name,
                "coverage_area": grp.coverage_area,
            }

    return {
        "total_count": total_count,
        "total_litter_count": total_litter_count,
        "reports": reports,
        "groups": list(group_map.values()),
    }
    
def get_user_litter_report(db: Session, report_id: uuid.UUID, user_id: int) -> LitterReport:
    """
    Fetches a single LitterReport by ID for the current user.
    Raises 404 if not found.
    """
    report = (
        db.query(LitterReport)
          .filter(
             LitterReport.id == report_id,
             LitterReport.user_id == user_id
          )
          .options(joinedload(LitterReport.group))
          .first()
    )
    if not report:
        return None
    return report

def update_litter_report(
    db: Session,
    report_id: uuid.UUID,
    update_data: dict,
):
    report = db.query(LitterReport).filter(LitterReport.id == report_id).first()
    if not report:
        return None

    # Convert dict safely
    geom_data = update_data.get("geom")
    if geom_data:
        geom = shape(geom_data)  # GeoJSON → Shapely
        report.geom = from_shape(geom, srid=4326)
        # Remove geom from update dict to avoid overwrite
        update_data.pop("geom", None)

    update_dict = jsonable_encoder(update_data)

    # Handle status change check
    status_being_approved = (
        update_dict.get("status") == "approved"
        and report.status != "approved"
    )

    # Apply all other updates (except geom)
    for k, v in update_dict.items():
        setattr(report, k, v)

    # Reverse-geocode city if approved
    if status_being_approved and report.geom is not None:
        # Convert WKBElement → Shapely Point
        raw = bytes(report.geom.data)
        point: Point = wkb.loads(raw)

        lat, lon = point.y, point.x
        city = LitterGroupService.reverse_geocode_city(lat, lon)
        if city:
            report.city = city

    db.commit()
    db.refresh(report)
    return report

def delete_litter_report(db: Session, report_id: uuid.UUID, user_id: int):
    report = (
        db.query(LitterReport)
          .filter(
             LitterReport.id == report_id,
             LitterReport.user_id == user_id
          )
          .first()
    )
    if report:
        db.delete(report)
        db.commit()
    return report


def get_reports_to_map(db: Session):
    return db.query(LitterReport).filter(
        LitterReport.is_mapped == False,
        LitterReport.is_detected == True
    ).all()


def mark_reports_on_map(db: Session):
    reports_to_map = get_reports_to_map(db)
    for report in reports_to_map:
        if report.latitude is None or report.longitude is None:
            continue
        report.is_mapped = True
        db.commit()
        db.refresh(report)
    return len(reports_to_map)


def _assign_to_nearest_group(db: Session, report_id: uuid.UUID, lat: float, lng: float, radius_m: float):
    """
    Find the nearest existing group within `radius_m` meters and assign report to it.
    """
    sql = text("""
      SELECT id
      FROM litter_groups
      WHERE ST_DWithin(
        geom,
        ST_SetSRID(ST_MakePoint(:lng, :lat),4326),
        :radius
      )
      ORDER BY ST_Distance(
        geom,
        ST_SetSRID(ST_MakePoint(:lng, :lat),4326)
      )
      LIMIT 1
    """)
    row = db.execute(sql, {"lng": lng, "lat": lat, "radius": radius_m}).first()
    if row:
        db.execute(text("""
          UPDATE litter_reports
             SET group_id = :gid,
                 is_grouped = TRUE
           WHERE id = :rid
        """), {"gid": str(row.id), "rid": str(report_id)})
        db.commit()
