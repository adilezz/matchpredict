from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, func
from app.models.base import Base, IDMixin


class ModelEvaluation(Base, IDMixin):
    __tablename__ = "model_evaluations"

    evaluated_at = Column(DateTime, server_default=func.now(), nullable=False)
    model_version = Column(String(20), nullable=False)
    league_code = Column(String(30))
    season = Column(String(9))

    sample_size = Column(Integer, nullable=False)
    accuracy_1x2 = Column(Float)
    log_loss = Column(Float)
    brier_score = Column(Float)
    ou_accuracy = Column(Float)
    calibration_error = Column(Float)

    needs_retrain = Column(String(5), default="no")
