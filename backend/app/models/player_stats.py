from sqlalchemy import Column, Float, ForeignKey, Integer, String, UniqueConstraint
from app.models.base import Base, IDMixin


class PlayerSeasonStats(Base, IDMixin):
    __tablename__ = "player_season_stats"
    __table_args__ = (
        UniqueConstraint("name", "team_id", "season", name="uq_player_team_season"),
    )

    name = Column(String(150), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), index=True)
    season = Column(String(9), nullable=False, index=True)
    position = Column(String(30))

    games = Column(Integer, default=0)
    minutes = Column(Integer, default=0)
    goals = Column(Integer, default=0)
    xg = Column(Float, default=0)
    assists = Column(Integer, default=0)
    xa = Column(Float, default=0)
    shots = Column(Integer, default=0)
    key_passes = Column(Integer, default=0)
    npxg = Column(Float, default=0)
    xg_chain = Column(Float, default=0)
    xg_buildup = Column(Float, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
