"""
Fresh launch: drop DB, recreate, full scrape, load, train, predict, start.

Usage:
    python -m scripts.fresh_launch                   # full pipeline
    python -m scripts.fresh_launch --skip-scrape     # skip scraping (use existing CSVs)
    python -m scripts.fresh_launch --skip-tm         # skip Transfermarkt (rate-limited)
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
PYTHON = sys.executable


def run(module: str, *args: str, timeout: int = 7200):
    cmd = [PYTHON, "-m", module] + list(args)
    logger.info(f"{'='*60}")
    logger.info(f"Running: {' '.join(cmd)}")
    logger.info(f"{'='*60}")
    result = subprocess.run(cmd, cwd=BACKEND_DIR, timeout=timeout)
    if result.returncode != 0:
        logger.error(f"FAILED: {module} (exit code {result.returncode})")
        sys.exit(1)


def reset_database():
    """Drop all tables and recreate them."""
    logger.info("Resetting database...")
    from app.core.database import sync_engine, Base
    import app.models  # noqa: F401 — register all models

    Base.metadata.drop_all(sync_engine)
    Base.metadata.create_all(sync_engine)
    logger.info("Database reset complete")


def main():
    parser = argparse.ArgumentParser(description="Fresh launch of MatchPredict")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping, use existing CSVs")
    parser.add_argument("--skip-tm", action="store_true", help="Skip Transfermarkt scraping")
    args = parser.parse_args()

    logger.info("="*60)
    logger.info("MatchPredict Fresh Launch")
    logger.info("="*60)

    # Step 1: Reset database
    reset_database()

    # Step 2: Scrape all data (unless --skip-scrape)
    if not args.skip_scrape:
        scrape_args = ["--force"]
        if args.skip_tm:
            run("scripts.scrape_data", *scrape_args)
        else:
            run("scripts.scrape_data", *scrape_args, "--transfermarkt")
    else:
        logger.info("Skipping scrape (using existing CSVs)")

    # Step 3: Build alias map from scraped data
    try:
        run("scripts.build_alias_map")
    except Exception as e:
        logger.warning(f"Alias map build failed (non-critical): {e}")

    # Step 4: Load all data
    run("scripts.load_data")

    # Step 5: Train models
    run("scripts.train_models")

    # Step 6: Generate predictions
    run("scripts.generate_predictions", "--evaluate")

    logger.info("="*60)
    logger.info("FRESH LAUNCH COMPLETE")
    logger.info("")
    logger.info("Start the API server with:")
    logger.info("  cd backend && uvicorn app.main:app --reload --port 8000")
    logger.info("")
    logger.info("Start the frontend with:")
    logger.info("  cd frontend && npm run dev")
    logger.info("="*60)


if __name__ == "__main__":
    main()
