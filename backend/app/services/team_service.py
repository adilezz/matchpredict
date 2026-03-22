"""Team-related service functions."""

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.models.match import Match
from app.models.league import League


async def get_team_by_id(db: AsyncSession, team_id: int) -> Team | None:
    result = await db.execute(select(Team).where(Team.id == team_id))
    return result.scalar_one_or_none()


async def get_teams_by_league(db: AsyncSession, league_code: str) -> list[Team]:
    result = await db.execute(
        select(Team)
        .join(League)
        .where(League.code == league_code)
        .order_by(Team.name)
    )
    return list(result.scalars().all())


async def get_team_matches(
    db: AsyncSession, team_id: int, limit: int = 20, status: str | None = None
) -> list[Match]:
    query = (
        select(Match)
        .options(
            selectinload(Match.league),
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.prediction),
        )
        .where(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
    )
    if status:
        query = query.where(Match.status == status)
    query = query.order_by(Match.match_date.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().unique().all())
