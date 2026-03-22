"""Create the matchpredic database if it doesn't exist."""
from sqlalchemy import create_engine, text

eng = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/postgres")
with eng.connect() as conn:
    conn.execute(text("COMMIT"))
    exists = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname='matchpredic'")
    ).fetchone()
    if exists:
        print("Database 'matchpredic' already exists")
    else:
        conn.execute(text("CREATE DATABASE matchpredic"))
        print("Database 'matchpredic' created successfully")
