from fastapi import HTTPException, status, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from pydantic import EmailStr
from typing import Optional, List
from middlewares.auth_middleware import auth_middleware
from api.user.user_points_model import UserPointsLog
from config.points_config import PointReason, POINT_VALUES
from config.database import get_db
from api.user.user_schema import (
    UserRegister,
    UserResponse,
    OTPRequest,
    OTPVerifyRequest,
    LoginRequest,
    ChangePasswordRequest,
    UserUpdate,
    LeaderboardEntry
)
from api.user.user_service import (
    create_user,
    authenticate_user,
    get_access_token,
    logout_user,
    change_user_password,
    reset_user_password,
    award_points,
    get_user_points_log,
    get_leaderboard
)
from api.otp.otp_service import send_otp_to_email as otp_service_send, verify_otp_for_email as otp_service_verify
from api.user.user_model import User, UserStatus

# Controller functions for user operations

# Step 1: register user and send OTP
def register_user(
    req: UserRegister,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> dict:
    """
    Creates an unverified user and sends an OTP to email.
    """
    db_user = create_user(db, req)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User registration failed"
        )
    background_tasks.add_task(
        otp_service_send,
        db,
        db_user.email,
        db_user.username, 
        "user_registration"
    )
    return {"message": "User created; OTP sent to email. Please verify."}

# Step 2: verify OTP and complete registration
def verify_and_register(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Verifies OTP, activates user account, and returns token.
    """
    if not otp_service_verify(db, request.email, request.otp_code, "user_registration"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user.is_verified = True
    user.status = UserStatus.active
    db.commit()
    token = get_access_token(db, user)
    validated = UserResponse.model_validate(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": validated,
        "message": "OTP verified; registration complete"
    }


def login_user(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
) -> dict:
    # authenticate_user will raise HTTPException with structured detail on failure
    user = authenticate_user(db, credentials.email, credentials.password)

    token = get_access_token(db, user)
    validated = UserResponse.model_validate(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": validated,
        "message": "Login successful"
    }

# Logout
def logout_user_account(
    current_user: dict,
    db: Session = Depends(get_db)
) -> dict:
    user_id = current_user.get("id")
    success = logout_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )
    return {"message": "Logged out successfully"}

# Send OTP (generic)
def send_otp(
    request: OTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> dict:
    # lookup user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    background_tasks.add_task(
        otp_service_send,
        db,
        request.email,
        user.username,
        request.purpose
    )
    return {"message": "OTP sent successfully"}

# # Verify OTP (generic)
# def verify_otp(
#     request: OTPVerifyRequest,
#     db: Session = Depends(get_db)
# ) -> dict:
#     if otp_service_verify(db, request.email, request.otp_code, request.purpose):
#         return {"message": "OTP verified successfully"}
#     raise HTTPException(
#         status_code=status.HTTP_400_BAD_REQUEST,
#         detail="OTP verification failed"
#     )

# Profile retrieval
def get_profile_details(
    current_user: dict,
    db: Session = Depends(get_db)
) -> UserResponse:
    user = db.query(User).filter(User.id == current_user.get("id")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.model_validate(user)

# Profile update
def update_profile(
    data: UserUpdate,
    current_user: dict,
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Update profile fields for the current_user.
    """
    user = db.query(User).filter(User.id == current_user.get("id")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)

# Change password
def change_password_controller(
    data: ChangePasswordRequest,
    current_user: dict,
    db: Session = Depends(get_db)
) -> dict:
    """
    Change password for the current_user.
    """
    success = change_user_password(
        db,
        current_user.get("id"),
        data.current_password,
        data.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    return {"message": "Password changed successfully"}

# award points endpoint for manual/admin use
def award_user_points(
    user_id: int,
    reason: PointReason,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> UserPointsLog:
    """
    Admin/manual endpoint to award points to a user.
    """
    result = award_points(db, current_user, user_id, reason)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reason or zero points"
        )
    _, log = result
    return log

# fetch current user's points log
def get_my_points_log(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
) -> List[UserPointsLog]:
    return get_user_points_log(db, current_user["id"])

def get_leaderboard_controller(
    limit: int = 5,
    db: Session = Depends(get_db)
) -> List[LeaderboardEntry]:
    users = get_leaderboard(db, limit)

    results: List[LeaderboardEntry] = []
    for u in users:
        # ensure `username` is never None; fallback to email
        entry_data = {
            "id": u.id,
            "username": u.username or u.email,
            "points": u.points,
        }
        # This will validate and convert to a LeaderboardEntry
        entry = LeaderboardEntry.model_validate(entry_data)
        results.append(entry)

    return results

def forgot_password_request(
    request: OTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> dict:
    """
    Sends an OTP to the user's email for password reset.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email"
        )

    # Use username from DB instead of request
    background_tasks.add_task(
        otp_service_send,
        db,
        request.email,
        user.username,  
        "password_reset"
    )
    return {"message": "OTP sent to email for password reset."}


def forgot_password_verify(
    email: EmailStr,
    otp_code: str,
    new_password: str,
    db: Session
) -> dict:
    """
    Verifies OTP and updates the user's password.
    """
    if not otp_service_verify(db, email, otp_code, "password_reset"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    success = reset_user_password(db, user.id, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

    return {"message": "Password reset successfully"}