# File: api/user_details/user_controller.py

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from api.user_details.user_service import (
    get_user_with_details,
    create_user_details,
    update_user_details,
)
from api.user_details.user_details_schema import (
    UserDetailsResponse,
    UserDetailsCreate,
    UserDetailsUpdate,
)

def get_user_details_controller(user_id: int, db: Session) -> Optional[UserDetailsResponse]:
    """
    Fetch the User (with eager-loaded .details), then extract
    the UserDetails instance for Pydantic validation.
    """
    user = get_user_with_details(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.details:
        # Instead of raising 404, return None
        return None

    return UserDetailsResponse.model_validate(user.details)

def create_user_details_controller(
    user_id: int,
    details_data: UserDetailsCreate,
    db: Session
) -> UserDetailsResponse:
    # Prevent duplicates
    # Here we call your original get_user_details (or check user.details)
    user = get_user_with_details(db, user_id)
    if user and user.details:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User details already exist"
        )

    new_details = create_user_details(db, user_id, details_data.model_dump())
    return UserDetailsResponse.model_validate(new_details)


def update_user_details_controller(
    user_id: int,
    details_data: UserDetailsUpdate,
    db: Session
) -> UserDetailsResponse:
    updated = update_user_details(
        db,
        user_id,
        details_data.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User details not found"
        )
    return UserDetailsResponse.model_validate(updated)
