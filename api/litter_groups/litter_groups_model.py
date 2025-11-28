from sqlalchemy import (
    Column, String, Integer, DateTime, Enum, ForeignKey, Text, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
import uuid
from config.database import Base
from enum import Enum as PyEnum
from api.cleanup_events.cleanup_events_model import CleanupEvent
class GroupTypeEnum(PyEnum):
    public = "public"
    private = "private"

class GroupStatusEnum(PyEnum):
    active   = "active"    # ready to be picked and hosted
    locked   = "locked"    # already claimed by an event
    archived = "archived"  # cleanup done, keep for record

class GroupVerificationEnum(PyEnum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"

class LitterGroup(Base):
    __tablename__ = "litter_groups"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name           = Column(String(100), nullable=False)
    description    = Column(Text, nullable=True)
    created_by     = Column(Integer, ForeignKey("users.id"), nullable=False)

    group_type     = Column(
        Enum(GroupTypeEnum, name="group_type_enum"),
        nullable=False,
        default=GroupTypeEnum.public,
    )
    location       = Column(String(100), nullable=True)

    member_count   = Column(Integer, default=0)
    report_count   = Column(Integer, default=0)

    status         = Column(
        Enum(GroupStatusEnum, name="group_status_enum"),
        default=GroupStatusEnum.active,
    )
    verification_status = Column(
        Enum(GroupVerificationEnum, name="group_verification_enum"),
        default=GroupVerificationEnum.pending,
    )
    severity       = Column(String, nullable=True)

    geom           = Column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    is_locked      = Column(Boolean, nullable=False, default=False,
                              comment="True if locked, False if unlocked")
    coverage_area  = Column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=True,
        comment="Polygon hull used to prevent reclustering of locked groups"
    )
    created_at     = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at     = Column(DateTime(timezone=True),
                            default=datetime.utcnow,
                            onupdate=datetime.utcnow)

    # Relationships
    creator        = relationship("User", foreign_keys=[created_by])
    # one group → many cleanup events
    cleanup_events = relationship(
         CleanupEvent,
         back_populates="litter_group",
         cascade="all, delete-orphan"
     )
    # one group → many reports
    litter_reports = relationship("LitterReport", back_populates="group")
