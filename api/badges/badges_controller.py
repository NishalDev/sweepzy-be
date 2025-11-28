# badges_controller.py
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.badges.badges_schema import BadgeCreate, BadgeRead, UserBadgeRead
from api.badges.badges_service import BadgeService
from api.badges.badges_model import Badge as BadgeModel

service = BadgeService

def list_all_badges(db: Session = Depends(get_db)) -> List[BadgeRead]:
    return service(db).list_badges()

def create_new_badge(
    badge_in: BadgeCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> BadgeRead:
    exists = db.query(BadgeModel).filter(BadgeModel.name == badge_in.name).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Badge name already exists")
    return service(db).create_badge(badge_in)

def read_my_badges(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> List[UserBadgeRead]:
    return service(db).list_user_badges(current_user['id'])

def assign_badge(
    user_id: int,
    badge_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> UserBadgeRead:
    badge = service(db).get_badge(badge_id)
    if not badge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found")
    return service(db).assign_badge_to_user(user_id, badge_id)