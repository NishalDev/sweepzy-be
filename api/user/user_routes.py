from fastapi import APIRouter, Depends, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from middlewares.auth_middleware import auth_middleware
from api.user.user_controller import (
    register_user,
    verify_and_register,
    login_user,
    logout_user_account,
    send_otp,
    get_profile_details,
    update_profile,
    change_password_controller,
    get_my_points_log,
    award_user_points,
    get_leaderboard_controller,
    forgot_password_request,
    forgot_password_verify
)
from api.user.user_points_model import UserPointsLog
from api.user.user_schema import PointsLogEntry
from config.points_config import PointReason
from api.user.user_schema import (
    UserRegister,
    OTPVerifyRequest,
    OTPVerifyPasswordRequest,
    LoginRequest,
    OTPRequest,
    ChangePasswordRequest,
    UserUpdate,
    UserResponse,
    Message,
    TokenResponse,
    LeaderboardEntry
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ─── Registration & OTP Verification ───────────────────────────────────────────
@router.post(
    "/register",
    response_model=Message,
    status_code=status.HTTP_201_CREATED
)
def register(
    req: UserRegister,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create unverified user and send OTP to their email.
    """
    return register_user(req, background_tasks, db)

@router.post(
    "/register/verify",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK
)
def register_verify(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and complete registration by activating the user and issuing token.
    """
    return verify_and_register(request, db)

# ─── Authentication Routes ─────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    return login_user(credentials, db)

@router.post(
    "/logout",
    response_model=Message,
    dependencies=[Depends(auth_middleware)]
)
def logout(
    current_user=Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    return logout_user_account(current_user, db)

# ─── Generic OTP Routes ─────────────────────────────────────────────────────────
@router.post("/otp/send", response_model=Message)
def otp_send(
    request: OTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    return send_otp(request, background_tasks, db)

# ─── Profile Routes (protected) ─────────────────────────────────────────────────
@router.get(
    "/profile",
    response_model=UserResponse,
    dependencies=[Depends(auth_middleware)]
)
def get_profile(
    current_user=Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    return get_profile_details(current_user, db)

@router.put(
    "/profile",
    response_model=UserResponse,
    dependencies=[Depends(auth_middleware)]
)
def edit_profile(
    data: UserUpdate,
    current_user=Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    return update_profile(data, current_user, db)

@router.post(
    "/change-password",
    response_model=Message,
    dependencies=[Depends(auth_middleware)]
)
def change_password(
    data: ChangePasswordRequest,
    current_user=Depends(auth_middleware),
    db: Session = Depends(get_db)
):
    return change_password_controller(data, current_user, db)

@router.post(
    "/forgot-password-request",
    response_model=Message
)
def forgot_password_request_route(
    data: OTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    return forgot_password_request(data, background_tasks, db)


@router.post(
    "/forgot-password-verify",
    response_model=Message
)
def forgot_password_verify_route(
    data: OTPVerifyPasswordRequest,
    db: Session = Depends(get_db)
):
    return forgot_password_verify(data.email, data.otp_code, data.new_password, db)

@router.post("/users/{user_id}", response_model=PointsLogEntry)
def post_award_points(
    user_id: int,
    reason: PointReason,
    db = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    return award_user_points(user_id, reason, db, current_user)

@router.get(
    "/users/points",
    response_model=None   # disable automatic response-model generation
)
def read_my_points_log(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth_middleware)
):
    return get_my_points_log(db, current_user)

@router.get(
    "/users/leaderboard",
    response_model=List[LeaderboardEntry],
    summary="Get top users by points"
)
def read_leaderboard(
    limit: int = Query(5, ge=1, le=100, description="Number of top users to return"),
    leaderboard = Depends(get_leaderboard_controller)
) -> List[LeaderboardEntry]:
    return leaderboard