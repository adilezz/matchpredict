from sqlalchemy import (
    Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class Match(Base, IDMixin, TimestampMixin):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint(
            "league_id", "home_team_id", "away_team_id", "match_date",
            name="uq_match_identity",
        ),
    )

    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False, index=True)
    season = Column(String(9), nullable=False, index=True)
    matchday = Column(Integer)
    match_date = Column(Date, nullable=False, index=True)
    kickoff_utc = Column(DateTime)
    status = Column(String(12), nullable=False, default="scheduled", index=True)
    venue = Column(String(150))
    referee = Column(String(120))

    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    home_goals = Column(Integer)
    away_goals = Column(Integer)
    ht_home_goals = Column(Integer)
    ht_away_goals = Column(Integer)
    result = Column(String(1))

    home_xg = Column(Float)
    away_xg = Column(Float)
    home_shots = Column(Integer)
    away_shots = Column(Integer)
    home_shots_on_target = Column(Integer)
    away_shots_on_target = Column(Integer)
    home_possession = Column(Float)
    away_possession = Column(Float)
    home_corners = Column(Integer)
    away_corners = Column(Integer)
    home_fouls = Column(Integer)
    away_fouls = Column(Integer)
    home_yellow_cards = Column(Integer)
    away_yellow_cards = Column(Integer)
    home_red_cards = Column(Integer)
    away_red_cards = Column(Integer)

    home_elo = Column(Float)
    away_elo = Column(Float)

    league = relationship("League", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    prediction = relationship("Prediction", back_populates="match", uselist=False, lazy="selectin")
