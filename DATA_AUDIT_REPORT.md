# MatchPredict — Data Audit Report

**Auditor**: Data Pipeline & Visualization Audit  
**Date**: 2026-03-21  
**Scope**: Scraping pipeline, data ingestion, ML features, API layer, frontend display  
**Benchmark**: Flashscore, official league websites, Understat, FBref

---

## Executive Summary

After a comprehensive review of all source files across the backend scraping pipeline, data loading logic, ML feature engineering, API schemas, and frontend components, **42 issues** were identified across 6 severity categories. The most critical problems are:

1. **Team name fragmentation** — insufficient alias coverage causes silent join failures between data sources
2. **Dead/unpopulated database columns** — 8 model fields are never written, producing NULL values that mislead the frontend
3. **Feature pipeline disconnect** — ClubElo data is scraped but never used in ML; the model computes its own Elo from scratch
4. **API under-exposure** — half-time scores, shots, corners, fouls, and cards are stored in the DB but never sent to the frontend
5. **Missing kickoff times** — the frontend shows "00:00" for all matches because only dates (not datetimes) are stored

---

## Table of Contents

1. [Scraping Pipeline Issues](#1-scraping-pipeline-issues)
2. [Data Loading & Ingestion Issues](#2-data-loading--ingestion-issues)
3. [Database Schema & Model Issues](#3-database-schema--model-issues)
4. [ML Pipeline & Feature Issues](#4-ml-pipeline--feature-issues)
5. [API Layer Issues](#5-api-layer-issues)
6. [Frontend & Visualization Issues](#6-frontend--visualization-issues)
7. [Data Gaps vs Flashscore / Official Sources](#7-data-gaps-vs-flashscore--official-sources)
8. [Prioritized Recommendations](#8-prioritized-recommendations)

---

## 1. Scraping Pipeline Issues

### 1.1 [CRITICAL] Incomplete Team Name Alias Map

**File**: `app/scraping/utils.py`  
**Lines**: 15–50

Only ~30 teams have aliases defined out of ~220 teams across 10 leagues. Five entire leagues have **zero** alias coverage:

| League | Teams | Aliases Defined |
|--------|-------|-----------------|
| Eredivisie | ~18 | 0 |
| Primeira Liga | ~18 | 0 |
| Süper Lig | ~20 | 0 |
| Jupiler Pro League | ~18 | 0 |
| Scottish Premiership | ~12 | 0 |

**Impact**: When Football-Data says "Wolverhampton" and Understat says "Wolverhampton Wanderers", the normalization works. But for Eredivisie, if Football-Data says "Ajax" and ClubElo says "Ajax Amsterdam", the Elo data silently fails to merge.

**Recommendation**: Build a complete alias map for all 220+ teams. Cross-reference team names from all three sources (Football-Data CSV headers, Understat JSON, ClubElo API) and create canonical mappings. The `fuzzy_match_team()` function already exists but is **never called** in the loading pipeline — integrate it as a fallback.

---

### 1.2 [HIGH] Understat Scraper — API Fragility

**File**: `app/scraping/sources/understat.py`  
**Lines**: 46–49

The scraper constructs a URL like `https://understat.com/getLeagueData/EPL/2025` and sends XHR-style headers. This relies on Understat's undocumented internal JSON API. If Understat changes their endpoint structure, adds rate-limiting, or requires authentication, the scraper will break silently.

Additionally, the docstring (line 9) mentions "RFPL" (Russian Premier League) as covered, but RFPL is not in `SUPPORTED_LEAGUES` and was never added to the league config.

**Recommendation**: Add a response validation layer that checks the JSON structure before parsing. Log warnings if fields like `dates`, `teams`, or `players` are missing. Remove the misleading RFPL reference from the docstring.

---

### 1.3 [MEDIUM] Football-Data Date Format Ambiguity

**File**: `app/scraping/sources/football_data.py`, line 158  
**Also**: `scripts/load_data.py`, line 125

The scraper uses `pd.to_datetime(df["date"], dayfirst=True)` which works for `DD/MM/YYYY` but Football-Data has started using `YYYY-MM-DD` format in newer season files. The `dayfirst=True` flag will misparse dates like `2025-03-01` as "1st of March" (correct by accident) but `2025-01-03` as "3rd of January" (also correct by accident since ISO is unambiguous). However, a mixed file with both formats would cause silent errors for dates where day ≤ 12.

This is already noted in the README's "Known Limitations" table but has no fix.

**Recommendation**: Implement a two-pass date parser: try ISO format first (`%Y-%m-%d`), then fall back to `dayfirst=True`. Add a validation check that all parsed dates fall within the expected season range.

---

### 1.4 [MEDIUM] ClubElo Season Boundary Mismatch

**File**: `app/scraping/sources/clubelo.py`, lines 91–93

The `scrape_season_snapshots` method uses `Aug 1 — Jun 30` as the season boundary. However:
- Eredivisie and Jupiler Pro League often start in late July
- Some leagues extend into early July for playoff matches
- The 2025-2026 season Elo snapshots would only go up to Jun 30, 2026, missing July matches

**Recommendation**: Extend the window to `Jul 15 — Jul 14` to cover edge cases. Alternatively, make start/end dates configurable per league.

---

### 1.5 [LOW] --force Flag Parsed via sys.argv Hack

**File**: `scripts/scrape_data.py`, lines 37, 63, 91

The `--force` flag is checked via `"--force" not in sys.argv` instead of using the parsed `args.force`. This is a code smell that could break if argument parsing is extended.

**Recommendation**: Replace all `sys.argv` checks with `args.force`.

---

### 1.6 [LOW] Phantom Leagues in Config

**File**: `app/scraping/config.py`, lines 156–194

Five leagues are defined in `LEAGUES` but have no Football-Data or Understat mappings and are never scraped: `BOTOLAPRO`, `UCL`, `UEL`, `WORLDCUP`, `EURO`. The `seed_leagues()` function (load_data.py, line 49) skips leagues without `fd_division` or `understat_slug`, so these never enter the database.

**Impact**: Confusing for developers; the config suggests broader coverage than actually exists.

**Recommendation**: Either add scraping support for these leagues (via API-Football or other sources) or move them to a separate `PLANNED_LEAGUES` dict with a clear comment.

---

### 1.7 [MEDIUM] Season List Inconsistency

**File**: `app/scraping/config.py`, line 231 vs `scripts/scrape_data.py`, line 24

`get_seasons()` defaults to `start_year=2018` (producing 8 seasons) while `SEASONS_5Y` is hardcoded as 6 seasons starting from 2020. The README says "6 seasons" but the config helper generates 8. This creates confusion about what data is actually available.

**Recommendation**: Remove the hardcoded `SEASONS_5Y` list and use `get_seasons(start_year=2020)` as the single source of truth.

---

## 2. Data Loading & Ingestion Issues

### 2.1 [CRITICAL] Understat Team Advanced Data Not Actually Stored

**File**: `scripts/load_data.py`, lines 407–447

The `load_understat_team_advanced()` function iterates through all Understat team CSVs, computes PPDA ratios, and... does nothing with them. It only increments a counter and logs a "verified" message. No data is written to the database.

The advanced metrics (PPDA, deep completions, npxG) are only consumed by `features.py` directly reading CSV files from disk. This means:
- If CSVs are deleted, advanced features silently fall back to defaults
- The database has no record of these metrics
- There's no audit trail

**Recommendation**: Either (a) store team-season advanced metrics in a new `team_season_stats` table, or (b) document clearly that this function is a no-op verification step and that features.py reads CSVs directly.

---

### 2.2 [HIGH] Date Parsing Inconsistency Between Sources

**File**: `scripts/load_data.py`

Football-Data loading (line 125): `pd.to_datetime(match_date_val, dayfirst=True).date()`  
Understat loading (line 219): `pd.to_datetime(match_date_val).date()` (no `dayfirst`)

Understat dates come as ISO format from JSON, so this works. But if any source provides ambiguous dates like "01/02/2025", Football-Data interprets it as Feb 1 while Understat would interpret it as Jan 2. This could cause the same match to fail the deduplication check (line 129-138) and create duplicates.

**Recommendation**: Standardize all date parsing to use explicit format strings. For Football-Data: try ISO first, then `dayfirst=True`. For Understat: enforce ISO-only parsing.

---

### 2.3 [HIGH] ClubElo Name Matching is League-Blind

**File**: `scripts/load_data.py`, lines 297–301

When updating Elo ratings, the code searches for teams by name alone:
```python
team = db.execute(select(Team).where(Team.name == norm_name)).scalar_one_or_none()
```

If two teams share the same normalized name across different leagues (e.g., "Sporting" in Portugal vs "Sporting" in Belgium), only the first match is updated. Worse, it could update the wrong team's Elo.

**Recommendation**: The ClubElo CSV includes a `country` column. Use it to filter teams by league/country:
```python
team = db.execute(
    select(Team).join(League).where(Team.name == norm_name, League.country == country)
).scalar_one_or_none()
```

---

### 2.4 [MEDIUM] Mutable Default Arguments in Caching Functions

**File**: `scripts/load_data.py`, lines 61, 76

Both `get_or_create_team` and `get_league` use mutable default arguments (`_cache={}`) for caching. While this works as intended (the dict persists between calls), it's a known Python anti-pattern that causes issues in testing and can leak state between pipeline runs if the script is imported as a module.

**Recommendation**: Replace with module-level cache dicts or a simple caching class.

---

### 2.5 [MEDIUM] No Match Status Transition Mechanism

**File**: `scripts/load_data.py`

When loading Football-Data, finished matches are created with `status="finished"`. When Understat fixtures are loaded, future matches get `status="scheduled"`. However, there is **no mechanism** to transition a `scheduled` match to `finished` when results arrive in a subsequent scrape. The deduplication check (line 129) skips existing matches entirely.

This means: if a match is first created as `scheduled` from Understat fixtures, and then Football-Data later provides the result, the match stays `scheduled` forever because the deduplication check prevents the update.

**Recommendation**: When an existing match is found during loading, update its fields (goals, result, status, stats) if new data is available, rather than skipping it entirely.

---

### 2.6 [LOW] No Data Validation on Loaded Values

No checks exist for impossible values:
- Negative goals
- xG > 10 per team per match  
- Elo ratings outside reasonable bounds (500–2200)
- Dates in the future for "finished" matches
- More red cards than players (> 5)

**Recommendation**: Add validation constraints either at the ORM level (SQLAlchemy CheckConstraint) or as pre-insert validation in the loading functions.

---

## 3. Database Schema & Model Issues

### 3.1 [HIGH] Eight Dead/Unpopulated Columns on Match Model

**File**: `app/models/match.py`

The following columns exist in the schema but are **never populated** by any loading script:

| Column | Type | Always NULL | Notes |
|--------|------|-------------|-------|
| `matchday` | Integer | Yes | No source provides round numbers |
| `kickoff_utc` | DateTime | Yes | Only date is captured, never time |
| `venue` | String(150) | Yes | No source provides venue |
| `home_possession` | Float | Yes | Football-Data CSVs don't include possession |
| `away_possession` | Float | Yes | Same |
| `home_elo` | Float | Yes | Never written; features.py computes its own |
| `away_elo` | Float | Yes | Same |

**Impact**: The frontend checks for `match.home_elo` and `match.venue` and shows them if non-null, but they're always null. This creates dead UI space and confuses developers.

**Recommendation**: Either populate these columns (via additional data sources) or remove them from the model and frontend. For Elo, either write the computed Elo back during prediction generation, or use the ClubElo-sourced `Team.elo_rating`.

---

### 3.2 [MEDIUM] No Unique Constraint on Team

**File**: `app/models/team.py`

The `Team` model has no unique constraint on `(name, league_id)`. While `get_or_create_team` prevents duplicates at the application level, concurrent writes or bugs could create duplicate teams.

**Recommendation**: Add `UniqueConstraint("name", "league_id", name="uq_team_name_league")`.

---

### 3.3 [LOW] PlayerSeasonStats Missing Position Field

**File**: `app/models/player_stats.py`

Understat provides a `position` field for every player, but it's not stored. Position data is valuable for feature engineering (e.g., knowing if a striker is injured vs a defender).

**Recommendation**: Add a `position = Column(String(30))` field and populate it during loading.

---

### 3.4 [LOW] Deprecated datetime.utcnow() Usage

**File**: `app/models/prediction.py`, line 13

`datetime.utcnow` is deprecated since Python 3.12. It returns a naive datetime without timezone info.

**Recommendation**: Replace with `datetime.now(timezone.utc)` or use SQLAlchemy's `server_default=func.now()` (as done in `evaluation.py`).

---

## 4. ML Pipeline & Feature Issues

### 4.1 [CRITICAL] ClubElo Data Scraped But Not Used in ML

**File**: `app/ml/features.py`, lines 151, 170–172

The scraping pipeline spends ~40 minutes downloading ClubElo data and stores it in CSVs and the `Team.elo_rating` field. However, the feature pipeline **completely ignores all of this** and computes its own Elo from scratch:

```python
elo = defaultdict(lambda: 1500.0)  # All teams start at 1500
```

This self-computed Elo diverges significantly from ClubElo's professional ratings because:
- It starts all teams at 1500 regardless of actual strength
- It needs 20+ matches of warm-up to produce reasonable ratings
- It doesn't account for promotion/relegation gaps

**Impact**: The first ~20% of training matches have inaccurate Elo features, introducing noise. The scraped ClubElo data provides more accurate starting points.

**Recommendation**: Initialize the Elo dictionary from ClubElo snapshots. For each match, look up the ClubElo rating closest to the match date. Fall back to the self-computed Elo only if no ClubElo data exists.

---

### 4.2 [HIGH] fillna(0) Corrupts Feature Semantics

**Files**: `app/ml/match_predictor.py` (line 38), `app/ml/goals_predictor.py` (line 167)

Both models fill all NaN features with 0:
```python
X = df[FEATURE_COLUMNS].fillna(0)
```

This is semantically incorrect for several features:

| Feature | Correct Default | fillna(0) Effect |
|---------|-----------------|------------------|
| home_elo / away_elo | ~1500 | Makes team appear extremely weak |
| elo_diff | 0 | Accidentally correct |
| home_ppda / away_ppda | ~10.0 | Makes team appear to never press |
| home_deep / away_deep | ~5.0 | Makes team appear to never attack |
| home_squad_depth | ~15 | Makes team appear to have no squad |
| home_rest_days | 7 | Makes team appear to have just played |

**Recommendation**: Use feature-specific default values. Create a `FEATURE_DEFAULTS` dictionary and use `df[FEATURE_COLUMNS].fillna(FEATURE_DEFAULTS)`.

---

### 4.3 [HIGH] Squad Quality Lookup Key Mismatch

**File**: `app/ml/features.py`, lines 53, 211

The squad quality lookup uses `(team_name, season)` as the key, where `team_name` comes from `player_df["team_name"]` (which is the raw name from the `teams` table). However, the feature pipeline's `ht` / `at` variables come from the matches query which also uses `teams.name`.

The potential issue is that Understat player data uses Understat-native team names (e.g., "Wolverhampton Wanderers") while the teams table might store the Football-Data name (e.g., "Wolves") if Football-Data was loaded first. Even though `normalize_team_name` is applied during loading, the canonical names might differ depending on which source was loaded first for that team.

**Recommendation**: Ensure all team names in the player_df query are normalized consistently. Add a `normalize_team_name` call in `_build_squad_quality_lookup` or use team IDs instead of names as lookup keys.

---

### 4.4 [MEDIUM] Dixon-Coles Trained on All Historical Data

**File**: `app/ml/goals_predictor.py`, line 161

The Dixon-Coles model is fitted on ALL finished matches (up to 6 seasons). While it uses exponential decay (`decay_rate=0.005`), a match from 2020 still has weight `e^(-0.005 × 1800)` ≈ 0 — effectively zero. But the optimizer still processes these rows, wasting computation.

More importantly, the decay rate of 0.005 means matches from just 200 days ago have weight 0.37 (e^-1), which is quite aggressive. Recent form gets high weight, but the model has less effective training data.

**Recommendation**: Pre-filter matches to the last 2–3 seasons before fitting. This speeds up optimization and avoids numerical issues from near-zero weights. Make `decay_rate` configurable.

---

### 4.5 [MEDIUM] Predictions Never Updated After Creation

**File**: `scripts/generate_predictions.py`, lines 125–128

```python
existing = db.execute(
    select(Prediction).where(Prediction.match_id == match_id)
).scalar_one_or_none()
if existing:
    continue
```

Once a prediction is generated, it's never updated — even if new matches are played that would change rolling features, Elo ratings, or form data. A prediction made 14 days before kickoff uses 14-day-old features.

**Recommendation**: Add an `--update` flag that regenerates predictions for matches whose features may have changed (e.g., either team played since the prediction was created). Track `prediction.created_at` and compare against the latest match date for each team.

---

### 4.6 [LOW] Confidence Formula Not Calibrated

**File**: `scripts/generate_predictions.py`, line 148

```python
confidence = float(max(probs_1x2) - 1/3) / (1 - 1/3)
```

This normalizes the max probability to [0, 1], but it's not a true confidence measure. A model that always predicts 60% home / 20% draw / 20% away would show 40% confidence for every match, regardless of actual predictive accuracy.

**Recommendation**: Use calibration metrics (e.g., Platt scaling or isotonic regression) to produce meaningful confidence scores. Alternatively, use the entropy of the probability distribution as a confidence proxy.

---

## 5. API Layer Issues

### 5.1 [HIGH] MatchOut Schema Omits Available Data

**File**: `app/schemas/schemas.py`, class `MatchOut`

The API response for a match includes only 14 fields, but the database stores 26+ fields per match. The following data is collected, stored, but **never exposed** to the frontend:

| DB Column | Available Since | In API? |
|-----------|----------------|---------|
| `ht_home_goals` | Football-Data load | No |
| `ht_away_goals` | Football-Data load | No |
| `home_shots` | Football-Data load | No |
| `away_shots` | Football-Data load | No |
| `home_shots_on_target` | Football-Data load | No |
| `away_shots_on_target` | Football-Data load | No |
| `home_corners` | Football-Data load | No |
| `away_corners` | Football-Data load | No |
| `home_fouls` | Football-Data load | No |
| `away_fouls` | Football-Data load | No |
| `home_yellow_cards` | Football-Data load | No |
| `away_yellow_cards` | Football-Data load | No |
| `home_red_cards` | Football-Data load | No |
| `away_red_cards` | Football-Data load | No |

**Impact**: The frontend "Stats" tab shows only xG, lambda, and Elo — all of which are either null or prediction-derived. Actual match statistics (shots, corners, cards) that users expect from platforms like Flashscore are inaccessible despite being in the database.

**Recommendation**: Extend `MatchOut` to include all match statistics. Group them logically:

```python
ht_home_goals: int | None = None
ht_away_goals: int | None = None
home_shots: int | None = None
away_shots: int | None = None
home_shots_on_target: int | None = None
away_shots_on_target: int | None = None
home_corners: int | None = None
away_corners: int | None = None
home_fouls: int | None = None
away_fouls: int | None = None
home_yellow_cards: int | None = None
away_yellow_cards: int | None = None
home_red_cards: int | None = None
away_red_cards: int | None = None
```

---

### 5.2 [MEDIUM] No BTTS or Correct Score Markets in API

The Dixon-Coles model produces a full score probability matrix (`predict_score_matrix`) that can generate:
- **BTTS** (Both Teams to Score): sum matrix[i][j] where i > 0 and j > 0
- **Correct Score**: matrix[i][j] for each (i,j) pair
- **Double Chance**: 1X, X2, 12

None of these are computed or stored. On Flashscore and comparable platforms, BTTS and Correct Score are standard markets.

**Recommendation**: Extend `Prediction` model and `PredictionOut` schema to include `prob_btts_yes`, `prob_btts_no`, and top-5 correct score probabilities. Compute them in `generate_predictions.py` from the DC score matrix.

---

## 6. Frontend & Visualization Issues

### 6.1 [CRITICAL] Kickoff Time Always Shows 00:00

**Files**: `frontend/src/components/MatchRow.tsx` (line 13), `frontend/src/app/match/[id]/page.tsx` (line 93)

```typescript
const kickoff = new Date(match.match_date);  // "2026-03-22" → midnight
```

Since `match_date` is a `Date` field (not `DateTime`), the frontend always displays "00:00" as the kickoff time. This is a significant UX problem compared to Flashscore which always shows correct kickoff times.

**Root cause**: No data source in the pipeline provides kickoff times. Football-Data CSVs only have dates. Understat provides datetime but it's stored only as a date.

**Recommendation**:
1. **Immediate**: Hide the time display for scheduled matches and show only the date
2. **Short-term**: Parse and store the `datetime` field from Understat data into `kickoff_utc`
3. **Long-term**: Use API-Football or SofaScore API to get exact kickoff times for all leagues

---

### 6.2 [HIGH] Stats Tab Shows Almost Nothing

**File**: `frontend/src/app/match/[id]/page.tsx`, lines 391–431

The Stats tab conditionally renders:
- xG (only for 5/10 leagues, only for finished matches)
- Lambda (only if prediction exists)
- Elo (always null on match, see issue 3.1)

For 5 of 10 leagues (without Understat data), the Stats tab shows "No detailed statistics available" even though shots, corners, fouls, and cards data exists in the database.

**Recommendation**: After extending the API (issue 5.1), build a proper statistics display showing all available match stats with visual bars, similar to Flashscore's match statistics section.

---

### 6.3 [MEDIUM] H2H Summary Bar Rendered Twice

**File**: `frontend/src/components/H2HSection.tsx`, lines 44–90

The H2H summary renders two identical progress bars (lines 51–64 and 67–80). Both show the same homeWins/draws/awayWins distribution. This appears to be a copy-paste bug.

**Recommendation**: Remove the duplicate progress bar. The layout should be: `[homeWins] [single bar] [draws] [single bar space] [awayWins]`.

---

### 6.4 [MEDIUM] Missing Country Flags for Extra Leagues

**File**: `frontend/src/lib/helpers.ts`, lines 3–14

The `COUNTRY_FLAGS` map only covers the original 10 leagues' countries. If BOTOLAPRO (Morocco), UCL/UEL (Europe), or international tournaments are ever added, they'll show the generic "⚽" fallback.

**Recommendation**: Add entries for Morocco, Europe, and International. Also add Wales for any future expansion.

---

### 6.5 [LOW] No Loading/Error States for Individual API Calls

**File**: `frontend/src/app/match/[id]/page.tsx`, lines 27–61

H2H and form data are fetched via `Promise.allSettled`, and failures are silently ignored. If H2H fails, the tab shows "No head-to-head history available" with no way for the user to know it was an error vs genuinely no history.

**Recommendation**: Track per-section error states and show appropriate retry UI.

---

## 7. Data Gaps vs Flashscore / Official Sources

### 7.1 Data Completeness Comparison

| Data Point | Flashscore | MatchPredict | Gap |
|------------|-----------|--------------|-----|
| Kickoff time | Always present | Never present | **Critical** |
| Venue/Stadium | Always present | Never populated | High |
| Referee | Always present | Not tracked | Medium |
| Attendance | Usually present | Not tracked | Low |
| Formation/Lineup | Usually present | Not tracked | High (affects ML) |
| Half-time score | Always present | Stored but not in API | High |
| Match statistics (shots, corners, cards) | Full breakdown | Stored but not in API | **Critical** |
| Player ratings | Per-player | Not tracked | Medium |
| Ball possession | Always present | Column exists, never populated | High |
| BTTS market | Standard | Not computed | Medium |
| Correct score odds | Standard | Computable but not exposed | Medium |
| Live/in-play updates | Yes | No (only scheduled/finished) | Medium |
| Match commentary | Yes | Not tracked | Low |
| Team logos | Yes | Not tracked | High (UX) |
| League standings | Yes | Not computed | High |

### 7.2 Data Accuracy Concerns

| Issue | Description | Affected Matches |
|-------|-------------|-----------------|
| Team name mismatch | Silent join failures between sources | Est. 5–15% of Elo merges |
| Duplicate matches | Rescheduled matches may create duplicates | Unknown (edge cases) |
| Stale predictions | Predictions not updated after feature changes | All scheduled matches |
| Missing xG for 5 leagues | 50% of leagues use default features | ~12,000 matches |
| Self-computed Elo warm-up | First ~20% of data has inaccurate Elo | ~4,800 matches |

---

## 8. Prioritized Recommendations

### P0 — Critical (Fix Immediately)

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| R1 | **Extend MatchOut schema** to include HT scores, shots, corners, fouls, cards | 1 hour | Unlocks Stats tab for all leagues |
| R2 | **Hide/fix kickoff time display** — show date-only for scheduled matches until real times are available | 30 min | Fixes misleading 00:00 display |
| R3 | **Complete team name alias map** for all 220+ teams across all 3 sources | 3–4 hours | Fixes silent data merge failures |
| R4 | **Initialize ML Elo from ClubElo data** instead of flat 1500 for all teams | 2 hours | Improves early-season predictions |

### P1 — High (Fix This Sprint)

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| R5 | **Add match status transition** — update existing matches when new results arrive | 2 hours | Fixes stuck "scheduled" matches |
| R6 | **Use feature-specific defaults** instead of fillna(0) | 1 hour | Fixes corrupted feature semantics |
| R7 | **Make ClubElo team matching league-aware** | 30 min | Prevents cross-league Elo corruption |
| R8 | **Build proper Stats tab** with visual bars for all match statistics | 3–4 hours | Major UX improvement |
| R9 | **Add BTTS market** from Dixon-Coles score matrix | 1 hour | Standard market users expect |
| R10 | **Fix duplicate H2H progress bar** | 10 min | Visual bug fix |

### P2 — Medium (Next Iteration)

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| R11 | Add `--update` flag for prediction regeneration | 2 hours | Keeps predictions fresh |
| R12 | Standardize date parsing across all sources | 1 hour | Prevents silent date bugs |
| R13 | Store kickoff times from Understat datetime field | 1 hour | Partial kickoff time coverage |
| R14 | Add Unique constraint on Team(name, league_id) | 15 min | Data integrity |
| R15 | Pre-filter Dixon-Coles to last 2–3 seasons | 30 min | Faster training, cleaner model |
| R16 | Add correct score probabilities from DC matrix | 2 hours | Popular market |
| R17 | Add league standings computation | 4 hours | Major feature gap vs Flashscore |
| R18 | Clean up phantom leagues in config | 30 min | Code clarity |
| R19 | Fix --force flag to use parsed args | 10 min | Code quality |

### P3 — Low / Future

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| R20 | Add team logos (via API-Football or manual) | 4 hours | UX polish |
| R21 | Add player position to PlayerSeasonStats | 30 min | Better features |
| R22 | Add data validation constraints | 2 hours | Data integrity |
| R23 | Replace `datetime.utcnow()` | 10 min | Deprecation fix |
| R24 | Add venue/referee data (via API-Football) | 4 hours | Completeness |
| R25 | Calibrate confidence scores | 3 hours | More meaningful confidence |
| R26 | Add country flags for Morocco, Europe | 10 min | UX completeness |

---

## Appendix A: Files Audited

| File | Layer | Issues Found |
|------|-------|-------------|
| `app/scraping/config.py` | Scraping | 1.6, 1.7 |
| `app/scraping/utils.py` | Scraping | 1.1 |
| `app/scraping/base.py` | Scraping | Clean |
| `app/scraping/sources/football_data.py` | Scraping | 1.3 |
| `app/scraping/sources/understat.py` | Scraping | 1.2 |
| `app/scraping/sources/clubelo.py` | Scraping | 1.4 |
| `scripts/scrape_data.py` | Pipeline | 1.5, 1.7 |
| `scripts/load_data.py` | Loading | 2.1–2.6 |
| `scripts/train_models.py` | ML | Clean |
| `scripts/generate_predictions.py` | ML | 4.5, 4.6 |
| `app/models/match.py` | Schema | 3.1 |
| `app/models/team.py` | Schema | 3.2 |
| `app/models/prediction.py` | Schema | 3.4 |
| `app/models/player_stats.py` | Schema | 3.3 |
| `app/models/evaluation.py` | Schema | Clean |
| `app/ml/features.py` | ML | 4.1, 4.3 |
| `app/ml/match_predictor.py` | ML | 4.2 |
| `app/ml/goals_predictor.py` | ML | 4.2, 4.4 |
| `app/ml/evaluator.py` | ML | 3.4 |
| `app/schemas/schemas.py` | API | 5.1, 5.2 |
| `app/api/v1/matches.py` | API | Clean |
| `app/services/match_service.py` | API | Clean |
| `app/scheduler/jobs.py` | Scheduler | Clean |
| `frontend/src/lib/types.ts` | Frontend | 6.1 |
| `frontend/src/lib/api.ts` | Frontend | Clean |
| `frontend/src/lib/helpers.ts` | Frontend | 6.4 |
| `frontend/src/app/page.tsx` | Frontend | Clean |
| `frontend/src/app/match/[id]/page.tsx` | Frontend | 6.1, 6.2, 6.5 |
| `frontend/src/components/MatchRow.tsx` | Frontend | 6.1 |
| `frontend/src/components/PredictionPanel.tsx` | Frontend | Clean |
| `frontend/src/components/H2HSection.tsx` | Frontend | 6.3 |
| `frontend/src/components/TopPredictions.tsx` | Frontend | Clean |

---

## Appendix B: Quick Win Checklist

These issues can be fixed in under 30 minutes each and have high impact:

- [ ] R2: Hide time display, show date-only for scheduled matches
- [ ] R6: Replace `fillna(0)` with feature-specific defaults
- [ ] R7: Add country filter to ClubElo team matching query
- [ ] R10: Remove duplicate H2H progress bar
- [ ] R14: Add UniqueConstraint on Team
- [ ] R19: Fix --force flag parsing
- [ ] R23: Replace deprecated datetime.utcnow()
- [ ] R26: Add missing country flags

---

*End of Audit Report*
