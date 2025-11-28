# api/user_details/user_routes.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from api.user_details.user_controller import (
    get_user_details_controller,
    create_user_details_controller,
    update_user_details_controller
)
from api.user_details.user_details_schema import UserDetailsResponse, UserDetailsCreate, UserDetailsUpdate
from config.database import get_db

# Use empty-string paths so GET, POST, PUT all match both with and without trailing slash
router = APIRouter(prefix="/users/{user_id}/details", tags=["User Details"])

@router.get("", response_model=Optional[UserDetailsResponse])
def get_details(user_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed profile information for a user."""
    return get_user_details_controller(user_id, db)

@router.post("", response_model=UserDetailsResponse)
def create_details(user_id: int, details: UserDetailsCreate, db: Session = Depends(get_db)):
    """Create new details record for a user."""
    return create_user_details_controller(user_id, details, db)

@router.put("", response_model=UserDetailsResponse)
def update_details(user_id: int, details: UserDetailsUpdate, db: Session = Depends(get_db)):
    """Update the user's details."""
    return update_user_details_controller(user_id, details, db)
