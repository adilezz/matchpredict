from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class League(Base, IDMixin, TimestampMixin):
    __tablename__ = "leagues"

    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    country = Column(String(60), nullable=False)
    is_active = Column(Boolean, default=True)

    teams = relationship("Team", back_populates="league", lazy="selectin")
    matches = relationship("Match", back_populates="league", lazy="dynamic")
