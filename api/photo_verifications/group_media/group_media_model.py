# models/group_media.py
from sqlalchemy import Column, BigInteger, String, Boolean, JSON, TIMESTAMP, Double, Enum
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class MediaTypeEnum(str, enum.Enum):
    image = "image"
    video = "video"

class GroupMedia(Base):
    __tablename__ = "group_media"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(String(36), nullable=False)
    uploaded_by = Column(BigInteger, nullable=True)
    object_key = Column(String(1024), nullable=False)
    file_url = Column(String(1024), nullable=False)
    thumb_url = Column(String(1024), nullable=True)
    mime_type = Column(String(128), nullable=True)
    media_type = Column(Enum(MediaTypeEnum), nullable=False)
    size_bytes = Column(BigInteger, nullable=True)
    latitude = Column(Double, nullable=True)
    longitude = Column(Double, nullable=True)

    # <<-- DO NOT name this attribute `metadata` (reserved) --
    # keep DB column name 'metadata' but map it to Python attr 'metadata_json'
    metadata_json = Column("metadata", JSON, nullable=True)

    verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
