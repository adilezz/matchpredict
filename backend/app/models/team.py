from sqlalchemy import Column, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class Team(Base, IDMixin, TimestampMixin):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("name", "league_id", name="uq_team_name_league"),
    )

    name = Column(String(120), nullable=False, index=True)
    short_name = Column(String(30))
    country = Column(String(60))
    league_id = Column(Integer, ForeignKey("leagues.id"), index=True)

    elo_rating = Column(Float)
    logo_url = Column(String(300))

    league = relationship("League", back_populates="teams")
    home_matches = relationship(
        "Match", foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    away_matches = relationship(
        "Match", foreign_keys="Match.away_team_id", back_populates="away_team"
    )
