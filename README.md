# MatchPredict

AI-powered football match prediction engine. Predicts **1X2 outcomes**, **over/under goals** (total + per-team), and provides detailed match analytics across 10 European leagues.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Data Pipeline](#data-pipeline)
- [Machine Learning](#machine-learning)
- [API Reference](#api-reference)
- [Scheduler](#scheduler)
- [Database Schema](#database-schema)
- [Configuration](#configuration)
- [How to Extend](#how-to-extend)
- [Known Limitations](#known-limitations)

---

## Architecture

```
                 ┌────────────────────────────────────────────────┐
                 │                   SCHEDULER                    │
                 │  daily: scrape -> load -> predict -> evaluate  │
                 │  weekly: forced retrain (Monday 04:00)         │
                 └──────┬──────────┬───────────┬─────────────────┘
                        │          │           │
              ┌─────────▼──┐ ┌─────▼─────┐ ┌──▼──────────┐
              │  SCRAPING   │ │    ML     │ │  FASTAPI    │
              │             │ │  PIPELINE │ │  REST API   │
              │ Football-   │ │           │ │             │
              │ Data.co.uk  │ │ Features  │ │ /leagues    │
              │ Understat   │ │ XGB+LGBM  │ │ /matches    │
              │ ClubElo     │ │ Dixon-    │ │ /predictions│
              │             │ │ Coles+RF  │ │             │
              └──────┬──────┘ └─────┬─────┘ └──────┬──────┘
                     │              │               │
                     └──────────────┼───────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   POSTGRESQL DB    │
                          │                    │
                          │ leagues, teams,    │
                          │ matches, predictions│
                          │ player_season_stats │
                          │ model_evaluations  │
                          └────────────────────┘
```

---

## Tech Stack

| Layer       | Technology                                                    |
|-------------|---------------------------------------------------------------|
| API         | FastAPI + Uvicorn                                             |
| Database    | PostgreSQL (asyncpg for async, psycopg2 for sync scripts)     |
| ORM         | SQLAlchemy 2.0 (async sessions for API, sync for pipelines)   |
| ML          | XGBoost, LightGBM, Scikit-learn, SciPy (Dixon-Coles Poisson) |
| Scraping    | httpx (async HTTP), BeautifulSoup4                            |
| Scheduling  | APScheduler (background jobs)                                 |
| Config      | Pydantic-settings + `.env` files                              |
| Logging     | Loguru                                                        |

---

## Project Structure

```
matchpredic/
├── .gitignore
├── README.md
└── backend/
    ├── .env.example          # Environment variable template
    ├── requirements.txt      # Python dependencies (pinned versions)
    │
    ├── app/                  # Application package
    │   ├── main.py           # FastAPI app entry point, lifespan, middleware
    │   │
    │   ├── core/             # Cross-cutting concerns
    │   │   ├── config.py     #   Pydantic Settings (reads .env)
    │   │   └── database.py   #   SQLAlchemy engines, sessions, Base
    │   │
    │   ├── models/           # SQLAlchemy ORM models
    │   │   ├── __init__.py   #   Re-exports all models
    │   │   ├── base.py       #   Base, IDMixin, TimestampMixin
    │   │   ├── league.py     #   League
    │   │   ├── team.py       #   Team (with elo_rating)
    │   │   ├── match.py      #   Match (goals, xG, shots, cards, status)
    │   │   ├── prediction.py #   Prediction (1X2 probs, O/U, lambdas)
    │   │   ├── evaluation.py #   ModelEvaluation (accuracy, retrain flag)
    │   │   └── player_stats.py # PlayerSeasonStats (xG, xA, npxG, etc.)
    │   │
    │   ├── schemas/          # Pydantic request/response schemas
    │   │   └── schemas.py    #   LeagueOut, TeamOut, MatchOut, PredictionOut
    │   │
    │   ├── services/         # Business logic (database queries)
    │   │   ├── league_service.py
    │   │   ├── match_service.py
    │   │   └── prediction_service.py
    │   │
    │   ├── api/              # REST API layer
    │   │   ├── deps.py       #   Shared dependencies (get_db)
    │   │   └── v1/           #   Version 1 endpoints
    │   │       ├── router.py #     Aggregates all v1 routers
    │   │       ├── leagues.py
    │   │       ├── matches.py
    │   │       └── predictions.py
    │   │
    │   ├── ml/               # Machine learning pipeline
    │   │   ├── features.py   #   Feature engineering (27 features)
    │   │   ├── match_predictor.py  # 1X2: XGBoost + LightGBM ensemble
    │   │   ├── goals_predictor.py  # Goals: Dixon-Coles + Random Forest
    │   │   └── evaluator.py  #   Model evaluation + retrain trigger
    │   │
    │   ├── scraping/         # Data collection
    │   │   ├── base.py       #   BaseScraper (rate-limited async HTTP)
    │   │   ├── config.py     #   League mappings, source URLs, constants
    │   │   ├── utils.py      #   Team name normalization
    │   │   └── sources/      #   One scraper per data source
    │   │       ├── football_data.py  # Football-Data.co.uk (10 leagues)
    │   │       ├── understat.py      # Understat JSON API (5 leagues)
    │   │       └── clubelo.py        # ClubElo ratings (all European)
    │   │
    │   └── scheduler/        # Background job definitions
    │       └── jobs.py       #   Daily pipeline + weekly retrain
    │
    ├── scripts/              # CLI scripts (run with: python -m scripts.NAME)
    │   ├── create_db.py      #   Create PostgreSQL database
    │   ├── scrape_data.py    #   Scrape all sources -> CSVs in data/
    │   ├── load_data.py      #   CSVs -> PostgreSQL tables
    │   ├── train_models.py   #   Build features + train models -> ml_models/
    │   ├── generate_predictions.py  # Predict scheduled matches + evaluate
    │   └── check_db.py       #   Print database statistics
    │
    ├── data/                 # Scraped CSVs (gitignored, regenerable)
    │   ├── football_data/    #   {LEAGUE}_{SEASON}.csv
    │   ├── understat_matches/#   {LEAGUE}_{SEASON}.csv
    │   ├── understat_teams/  #   {LEAGUE}_{SEASON}.csv (PPDA, deep, npxG)
    │   ├── understat_players/#   {LEAGUE}_{SEASON}.csv (per-player stats)
    │   └── clubelo/          #   {LEAGUE}_{SEASON}.csv (Elo snapshots)
    │
    └── ml_models/            # Trained model artifacts (gitignored)
        ├── xgb_1x2.pkl
        ├── lgbm_1x2.pkl
        ├── dixon_coles.pkl
        └── rf_goals.pkl
```

---

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (running locally, password: `postgres` by default)

### Installation

```bash
cd backend

# Virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# Dependencies
pip install -r requirements.txt

# Environment
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/Mac
# Edit .env if your PostgreSQL credentials differ
```

### First Run (Full Pipeline)

```bash
# 1. Create database
python scripts/create_db.py

# 2. Scrape data (all 6 seasons, ~40 min due to ClubElo rate limits)
python -m scripts.scrape_data

# 3. Load into database
python -m scripts.load_data

# 4. Train ML models (~4 min)
python -m scripts.train_models

# 5. Generate predictions for upcoming matches
python -m scripts.generate_predictions

# 6. Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Quick Refresh (Current Season Only)

```bash
python -m scripts.scrape_data --current-season
python -m scripts.load_data
python -m scripts.generate_predictions --evaluate --auto-retrain
```

---

## Data Pipeline

### Sources

| Source               | Data                                           | Leagues | Free |
|----------------------|------------------------------------------------|---------|------|
| Football-Data.co.uk  | Match results, shots, cards, HT scores         | 10      | Yes  |
| Understat            | xG, xA, npxG, PPDA, player stats, fixtures     | 5       | Yes  |
| ClubElo              | Elo ratings (bi-weekly snapshots)               | All EU  | Yes  |

### Flow

```
scrape_data.py  -->  data/*.csv  -->  load_data.py  -->  PostgreSQL
                                                           │
                     ml_models/  <--  train_models.py  <---┘
                         │
                         └--->  generate_predictions.py  -->  predictions table
```

### Seasons Covered

2020-2021 through 2025-2026 (6 seasons).

### Leagues (10)

EPL, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga, Super Lig, Jupiler Pro League, Scottish Premiership.

---

## Machine Learning

### 1X2 Predictor (`match_predictor.py`)

- **Algorithm**: XGBoost + LightGBM ensemble (55% XGB / 45% LGBM)
- **Training**: TimeSeriesSplit (5 folds), early stopping on last fold
- **Validation accuracy**: ~53% (above random baseline of 33%)

### Goals Predictor (`goals_predictor.py`)

- **Algorithm**: Dixon-Coles Bivariate Poisson (team-specific lambdas with low-score correction) + Random Forest Regressor (blended 60/40)
- **Output**: per-team lambda (expected goals), score probability matrix
- **MAE**: ~1.29 total goals

### Feature Set (27 features in `features.py`)

| Category              | Features                                                         |
|-----------------------|------------------------------------------------------------------|
| Elo                   | home_elo, away_elo, elo_diff                                     |
| Form (rolling 5)      | home/away: xg_diff, form (pts), goal_rate, shot_conv             |
| Rest                  | home_rest_days, away_rest_days                                   |
| H2H                   | h2h_home_wr                                                      |
| League                | league_hfa (home field advantage)                                |
| Squad quality         | home/away: squad_xg90, top3_xg_share, squad_depth                |
| Advanced metrics      | home/away: ppda, deep, npxg_diff                                 |

### Predictions Generated

| Market              | Values                        |
|---------------------|-------------------------------|
| 1X2                 | prob_home, prob_draw, prob_away|
| Total goals O/U     | 0.5, 1.5, 2.5, 3.5           |
| Home team goals O/U | 0.5, 1.5, 2.5                |
| Away team goals O/U | 0.5, 1.5, 2.5                |
| Expected goals      | home_lambda, away_lambda      |

### Auto-Retrain Pipeline

- **Evaluator** (`evaluator.py`): compares predictions vs actual results; triggers retrain if accuracy < 38% or model is > 4 weeks stale.
- **`--auto-retrain` flag**: when passed to `generate_predictions`, it automatically runs `train_models` + regenerates predictions if evaluator recommends it.
- **Weekly forced retrain**: every Monday at 04:00 via scheduler, regardless of evaluation metrics.

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint                            | Description                       |
|--------|-------------------------------------|-----------------------------------|
| GET    | `/api/health`                       | Health check                      |
| GET    | `/api/v1/leagues/`                  | List all leagues                  |
| GET    | `/api/v1/leagues/{code}`            | Get league by code (e.g. `EPL`)   |
| POST   | `/api/v1/leagues/seed`              | Seed leagues from config          |
| GET    | `/api/v1/matches/`                  | List matches (query params below) |
| GET    | `/api/v1/matches/upcoming?days=7`   | Upcoming matches with predictions |
| GET    | `/api/v1/matches/{id}`              | Single match detail               |
| GET    | `/api/v1/matches/{id}/h2h`          | Head-to-head history              |
| GET    | `/api/v1/matches/{id}/form`         | Recent form for both teams        |
| GET    | `/api/v1/predictions/{match_id}`    | Detailed prediction for a match   |
| GET    | `/api/v1/predictions/stats`         | Dashboard statistics              |

### Match List Query Parameters

| Param         | Type   | Example              |
|---------------|--------|----------------------|
| league_code   | string | `EPL`                |
| status        | string | `scheduled`/`finished`|
| season        | string | `2025-2026`          |
| date_from     | date   | `2026-03-20`         |
| date_to       | date   | `2026-04-01`         |

---

## Scheduler

Managed by APScheduler (started inside the FastAPI lifespan).

| Job              | Schedule          | What it does                                      |
|------------------|-------------------|---------------------------------------------------|
| daily_scrape     | Daily 06:00       | Scrape current season from all sources             |
| daily_load       | Daily 07:00       | Load new CSVs into PostgreSQL                      |
| daily_predict    | Daily 08:00       | Generate predictions for scheduled matches         |
| daily_evaluate   | Daily 09:00       | Evaluate + auto-retrain if needed                  |
| weekly_retrain   | Monday 04:00      | Forced retrain with all latest data                |

---

## Database Schema

### Tables

| Table                  | Purpose                                           |
|------------------------|---------------------------------------------------|
| `leagues`              | League metadata (code, name, country)             |
| `teams`                | Team names + current Elo rating                   |
| `matches`              | All match data (results, xG, shots, cards, status)|
| `predictions`          | ML predictions (1X2 probs, O/U, lambdas)          |
| `model_evaluations`    | Evaluation history (accuracy, log_loss, retrain)   |
| `player_season_stats`  | Per-player per-season stats from Understat        |

### Key Relationships

```
League  1──N  Team
League  1──N  Match
Team    1──N  Match (as home_team or away_team)
Match   1──1  Prediction
League  1──N  PlayerSeasonStats
Team    1──N  PlayerSeasonStats
```

### Current Data Volume

- ~24,000 historical matches (6 seasons, 10 leagues)
- ~10,000 matches with xG data (5 leagues via Understat)
- ~220 teams with Elo ratings
- ~16,600 player-season stat records (5 leagues, 6 seasons)
- ~400 predictions for upcoming fixtures

---

## Configuration

All settings are in `backend/.env` (see `.env.example`).

| Variable           | Default                                                            | Description               |
|--------------------|--------------------------------------------------------------------|---------------------------|
| DATABASE_URL       | `postgresql+asyncpg://postgres:postgres@localhost:5432/matchpredic` | Async DB URL (for API)    |
| DATABASE_URL_SYNC  | `postgresql+psycopg2://postgres:postgres@localhost:5432/matchpredic`| Sync DB URL (for scripts) |
| DEBUG              | `false`                                                            | SQL echo, verbose logging |
| MODEL_DIR          | `ml_models`                                                        | Path to saved model files |
| SCRAPE_DELAY_MIN   | `2.0`                                                              | Min seconds between requests |
| SCRAPE_DELAY_MAX   | `5.0`                                                              | Max seconds between requests |

---

## How to Extend

### Adding a New Data Source

1. Create `app/scraping/sources/new_source.py` extending `BaseScraper`.
2. Add a scrape function in `scripts/scrape_data.py` to save CSVs.
3. Add a load function in `scripts/load_data.py` to ingest into DB.
4. If it produces new columns, add them to the relevant model in `app/models/`.

### Adding New Features to the ML Model

1. Edit `app/ml/features.py`:
   - Add feature name to `FEATURE_COLUMNS` list.
   - Compute it inside `build_feature_matrix()`.
2. Re-run `python -m scripts.train_models` to retrain.
3. The predictor and goals models automatically pick up new features from `FEATURE_COLUMNS`.

### Adding a New Prediction Market

1. Add columns to `app/models/prediction.py`.
2. Add corresponding fields to `app/schemas/schemas.py` (`PredictionOut`).
3. Compute the new market in `scripts/generate_predictions.py` (or in `goals_predictor.py`).
4. Run: `python -m scripts.load_data` (to apply migration), then regenerate predictions.

### Adding Odds / Value Betting (Planned)

1. Create `app/models/odds.py` with a `MatchOdds` model (bookmaker, odds_home, odds_draw, odds_away, etc.).
2. Create `app/scraping/sources/odds_api.py` extending `BaseScraper`.
3. Add an odds comparison endpoint in `app/api/v1/odds.py`.
4. Add value detection in `app/ml/value_engine.py` (compare model probs vs implied probs).

### Adding a Frontend Dashboard

The API is designed to power a Flashscore-style dashboard:

1. **League selector** -> `GET /api/v1/leagues/`
2. **Match list** -> `GET /api/v1/matches/?league_code=EPL&status=scheduled`
3. **Match detail** -> `GET /api/v1/matches/{id}` (includes prediction)
4. **H2H** -> `GET /api/v1/matches/{id}/h2h`
5. **Form** -> `GET /api/v1/matches/{id}/form`
6. **Dashboard stats** -> `GET /api/v1/predictions/stats`

CORS is pre-configured for `localhost:3000`.

### Adding Real-Time Lineup / Injury Data (Paid API)

Current player features use season-level aggregates. To add match-day lineups:

1. Subscribe to API-Football (~$20/mo) or similar.
2. Add `FOOTBALL_API_KEY` to `.env`.
3. Create `app/scraping/sources/api_football.py` for lineup/injury fetching.
4. Add pre-match features in `features.py`: starting XI quality, key absences, etc.

---

## Known Limitations

| Limitation                          | Impact                                                   | Mitigation Path                          |
|-------------------------------------|----------------------------------------------------------|------------------------------------------|
| No pre-match lineups                | Can't account for rotation / resting players             | Add API-Football (paid)                  |
| No real-time injury data            | Squad depth proxy only                                   | Add Transfermarkt or API-Football        |
| Player features are per-season      | Recent hot streaks at player level not captured           | Team-level form IS captured via rolling  |
| 5 of 10 leagues have player data    | Eredivisie, Portuguese, Turkish, Belgian, Scottish lack squad quality features | Default values used; add more sources |
| Dixon-Coles may not converge        | Falls back to unconverged parameters (still usable)      | Increase maxiter or switch optimizer     |
| Date parsing edge cases             | Some Football-Data CSVs mix DD/MM and YYYY-MM-DD formats | Improve date parsing in load_data.py     |

---

## CLI Quick Reference

All scripts run from the `backend/` directory:

```bash
python scripts/create_db.py                              # Create database
python -m scripts.scrape_data                             # Scrape all 6 seasons
python -m scripts.scrape_data --current-season            # Scrape current season only
python -m scripts.scrape_data --force                     # Re-scrape (overwrite existing)
python -m scripts.load_data                               # Load CSVs into database
python -m scripts.train_models                            # Train all ML models
python -m scripts.generate_predictions                    # Predict scheduled matches
python -m scripts.generate_predictions --evaluate         # + run evaluation
python -m scripts.generate_predictions --evaluate --auto-retrain  # + retrain if needed
python -m scripts.check_db                                # Print database statistics
uvicorn app.main:app --host 0.0.0.0 --port 8000          # Start API server
```
