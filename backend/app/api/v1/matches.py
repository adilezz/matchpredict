from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.schemas import MatchOut, MatchListOut
from app.services import match_service

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/", response_model=MatchListOut)
async def list_matches(
    league_code: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    season: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    matches, total = await match_service.list_matches(
        db, league_code=league_code, status=status,
        date_from=date_from, date_to=date_to, season=season,
        limit=limit, offset=offset,
    )
    return MatchListOut(total=total, matches=[MatchOut.model_validate(m) for m in matches])


@router.get("/upcoming", response_model=list[MatchOut])
async def upcoming_matches(
    league_code: str | None = None,
    days: int = Query(default=7, le=30),
    db: AsyncSession = Depends(get_db),
):
    matches = await match_service.get_upcoming_matches(db, league_code=league_code, days=days)
    return [MatchOut.model_validate(m) for m in matches]


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(match_id: int, db: AsyncSession = Depends(get_db)):
    match = await match_service.get_match_by_id(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return MatchOut.model_validate(match)


@router.get("/{match_id}/h2h", response_model=list[MatchOut])
async def head_to_head(match_id: int, limit: int = 10, db: AsyncSession = Depends(get_db)):
    match = await match_service.get_match_by_id(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    h2h = await match_service.get_h2h(db, match.home_team_id, match.away_team_id, limit)
    return [MatchOut.model_validate(m) for m in h2h]


@router.get("/{match_id}/form")
async def team_form(match_id: int, limit: int = 5, db: AsyncSession = Depends(get_db)):
    match = await match_service.get_match_by_id(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    home_form = await match_service.get_team_form(db, match.home_team_id, limit)
    away_form = await match_service.get_team_form(db, match.away_team_id, limit)
    return {
        "home_team": match.home_team.name,
        "away_team": match.away_team.name,
        "home_form": [MatchOut.model_validate(m) for m in home_form],
        "away_form": [MatchOut.model_validate(m) for m in away_form],
    }
