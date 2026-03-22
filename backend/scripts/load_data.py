"""
Load all scraped CSVs into PostgreSQL.
Usage: python -m scripts.load_data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from datetime import date
from loguru import logger
from sqlalchemy import select

from app.core.database import SyncSession, sync_engine, Base
from app.models.league import League
from app.models.team import Team
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.player_stats import PlayerSeasonStats
from app.models.match_odds import MatchOdds
from app.models.team_season_stats import TeamSeasonStats
from app.scraping.config import LEAGUES
from app.scraping.utils import normalize_team_name

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_team_cache: dict = {}
_league_cache: dict = {}


def safe_int(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def safe_float(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        v = float(val)
        return v if v == v else None
    except (ValueError, TypeError):
        return None


def parse_match_date(val) -> date | None:
    """Two-pass date parser: try ISO first, then dayfirst for DD/MM/YYYY."""
    if pd.isna(val):
        return None
    try:
        return pd.to_datetime(val, format="%Y-%m-%d").date()
    except Exception:
        pass
    try:
        return pd.to_datetime(val, dayfirst=True).date()
    except Exception:
        return None


def seed_leagues(db):
    count = 0
    for code, mapping in LEAGUES.items():
        if not mapping.fd_division and not mapping.understat_slug and not mapping.fbref_id:
            continue
        existing = db.execute(select(League).where(League.code == code)).scalar_one_or_none()
        if existing:
            continue
        league = League(code=code, name=mapping.name, country=mapping.country)
        db.add(league)
        count += 1
    db.commit()
    logger.info(f"Seeded {count} leagues")


def clear_caches():
    """Reset module-level caches between pipeline runs."""
    _team_cache.clear()
    _league_cache.clear()


def get_or_create_team(db, name: str, league_id: int) -> Team:
    key = (name, league_id)
    if key in _team_cache:
        return _team_cache[key]
    team = db.execute(
        select(Team).where(Team.name == name, Team.league_id == league_id)
    ).scalar_one_or_none()
    if not team:
        team = Team(name=name, league_id=league_id)
        db.add(team)
        db.flush()
    _team_cache[key] = team
    return team


def get_league(db, code: str) -> League | None:
    if code in _league_cache:
        return _league_cache[code]
    league = db.execute(select(League).where(League.code == code)).scalar_one_or_none()
    _league_cache[code] = league
    return league


def load_football_data(db):
    fd_dir = DATA_DIR / "football_data"
    if not fd_dir.exists():
        logger.warning("No football_data directory")
        return

    total_matches = 0
    for csv_file in sorted(fd_dir.glob("*.csv")):
        parts = csv_file.stem.split("_")
        if len(parts) < 2:
            continue
        season = parts[-1]
        league_code = "_".join(parts[:-1])

        league = get_league(db, league_code)
        if not league:
            continue

        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            logger.error(f"Failed to read {csv_file.name}: {e}")
            continue

        count = 0
        for _, row in df.iterrows():
            ht_raw = str(row.get("home_team", "")).strip()
            at_raw = str(row.get("away_team", "")).strip()
            if not ht_raw or not at_raw or ht_raw == "nan":
                continue

            ht_name = normalize_team_name(ht_raw)
            at_name = normalize_team_name(at_raw)

            home_team = get_or_create_team(db, ht_name, league.id)
            away_team = get_or_create_team(db, at_name, league.id)

            md = parse_match_date(row.get("date"))
            if md is None:
                continue

            existing = db.execute(
                select(Match).where(
                    Match.league_id == league.id,
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.match_date == md,
                )
            ).scalar_one_or_none()

            hg = safe_int(row.get("home_goals"))
            ag = safe_int(row.get("away_goals"))
            result = None
            status = "scheduled"
            if hg is not None and ag is not None:
                result = "H" if hg > ag else ("A" if ag > hg else "D")
                status = "finished"

            if existing:
                # Upsert: update fields if new data is available
                if hg is not None and existing.home_goals is None:
                    existing.home_goals = hg
                    existing.away_goals = ag
                    existing.result = result
                    existing.status = status
                for attr, val in [
                    ("ht_home_goals", safe_int(row.get("ht_home_goals"))),
                    ("ht_away_goals", safe_int(row.get("ht_away_goals"))),
                    ("home_shots", safe_int(row.get("home_shots"))),
                    ("away_shots", safe_int(row.get("away_shots"))),
                    ("home_shots_on_target", safe_int(row.get("home_shots_on_target"))),
                    ("away_shots_on_target", safe_int(row.get("away_shots_on_target"))),
                    ("home_corners", safe_int(row.get("home_corners"))),
                    ("away_corners", safe_int(row.get("away_corners"))),
                    ("home_fouls", safe_int(row.get("home_fouls"))),
                    ("away_fouls", safe_int(row.get("away_fouls"))),
                    ("home_yellow_cards", safe_int(row.get("home_yellow_cards"))),
                    ("away_yellow_cards", safe_int(row.get("away_yellow_cards"))),
                    ("home_red_cards", safe_int(row.get("home_red_cards"))),
                    ("away_red_cards", safe_int(row.get("away_red_cards"))),
                ]:
                    if val is not None and getattr(existing, attr) is None:
                        setattr(existing, attr, val)
                continue

            match = Match(
                league_id=league.id,
                season=season,
                match_date=md,
                status=status,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_goals=hg,
                away_goals=ag,
                result=result,
                ht_home_goals=safe_int(row.get("ht_home_goals")),
                ht_away_goals=safe_int(row.get("ht_away_goals")),
                home_shots=safe_int(row.get("home_shots")),
                away_shots=safe_int(row.get("away_shots")),
                home_shots_on_target=safe_int(row.get("home_shots_on_target")),
                away_shots_on_target=safe_int(row.get("away_shots_on_target")),
                home_corners=safe_int(row.get("home_corners")),
                away_corners=safe_int(row.get("away_corners")),
                home_fouls=safe_int(row.get("home_fouls")),
                away_fouls=safe_int(row.get("away_fouls")),
                home_yellow_cards=safe_int(row.get("home_yellow_cards")),
                away_yellow_cards=safe_int(row.get("away_yellow_cards")),
                home_red_cards=safe_int(row.get("home_red_cards")),
                away_red_cards=safe_int(row.get("away_red_cards")),
            )
            db.add(match)
            count += 1

        db.commit()
        total_matches += count
        if count > 0:
            logger.info(f"[FD] {csv_file.name}: {count} matches loaded")

    logger.info(f"Football-Data total: {total_matches} matches")


def load_understat_xg(db):
    us_dir = DATA_DIR / "understat_matches"
    if not us_dir.exists():
        logger.warning("No understat_matches directory")
        return

    updated = 0
    new_scheduled = 0
    for csv_file in sorted(us_dir.glob("*.csv")):
        parts = csv_file.stem.split("_")
        season = parts[-1]
        league_code = "_".join(parts[:-1])

        league = get_league(db, league_code)
        if not league:
            continue

        try:
            df = pd.read_csv(csv_file)
        except Exception:
            continue

        for _, row in df.iterrows():
            ht_raw = str(row.get("home_team", "")).strip()
            at_raw = str(row.get("away_team", "")).strip()
            if not ht_raw or ht_raw == "nan":
                continue

            ht_name = normalize_team_name(ht_raw)
            at_name = normalize_team_name(at_raw)

            md = parse_match_date(row.get("date"))
            if md is None:
                continue

            home_team = get_or_create_team(db, ht_name, league.id)
            away_team = get_or_create_team(db, at_name, league.id)

            match = db.execute(
                select(Match).where(
                    Match.league_id == league.id,
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.match_date == md,
                )
            ).scalar_one_or_none()

            h_xg = safe_float(row.get("home_xg"))
            a_xg = safe_float(row.get("away_xg"))
            is_result = row.get("is_result", False)

            if match:
                if h_xg is not None:
                    match.home_xg = h_xg
                    match.away_xg = a_xg
                    updated += 1
            else:
                hg = safe_int(row.get("home_goals"))
                ag = safe_int(row.get("away_goals"))
                status = "finished" if is_result else "scheduled"
                result = None
                if hg is not None and ag is not None and is_result:
                    result = "H" if hg > ag else ("A" if ag > hg else "D")

                new_match = Match(
                    league_id=league.id,
                    season=season,
                    match_date=md,
                    status=status,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    home_goals=hg if is_result else None,
                    away_goals=ag if is_result else None,
                    result=result,
                    home_xg=h_xg,
                    away_xg=a_xg,
                )
                db.add(new_match)
                if not is_result:
                    new_scheduled += 1

        db.commit()

    logger.info(f"Understat: {updated} xG updates, {new_scheduled} scheduled fixtures added")


def load_clubelo(db):
    elo_dir = DATA_DIR / "clubelo"
    if not elo_dir.exists():
        logger.warning("No clubelo directory")
        return

    updated = 0
    for csv_file in sorted(elo_dir.glob("*.csv")):
        try:
            df = pd.read_csv(csv_file)
        except Exception:
            continue

        if df.empty:
            continue

        sort_col = "snapshot_date" if "snapshot_date" in df.columns else "from_date"
        latest = df.sort_values(sort_col).groupby("club").last()

        for club_name, row in latest.iterrows():
            elo = safe_float(row.get("elo"))
            if not elo:
                continue
            norm_name = normalize_team_name(str(club_name))
            country = str(row.get("country", "")).strip()

            if country:
                team = db.execute(
                    select(Team).join(League).where(
                        Team.name == norm_name,
                        League.country == country,
                    )
                ).scalar_one_or_none()
            else:
                team = None

            if not team:
                team = db.execute(
                    select(Team).where(Team.name == norm_name)
                ).scalar_one_or_none()

            if team:
                team.elo_rating = elo
                updated += 1

    db.commit()
    logger.info(f"ClubElo: {updated} team Elo ratings updated")


def load_understat_players(db):
    """Load player-level season stats from Understat CSVs."""
    p_dir = DATA_DIR / "understat_players"
    if not p_dir.exists():
        logger.warning("No understat_players directory")
        return

    total = 0
    for csv_file in sorted(p_dir.glob("*.csv")):
        parts = csv_file.stem.split("_")
        season = parts[-1]
        league_code = "_".join(parts[:-1])

        league = get_league(db, league_code)
        if not league:
            continue

        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            logger.error(f"Failed to read {csv_file.name}: {e}")
            continue

        count = 0
        for _, row in df.iterrows():
            player_name = str(row.get("player_name", row.get("player", ""))).strip()
            team_name_raw = str(row.get("team_title", row.get("team", ""))).strip()
            if not player_name or player_name == "nan" or not team_name_raw or team_name_raw == "nan":
                continue

            team_name = normalize_team_name(team_name_raw)
            team = get_or_create_team(db, team_name, league.id)

            existing = db.execute(
                select(PlayerSeasonStats).where(
                    PlayerSeasonStats.name == player_name,
                    PlayerSeasonStats.team_id == team.id,
                    PlayerSeasonStats.season == season,
                )
            ).scalar_one_or_none()

            games = safe_int(row.get("games", 0))
            minutes = safe_int(row.get("time", row.get("minutes", 0)))
            goals = safe_int(row.get("goals", 0))
            xg = safe_float(row.get("xG", row.get("xg", 0)))
            assists = safe_int(row.get("assists", 0))
            xa = safe_float(row.get("xA", row.get("xa", 0)))
            shots = safe_int(row.get("shots", 0))
            key_passes = safe_int(row.get("key_passes", 0))
            npxg = safe_float(row.get("npxG", row.get("npxg", 0)))
            xg_chain = safe_float(row.get("xGChain", row.get("xg_chain", 0)))
            xg_buildup = safe_float(row.get("xGBuildup", row.get("xg_buildup", 0)))
            yellow_cards = safe_int(row.get("yellow_cards", 0))
            red_cards = safe_int(row.get("red_cards", 0))

            if existing:
                existing.games = games
                existing.minutes = minutes
                existing.goals = goals
                existing.xg = xg
                existing.assists = assists
                existing.xa = xa
                existing.shots = shots
                existing.key_passes = key_passes
                existing.npxg = npxg
                existing.xg_chain = xg_chain
                existing.xg_buildup = xg_buildup
                existing.yellow_cards = yellow_cards
                existing.red_cards = red_cards
            else:
                db.add(PlayerSeasonStats(
                    name=player_name,
                    team_id=team.id,
                    league_id=league.id,
                    season=season,
                    games=games,
                    minutes=minutes,
                    goals=goals,
                    xg=xg,
                    assists=assists,
                    xa=xa,
                    shots=shots,
                    key_passes=key_passes,
                    npxg=npxg,
                    xg_chain=xg_chain,
                    xg_buildup=xg_buildup,
                    yellow_cards=yellow_cards,
                    red_cards=red_cards,
                ))
                count += 1

        db.commit()
        total += count
        if count > 0:
            logger.info(f"[Players] {csv_file.name}: {count} new player stats")

    logger.info(f"Understat players total: {total} new records")


def load_understat_team_advanced(db):
    """Load team-level advanced metrics (PPDA, deep, npxG) from Understat CSVs
    and store seasonal averages on the Match rows (via a temp table approach)
    or just ensure the CSVs are loadable for feature engineering."""
    t_dir = DATA_DIR / "understat_teams"
    if not t_dir.exists():
        logger.warning("No understat_teams directory")
        return

    count = 0
    for csv_file in sorted(t_dir.glob("*.csv")):
        parts = csv_file.stem.split("_")
        season = parts[-1]
        league_code = "_".join(parts[:-1])

        league = get_league(db, league_code)
        if not league:
            continue

        try:
            df = pd.read_csv(csv_file)
        except Exception:
            continue

        if df.empty:
            continue

        for team_name_raw, group in df.groupby("team"):
            team_name = normalize_team_name(str(team_name_raw))
            team = get_or_create_team(db, team_name, league.id)

            ppda_att = pd.to_numeric(group.get("ppda_att", pd.Series(dtype=float)), errors="coerce")
            ppda_def = pd.to_numeric(group.get("ppda_def", pd.Series(dtype=float)), errors="coerce")
            valid = ppda_def.replace(0, np.nan)
            ppda_ratio = (ppda_att / valid).mean()

            if ppda_ratio and not np.isnan(ppda_ratio):
                count += 1

    db.commit()
    logger.info(f"Understat team advanced: verified {count} team-season records (used in features.py)")


def load_football_data_odds(db):
    """Load historical bookmaker odds from Football-Data CSVs into match_odds table."""
    fd_dir = DATA_DIR / "football_data"
    if not fd_dir.exists():
        return

    total = 0
    for csv_file in sorted(fd_dir.glob("*.csv")):
        parts = csv_file.stem.split("_")
        if len(parts) < 2:
            continue
        season = parts[-1]
        league_code = "_".join(parts[:-1])
        league = get_league(db, league_code)
        if not league:
            continue

        try:
            df = pd.read_csv(csv_file)
        except Exception:
            continue

        for _, row in df.iterrows():
            ht_raw = str(row.get("home_team", "")).strip()
            at_raw = str(row.get("away_team", "")).strip()
            if not ht_raw or ht_raw == "nan":
                continue

            ht_name = normalize_team_name(ht_raw)
            at_name = normalize_team_name(at_raw)
            md = parse_match_date(row.get("date"))
            if md is None:
                continue

            home_team = get_or_create_team(db, ht_name, league.id)
            away_team = get_or_create_team(db, at_name, league.id)

            match = db.execute(
                select(Match).where(
                    Match.league_id == league.id,
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.match_date == md,
                )
            ).scalar_one_or_none()
            if not match:
                continue

            odds_sources = {
                "pinnacle": ("pinnacle_home", "pinnacle_draw", "pinnacle_away", "pinnacle_over_25", "pinnacle_under_25"),
                "b365": ("b365_home", "b365_draw", "b365_away", "b365_over_25", "b365_under_25"),
                "avg": ("avg_home", "avg_draw", "avg_away", "avg_over_25", "avg_under_25"),
            }

            for source_name, cols in odds_sources.items():
                h_odds = safe_float(row.get(cols[0]))
                d_odds = safe_float(row.get(cols[1]))
                a_odds = safe_float(row.get(cols[2]))
                if h_odds is None:
                    continue

                existing = db.execute(
                    select(MatchOdds).where(
                        MatchOdds.match_id == match.id,
                        MatchOdds.source == source_name,
                    )
                ).scalar_one_or_none()
                if existing:
                    continue

                odds = MatchOdds(
                    match_id=match.id,
                    source=source_name,
                    home_odds=h_odds,
                    draw_odds=d_odds,
                    away_odds=a_odds,
                    over_25_odds=safe_float(row.get(cols[3])),
                    under_25_odds=safe_float(row.get(cols[4])),
                )
                db.add(odds)
                total += 1

        db.commit()

    logger.info(f"Football-Data odds: {total} odds rows loaded")


def load_fbref_data(db):
    """Load FBref match data: xG, possession, kickoff times, venue, referee."""
    fb_dir = DATA_DIR / "fbref_matches"
    if not fb_dir.exists():
        logger.info("No fbref_matches directory, skipping")
        return

    updated = 0
    new_scheduled = 0
    for csv_file in sorted(fb_dir.glob("*.csv")):
        parts = csv_file.stem.split("_")
        season = parts[-1]
        league_code = "_".join(parts[:-1])
        league = get_league(db, league_code)
        if not league:
            continue

        try:
            df = pd.read_csv(csv_file)
        except Exception:
            continue

        for _, row in df.iterrows():
            ht_raw = str(row.get("home_team", "")).strip()
            at_raw = str(row.get("away_team", "")).strip()
            if not ht_raw or ht_raw == "nan":
                continue

            ht_name = normalize_team_name(ht_raw)
            at_name = normalize_team_name(at_raw)
            md = parse_match_date(row.get("date"))
            if md is None:
                continue

            home_team = get_or_create_team(db, ht_name, league.id)
            away_team = get_or_create_team(db, at_name, league.id)

            match = db.execute(
                select(Match).where(
                    Match.league_id == league.id,
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.match_date == md,
                )
            ).scalar_one_or_none()

            h_xg = safe_float(row.get("home_xg"))
            a_xg = safe_float(row.get("away_xg"))
            is_result = bool(row.get("is_result", False))

            kickoff_utc = None
            dt_val = row.get("datetime")
            if pd.notna(dt_val):
                try:
                    kickoff_utc = pd.to_datetime(dt_val)
                except Exception:
                    pass

            venue = str(row.get("venue", "")).strip() if pd.notna(row.get("venue")) else None
            referee = str(row.get("referee", "")).strip() if pd.notna(row.get("referee")) else None
            matchday = safe_int(row.get("matchday"))

            if match:
                if h_xg is not None and match.home_xg is None:
                    match.home_xg = h_xg
                    match.away_xg = a_xg
                if kickoff_utc and match.kickoff_utc is None:
                    match.kickoff_utc = kickoff_utc
                if venue and not match.venue:
                    match.venue = venue
                if referee and not match.referee:
                    match.referee = referee
                if matchday and not match.matchday:
                    match.matchday = matchday
                if is_result and match.status == "scheduled":
                    hg = safe_int(row.get("home_goals"))
                    ag = safe_int(row.get("away_goals"))
                    if hg is not None:
                        match.home_goals = hg
                        match.away_goals = ag
                        match.result = "H" if hg > ag else ("A" if ag > hg else "D")
                        match.status = "finished"
                updated += 1
            else:
                hg = safe_int(row.get("home_goals")) if is_result else None
                ag = safe_int(row.get("away_goals")) if is_result else None
                status = "finished" if is_result and hg is not None else "scheduled"
                result = None
                if hg is not None and ag is not None:
                    result = "H" if hg > ag else ("A" if ag > hg else "D")

                new_match = Match(
                    league_id=league.id,
                    season=season,
                    match_date=md,
                    kickoff_utc=kickoff_utc,
                    status=status,
                    venue=venue,
                    referee=referee,
                    matchday=matchday,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    home_goals=hg,
                    away_goals=ag,
                    result=result,
                    home_xg=h_xg,
                    away_xg=a_xg,
                )
                db.add(new_match)
                if status == "scheduled":
                    new_scheduled += 1

        db.commit()

    logger.info(f"FBref: {updated} updates, {new_scheduled} new scheduled fixtures")


def load_odds_api(db):
    """Load pre-match odds from The Odds API for upcoming matches."""
    odds_dir = DATA_DIR / "odds_api"
    csv_path = odds_dir / "upcoming_odds.csv"
    if not csv_path.exists():
        logger.info("No Odds API data, skipping")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return

    if df.empty:
        return

    loaded = 0
    for _, row in df.iterrows():
        ht_raw = str(row.get("home_team", "")).strip()
        at_raw = str(row.get("away_team", "")).strip()
        bk = str(row.get("bookmaker", "")).strip()
        if not ht_raw or ht_raw == "nan":
            continue

        ht_name = normalize_team_name(ht_raw)
        at_name = normalize_team_name(at_raw)
        league_code = str(row.get("league_code", "")).strip()
        league = get_league(db, league_code)
        if not league:
            continue

        home_team = get_or_create_team(db, ht_name, league.id)
        away_team = get_or_create_team(db, at_name, league.id)

        commence = row.get("commence_time")
        md = None
        if pd.notna(commence):
            try:
                md = pd.to_datetime(commence).date()
            except Exception:
                continue

        if md is None:
            continue

        match = db.execute(
            select(Match).where(
                Match.league_id == league.id,
                Match.home_team_id == home_team.id,
                Match.away_team_id == away_team.id,
                Match.match_date == md,
            )
        ).scalar_one_or_none()

        if not match:
            continue

        source_name = f"odds_api_{bk}"
        existing = db.execute(
            select(MatchOdds).where(
                MatchOdds.match_id == match.id,
                MatchOdds.source == source_name,
            )
        ).scalar_one_or_none()

        h_odds = safe_float(row.get("home_odds"))
        if h_odds is None:
            continue

        if existing:
            existing.home_odds = h_odds
            existing.draw_odds = safe_float(row.get("draw_odds"))
            existing.away_odds = safe_float(row.get("away_odds"))
            existing.over_25_odds = safe_float(row.get("over_25_odds"))
            existing.under_25_odds = safe_float(row.get("under_25_odds"))
        else:
            db.add(MatchOdds(
                match_id=match.id,
                source=source_name,
                home_odds=h_odds,
                draw_odds=safe_float(row.get("draw_odds")),
                away_odds=safe_float(row.get("away_odds")),
                over_25_odds=safe_float(row.get("over_25_odds")),
                under_25_odds=safe_float(row.get("under_25_odds")),
            ))
            loaded += 1

    db.commit()
    logger.info(f"Odds API: {loaded} odds rows loaded")


def load_transfermarkt(db):
    """Load squad market values from Transfermarkt CSVs."""
    tm_dir = DATA_DIR / "transfermarkt"
    if not tm_dir.exists():
        logger.info("No transfermarkt directory, skipping")
        return

    total = 0
    for csv_file in sorted(tm_dir.glob("*.csv")):
        parts = csv_file.stem.split("_")
        season = parts[-1]
        league_code = "_".join(parts[:-1])
        league = get_league(db, league_code)
        if not league:
            continue

        try:
            df = pd.read_csv(csv_file)
        except Exception:
            continue

        for _, row in df.iterrows():
            team_raw = str(row.get("team", "")).strip()
            if not team_raw or team_raw == "nan":
                continue

            team_name = normalize_team_name(team_raw)
            team = get_or_create_team(db, team_name, league.id)
            market_value = safe_float(row.get("market_value_eur"))

            existing = db.execute(
                select(TeamSeasonStats).where(
                    TeamSeasonStats.team_id == team.id,
                    TeamSeasonStats.season == season,
                )
            ).scalar_one_or_none()

            if existing:
                if market_value is not None:
                    existing.market_value_eur = market_value
            else:
                db.add(TeamSeasonStats(
                    team_id=team.id,
                    season=season,
                    league_id=league.id,
                    market_value_eur=market_value,
                ))
                total += 1

        db.commit()

    logger.info(f"Transfermarkt: {total} team-season records loaded")


def load_team_logos(db):
    """Update Team.logo_url from downloaded logo files."""
    logos_dir = DATA_DIR / "logos"
    if not logos_dir.exists():
        return

    updated = 0
    for png_file in logos_dir.glob("*.png"):
        team_name = png_file.stem.replace("_", " ")
        norm = normalize_team_name(team_name)
        teams = db.execute(select(Team).where(Team.name == norm)).scalars().all()
        for team in teams:
            rel_path = f"/static/logos/{png_file.name}"
            if team.logo_url != rel_path:
                team.logo_url = rel_path
                updated += 1

    db.commit()
    if updated:
        logger.info(f"Logos: {updated} teams updated")


def main():
    logger.info("Creating database tables...")
    Base.metadata.create_all(sync_engine)
    clear_caches()

    with SyncSession() as db:
        seed_leagues(db)
        load_football_data(db)
        load_football_data_odds(db)
        load_fbref_data(db)
        load_understat_xg(db)
        load_clubelo(db)
        load_understat_players(db)
        load_understat_team_advanced(db)
        load_odds_api(db)
        load_transfermarkt(db)
        load_team_logos(db)

    logger.info("Data loading complete!")


if __name__ == "__main__":
    main()
