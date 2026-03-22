from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.standings_service import get_league_standings

router = APIRouter(prefix="/standings", tags=["standings"])


@router.get("/{league_code}")
async def league_standings(
    league_code: str,
    season: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await get_league_standings(db, league_code, season)
