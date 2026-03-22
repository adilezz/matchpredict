from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.league import League
from app.scraping.config import LEAGUES


async def get_all_leagues(db: AsyncSession) -> list[League]:
    result = await db.execute(
        select(League).where(League.is_active == True).order_by(League.name)
    )
    return list(result.scalars().all())


async def get_league_by_code(db: AsyncSession, code: str) -> League | None:
    result = await db.execute(select(League).where(League.code == code))
    return result.scalar_one_or_none()


async def seed_leagues(db: AsyncSession) -> int:
    count = 0
    for code, mapping in LEAGUES.items():
        if not mapping.fd_division and not mapping.understat_slug:
            continue
        existing = await db.execute(select(League).where(League.code == code))
        if existing.scalar_one_or_none():
            continue
        league = League(code=code, name=mapping.name, country=mapping.country)
        db.add(league)
        count += 1
    await db.commit()
    return count
