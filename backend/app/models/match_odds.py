from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, IDMixin, TimestampMixin


class MatchOdds(Base, IDMixin, TimestampMixin):
    __tablename__ = "match_odds"
    __table_args__ = (
        UniqueConstraint("match_id", "source", name="uq_odds_match_source"),
    )

    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    source = Column(String(30), nullable=False)

    home_odds = Column(Float)
    draw_odds = Column(Float)
    away_odds = Column(Float)
    over_25_odds = Column(Float)
    under_25_odds = Column(Float)
    btts_yes_odds = Column(Float)
    btts_no_odds = Column(Float)

    captured_at = Column(DateTime)

    match = relationship("Match", backref="odds_entries")
