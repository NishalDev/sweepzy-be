# user_badges_model.py
from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from config.database import Base  # use same Base
from api.badges.badges_model import Badge
class UserBadge(Base):
    __tablename__ = "user_badges"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    badge_id = Column(Integer, ForeignKey("badges.id", ondelete="CASCADE"), primary_key=True)
    earned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship(
        "User",
        back_populates="badges"
    )
    badge = relationship(
        Badge,
        back_populates="user_badges"
    )

    def __repr__(self):
        return f"<UserBadge(user_id={self.user_id}, badge_id={self.badge_id})>"

