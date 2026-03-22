"""
Generate predictions for upcoming (or all unscored) matches.
Usage:
    python -m scripts.generate_predictions
    python -m scripts.generate_predictions --evaluate
    python -m scripts.generate_predictions --evaluate --auto-retrain
    python -m scripts.generate_predictions --update
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy import select, text

from app.core.database import SyncSession, sync_engine, Base
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.match_odds import MatchOdds
from app.ml.match_predictor import MatchPredictor
from app.ml.goals_predictor import GoalsPredictor
from app.ml.features import FEATURE_COLUMNS, FEATURE_DEFAULTS, build_feature_matrix

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_all_matches() -> pd.DataFrame:
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
            m.home_shots_on_target,
            m.away_shots_on_target,
            m.status
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        JOIN leagues l ON m.league_id = l.id
        ORDER BY m.match_date ASC
    """)
    with sync_engine.connect() as conn:
        return pd.read_sql(query, conn)


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
        return df if not df.empty else None
    except Exception:
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


def get_best_odds_for_match(db, match_id: int) -> dict:
    """Get the best available odds for value betting calculation."""
    rows = db.execute(
        select(MatchOdds).where(MatchOdds.match_id == match_id)
    ).scalars().all()
    if not rows:
        return {}
    for row in rows:
        if "pinnacle" in (row.source or "").lower():
            return {
                "home_odds": row.home_odds,
                "draw_odds": row.draw_odds,
                "away_odds": row.away_odds,
            }
    r = rows[0]
    return {
        "home_odds": r.home_odds,
        "draw_odds": r.draw_odds,
        "away_odds": r.away_odds,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluate", action="store_true", help="Run evaluation after predictions")
    parser.add_argument("--auto-retrain", action="store_true", help="Auto-retrain if evaluator says so")
    parser.add_argument("--update", action="store_true", help="Regenerate stale predictions")
    args = parser.parse_args()

    Base.metadata.create_all(sync_engine)

    match_pred = MatchPredictor()
    match_pred.load()
    if not match_pred.is_fitted:
        logger.error("1X2 model not found. Run train_models first.")
        return

    goals_pred = GoalsPredictor()
    goals_pred.load()

    player_df = load_player_data()
    odds_df = load_odds_data()
    elo_init_df = load_elo_init()
    mv_df = load_market_values()

    logger.info("Loading all matches and building features...")
    df = load_all_matches()
    if df.empty:
        logger.error("No matches in database")
        return

    df_features = build_feature_matrix(
        df, player_df=player_df, data_dir=DATA_DIR,
        odds_df=odds_df, market_value_df=mv_df, elo_init_df=elo_init_df,
    )

    scheduled = df_features[df_features["status"] == "scheduled"]
    logger.info(f"Found {len(scheduled)} scheduled matches to predict")

    if scheduled.empty:
        logger.info("No scheduled matches to predict")
        if args.evaluate:
            _run_evaluation()
        return

    generated = 0
    updated = 0
    with SyncSession() as db:
        for idx, row in scheduled.iterrows():
            match_id = row["match_id"]

            existing = db.execute(
                select(Prediction).where(Prediction.match_id == match_id)
            ).scalar_one_or_none()

            if existing and not args.update:
                continue
            if existing and args.update:
                db.delete(existing)
                db.flush()
                updated += 1

            features_dict = {col: row.get(col, FEATURE_DEFAULTS.get(col, 0)) for col in FEATURE_COLUMNS}
            X = pd.DataFrame([features_dict])[FEATURE_COLUMNS].fillna(FEATURE_DEFAULTS)

            try:
                probs_1x2 = match_pred.predict_proba(X)[0]
            except Exception as e:
                logger.warning(f"1X2 prediction failed for match {match_id}: {e}")
                continue

            try:
                goals_result = goals_pred.predict(
                    row["home_team"], row["away_team"], features_dict
                )
            except Exception as e:
                logger.warning(f"Goals prediction failed for match {match_id}: {e}")
                goals_result = {}

            # Calibrated confidence from max probability
            confidence = float(max(probs_1x2))

            # BTTS from Dixon-Coles score matrix
            prob_btts_yes = None
            prob_btts_no = None
            prob_dc_1x = None
            prob_dc_x2 = None
            prob_dc_12 = None
            correct_score_top5 = None
            try:
                matrix = goals_pred.dc_model.predict_score_matrix(
                    row["home_team"], row["away_team"]
                )
                n = matrix.shape[0]
                btts = sum(matrix[i][j] for i in range(1, n) for j in range(1, n))
                prob_btts_yes = float(btts)
                prob_btts_no = float(1 - btts)

                ph = float(probs_1x2[0])
                pd_val = float(probs_1x2[1])
                pa = float(probs_1x2[2])
                prob_dc_1x = ph + pd_val
                prob_dc_x2 = pd_val + pa
                prob_dc_12 = ph + pa

                scores = []
                for i in range(min(n, 7)):
                    for j in range(min(n, 7)):
                        scores.append((f"{i}-{j}", float(matrix[i][j])))
                top5 = sorted(scores, key=lambda x: -x[1])[:5]
                correct_score_top5 = json.dumps(top5)
            except Exception:
                pass

            # Value betting
            odds_data = get_best_odds_for_match(db, match_id)
            implied_h = 1.0 / odds_data["home_odds"] if odds_data.get("home_odds") else None
            implied_d = 1.0 / odds_data["draw_odds"] if odds_data.get("draw_odds") else None
            implied_a = 1.0 / odds_data["away_odds"] if odds_data.get("away_odds") else None
            edge_h = float(probs_1x2[0]) - implied_h if implied_h else None
            edge_d = float(probs_1x2[1]) - implied_d if implied_d else None
            edge_a = float(probs_1x2[2]) - implied_a if implied_a else None

            prediction = Prediction(
                match_id=match_id,
                prob_home=float(probs_1x2[0]),
                prob_draw=float(probs_1x2[1]),
                prob_away=float(probs_1x2[2]),
                expected_total_goals=goals_result.get("expected_total_goals"),
                prob_over_05=goals_result.get("over_0.5"),
                prob_under_05=goals_result.get("under_0.5"),
                prob_over_15=goals_result.get("over_1.5"),
                prob_under_15=goals_result.get("under_1.5"),
                prob_over_25=goals_result.get("over_2.5"),
                prob_under_25=goals_result.get("under_2.5"),
                prob_over_35=goals_result.get("over_3.5"),
                prob_under_35=goals_result.get("under_3.5"),
                home_prob_over_05=goals_result.get("home_over_0.5"),
                home_prob_under_05=goals_result.get("home_under_0.5"),
                home_prob_over_15=goals_result.get("home_over_1.5"),
                home_prob_under_15=goals_result.get("home_under_1.5"),
                home_prob_over_25=goals_result.get("home_over_2.5"),
                home_prob_under_25=goals_result.get("home_under_2.5"),
                away_prob_over_05=goals_result.get("away_over_0.5"),
                away_prob_under_05=goals_result.get("away_under_0.5"),
                away_prob_over_15=goals_result.get("away_over_1.5"),
                away_prob_under_15=goals_result.get("away_under_1.5"),
                away_prob_over_25=goals_result.get("away_over_2.5"),
                away_prob_under_25=goals_result.get("away_under_2.5"),
                home_lambda=goals_result.get("home_lambda"),
                away_lambda=goals_result.get("away_lambda"),
                prob_btts_yes=prob_btts_yes,
                prob_btts_no=prob_btts_no,
                prob_dc_1x=prob_dc_1x,
                prob_dc_x2=prob_dc_x2,
                prob_dc_12=prob_dc_12,
                correct_score_top5=correct_score_top5,
                odds_implied_home=implied_h,
                odds_implied_draw=implied_d,
                odds_implied_away=implied_a,
                value_edge_home=edge_h,
                value_edge_draw=edge_d,
                value_edge_away=edge_a,
                confidence=confidence,
            )
            db.add(prediction)
            generated += 1

        db.commit()

    logger.info(f"Generated {generated} predictions" + (f", updated {updated}" if updated else ""))

    if args.evaluate:
        should_retrain = _run_evaluation()
        if args.auto_retrain and should_retrain:
            logger.info("Evaluator recommends retraining — launching train_models...")
            subprocess.run(
                [sys.executable, "-m", "scripts.train_models"],
                cwd=str(Path(__file__).resolve().parent.parent),
            )
            logger.info("Retrain complete. Clearing old predictions for scheduled matches...")
            with SyncSession() as db:
                scheduled_ids = [
                    r[0] for r in db.execute(
                        text("SELECT id FROM matches WHERE status = 'scheduled'")
                    ).fetchall()
                ]
                if scheduled_ids:
                    db.execute(
                        text("DELETE FROM predictions WHERE match_id = ANY(:ids)"),
                        {"ids": scheduled_ids},
                    )
                    db.commit()
            logger.info("Re-generating predictions with retrained models...")
            subprocess.run(
                [sys.executable, "-m", "scripts.generate_predictions"],
                cwd=str(Path(__file__).resolve().parent.parent),
            )


def _run_evaluation() -> bool:
    """Run evaluation and return True if retrain is needed."""
    from app.ml.evaluator import evaluate_predictions
    logger.info("Running model evaluation...")
    with SyncSession() as db:
        return evaluate_predictions(db)


if __name__ == "__main__":
    main()
