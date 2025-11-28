from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from api.user_settings.user_settings_controller import (
    get_tour_status_controller,
    post_tour_shown_controller,
    update_user_language_controller,
    get_user_language_controller
)
from api.user_settings.user_settings_schema import TourStatus, LanguageResponse, LanguageUpdate
from config.database import get_db
from middlewares.auth_middleware import auth_middleware

router = APIRouter(
    prefix="/me/settings",
    tags=["settings"],
    dependencies=[Depends(auth_middleware)],
)

@router.get("/instruction-tour", response_model=TourStatus)
def get_instruction_tour_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
):
    return get_tour_status_controller(db=db, current_user=current_user)

@router.post("/instruction-tour", status_code=status.HTTP_204_NO_CONTENT)
def mark_instruction_tour_shown(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
):
    post_tour_shown_controller(db=db, current_user=current_user)
    return None

@router.get(
    "/language",
    response_model=LanguageResponse,
    summary="Get the user's preferred UI language",
)
def get_user_language(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
):
    """
    Returns the current user's preferred language setting.
    """
    return get_user_language_controller(
        db=db,
        user_id=current_user["id"],
    )
    
@router.post(
    "/language",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set or update the user's preferred UI language",
)
def set_user_language(
    payload: LanguageUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware),
):
    """
    Updates the current user's preferred language setting.
    """
    update_user_language_controller(
        db=db,
        user_id=current_user['id'],
        language=payload.language,
    )
    return None