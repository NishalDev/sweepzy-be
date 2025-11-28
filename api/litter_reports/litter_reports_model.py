from sqlalchemy import (
    Column, String, Float, JSON, ForeignKey, Boolean, Integer, DateTime
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from geoalchemy2 import Geometry
import uuid
from config.database import Base
from api.litter_groups.litter_groups_model import LitterGroup
from api.litter_reports.image_fingerprints_model import ImageFingerprint
class LitterReport(Base):
    __tablename__ = "litter_reports"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id      = Column(UUID(as_uuid=True), ForeignKey("litter_groups.id"), nullable=True)
    event_id      = Column(UUID(as_uuid=True), ForeignKey("cleanup_events.id"), nullable=True)
    upload_id     = Column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    city_id       = Column(Integer, ForeignKey("cities.id"), nullable=True)
    landmark_id   = Column(Integer, ForeignKey("landmarks.id"), nullable=True)

    latitude      = Column(Float, nullable=False)
    longitude     = Column(Float, nullable=False)
    landmark      = Column(String, nullable=True)
    detection_results = Column(JSON, nullable=True)
    severity          = Column(String, nullable=True)   # low, medium, high
    status            = Column(String, default="pending", nullable=False)
    reviewed_by       = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_detected   = Column(Boolean, nullable=False, default=False)
    is_mapped     = Column(Boolean, nullable=False, default=False)
    is_grouped    = Column(Boolean, nullable=False, default=False)
    reward_points = Column(Integer, default=0)

    created_at    = Column(DateTime, default=datetime.now)
    updated_at    = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    # relationships
    reporter  = relationship("User", foreign_keys=[user_id])
    reviewer  = relationship("User", foreign_keys=[reviewed_by])

    detections = relationship(
        "LitterDetection",
        back_populates="litter_report",
        cascade="all, delete-orphan"
    )
    group      = relationship(LitterGroup, back_populates="litter_reports")
    upload     = relationship("Upload", foreign_keys=[upload_id])

    # association to CleanupEventReport
    event_associations = relationship(
        "CleanupEventReport",
        back_populates="report",
        cascade="all, delete-orphan",
        overlaps="events"
    )
    fingerprint = relationship(
        ImageFingerprint,
        back_populates='report',
        uselist=False,
        cascade='all, delete-orphan'
    )
    # direct many-to-many to CleanupEvent via secondary
    events = relationship(
        "CleanupEvent",
        secondary="cleanup_event_reports",
        back_populates="litter_reports",
        overlaps="event_associations,report"
    )

    city = relationship("City", back_populates="reports")
    landmark = relationship("Landmark", back_populates="reports")
