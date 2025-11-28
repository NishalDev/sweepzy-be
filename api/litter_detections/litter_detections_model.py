from sqlalchemy import Column, String, Float, JSON, ForeignKey, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from config.database import Base

class LitterDetection(Base):
    __tablename__ = "litter_detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    litter_report_id = Column(UUID(as_uuid=True), ForeignKey("litter_reports.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    detected_objects = Column(JSON, nullable=True)
    bounding_boxes = Column(JSON, nullable=True)
    total_litter_count = Column(Integer, nullable=True)
    severity_level = Column(String, nullable=True)
    detection_source = Column(String, nullable=True)
    detection_confidence = Column(Float, nullable=True)
    review_status = Column(String, default="pending", nullable=False)
    review_notes = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # ✅ Relationships
    litter_report = relationship("LitterReport", back_populates="detections")
    reviewer = relationship("User", backref="reviewed_detections", foreign_keys=[reviewed_by])
