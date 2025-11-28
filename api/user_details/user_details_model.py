# File: api/user/user_details_model.py

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class UserDetails(Base):
    __tablename__ = "user_details"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Personal Info
    full_name       = Column(String(150), nullable=True)
    profile_photo   = Column(String(255), nullable=True)
    bio             = Column(String(500), nullable=True)

    # Location
    city            = Column(String(100), nullable=True)
    state           = Column(String(100), nullable=True)
    country         = Column(String(100), nullable=True)
    postal_code     = Column(String(20), nullable=True)

    # Contact
    phone           = Column(String(20), nullable=True)
    social_links    = Column(JSON, nullable=True)  # e.g. {"instagram": "...", "twitter": "..."}

    # Preferences
    cleanup_types   = Column(JSON, nullable=True)  # e.g. ["beach", "park"]
    availability    = Column(JSON, nullable=True)  # e.g. {"weekends": true, "weekdays": ["evening"]}
    skills          = Column(JSON, nullable=True)  # e.g. ["first aid", "leadership"]

    # Audit
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationship
    user = relationship("User", back_populates="details", uselist=False, lazy="joined")
