# badges_model.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from config.database import Base

class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    icon_key = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user_badges = relationship(
        "UserBadge",
        back_populates="badge",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Badge(id={self.id}, name='{self.name}')>"
