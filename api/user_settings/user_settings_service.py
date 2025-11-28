from sqlalchemy.orm import Session
from api.user_settings.user_settings_model import UserSettings


def get_or_create_user_settings(db: Session, user_id: int) -> UserSettings:
    """
    Retrieve user settings if they exist; otherwise, create default settings.
    """
    settings = db.query(UserSettings).filter_by(user_id=user_id).first()
    if not settings:
        settings = UserSettings(user_id=user_id, seen_tour=False)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def has_shown_tour(db: Session, user_id: int) -> bool:
    """
    Returns True if the user has already seen the instruction tour.
    """
    settings = get_or_create_user_settings(db, user_id)
    return settings.seen_tour


def mark_tour_shown(db: Session, user_id: int) -> None:
    """
    Mark the tour as shown for the given user.
    """
    settings = get_or_create_user_settings(db, user_id)
    if not settings.seen_tour:
        settings.seen_tour = True
        db.commit()
