from sqlalchemy import Column, BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import relationship

from config.database import Base # adjust import as needed


class UserSettings(Base):
    __tablename__ = "user_settings"

    # Primary key and FK to users.id
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Flag for whether the instruction tour has been seen
     # Flag for whether the instruction tour has been seen
    seen_tour = Column(
        Boolean,
        nullable=False,
        server_default="false",
    )
   
    language = Column(
        String(2),
        nullable=True,
        server_default=None,   # or 'kn' if you want Kannada as default
    )
    # Optional back reference to User model
    user = relationship(
        "User",
        back_populates="settings",
        uselist=False,
    )
