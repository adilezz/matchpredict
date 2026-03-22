"""Auto-evaluation: compare predictions against actual results."""

import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.prediction import Prediction
from app.models.evaluation import ModelEvaluation
from loguru import logger

ACCURACY_RETRAIN_THRESHOLD = 0.38
WEEKS_BEFORE_FORCED_RETRAIN = 4


def evaluate_predictions(db: Session, season: str | None = None) -> bool:
    """Compare stored predictions against finished match results.
    Returns True if the model should be retrained."""
    query = (
        select(Match, Prediction)
        .join(Prediction, Prediction.match_id == Match.id)
        .where(Match.status == "finished")
        .where(Match.home_goals.isnot(None))
    )
    if season:
        query = query.where(Match.season == season)

    rows = db.execute(query).all()
    if not rows or len(rows) < 10:
        logger.info(f"Not enough evaluated matches ({len(rows) if rows else 0})")
        return False

    correct_1x2 = 0
    correct_ou25 = 0
    log_losses = []
    rps_scores = []
    n = len(rows)

    for match, pred in rows:
        hg, ag = match.home_goals, match.away_goals
        actual = 0 if hg > ag else (1 if hg == ag else 2)

        probs = [pred.prob_home, pred.prob_draw, pred.prob_away]
        predicted = np.argmax(probs)
        if predicted == actual:
            correct_1x2 += 1

        eps = 1e-10
        ll = -np.log(max(probs[actual], eps))
        log_losses.append(ll)

        # Ranked Probability Score (standard in football prediction)
        actual_vec = [1.0 if i == actual else 0.0 for i in range(3)]
        cum_pred = np.cumsum(probs)
        cum_actual = np.cumsum(actual_vec)
        rps = float(np.mean((cum_pred - cum_actual) ** 2))
        rps_scores.append(rps)

        if pred.prob_over_25 is not None:
            total = hg + ag
            predicted_over = pred.prob_over_25 > 0.5
            actual_over = total > 2.5
            if predicted_over == actual_over:
                correct_ou25 += 1

    metrics = {
        "sample_size": n,
        "accuracy_1x2": round(correct_1x2 / n, 4),
        "log_loss": round(float(np.mean(log_losses)), 4),
        "rps": round(float(np.mean(rps_scores)), 4),
        "ou_accuracy": round(correct_ou25 / n, 4) if correct_ou25 else None,
    }

    accuracy_low = metrics["accuracy_1x2"] < ACCURACY_RETRAIN_THRESHOLD

    last_eval = db.execute(
        select(ModelEvaluation)
        .where(ModelEvaluation.needs_retrain == "no")
        .order_by(desc(ModelEvaluation.evaluated_at))
        .limit(1)
    ).scalar_one_or_none()

    stale = False
    if last_eval and last_eval.evaluated_at:
        weeks_since = (datetime.now(timezone.utc) - last_eval.evaluated_at.replace(tzinfo=timezone.utc)).days / 7
        stale = weeks_since >= WEEKS_BEFORE_FORCED_RETRAIN
    elif not last_eval:
        stale = True

    should_retrain = accuracy_low or stale
    needs_retrain = "yes" if should_retrain else "no"

    reason = []
    if accuracy_low:
        reason.append(f"accuracy {metrics['accuracy_1x2']:.4f} < {ACCURACY_RETRAIN_THRESHOLD}")
    if stale:
        reason.append(f"model stale (>={WEEKS_BEFORE_FORCED_RETRAIN} weeks)")

    evaluation = ModelEvaluation(
        model_version="v1",
        season=season,
        sample_size=n,
        accuracy_1x2=metrics["accuracy_1x2"],
        log_loss=metrics["log_loss"],
        ou_accuracy=metrics["ou_accuracy"],
        needs_retrain=needs_retrain,
    )
    db.add(evaluation)
    db.commit()

    logger.info(f"Evaluation: {metrics} | retrain={needs_retrain} ({', '.join(reason) if reason else 'model OK'})")
    return should_retrain
