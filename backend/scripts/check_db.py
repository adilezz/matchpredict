"""Quick DB check script."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SyncSession
from sqlalchemy import text

with SyncSession() as db:
    print("=== Match status counts ===")
    for row in db.execute(text("SELECT status, count(*) as cnt FROM matches GROUP BY status")).fetchall():
        print(f"  {row[0]}: {row[1]}")

    print("\n=== Matches per league ===")
    for row in db.execute(text("SELECT l.code, count(*) FROM matches m JOIN leagues l ON m.league_id = l.id GROUP BY l.code ORDER BY l.code")).fetchall():
        print(f"  {row[0]}: {row[1]}")

    print("\n=== Matches with xG ===")
    for row in db.execute(text("SELECT count(*) FROM matches WHERE home_xg IS NOT NULL")).fetchall():
        print(f"  {row[0]}")

    print("\n=== Teams with Elo ===")
    for row in db.execute(text("SELECT count(*) FROM teams WHERE elo_rating IS NOT NULL")).fetchall():
        print(f"  {row[0]}")

    print("\n=== Predictions ===")
    for row in db.execute(text("SELECT count(*) FROM predictions")).fetchall():
        print(f"  {row[0]}")
