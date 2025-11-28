from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from datetime import datetime
from api.user.user_model import UserStatus
from api.user_details.user_details_schema import UserDetailsResponse
from config.points_config import PointReason
# ----- Shared Schemas -----
class UserBase(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Alphanumeric usernames (underscores allowed), 3–50 chars"
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address required"
    )
    is_verified: bool = Field(
        False,
        description="Has the user completed email/OTP verification?"
    )
    status: UserStatus = Field(
        UserStatus.unverified,
        description="Current user status"
    )
    points: int = Field(
        0,
        description="Cumulative points for leaderboard"
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )

# ----- Registration Schema -----
class UserRegister(BaseModel):
    username: str = Field(
        ...,
        min_length=3, max_length=30,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Alphanumeric usernames (underscores allowed), 3–30 chars"
    )
    email: EmailStr = Field(
        ...,
        description="A valid email address"
    )
    password: str = Field(
        ...,
        min_length=8,
        description="At least 8 characters; mix of letters and numbers recommended"
    )
    accept_terms: bool = Field(
        ...,
        description="User must accept Terms of Service and Privacy Policy"
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )

# ----- Response Schema -----
class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    details: Optional[UserDetailsResponse] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        extra="forbid"
    )

# ----- Generic Response -----
class Message(BaseModel):
    message: str

# ----- Update Schema -----
class UserUpdate(BaseModel):
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Alphanumeric usernames (underscores allowed), 3–50 chars"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Valid email address required"
    )
    status: Optional[UserStatus] = Field(
        None,
        description="New user status"
    )
    is_verified: Optional[bool] = Field(
        None,
        description="Mark user as verified"
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )

# ----- Auth & OTP Schemas -----
class LoginRequest(BaseModel):
    email: EmailStr = Field(
        ..., description="Registered user email"
    )
    password: str = Field(
        ..., min_length=8, description="User password"
    )

    model_config = ConfigDict(extra="forbid")

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        ..., min_length=8, description="Existing password"
    )
    new_password: str = Field(
        ..., min_length=8, description="New password"
    )

    model_config = ConfigDict(extra="forbid")

class OTPRequest(BaseModel):
    email: EmailStr = Field(
        ..., description="Target email for OTP"
    )
    purpose: str = Field(
        ..., description="OTP purpose, e.g., 'user_registration', 'password_reset'"
    )

    model_config = ConfigDict(extra="forbid")

class OTPVerifyRequest(BaseModel):
    email: EmailStr = Field(
        ..., description="Email used for OTP"
    )
    otp_code: str = Field(
        ..., min_length=6, max_length=6, description="6-digit OTP code"
    )
    purpose: str = Field(
        ..., description="OTP purpose"
    )

    model_config = ConfigDict(extra="forbid")
    
class OTPVerifyPasswordRequest(BaseModel):
    email: EmailStr = Field(
        ..., description="Email used for OTP"
    )
    otp_code: str = Field(
        ..., min_length=6, max_length=6, description="6-digit OTP code"
    )
    new_password: str = Field(
        ..., min_length=8, description="New password"
    )

    model_config = ConfigDict(extra="forbid")
    
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
    message: str
    
class PointsLogEntry(BaseModel):
    delta: int
    reason: PointReason
    created_at: datetime

    class Config:
        orm_mode = True
        
class LeaderboardEntry(BaseModel):
    id: int
    username: str
    points: int

    model_config = {
        "from_attributes": True
    }