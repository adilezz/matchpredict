"""League standings computation from match results."""

from sqlalchemy import select, and_, func, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.league import League
from app.models.team import Team


async def get_league_standings(
    db: AsyncSession, league_code: str, season: str | None = None
) -> list[dict]:
    """Compute league standings from finished matches."""
    league_q = select(League).where(League.code == league_code)
    league_res = await db.execute(league_q)
    league = league_res.scalar_one_or_none()
    if not league:
        return []

    if not season:
        latest_q = (
            select(Match.season)
            .where(Match.league_id == league.id)
            .order_by(Match.match_date.desc())
            .limit(1)
        )
        season_res = await db.execute(latest_q)
        season = season_res.scalar_one_or_none()
        if not season:
            return []

    matches_q = (
        select(Match)
        .where(
            and_(
                Match.league_id == league.id,
                Match.season == season,
                Match.status == "finished",
                Match.home_goals.isnot(None),
                Match.away_goals.isnot(None),
            )
        )
    )
    matches_res = await db.execute(matches_q)
    matches = list(matches_res.scalars().all())

    teams_q = select(Team).where(Team.league_id == league.id)
    teams_res = await db.execute(teams_q)
    teams = {t.id: t for t in teams_res.scalars().all()}

    stats: dict[int, dict] = {}
    for m in matches:
        for tid in (m.home_team_id, m.away_team_id):
            if tid not in stats:
                team = teams.get(tid)
                stats[tid] = {
                    "team_id": tid,
                    "team_name": team.name if team else f"Team {tid}",
                    "logo_url": team.logo_url if team else None,
                    "elo_rating": team.elo_rating if team else None,
                    "played": 0, "won": 0, "drawn": 0, "lost": 0,
                    "gf": 0, "ga": 0, "gd": 0, "points": 0,
                    "form": [],
                }

        hg, ag = m.home_goals, m.away_goals

        hs = stats[m.home_team_id]
        hs["played"] += 1
        hs["gf"] += hg
        hs["ga"] += ag
        if hg > ag:
            hs["won"] += 1
            hs["points"] += 3
            hs["form"].append("W")
        elif hg == ag:
            hs["drawn"] += 1
            hs["points"] += 1
            hs["form"].append("D")
        else:
            hs["lost"] += 1
            hs["form"].append("L")

        aws = stats[m.away_team_id]
        aws["played"] += 1
        aws["gf"] += ag
        aws["ga"] += hg
        if ag > hg:
            aws["won"] += 1
            aws["points"] += 3
            aws["form"].append("W")
        elif ag == hg:
            aws["drawn"] += 1
            aws["points"] += 1
            aws["form"].append("D")
        else:
            aws["lost"] += 1
            aws["form"].append("L")

    for s in stats.values():
        s["gd"] = s["gf"] - s["ga"]
        s["form"] = s["form"][-5:]

    standings = sorted(
        stats.values(),
        key=lambda x: (-x["points"], -x["gd"], -x["gf"]),
    )
    for i, s in enumerate(standings, 1):
        s["position"] = i

    return standings
