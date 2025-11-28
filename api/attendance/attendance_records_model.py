from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
import enum
from config.database import Base

class AttendanceMethod(enum.Enum):
    token = "token"
    qr    = "qr"
    gps   = "gps"
    otp   = "otp"

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_attendance_event_user"),
    )

    id             = Column(Integer, primary_key=True, index=True)
    event_id       = Column(UUID(as_uuid=True), ForeignKey("cleanup_events.id"), nullable=False)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    checked_in_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    recorded_by    = Column(Integer, ForeignKey("users.id"), nullable=False)  
    method         = Column(Enum(AttendanceMethod), nullable=False, default=AttendanceMethod.token)
    details        = Column(JSON, nullable=True) 
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, event_id, user_id, recorded_by, method, details=None):
        self.event_id      = event_id
        self.user_id       = user_id
        self.recorded_by   = recorded_by
        self.method        = method
        self.details       = details
