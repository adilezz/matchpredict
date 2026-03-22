"""
Feature engineering pipeline.
Optimized O(n) approach using per-team history accumulation.
Includes squad quality, advanced team metrics, odds-based, and market value features.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

from loguru import logger


FEATURE_COLUMNS = [
    # Elo features
    "home_elo",
    "away_elo",
    "elo_diff",
    # Rolling form (window=5)
    "home_xg_diff",
    "away_xg_diff",
    "home_form",
    "away_form",
    "home_goal_rate",
    "away_goal_rate",
    "home_shot_conv",
    "away_shot_conv",
    # Rest days
    "home_rest_days",
    "away_rest_days",
    # Head-to-head
    "h2h_home_wr",
    # League home-field advantage
    "league_hfa",
    # Squad quality (from player stats)
    "home_squad_xg90",
    "away_squad_xg90",
    "home_top3_xg_share",
    "away_top3_xg_share",
    "home_squad_depth",
    "away_squad_depth",
    # Advanced team metrics (from FBref / Understat)
    "home_ppda",
    "away_ppda",
    "home_deep",
    "away_deep",
    "home_npxg_diff",
    "away_npxg_diff",
    # Odds-based features (from match_odds table)
    "pinnacle_implied_home",
    "pinnacle_implied_draw",
    "pinnacle_implied_away",
    "avg_implied_home",
    "avg_implied_draw",
    "avg_implied_away",
    "odds_overround",
    # Market value features (from Transfermarkt)
    "home_market_value_ratio",
]

FEATURE_DEFAULTS = {
    "home_elo": 1500.0,
    "away_elo": 1500.0,
    "elo_diff": 0.0,
    "home_xg_diff": 0.0,
    "away_xg_diff": 0.0,
    "home_form": 1.0,
    "away_form": 1.0,
    "home_goal_rate": 1.2,
    "away_goal_rate": 1.2,
    "home_shot_conv": 0.3,
    "away_shot_conv": 0.3,
    "home_rest_days": 7,
    "away_rest_days": 7,
    "h2h_home_wr": 0.5,
    "league_hfa": 0.46,
    "home_squad_xg90": 0.12,
    "away_squad_xg90": 0.12,
    "home_top3_xg_share": 0.5,
    "away_top3_xg_share": 0.5,
    "home_squad_depth": 18,
    "away_squad_depth": 18,
    "home_ppda": 10.0,
    "away_ppda": 10.0,
    "home_deep": 5.0,
    "away_deep": 5.0,
    "home_npxg_diff": 0.0,
    "away_npxg_diff": 0.0,
    "pinnacle_implied_home": 0.45,
    "pinnacle_implied_draw": 0.27,
    "pinnacle_implied_away": 0.28,
    "avg_implied_home": 0.45,
    "avg_implied_draw": 0.27,
    "avg_implied_away": 0.28,
    "odds_overround": 1.05,
    "home_market_value_ratio": 1.0,
}


def _build_squad_quality_lookup(player_df: pd.DataFrame | None) -> dict:
    """Pre-compute squad quality metrics per (team, season) from player stats."""
    if player_df is None or player_df.empty:
        return {}

    lookup = {}
    for (team, season), group in player_df.groupby(["team_name", "season"]):
        total_minutes = group["minutes"].sum()
        total_xg = group["xg"].sum()

        xg90 = (total_xg / max(total_minutes, 1)) * 90 if total_minutes > 0 else 0

        sorted_by_xg = group.sort_values("xg", ascending=False)
        top3_xg = sorted_by_xg.head(3)["xg"].sum()
        top3_share = top3_xg / max(total_xg, 0.01) if total_xg > 0 else 0.5

        depth = len(group[group["games"] >= 5])

        lookup[(team, season)] = {
            "xg90": xg90,
            "top3_share": top3_share,
            "depth": depth,
        }
    return lookup


def _build_team_advanced_lookup(data_dir: Path | None) -> dict:
    """Pre-compute rolling advanced metrics (PPDA, deep, npxG diff) per team
    from Understat/FBref team CSVs."""
    if data_dir is None:
        return {}

    lookup = {}
    for subdir in ["understat_teams", "fbref_teams"]:
        t_dir = data_dir / subdir
        if not t_dir.exists():
            continue

        for csv_file in sorted(t_dir.glob("*.csv")):
            try:
                df = pd.read_csv(csv_file)
            except Exception:
                continue
            if df.empty:
                continue

            parts = csv_file.stem.split("_")
            season = parts[-1]

            for col in ("ppda_att", "ppda_def", "deep", "deep_allowed", "npxg", "npxga"):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            team_col = "team" if "team" in df.columns else df.columns[0]
            for team_name, group in df.groupby(team_col):
                from app.scraping.utils import normalize_team_name
                norm = normalize_team_name(str(team_name))

                ppda_att = group.get("ppda_att", pd.Series(dtype=float))
                ppda_def = group.get("ppda_def", pd.Series(dtype=float)).replace(0, np.nan)
                ppda = (ppda_att / ppda_def).mean()

                deep = group.get("deep", pd.Series(dtype=float)).mean()

                npxg_for = group.get("npxg", pd.Series(dtype=float)).mean()
                npxg_ag = group.get("npxga", pd.Series(dtype=float)).mean()
                npxg_diff = (npxg_for if not np.isnan(npxg_for) else 0) - (npxg_ag if not np.isnan(npxg_ag) else 0)

                key = (norm, season)
                if key not in lookup:
                    lookup[key] = {
                        "ppda": ppda if not np.isnan(ppda) else 10.0,
                        "deep": deep if not np.isnan(deep) else 5.0,
                        "npxg_diff": npxg_diff,
                    }

    return lookup


def _build_odds_lookup(odds_df: pd.DataFrame | None) -> dict:
    """Build per-match odds lookup from a DataFrame of match_odds joined to matches."""
    if odds_df is None or odds_df.empty:
        return {}

    lookup = {}
    for match_id, group in odds_df.groupby("match_id"):
        entry = {}
        for _, row in group.iterrows():
            src = str(row.get("source", "")).lower()
            h = row.get("home_odds")
            d = row.get("draw_odds")
            a = row.get("away_odds")
            if pd.isna(h) or h is None or h <= 1:
                continue

            implied_h = 1.0 / h
            implied_d = 1.0 / d if d and d > 1 else 0.27
            implied_a = 1.0 / a if a and a > 1 else 0.28

            if "pinnacle" in src:
                entry["pinnacle_implied_home"] = implied_h
                entry["pinnacle_implied_draw"] = implied_d
                entry["pinnacle_implied_away"] = implied_a
            elif "avg" in src:
                entry["avg_implied_home"] = implied_h
                entry["avg_implied_draw"] = implied_d
                entry["avg_implied_away"] = implied_a

            overround = implied_h + implied_d + implied_a
            if overround > 0:
                entry["odds_overround"] = overround

        if entry:
            lookup[match_id] = entry
    return lookup


def _build_market_value_lookup(mv_df: pd.DataFrame | None) -> dict:
    """Build team-season market value lookup."""
    if mv_df is None or mv_df.empty:
        return {}

    lookup = {}
    for _, row in mv_df.iterrows():
        team = row.get("team_name", "")
        season = row.get("season", "")
        val = row.get("market_value_eur")
        if team and season and pd.notna(val) and val > 0:
            lookup[(team, season)] = float(val)
    return lookup


def _init_elo_from_teams(elo_df: pd.DataFrame | None) -> dict:
    """Initialize Elo from ClubElo-sourced Team.elo_rating values."""
    elo = defaultdict(lambda: 1500.0)
    if elo_df is not None and not elo_df.empty:
        for _, row in elo_df.iterrows():
            name = row.get("name", "")
            rating = row.get("elo_rating")
            if name and pd.notna(rating) and rating > 0:
                elo[name] = float(rating)
    return elo


def build_feature_matrix(
    df: pd.DataFrame,
    window: int = 5,
    player_df: pd.DataFrame | None = None,
    data_dir: Path | None = None,
    odds_df: pd.DataFrame | None = None,
    market_value_df: pd.DataFrame | None = None,
    elo_init_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Build all features for a match DataFrame in a single chronological pass.
    """
    df = df.copy().sort_values("match_date").reset_index(drop=True)
    n = len(df)

    feats = {col: np.full(n, np.nan) for col in FEATURE_COLUMNS}
    feats["total_goals"] = np.full(n, np.nan)
    feats["result_1x2"] = np.full(n, np.nan)

    squad_lookup = _build_squad_quality_lookup(player_df)
    adv_lookup = _build_team_advanced_lookup(data_dir)
    odds_lookup = _build_odds_lookup(odds_df)
    mv_lookup = _build_market_value_lookup(market_value_df)

    team_history = defaultdict(list)
    team_last_date = {}
    elo = _init_elo_from_teams(elo_init_df)
    h2h_record = defaultdict(lambda: {"wins_a": 0, "wins_b": 0, "total": 0})
    league_hw = defaultdict(lambda: {"wins": 0, "total": 0})

    for i, row in df.iterrows():
        ht = row["home_team"]
        at = row["away_team"]
        md = row["match_date"]
        lc = row.get("league_code", "UNK")
        season = row.get("season", "")
        hg = row.get("home_goals")
        ag = row.get("away_goals")
        h_xg = row.get("home_xg")
        a_xg = row.get("away_xg")
        h_sot = row.get("home_shots_on_target")
        a_sot = row.get("away_shots_on_target")
        match_id = row.get("match_id")

        finished = hg is not None and ag is not None and not (isinstance(hg, float) and np.isnan(hg))

        # --- Elo at match time ---
        feats["home_elo"][i] = elo[ht]
        feats["away_elo"][i] = elo[at]
        feats["elo_diff"][i] = elo[ht] - elo[at]

        # --- Rest days ---
        if ht in team_last_date:
            delta = (pd.Timestamp(md) - pd.Timestamp(team_last_date[ht])).days
            feats["home_rest_days"][i] = min(delta, 30)
        else:
            feats["home_rest_days"][i] = 7
        if at in team_last_date:
            delta = (pd.Timestamp(md) - pd.Timestamp(team_last_date[at])).days
            feats["away_rest_days"][i] = min(delta, 30)
        else:
            feats["away_rest_days"][i] = 7

        # --- Rolling features from history ---
        for prefix, team in [("home", ht), ("away", at)]:
            hist = team_history[team][-window:]
            if hist:
                xg_diffs = [h.get("xg_for", 0) - h.get("xg_ag", 0) for h in hist]
                feats[f"{prefix}_xg_diff"][i] = np.mean(xg_diffs)

                pts = sum(h.get("pts", 0) for h in hist)
                feats[f"{prefix}_form"][i] = pts / len(hist)

                goals = sum(h.get("goals_for", 0) for h in hist)
                feats[f"{prefix}_goal_rate"][i] = goals / len(hist)

                sot_total = sum(h.get("sot", 0) for h in hist)
                goals_total = sum(h.get("goals_for", 0) for h in hist)
                feats[f"{prefix}_shot_conv"][i] = goals_total / max(sot_total, 1)
            else:
                feats[f"{prefix}_xg_diff"][i] = 0
                feats[f"{prefix}_form"][i] = 1.0
                feats[f"{prefix}_goal_rate"][i] = 1.2
                feats[f"{prefix}_shot_conv"][i] = 0.3

        # --- Squad quality features ---
        for prefix, team in [("home", ht), ("away", at)]:
            sq = squad_lookup.get((team, season))
            if sq:
                feats[f"{prefix}_squad_xg90"][i] = sq["xg90"]
                feats[f"{prefix}_top3_xg_share"][i] = sq["top3_share"]
                feats[f"{prefix}_squad_depth"][i] = sq["depth"]
            else:
                feats[f"{prefix}_squad_xg90"][i] = FEATURE_DEFAULTS[f"{prefix}_squad_xg90"]
                feats[f"{prefix}_top3_xg_share"][i] = FEATURE_DEFAULTS[f"{prefix}_top3_xg_share"]
                feats[f"{prefix}_squad_depth"][i] = FEATURE_DEFAULTS[f"{prefix}_squad_depth"]

        # --- Advanced team metrics ---
        for prefix, team in [("home", ht), ("away", at)]:
            adv = adv_lookup.get((team, season))
            if adv:
                feats[f"{prefix}_ppda"][i] = adv["ppda"]
                feats[f"{prefix}_deep"][i] = adv["deep"]
                feats[f"{prefix}_npxg_diff"][i] = adv["npxg_diff"]
            else:
                feats[f"{prefix}_ppda"][i] = FEATURE_DEFAULTS[f"{prefix}_ppda"]
                feats[f"{prefix}_deep"][i] = FEATURE_DEFAULTS[f"{prefix}_deep"]
                feats[f"{prefix}_npxg_diff"][i] = FEATURE_DEFAULTS[f"{prefix}_npxg_diff"]

        # --- Odds-based features ---
        if match_id and match_id in odds_lookup:
            odds_entry = odds_lookup[match_id]
            for key in ["pinnacle_implied_home", "pinnacle_implied_draw", "pinnacle_implied_away",
                         "avg_implied_home", "avg_implied_draw", "avg_implied_away", "odds_overround"]:
                feats[key][i] = odds_entry.get(key, FEATURE_DEFAULTS[key])
        else:
            for key in ["pinnacle_implied_home", "pinnacle_implied_draw", "pinnacle_implied_away",
                         "avg_implied_home", "avg_implied_draw", "avg_implied_away", "odds_overround"]:
                feats[key][i] = FEATURE_DEFAULTS[key]

        # --- Market value ratio ---
        h_mv = mv_lookup.get((ht, season))
        a_mv = mv_lookup.get((at, season))
        if h_mv and a_mv and a_mv > 0:
            feats["home_market_value_ratio"][i] = h_mv / a_mv
        else:
            feats["home_market_value_ratio"][i] = FEATURE_DEFAULTS["home_market_value_ratio"]

        # --- H2H ---
        pair_key = tuple(sorted([ht, at]))
        h2h = h2h_record[pair_key]
        if h2h["total"] > 0:
            feats["h2h_home_wr"][i] = h2h["wins_a"] / h2h["total"] if ht == pair_key[0] else h2h["wins_b"] / h2h["total"]
        else:
            feats["h2h_home_wr"][i] = 0.5

        # --- League HFA ---
        lh = league_hw[lc]
        feats["league_hfa"][i] = lh["wins"] / max(lh["total"], 1) if lh["total"] > 0 else 0.46

        # --- Targets ---
        if finished:
            hg_int, ag_int = int(hg), int(ag)
            feats["total_goals"][i] = hg_int + ag_int
            if hg_int > ag_int:
                feats["result_1x2"][i] = 0
            elif hg_int == ag_int:
                feats["result_1x2"][i] = 1
            else:
                feats["result_1x2"][i] = 2

        # --- Update accumulators (only with completed matches) ---
        if finished:
            hg_int, ag_int = int(hg), int(ag)
            h_xg_val = float(h_xg) if h_xg is not None and not (isinstance(h_xg, float) and np.isnan(h_xg)) else hg_int * 1.0
            a_xg_val = float(a_xg) if a_xg is not None and not (isinstance(a_xg, float) and np.isnan(a_xg)) else ag_int * 1.0
            h_sot_val = int(h_sot) if h_sot is not None and not (isinstance(h_sot, float) and np.isnan(h_sot)) else max(hg_int, 1)
            a_sot_val = int(a_sot) if a_sot is not None and not (isinstance(a_sot, float) and np.isnan(a_sot)) else max(ag_int, 1)

            h_pts = 3 if hg_int > ag_int else (1 if hg_int == ag_int else 0)
            a_pts = 3 if ag_int > hg_int else (1 if hg_int == ag_int else 0)

            team_history[ht].append({
                "xg_for": h_xg_val, "xg_ag": a_xg_val,
                "goals_for": hg_int, "goals_ag": ag_int,
                "sot": h_sot_val, "pts": h_pts,
            })
            team_history[at].append({
                "xg_for": a_xg_val, "xg_ag": h_xg_val,
                "goals_for": ag_int, "goals_ag": hg_int,
                "sot": a_sot_val, "pts": a_pts,
            })

            # Elo update
            exp_h = 1 / (1 + 10 ** ((elo[at] - elo[ht] - 65) / 400))
            actual_h = 1.0 if hg_int > ag_int else (0.5 if hg_int == ag_int else 0.0)
            gd_mult = np.log(max(abs(hg_int - ag_int), 1) + 1)
            elo[ht] += 32 * gd_mult * (actual_h - exp_h)
            elo[at] += 32 * gd_mult * ((1 - actual_h) - (1 - exp_h))

            # H2H
            pair_key = tuple(sorted([ht, at]))
            h2h_record[pair_key]["total"] += 1
            if hg_int > ag_int:
                if ht == pair_key[0]:
                    h2h_record[pair_key]["wins_a"] += 1
                else:
                    h2h_record[pair_key]["wins_b"] += 1
            elif ag_int > hg_int:
                if at == pair_key[0]:
                    h2h_record[pair_key]["wins_a"] += 1
                else:
                    h2h_record[pair_key]["wins_b"] += 1

            # League HFA
            league_hw[lc]["total"] += 1
            if hg_int > ag_int:
                league_hw[lc]["wins"] += 1

        team_last_date[ht] = md
        team_last_date[at] = md

    for col, arr in feats.items():
        df[col] = arr

    return df
