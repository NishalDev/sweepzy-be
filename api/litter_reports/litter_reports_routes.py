import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Form, Query, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from middlewares.role_middleware import role_middleware
from api.litter_reports.litter_reports_controller import (
    create_report_controller,
    get_litter_report_controller,
    update_report_controller,
    delete_report_controller,
    mark_reports_on_map_controller,
    list_litter_reports_controller,
    get_user_litter_reports_controller,
    get_user_litter_report_controller
)
from api.litter_reports.litter_reports_schema import (
    LitterReportCreate,
    LitterReportResponse,
    LitterReportUpdate,
    LitterReportListResponse
)
from utils.query_params import QueryParams
from api.litter_reports.litter_reports_model import LitterReport
from utils.deps import optional_pagination

router = APIRouter(prefix="/litter_reports", tags=["Litter Reports"])


@router.post("/", response_model=LitterReportResponse, summary="Create a new litter report")
def create_litter_report_endpoint(
    upload_id: uuid.UUID = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    severity: Optional[str] = Form(None),
    detection_results: Optional[str] = Form(None),
    reward_points: Optional[int] = Form(0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),   # ← protect
):
    """
    Create a new litter report linked to an existing upload.
    """
    user_id = current_user["id"]

    # Parse JSON string for detection results if provided
    parsed_results = None
    if detection_results:
        try:
            parsed_results = json.loads(detection_results)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON for detection_results")

    payload = LitterReportCreate(
        user_id=user_id,
        upload_id=upload_id,
        latitude=latitude,
        longitude=longitude,
        severity=severity,
        detection_results=parsed_results,
        reward_points=reward_points
    )
    return create_report_controller(payload, db, current_user["id"])

@router.get(
    "/user_reports",
    response_model=LitterReportListResponse,
    summary="List all user-specific litter reports"
)
def get_user_litter_reports(
    params: QueryParams[LitterReport] = Depends(),
    status: Optional[str] = Query(None, description="Filter by report status"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
    detection_status: Optional[str] = None
):
    """
    Returns every litter report (optional status filter), 
    plus counts and clusters.
    """
    return get_user_litter_reports_controller(db, params, current_user["id"], status, detection_status)

@router.get(
    "/user_reports/{report_id}",
    response_model=LitterReportResponse,
    summary="Get a single user litter report",
)
def get_user_litter_report_route(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
):
    """
    Route-level protection ensures only users with the 'admin' role
    can reach this function. Simply delegates to the controller.
    """
    return get_user_litter_report_controller(report_id, db, current_user["id"])



@router.get(
    "/for_user",
    response_model=LitterReportListResponse,
    summary="List all litter reports",
)
def list_litter_reports(
    params: Optional[QueryParams[LitterReport]] = Depends(optional_pagination),
    status: Optional[str] = Query(None, description="Filter by report status"),
    city: Optional[str] = Query(None, description="Filter by city name"),
    landmark: Optional[str] = Query(None, description="Filter by landmark name"),
    detection_status: Optional[str] = Query(None, description="Filter by detection_status"),
    db: Session = Depends(get_db),
):
    return list_litter_reports_controller(
        db=db,
        params=params,
        status=status,
        city=city,
        landmark=landmark,
        detection_status=detection_status,
    )
    
@router.get(
    "",
    response_model=LitterReportListResponse,
    summary="List all litter reports",
    dependencies=[Depends(role_middleware(required_roles=["admin"]))]
)
def list_litter_reports_user(
    params: QueryParams[LitterReport] = Depends(),
    status:            Optional[str]   = Query(None, description="Filter by report status"),
    city:              Optional[str]   = Query(None, description="Filter by city name"),
    detection_status:  Optional[str]   = Query(None, description="Filter by detection_status"),
    db:                Session          = Depends(get_db),
):
    """
    Returns every litter report (optional status, city, detection_status filters),
    plus counts and clusters.
    """
    return list_litter_reports_controller(
        db=db,
        params=params,
        status=status,
        city=city,
        detection_status=detection_status,
    )
@router.get(
    "/{report_id}",
    response_model=LitterReportResponse,
    summary="(Admin only) Get a single litter report",
    dependencies=[Depends(role_middleware(required_roles=["admin"]))]
)
def get_litter_report_route(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Route-level protection ensures only users with the 'admin' role
    can reach this function. Simply delegates to the controller.
    """
    return get_litter_report_controller(report_id, db)

@router.put("/{report_id}", response_model=LitterReportResponse, dependencies=[Depends(role_middleware(required_roles=["admin"]))], summary="Update a litter report")
def update_litter_report(
    report_id: uuid.UUID,
    update_data: LitterReportUpdate,
    db: Session = Depends(get_db),
):
    return update_report_controller(report_id, update_data.dict(exclude_unset=True), db)


@router.delete("/{report_id}", summary="Delete a litter report")
def delete_litter_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),   # ← protect
):
    return delete_report_controller(report_id, db, current_user["id"])


@router.post("/mark-reports", summary="Mark all reports on map")
def mark_reports_on_map_endpoint(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),   # ← protect
):
    return mark_reports_on_map_controller(db)
