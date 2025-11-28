from sqlalchemy import Column, Integer, Boolean, Enum, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
import enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from config.database import Base  # Import Base from shared config

class EventJoinRole(enum.Enum):
    organizer           = 'organizer'
    volunteer           = 'volunteer'
    sponsor             = 'sponsor'
    photo_verifier      = 'photo_verifier'
    field_recorder      = 'field_recorder'
    logistics_assistant = 'logistics_assistant'
    reporter            = 'reporter'

class EventJoinStatus(enum.Enum):
    pending   = 'pending'
    approved  = 'approved'
    rejected  = 'rejected'

class EventJoin(Base):
    __tablename__ = 'event_join'
    __table_args__ = (
        # Prevent duplicate registrations by the same user for the same event
        UniqueConstraint('cleanup_event_id', 'user_id', name='uq_event_user'),
    )

    id               = Column(Integer, primary_key=True, index=True)
    cleanup_event_id = Column(UUID(as_uuid=True), nullable=False)
    user_id          = Column(Integer, ForeignKey('users.id'), nullable=False)
    role             = Column(Enum(EventJoinRole), nullable=False, default=EventJoinRole.volunteer)
    status           = Column(
        Enum(EventJoinStatus),
        nullable=False,
        default=EventJoinStatus.approved
    )
    joined_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    auto_approved    = Column(Boolean, nullable=False, default=False)  # Optional
    approved_by      = Column(Integer, nullable=True)
    approved_at      = Column(DateTime(timezone=True), nullable=True)
    notes            = Column(Text, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at       = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )