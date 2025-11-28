from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from config.database import Base
import uuid

class CleanupEventReport(Base):
    __tablename__ = "cleanup_event_reports"

    # Surrogate primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # Foreign keys
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cleanup_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("litter_reports.id", ondelete="CASCADE"),
        nullable=False,
    )

    # relationships
    # Link to CleanupEvent
    event = relationship(
        "CleanupEvent",
        back_populates="event_associations",
        foreign_keys=[event_id],
        overlaps="litter_reports,events",
    )

    # Link to LitterReport
    report = relationship(
        "LitterReport",
        back_populates="event_associations",
        foreign_keys=[report_id],
        overlaps="event_associations,litter_reports",
    )
