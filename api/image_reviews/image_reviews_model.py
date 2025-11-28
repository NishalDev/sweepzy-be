from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from config.database import Base

class ImageReview(Base):
    __tablename__ = "image_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    litter_report_id = Column(UUID(as_uuid=True), ForeignKey("litter_reports.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_status = Column(String, nullable=False, default="pending")  # pending, approved, rejected
    review_notes = Column(String, nullable=True)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    litter_report = relationship("LitterReport", backref="image_reviews")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
