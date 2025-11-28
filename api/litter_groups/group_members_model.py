# from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, Text
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import relationship
# from geoalchemy2 import Geography
# from datetime import datetime
# import uuid
# from config.database import Base
# from enum import Enum as PyEnum
# from api.litter_groups.litter_groups_model import LitterGroup  # ensure this is imported

# class GroupMember(Base):
#     __tablename__ = "group_members"

#     id = Column(Integer, primary_key=True, index=True)
#     group_id = Column(UUID, ForeignKey("litter_groups.id"))

#     group = relationship("LitterGroup", back_populates="group_members")
