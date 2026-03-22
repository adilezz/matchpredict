from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.evaluation import ModelEvaluation
from app.schemas.schemas import PredictionOut, DashboardStats
from app.services import prediction_service

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    stats = await prediction_service.get_dashboard_stats(db)
    return DashboardStats(**stats)


@router.get("/performance")
async def model_performance(db: AsyncSession = Depends(get_db)):
    """Return model evaluation history and accuracy breakdown."""
    evals_q = select(ModelEvaluation).order_by(ModelEvaluation.evaluated_at.desc()).limit(30)
    evals_res = await db.execute(evals_q)
    evals = [
        {
            "id": e.id,
            "model_version": e.model_version,
            "accuracy": e.accuracy_1x2,
            "log_loss": e.log_loss,
            "brier_score": e.brier_score,
            "sample_size": e.sample_size,
            "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
        }
        for e in evals_res.scalars().all()
    ]

    correct_q = (
        select(func.count())
        .select_from(Prediction)
        .join(Match, Prediction.match_id == Match.id)
        .where(
            and_(
                Match.status == "finished",
                Match.home_goals.isnot(None),
            )
        )
    )
    total_evaluated = (await db.execute(correct_q)).scalar() or 0

    correct_count = 0
    if total_evaluated > 0:
        preds_q = (
            select(Prediction, Match.home_goals, Match.away_goals)
            .join(Match, Prediction.match_id == Match.id)
            .where(
                and_(
                    Match.status == "finished",
                    Match.home_goals.isnot(None),
                )
            )
        )
        preds_res = await db.execute(preds_q)
        for pred, hg, ag in preds_res.all():
            actual = "home" if hg > ag else "away" if ag > hg else "draw"
            predicted = max(
                [("home", pred.prob_home), ("draw", pred.prob_draw), ("away", pred.prob_away)],
                key=lambda x: x[1],
            )[0]
            if actual == predicted:
                correct_count += 1

    return {
        "evaluations": evals,
        "total_evaluated": total_evaluated,
        "correct_predictions": correct_count,
        "accuracy": correct_count / total_evaluated if total_evaluated > 0 else 0,
    }


@router.get("/{match_id}", response_model=PredictionOut)
async def get_prediction(match_id: int, db: AsyncSession = Depends(get_db)):
    pred = await prediction_service.get_prediction_for_match(db, match_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found for this match")
    return pred
