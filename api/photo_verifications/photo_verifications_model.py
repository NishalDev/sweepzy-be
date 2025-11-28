from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    func,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
import enum
from config.database import Base


class PhotoPhase(enum.Enum):
    before = "before"
    after = "after"

class VerificationStatus(enum.Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"

class PhotoVerification(Base):
    __tablename__ = "photo_verifications"
    __table_args__ = (
        # ensure one before+after pair per user per event per phase if needed
        UniqueConstraint('event_id', 'report_id', 'captured_by', 'phase', name='uq_photo_event_user_phase'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    event_id = Column(UUID(as_uuid=True), ForeignKey("cleanup_events.id"), nullable=False)
    report_id = Column(UUID(as_uuid=True), ForeignKey("litter_reports.id"), nullable=False)
    captured_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    phase = Column(Enum(PhotoPhase), nullable=False)
    photo_urls = Column(JSON, nullable=False)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(Enum(VerificationStatus), nullable=False, default=VerificationStatus.pending_review)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False
    )

    def __init__(self, event_id, report_id, captured_by, phase, photo_urls):
        self.event_id = event_id
        self.report_id = report_id
        self.captured_by = captured_by
        self.phase = phase
        self.photo_urls = photo_urls
