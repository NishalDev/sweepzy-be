import datetime
import random
import string
from typing import Optional, Tuple

from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, IntegrityError
from api.user.user_model import User, UserStatus
from api.otp.otp_model import OTP
from api.user.user_schema import UserRegister
from helpers.token_helper import create_user_token as create_access_token
from helpers.mail_helper import send_email
from api.user_details.user_details_model import UserDetails
from api.user.user_points_model import UserPointsLog
from config.points_config import PointReason, POINT_VALUES
from api.roles.user_roles.user_roles_model import UserRole
from api.roles.roles_model import Role
# Initialize password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash the given password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify that the plain password matches the hashed password."""
    return pwd_context.verify(plain, hashed)



def create_user(db: Session, data: UserRegister) -> User:
    """
    Create a new user and all related records in one transaction.
    Rolls back completely if anything fails.
    """
    try:
        with db.begin():
            # 1️⃣ Create the User
            new_user = User(
                username=data.username,
                email=data.email,
                password=hash_password(data.password),
                is_verified=False,
                status=UserStatus.unverified
            )
            db.add(new_user)

            # Make sure SQLAlchemy assigns us an ID
            db.flush()

            # 2️⃣ Assign the default "user" role
            user_role = (
                db.query(Role)
                  .filter_by(name="user")
                  .one_or_none()
            )
            if not user_role:
                raise RuntimeError("Default role 'user' not found in roles table")

            db.add(UserRole(user_id=new_user.id, role_id=user_role.id))

            # 3️⃣ Create associated empty UserDetails
            empty_details = UserDetails(
                user_id=new_user.id,
                full_name="",
                bio="",
                city="",
                state="",
                country="",
                postal_code="",
                phone="",
                profile_photo="",
                social_links={},
                cleanup_types=[],
                availability=None,
                skills=[]
            )
            db.add(empty_details)
        # commit happens here
        db.refresh(new_user)
        return new_user

    except IntegrityError as e:
        # this catches any UNIQUE constraint violation on username/email
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists."
        )


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Authenticate user and raise structured HTTPException on failure.
    """
    user = db.query(User).filter(User.email == email).first()

    # If user missing OR password mismatch -> generic INVALID_CREDENTIALS
    if not user or not verify_password(password, getattr(user, "password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Email or password incorrect"}
        )

    # If you still want to tell about verification state (optional)
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_VERIFIED", "message": "Account is registered but not verified.", "email": email}
        )


    # Activate user if login successful
    if user.status != UserStatus.active:
        user.status = UserStatus.active
        db.commit()
        db.refresh(user)

    return user


def logout_user(db: Session, user_id: int) -> bool:
    """
    Log out user by setting status to inactive.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    user.status = UserStatus.inactive
    db.commit()
    return True


def get_access_token(user: User, expires_hours: int = 24*30) -> str: 
    """
    Generate JWT access token for the user.
    """
    return create_access_token(user, expires_hours)


def send_otp(db: Session, email: str, purpose: str) -> str:
    """
    Generate and email an OTP code for the given purpose.
    """
    # Generate 6-digit code
    code = "".join(random.choices(string.digits, k=6))

    expires_at = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=10
    )
    otp = OTP(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
        used=False
    )
    db.add(otp)
    db.commit()

    subject = f"Your {purpose.replace('_', ' ').title()} OTP Code"
    body = (
        f"Your OTP code is {code}. "
        f"It will expire at {expires_at.isoformat()} UTC."
    )
    send_email(email, subject, body)
    return code


def verify_otp(db: Session, email: str, otp_code: str, purpose: str) -> bool:
    """
    Verify the provided OTP code for the email and purpose.
    Marks OTP as used upon success.
    """
    otp = (
        db.query(OTP)
        .filter_by(email=email, purpose=purpose, code=otp_code, used=False)
        .first()
    )
    if not otp or otp.expires_at < datetime.datetime.utcnow():
        return False
    otp.used = True
    db.commit()
    return True


def get_user_profile(db: Session, user_id: int) -> Optional[User]:
    """
    Fetch a user by ID with optimized query.
    """
    from sqlalchemy.orm import joinedload
    
    return (
        db.query(User)
        .options(
            joinedload(User.details),
            joinedload(User.roles)
        )
        .filter(User.id == user_id)
        .first()
    )


def update_user_profile(
    db: Session,
    user_id: int,
    **fields
) -> Optional[User]:
    """
    Update provided fields for a user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    for key, value in fields.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user

def reset_user_password(db: Session, user_id: int, new_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    user.password = hash_password(new_password)  # <-- changed to 'password'
    db.commit()
    db.refresh(user)
    return True

def change_user_password(
    db: Session,
    user_id: int,
    current_password: str,
    new_password: str
) -> bool:
    """
    Change a user's password after verifying current password.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not verify_password(current_password, user.password):
        return False
    user.password = hash_password(new_password)
    db.commit()
    return True


def deactivate_user_account(db: Session, user_id: int) -> bool:
    """
    Soft-delete/deactivate a user account.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    user.status = UserStatus.inactive
    db.commit()
    return True

# award points

def award_points(
    db: Session,
    current_user: dict,
    user_id: int,
    reason: PointReason
) -> Optional[Tuple[User, UserPointsLog]]:
    """
    Award points to `user_id` for the given `reason`.
    `current_user` is the actor (for auditing, if needed).
    Returns (updated_user, log) or None if reason has no points.
    """
    delta = POINT_VALUES.get(reason, 0)
    if delta <= 0:
        return None

    # fetch the target user
    target = db.query(User).filter(User.id == user_id).one_or_none()
    target.points += delta

    # record the points-log
    log = UserPointsLog(
        user_id=user_id,
        delta=delta,
        reason=reason.value
    )
    db.add(log)
    db.commit()
    db.refresh(target)
    return target, log

def get_user_points_log(
    db: Session,
    user_id: int
    ) -> list[UserPointsLog]:
    return (
        db.query(UserPointsLog)
          .filter(UserPointsLog.user_id == user_id)
          .order_by(UserPointsLog.created_at.desc())
          .all()
    )
    
    
def get_leaderboard(
    db: Session,
    limit: int = 5
) -> list[User]:
    """
    Return the top `limit` users ordered by points descending.
    """
    return (
        db.query(User)
          .order_by(User.points.desc())
          .limit(limit)
          .all()
    )

