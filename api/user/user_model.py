# api/user/user_model.py
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from config.database import Base
import enum
from api.user_details.user_details_model import UserDetails
from api.badges.user_badges_model import UserBadge
from api.cleanup_events.cleanup_events_model import CleanupEvent
from api.notifications.notifications_model import Notification
from api.user.user_points_model import UserPointsLog
from api.roles.roles_model import Role
from api.roles.user_roles.user_roles_model import UserRole
from api.user_settings.user_settings_model import UserSettings
class UserStatus(enum.Enum):
    active     = 'active'
    inactive   = 'inactive'
    blocked    = 'blocked'
    unverified = 'unverified'

class User(Base):
    __tablename__ = 'users'

    id          = Column(Integer, primary_key=True, index=True)
    username    = Column(String(50), nullable=False, unique=True, index=True)
    email       = Column(String(255), nullable=False, unique=True, index=True)
    password    = Column(String(255), nullable=False)
    is_verified = Column(Boolean, nullable=False, default=False)
    status      = Column(Enum(UserStatus), nullable=False, default=UserStatus.unverified)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Add points for leaderboard
    points      = Column(Integer, nullable=False, default=0)

    # one-to-one link to your profile/details table
    details = relationship(
        UserDetails,
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # link to badges this user has earned
    badges = relationship(
        UserBadge,
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # events this user organizes
    organized_events = relationship(
        CleanupEvent,
        back_populates="organizer",
        cascade="all, delete-orphan",
        foreign_keys="[CleanupEvent.organized_by]"
    )

    points_log = relationship(
        UserPointsLog,
        back_populates="user",
        cascade="all, delete-orphan"
    )
    notifications = relationship(Notification, back_populates="user", cascade="all, delete-orphan")
    roles = relationship(
        Role,
        secondary=UserRole.__table__,       # the association table name
        back_populates="users"        # matches Role.users
    )
    settings = relationship(UserSettings, back_populates="user", uselist=False)


    def get_notifications(self):
        return self.notifications

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', points={self.points})>"
