from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    UniqueConstraint,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
import uuid
from config.database import Base

class AttendanceToken(Base):
    __tablename__ = "attendance_tokens"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_token_event_user"),
    )

    id               = Column(Integer, primary_key=True, index=True)
    event_id         = Column(UUID(as_uuid=True), ForeignKey("cleanup_events.id"), nullable=False)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    token            = Column(String(4), nullable=False, unique=True)
    not_valid_before = Column(DateTime(timezone=True), nullable=False)
    expires_at       = Column(DateTime(timezone=True), nullable=False)
    used_at          = Column(DateTime(timezone=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, event_id, user_id, token, not_valid_before, expires_at):
        self.event_id         = event_id
        self.user_id          = user_id
        self.token            = token
        self.not_valid_before = not_valid_before
        self.expires_at       = expires_at
