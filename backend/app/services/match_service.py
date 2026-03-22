from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.league import League
from app.models.team import Team
from app.models.prediction import Prediction


def _match_query_with_relations():
    return (
        select(Match)
        .options(
            selectinload(Match.league),
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.prediction),
        )
    )


async def list_matches(
    db: AsyncSession,
    league_code: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    season: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Match], int]:
    query = _match_query_with_relations()

    if league_code:
        query = query.join(League).where(League.code == league_code)
    if status:
        query = query.where(Match.status == status)
    if date_from:
        query = query.where(Match.match_date >= date_from)
    if date_to:
        query = query.where(Match.match_date <= date_to)
    if season:
        query = query.where(Match.season == season)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Match.match_date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().unique().all()), total


async def get_upcoming_matches(
    db: AsyncSession,
    league_code: str | None = None,
    days: int = 7,
) -> list[Match]:
    today = date.today()
    end = today + timedelta(days=days)

    query = (
        _match_query_with_relations()
        .where(and_(
            Match.match_date >= today,
            Match.match_date <= end,
            Match.status == "scheduled",
        ))
        .order_by(Match.match_date.asc())
    )
    if league_code:
        query = query.join(League).where(League.code == league_code)

    result = await db.execute(query)
    return list(result.scalars().unique().all())


async def get_match_by_id(db: AsyncSession, match_id: int) -> Match | None:
    result = await db.execute(
        _match_query_with_relations().where(Match.id == match_id)
    )
    return result.scalar_one_or_none()


async def get_h2h(
    db: AsyncSession, home_team_id: int, away_team_id: int, limit: int = 10
) -> list[Match]:
    query = (
        _match_query_with_relations()
        .where(or_(
            and_(Match.home_team_id == home_team_id, Match.away_team_id == away_team_id),
            and_(Match.home_team_id == away_team_id, Match.away_team_id == home_team_id),
        ))
        .where(Match.status == "finished")
        .order_by(Match.match_date.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().unique().all())


async def get_team_form(
    db: AsyncSession, team_id: int, limit: int = 5
) -> list[Match]:
    query = (
        _match_query_with_relations()
        .where(or_(
            Match.home_team_id == team_id,
            Match.away_team_id == team_id,
        ))
        .where(Match.status == "finished")
        .order_by(Match.match_date.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().unique().all())
