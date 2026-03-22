"""
Auto-generate team alias map by cross-referencing all data sources.
Reads all CSVs from football_data/, understat_matches/, clubelo/ and
clusters team names by league using fuzzy matching.

Usage: python -m scripts.build_alias_map
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from loguru import logger

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def collect_names_by_league() -> dict[str, set[str]]:
    """Collect all unique team names per league code from every CSV source."""
    names: dict[str, set[str]] = defaultdict(set)

    fd_dir = DATA_DIR / "football_data"
    if fd_dir.exists():
        for csv_file in fd_dir.glob("*.csv"):
            parts = csv_file.stem.split("_")
            league = "_".join(parts[:-1])
            try:
                df = pd.read_csv(csv_file, usecols=lambda c: c in ("home_team", "away_team", "HomeTeam", "AwayTeam"))
                for col in ("home_team", "away_team", "HomeTeam", "AwayTeam"):
                    if col in df.columns:
                        names[league].update(df[col].dropna().astype(str).str.strip().unique())
            except Exception:
                continue

    us_dir = DATA_DIR / "understat_matches"
    if us_dir.exists():
        for csv_file in us_dir.glob("*.csv"):
            parts = csv_file.stem.split("_")
            league = "_".join(parts[:-1])
            try:
                df = pd.read_csv(csv_file, usecols=lambda c: c in ("home_team", "away_team"))
                for col in ("home_team", "away_team"):
                    if col in df.columns:
                        names[league].update(df[col].dropna().astype(str).str.strip().unique())
            except Exception:
                continue

    elo_dir = DATA_DIR / "clubelo"
    if elo_dir.exists():
        for csv_file in elo_dir.glob("*.csv"):
            parts = csv_file.stem.split("_")
            league = "_".join(parts[:-1])
            try:
                df = pd.read_csv(csv_file)
                col = "club" if "club" in df.columns else None
                if col:
                    names[league].update(df[col].dropna().astype(str).str.strip().unique())
            except Exception:
                continue

    return {k: v for k, v in names.items() if v}


def build_clusters(all_names: dict[str, set[str]]) -> dict[str, list[str]]:
    """Cluster similar names within each league. Returns canonical -> aliases."""
    try:
        from thefuzz import fuzz
    except ImportError:
        logger.error("thefuzz not installed. Run: pip install thefuzz python-Levenshtein")
        return {}

    from app.scraping.utils import normalize_team_name

    clusters: dict[str, list[str]] = {}

    for league, raw_names in all_names.items():
        sorted_names = sorted(raw_names, key=len, reverse=True)
        assigned: set[str] = set()

        for name in sorted_names:
            if name in assigned:
                continue
            canonical = normalize_team_name(name)
            group = [name] if canonical == name else [name]
            assigned.add(name)

            for other in sorted_names:
                if other in assigned:
                    continue
                score = fuzz.token_sort_ratio(canonical.lower(), other.lower())
                if score >= 85:
                    group.append(other)
                    assigned.add(other)

            if canonical not in clusters:
                clusters[canonical] = []
            for g in group:
                if g != canonical and g not in clusters[canonical]:
                    clusters[canonical].append(g)

    return {k: v for k, v in clusters.items() if v}


def main():
    logger.info("Collecting team names from all CSV sources...")
    all_names = collect_names_by_league()

    total_names = sum(len(v) for v in all_names.values())
    logger.info(f"Found {total_names} unique names across {len(all_names)} leagues")

    logger.info("Clustering similar names...")
    clusters = build_clusters(all_names)

    out_path = DATA_DIR / "team_aliases.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(clusters, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Saved {len(clusters)} clusters to {out_path}")

    for canonical, aliases in sorted(clusters.items()):
        logger.info(f"  {canonical}: {aliases}")


if __name__ == "__main__":
    main()
