from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.schemas import TeamOut, MatchOut
from app.services import team_service

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/{team_id}")
async def get_team(team_id: int, db: AsyncSession = Depends(get_db)):
    team = await team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return TeamOut.model_validate(team)


@router.get("/{team_id}/matches", response_model=list[MatchOut])
async def team_matches(
    team_id: int, limit: int = 20, status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    matches = await team_service.get_team_matches(db, team_id, limit, status)
    return [MatchOut.model_validate(m) for m in matches]
