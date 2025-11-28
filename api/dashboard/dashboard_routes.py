from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.dashboard.dashboard_controller import assemble_dashboard
from api.dashboard.dashboard_schema import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/user",
    response_model=DashboardResponse,
    response_model_exclude_none=False,  # hides any None fields
    summary="Full dashboard for every user"
)
def dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
):
    """
    Returns a unified dashboard containing:
      – User metrics
      – Host metrics
      – Charts & breakdowns
    """
    user_id = current_user["id"]
    # send through latitude/longitude if available; otherwise None
    user_lat = current_user.get("latitude")
    user_lng = current_user.get("longitude")

    # ALWAYS treat as 'host' under the covers so all metrics compute
    return assemble_dashboard(
        db=db,
        user_id=user_id,
        user_lat=user_lat,
        user_lng=user_lng,
        is_host=True,
    )
