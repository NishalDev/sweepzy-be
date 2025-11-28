# landmark_model.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from config.database import Base  # use the same Base as the rest of your app
from api.location.city.city_model import City  # to reference City model

class Landmark(Base):
    __tablename__ = "landmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city_id = Column(Integer, ForeignKey("cities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationship back to city
    city = relationship(
        "City",
        back_populates="landmarks"
    )

    # relationship to reports
    reports = relationship(
        "LitterReport",
        back_populates="landmark",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Landmark(id={self.id}, name='{self.name}', city_id={self.city_id})>"
