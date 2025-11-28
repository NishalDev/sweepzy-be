# app/models/notification.py

from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    Boolean,
    Enum,
    ForeignKey,
    DateTime,
    func,
)
from sqlalchemy.orm import relationship
from config.database import Base  # your declarative base
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(
        Enum("info", "alert", "reminder", name="notification_type"),
        nullable=False,
        server_default="info",
    )
    read_status = Column(Boolean, nullable=False, default=False)
    link = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="notifications")
