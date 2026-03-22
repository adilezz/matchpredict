from sqlalchemy import Column, Float, ForeignKey, Integer, String, UniqueConstraint

from app.models.base import Base, IDMixin, TimestampMixin


class TeamSeasonStats(Base, IDMixin, TimestampMixin):
    __tablename__ = "team_season_stats"
    __table_args__ = (
        UniqueConstraint("team_id", "season", name="uq_team_season"),
    )

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    season = Column(String(9), nullable=False, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)

    ppda = Column(Float)
    deep_completions = Column(Float)
    npxg_per90 = Column(Float)
    npxga_per90 = Column(Float)
    possession_avg = Column(Float)
    progressive_passes_per90 = Column(Float)
    progressive_carries_per90 = Column(Float)
    pressing_success_pct = Column(Float)
    market_value_eur = Column(Float)
