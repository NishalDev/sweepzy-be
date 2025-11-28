import uuid
from datetime import datetime
from sqlalchemy import Column, Float, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from config.database import Base

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Assuming user_id is UUID
    session_id = Column(String, nullable=True)
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size = Column(Integer, nullable=True)  # size in bytes
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Upload(id={self.id}, file_name='{self.file_name}', file_url='{self.file_url}')>"
