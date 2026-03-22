from datetime import datetime, timezone
from sqlalchemy import Integer, Float, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    model_version: Mapped[str] = mapped_column(String(20), default="v1")

    # 1X2 probabilities
    prob_home: Mapped[float] = mapped_column(Float, nullable=False)
    prob_draw: Mapped[float] = mapped_column(Float, nullable=False)
    prob_away: Mapped[float] = mapped_column(Float, nullable=False)

    # Total goals O/U
    expected_total_goals: Mapped[float | None] = mapped_column(Float)
    prob_over_05: Mapped[float | None] = mapped_column(Float)
    prob_under_05: Mapped[float | None] = mapped_column(Float)
    prob_over_15: Mapped[float | None] = mapped_column(Float)
    prob_under_15: Mapped[float | None] = mapped_column(Float)
    prob_over_25: Mapped[float | None] = mapped_column(Float)
    prob_under_25: Mapped[float | None] = mapped_column(Float)
    prob_over_35: Mapped[float | None] = mapped_column(Float)
    prob_under_35: Mapped[float | None] = mapped_column(Float)

    # Home team goals O/U
    home_prob_over_05: Mapped[float | None] = mapped_column(Float)
    home_prob_under_05: Mapped[float | None] = mapped_column(Float)
    home_prob_over_15: Mapped[float | None] = mapped_column(Float)
    home_prob_under_15: Mapped[float | None] = mapped_column(Float)
    home_prob_over_25: Mapped[float | None] = mapped_column(Float)
    home_prob_under_25: Mapped[float | None] = mapped_column(Float)

    # Away team goals O/U
    away_prob_over_05: Mapped[float | None] = mapped_column(Float)
    away_prob_under_05: Mapped[float | None] = mapped_column(Float)
    away_prob_over_15: Mapped[float | None] = mapped_column(Float)
    away_prob_under_15: Mapped[float | None] = mapped_column(Float)
    away_prob_over_25: Mapped[float | None] = mapped_column(Float)
    away_prob_under_25: Mapped[float | None] = mapped_column(Float)

    home_lambda: Mapped[float | None] = mapped_column(Float)
    away_lambda: Mapped[float | None] = mapped_column(Float)

    # BTTS
    prob_btts_yes: Mapped[float | None] = mapped_column(Float)
    prob_btts_no: Mapped[float | None] = mapped_column(Float)

    # Double chance
    prob_dc_1x: Mapped[float | None] = mapped_column(Float)
    prob_dc_x2: Mapped[float | None] = mapped_column(Float)
    prob_dc_12: Mapped[float | None] = mapped_column(Float)

    # Top-5 correct scores as JSON string: [["1-0", 0.12], ...]
    correct_score_top5: Mapped[str | None] = mapped_column(String(300))

    # Value betting edges (model prob - implied prob from bookmaker odds)
    odds_implied_home: Mapped[float | None] = mapped_column(Float)
    odds_implied_draw: Mapped[float | None] = mapped_column(Float)
    odds_implied_away: Mapped[float | None] = mapped_column(Float)
    value_edge_home: Mapped[float | None] = mapped_column(Float)
    value_edge_draw: Mapped[float | None] = mapped_column(Float)
    value_edge_away: Mapped[float | None] = mapped_column(Float)

    confidence: Mapped[float | None] = mapped_column(Float)

    match = relationship("Match", back_populates="prediction")
