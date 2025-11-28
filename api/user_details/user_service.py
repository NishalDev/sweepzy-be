# api/user_details/user_service.py

from sqlalchemy.orm import Session, selectinload
from api.user.user_model import User
from api.user_details.user_details_model import UserDetails

def get_user_with_details(db: Session, user_id: int) -> User | None:
    """
    Retrieve the User and its UserDetails (if any) in one query.
    Returns None if no User with that ID exists.
    """
    return (
        db.query(User)
        .options(selectinload(User.details))
        .filter(User.id == user_id)
        .first()
    )

def create_user_details(db: Session, user_id: int, details_data: dict) -> UserDetails:
    """
    Create a new user details record for the given user.
    
    Assumes details_data is a dictionary containing the fields from the corresponding Pydantic model.
    If a record already exists for the user, this function may either throw an error or return that record.
    """
    # Optionally, check if details already exist to avoid duplicates:
    existing = get_user_with_details(db, user_id)
    if existing:
        # Depending on your app's logic, you may raise an error instead.
        return existing

    new_details = UserDetails(user_id=user_id, **details_data)
    db.add(new_details)
    db.commit()
    db.refresh(new_details)
    return new_details

def update_user_details(db: Session, user_id: int, details_data: dict) -> UserDetails:
    """
    Update the user details record for the given user.
    
    Only the fields provided in details_data will be updated.
    Returns the updated record, or None if no record exists.
    """
    # Load the User *and* its .details relationship
    user = get_user_with_details(db, user_id)
    # If no user or no details record, bail out
    if not user or not user.details:
        return None

    # Grab the actual UserDetails instance
    details = user.details

    # Patch only the provided fields
    for key, value in details_data.items():
        setattr(details, key, value)

    db.commit()
    db.refresh(details)
    return details
