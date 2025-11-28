import uuid
from sqlalchemy import Column, String, LargeBinary, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from config.database import Base

class ImageFingerprint(Base):
    __tablename__ = 'image_fingerprints'

    # Use the litter_report's UUID as primary key (one-to-one)
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey('litter_reports.id', ondelete='CASCADE'),
        primary_key=True,
        default=uuid.uuid4
    )
    phash = Column(String(64), nullable=False)
    embedding = Column(LargeBinary, nullable=False)

    # backref to the report
    report = relationship(
        'LitterReport',
        back_populates='fingerprint',
        uselist=False
    )
