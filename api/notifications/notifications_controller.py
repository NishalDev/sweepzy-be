from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from config.database import get_db
from api.notifications.notifications_model import Notification
from api.notifications.notifications_schema import NotificationRead

def fetch_notifications(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 10
) -> List[NotificationRead]:
    offset = (page - 1) * limit

    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return notifications
