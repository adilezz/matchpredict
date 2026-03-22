"""
Train ML models from database data.
Usage: python -m scripts.train_models
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from loguru import logger
from sqlalchemy import text

from app.core.database import sync_engine, Base
from app.ml.match_predictor import MatchPredictor
from app.ml.goals_predictor import GoalsPredictor

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_training_data() -> pd.DataFrame:
    logger.info("Loading training data from database...")
    query = text("""
        SELECT
            m.id as match_id,
            m.match_date,
            m.season,
            ht.name as home_team,
            at.name as away_team,
            l.code as league_code,
            m.home_goals,
            m.away_goals,
            m.home_xg,
            m.away_xg,
            m.home_shots,
            m.away_shots,
            m.home_shots_on_target,
            m.away_shots_on_target,
            m.home_possession,
            m.away_possession,
            m.home_elo,
            m.away_elo,
            m.status
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        JOIN leagues l ON m.league_id = l.id
        ORDER BY m.match_date ASC
    """)
    with sync_engine.connect() as conn:
        df = pd.read_sql(query, conn)
    logger.info(f"Loaded {len(df)} total matches ({(df['status'] == 'finished').sum()} finished)")
    return df


def load_player_data() -> pd.DataFrame | None:
    query = text("""
        SELECT
            ps.name as player_name,
            t.name as team_name,
            ps.season,
            ps.games,
            ps.minutes,
            ps.goals,
            ps.xg,
            ps.assists,
            ps.xa,
            ps.shots,
            ps.key_passes,
            ps.npxg,
            ps.xg_chain,
            ps.xg_buildup
        FROM player_season_stats ps
        JOIN teams t ON ps.team_id = t.id
    """)
    try:
        with sync_engine.connect() as conn:
            df = pd.read_sql(query, conn)
        logger.info(f"Loaded {len(df)} player season stat records")
        return df if not df.empty else None
    except Exception as e:
        logger.warning(f"Could not load player stats: {e}")
        return None


def load_odds_data() -> pd.DataFrame | None:
    query = text("""
        SELECT match_id, source, home_odds, draw_odds, away_odds,
               over_25_odds, under_25_odds
        FROM match_odds
    """)
    try:
        with sync_engine.connect() as conn:
            df = pd.read_sql(query, conn)
        logger.info(f"Loaded {len(df)} odds records")
        return df if not df.empty else None
    except Exception:
        return None


def load_elo_init() -> pd.DataFrame | None:
    query = text("SELECT name, elo_rating FROM teams WHERE elo_rating IS NOT NULL")
    try:
        with sync_engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df if not df.empty else None
    except Exception:
        return None


def load_market_values() -> pd.DataFrame | None:
    query = text("""
        SELECT t.name as team_name, ts.season, ts.market_value_eur
        FROM team_season_stats ts
        JOIN teams t ON ts.team_id = t.id
        WHERE ts.market_value_eur IS NOT NULL
    """)
    try:
        with sync_engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df if not df.empty else None
    except Exception:
        return None


def main():
    Base.metadata.create_all(sync_engine)

    df = load_training_data()
    finished = df[df["status"] == "finished"]

    if len(finished) < 100:
        logger.error(f"Not enough data to train: {len(finished)} matches (need >= 100)")
        return

    player_df = load_player_data()
    odds_df = load_odds_data()
    elo_init_df = load_elo_init()
    mv_df = load_market_values()

    feature_kwargs = {
        "odds_df": odds_df,
        "market_value_df": mv_df,
        "elo_init_df": elo_init_df,
    }

    logger.info(f"Training on {len(finished)} finished matches across {finished['league_code'].nunique()} leagues")

    logger.info("=" * 60)
    logger.info("TRAINING 1X2 PREDICTOR")
    logger.info("=" * 60)
    match_pred = MatchPredictor()
    metrics_1x2 = match_pred.train(finished, player_df=player_df, data_dir=DATA_DIR, **feature_kwargs)
    match_pred.save()

    logger.info("=" * 60)
    logger.info("TRAINING GOALS PREDICTOR")
    logger.info("=" * 60)
    goals_pred = GoalsPredictor()
    metrics_goals = goals_pred.train(finished, player_df=player_df, data_dir=DATA_DIR)
    goals_pred.save()

    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info(f"1X2 accuracy: {metrics_1x2.get('accuracy', 'N/A')}")
    logger.info(f"Goals MAE: {metrics_goals.get('mae', 'N/A')}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
