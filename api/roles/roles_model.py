from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from config.database import Base
from api.roles.permissions.permissions_model import Permission
from api.roles.permissions.role_permissions.role_permissions_model import RolePermission
from api.roles.user_roles.user_roles_model import UserRole
class Role(Base):
    __tablename__ = "roles"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now(), nullable=False)
    import logging
    logging.warning("RolePermission is: %r", RolePermission)
    logging.warning("RolePermission.__table__ is: %r", getattr(RolePermission, "__table__", None))
    # relationships
    permissions = relationship(
        Permission,
        secondary=RolePermission.__table__,
        back_populates="roles",
        cascade="all"
    )
    users = relationship(
        "User",
        secondary=UserRole.__table__,
        back_populates="roles",
        cascade="all"
    )
