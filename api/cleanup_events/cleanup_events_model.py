from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, Numeric, ForeignKey, func
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from config.database import Base
import uuid
from api.litter_reports.cleanup_event_reports_model import CleanupEventReport
class CleanupEvent(Base):
    __tablename__ = "cleanup_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    litter_group_id = Column(UUID(as_uuid=True), ForeignKey("litter_groups.id"), nullable=True)
    organized_by     = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_name       = Column(Text, nullable=False)
    description      = Column(Text)
    location         = Column(Text)
    scheduled_date   = Column(DateTime(timezone=True), nullable=False)
    participant_limit     = Column(Integer)
    needs_approval        = Column(Boolean, nullable=False, default=False)
    registered_participants = Column(Integer, nullable=False, default=0)
    funding_required      = Column(Numeric(12, 2))
    funds_raised          = Column(Numeric(12, 2), nullable=False, default=0)
    event_status = Column(
        ENUM("upcoming", "ongoing", "completed", "cancelled",
             name="cleanup_event_status_enum", create_type=False),
        nullable=False, default="upcoming"
    )
    verification_status = Column(
        ENUM("pending", "submitted", "verified", "rejected",
             name="cleanup_event_verification_enum", create_type=False),
        nullable=False, default="pending"
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        server_default=func.now(), onupdate=func.now())

    litter_group = relationship("LitterGroup", back_populates="cleanup_events")
    organizer    = relationship("User", back_populates="organized_events")

    event_associations = relationship(
        CleanupEventReport,
        back_populates="event",
        cascade="all, delete-orphan",
        overlaps="litter_reports",
    )

    litter_reports = relationship(
        "LitterReport",
        secondary="cleanup_event_reports",
        back_populates="events",
        overlaps="event_associations",
    )
