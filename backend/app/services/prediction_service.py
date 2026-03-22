from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.prediction import Prediction
from app.models.league import League


async def get_prediction_for_match(db: AsyncSession, match_id: int) -> Prediction | None:
    result = await db.execute(
        select(Prediction).where(Prediction.match_id == match_id)
    )
    return result.scalar_one_or_none()


async def get_dashboard_stats(db: AsyncSession) -> dict:
    today = date.today()

    today_count = await db.execute(
        select(func.count(Match.id)).where(Match.match_date == today)
    )
    upcoming_count = await db.execute(
        select(func.count(Match.id)).where(
            Match.status == "scheduled",
            Match.match_date >= today,
        )
    )
    leagues_count = await db.execute(
        select(func.count(League.id)).where(League.is_active == True)
    )
    preds_count = await db.execute(select(func.count(Prediction.id)))

    return {
        "total_matches_today": today_count.scalar() or 0,
        "upcoming_matches": upcoming_count.scalar() or 0,
        "leagues_active": leagues_count.scalar() or 0,
        "predictions_generated": preds_count.scalar() or 0,
    }
