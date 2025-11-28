from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from api.user_settings.user_settings_service import (
    has_shown_tour, mark_tour_shown, get_or_create_user_settings
)
from api.user_settings.user_settings_schema import (
    TourStatus, LanguageResponse
)


def get_tour_status_controller(
    db: Session,
    current_user: dict,
) -> TourStatus:
    """
    Controller to get whether the user has seen the instruction tour.
    """
    try:
        shown = has_shown_tour(db, current_user['id'])
        return TourStatus(shown=shown)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch tour status: {str(e)}",
        )


def post_tour_shown_controller(
    db: Session,
    current_user: dict,
) -> None:
    """
    Controller to mark the instruction tour as shown for the user.
    """
    try:
        mark_tour_shown(db, current_user['id'])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to update tour status: {str(e)}",
        )


def get_user_language_controller(
    db: Session,
    user_id: int
) -> LanguageResponse:
    """
    Controller to fetch the current user's preferred UI language.
    Creates a settings row if none exists.
    """
    try:
        settings = get_or_create_user_settings(db, user_id)
        lang = settings.language or None
        return LanguageResponse(language=lang)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch user language: {str(e)}"
        )


def update_user_language_controller(
    db: Session,
    user_id: int,
    language: str
) -> None:
    """
    Update the user's preferred UI language and reset tour status.
    """
    try:
        settings = get_or_create_user_settings(db, user_id)
        settings.language = language
        # reset tour so they see it again in new language
        settings.seen_tour = False
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to update language: {str(e)}"
        )


def get_user_settings_controller(
    db: Session,
    user_id: int
) -> dict:
    """
    Combined endpoint to get both language and tour state.
    """
    try:
        settings = get_or_create_user_settings(db, user_id)
        return {
            "language": settings.language,
            "seen_tour": settings.seen_tour,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch settings: {str(e)}"
        )
