# badges_routes.py
from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.badges.badges_controller import (
    list_all_badges,
    create_new_badge,
    read_my_badges,
    assign_badge,
)
from api.badges.badges_schema import BadgeRead, BadgeCreate, UserBadgeRead

router = APIRouter(prefix="/achievements", tags=["Achievements"])

@router.get(
    "/badges",
    response_model=List[BadgeRead],
    summary="List all available badges"
)
def get_badges(
    db: Session = Depends(get_db)
):
    return list_all_badges(db)

@router.post(
    "/badges",
    response_model=BadgeRead,
    summary="Create a new badge"
)
def post_badge(
    badge_in: BadgeCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    return create_new_badge(badge_in, db, current_user)

@router.get(
    "/me/badges",
    response_model=List[UserBadgeRead],
    summary="List badges earned by current user"
)
def get_my_badges(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    return read_my_badges(db, current_user)

@router.post(
    "/users/{user_id}/badges/{badge_id}",
    response_model=UserBadgeRead,
    summary="Assign a badge to a user"
)
def post_assign_badge(
    user_id: int,
    badge_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    return assign_badge(user_id, badge_id, db, current_user)