"""Background scheduled jobs using APScheduler."""

import subprocess
import sys
from pathlib import Path
from loguru import logger

BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent)
PYTHON = sys.executable


def run_script(script_name: str, *args: str):
    cmd = [PYTHON, "-m", f"scripts.{script_name}"] + list(args)
    logger.info(f"[Scheduler] Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=BACKEND_DIR, timeout=3600
        )
        if result.returncode == 0:
            logger.info(f"[Scheduler] {script_name} completed successfully")
        else:
            logger.error(f"[Scheduler] {script_name} failed: {result.stderr[-500:]}")
    except subprocess.TimeoutExpired:
        logger.error(f"[Scheduler] {script_name} timed out")
    except Exception as e:
        logger.error(f"[Scheduler] {script_name} error: {e}")


def daily_scrape():
    run_script("scrape_data", "--current-season")


def daily_load():
    run_script("load_data")


def daily_predict():
    run_script("generate_predictions")


def daily_evaluate():
    run_script("generate_predictions", "--evaluate", "--auto-retrain")


def daily_odds():
    """Fetch fresh pre-match odds for upcoming matches."""
    run_script("scrape_data", "--odds-only")
    run_script("load_data")


def daily_freshen():
    """Re-generate predictions with latest odds data."""
    run_script("generate_predictions", "--update")


def weekly_retrain():
    """Forced weekly retrain with latest data regardless of evaluation metrics."""
    logger.info("[Scheduler] Weekly forced retrain starting...")
    run_script("train_models")
    run_script("generate_predictions")
    logger.info("[Scheduler] Weekly retrain complete")


def setup_scheduler(scheduler):
    """Register all jobs with an APScheduler instance."""
    scheduler.add_job(daily_scrape, "cron", hour=6, minute=0, id="daily_scrape")
    scheduler.add_job(daily_load, "cron", hour=7, minute=0, id="daily_load")
    scheduler.add_job(daily_predict, "cron", hour=8, minute=0, id="daily_predict")
    scheduler.add_job(daily_evaluate, "cron", hour=9, minute=0, id="daily_evaluate")
    scheduler.add_job(daily_odds, "cron", hour=12, minute=0, id="daily_odds")
    scheduler.add_job(daily_odds, "cron", hour=18, minute=0, id="daily_odds_evening")
    scheduler.add_job(daily_freshen, "cron", hour=13, minute=0, id="daily_freshen")
    scheduler.add_job(daily_freshen, "cron", hour=19, minute=0, id="daily_freshen_evening")
    scheduler.add_job(weekly_retrain, "cron", day_of_week="mon", hour=4, minute=0, id="weekly_retrain")
    logger.info(
        "[Scheduler] Jobs registered: scrape@06:00, load@07:00, predict@08:00, "
        "evaluate@09:00, odds@12:00+18:00, freshen@13:00+19:00 (daily), "
        "retrain@Mon 04:00 (weekly)"
    )
