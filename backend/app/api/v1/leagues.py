from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.schemas import LeagueOut
from app.services import league_service

router = APIRouter(prefix="/leagues", tags=["leagues"])


@router.get("/", response_model=list[LeagueOut])
async def list_leagues(db: AsyncSession = Depends(get_db)):
    return await league_service.get_all_leagues(db)


@router.get("/{code}", response_model=LeagueOut)
async def get_league(code: str, db: AsyncSession = Depends(get_db)):
    league = await league_service.get_league_by_code(db, code)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    return league


@router.post("/seed")
async def seed(db: AsyncSession = Depends(get_db)):
    count = await league_service.seed_leagues(db)
    return {"message": f"Seeded {count} leagues"}
