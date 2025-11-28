# routes/notifications_route.py

from fastapi import APIRouter, Depends, Query
from typing import List
from sqlalchemy.orm import Session

from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.notifications.notifications_schema import NotificationRead
from api.notifications.notifications_controller import fetch_notifications

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "/",
    response_model=List[NotificationRead],
    summary="Fetch paginated notifications for the authenticated user"
)
def get_user_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
):
    """
    Returns the paginated list of notifications for the logged‑in user.
    """
    user_id = current_user["id"]
    return fetch_notifications(db=db, user_id=user_id, page=page, limit=limit)
