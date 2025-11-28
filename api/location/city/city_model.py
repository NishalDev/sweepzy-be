# city_model.py
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from config.database import Base  # use the same Base as the rest of your app

class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # relationship to landmarks
    landmarks = relationship(
        "Landmark",
        back_populates="city",
        cascade="all, delete-orphan"
    )

    # relationship to reports
    reports = relationship(
        "LitterReport",          # keep string
        back_populates="city",
        cascade="all, delete-orphan",
        lazy="selectin"    # optional, improves performance
    )

    def __repr__(self):
        return f"<City(id={self.id}, name='{self.name}')>"
