import uuid
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from config.database import get_db
from api.litter_reports.litter_reports_service import (
    create_litter_report,
    get_user_litter_reports,
    get_all_litter_reports,
    get_litter_report,
    update_litter_report,
    delete_litter_report,
    mark_reports_on_map,
    get_user_litter_report
)
from api.litter_reports.litter_reports_schema import (
    LitterReportCreate,
    LitterReportResponse,
    LitterReportUpdate,
    LitterReportListResponse
)
from api.uploads.uploads_model import Upload
# from api.notifications.notifications_service import report_approved, report_rejected
from api.litter_reports.litter_reports_model import LitterReport
from middlewares.auth_middleware import auth_middleware
from utils.query_params import QueryParams

def create_report_controller(
    report_data: LitterReportCreate,
    db: Session,
    user_id: int
) -> LitterReportResponse:
    """
    Create a new litter report (linked to an existing Upload), persist it,
    emit the `report_submitted` signal, and return the full Report object.
    """
    # 1️⃣ Build the payload and persist
    payload = report_data.model_dump(exclude_none=False) | {"user_id": user_id}
    report: LitterReport = create_litter_report(db, payload)  # this should do db.add() and db.flush()

    if not report:
        raise HTTPException(status_code=400, detail="Failed to create litter report")

    # 2️⃣ Make sure it’s in the DB
    db.commit()
    db.refresh(report)   # reload any defaults (timestamps, etc.)
    print(f"[controller] Created report {report.id!r}, about to send signal")
    # 3️⃣ Emit the signal so your listener can pick it up
    #    We send the ID as a string to match your listener’s expectation.
    # report_submitted.send(None, report_id=str(report.id))
    # print(f"[controller] Sent report_submitted for {report.id!r}")
    # 4️⃣ Return what your endpoint expects
    return report

def get_user_litter_reports_controller(
    db: Session,
    params: QueryParams[LitterReport],   # pagination params
    user_id: int,
    status: Optional[str] = None,
    detection_status: Optional[str] = None
) -> LitterReportListResponse:
    """
    Invokes the service and wraps its output in our Pydantic schema.
    """
    result = get_user_litter_reports(
        db=db,
        params=params,
        user_id=user_id,
        status=status,
        detection_status=detection_status
    )
    return LitterReportListResponse(
        total_count=result["total_count"],
        total_litter_count=result["total_litter_count"],
        reports=result["reports"],
        groups=result["groups"],
    )

def get_user_litter_report_controller(
    report_id: uuid.UUID,
    db: Session,
    user_id: int, 
) -> LitterReportResponse:  
    """
    Fetches a single LitterReport by ID for the current user.
    Raises 404 if not found.
    (Admins-only check is done at the route level.)
    """
    report = get_user_litter_report(db, report_id, user_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

def list_litter_reports_controller(
    db: Session,
    params: Optional[QueryParams[LitterReport]] = None,
    status: Optional[str] = None,
    city: Optional[str] = None,
    landmark: Optional[str] = None,
    detection_status: Optional[str] = None,
) -> LitterReportListResponse:
    result = get_all_litter_reports(
        db=db,
        params=params,
        status=status,
        city=city,
        landmark=landmark,
        detection_status=detection_status,
    )

    return LitterReportListResponse(
        total_count=result["total_count"],
        total_litter_count=result["total_litter_count"],
        reports=result["items"],
        groups=result["clusters"],
    )

def get_litter_report_controller(
    report_id: uuid.UUID,
    db: Session
) -> LitterReportResponse:
    report = db.get(LitterReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Attach image_url
    if report.upload_id:
        upload = db.get(Upload, report.upload_id)
        if upload:
            report.image_url = upload.file_url

    # (Optionally: load total_litter_count here, or leave that for another endpoint)

    # Wrap it in the Pydantic model and return
    return LitterReportResponse.from_orm(report)


def update_report_controller(
    report_id: uuid.UUID,
    update_data: dict,
    db: Session,
) -> LitterReportResponse:
    # perform the update
    report = update_litter_report(db, report_id, update_data)

    # trigger notifications based on new status
    # new_status = getattr(report, "status", None)
    # if new_status == "approved":
    #     report_approved.send(None, report_id=report.id)
    # elif new_status == "rejected":
    #     report_rejected.send(None, report_id=report.id)

    return report

def delete_report_controller(
    report_id: uuid.UUID,
    db: Session,
    user_id: int,                              # ← added
) -> dict:
    return delete_litter_report(db, report_id, user_id)

def mark_reports_on_map_controller(
    db: Session = Depends(get_db)
) -> dict:
    """
    Mark all detected litter reports on the map (update is_mapped to True).
    """
    mapped_count = mark_reports_on_map(db)  # Call the service function
    if mapped_count == 0:
        raise HTTPException(status_code=404, detail="No reports to map")
    
    return {"detail": f"{mapped_count} reports marked on the map."}