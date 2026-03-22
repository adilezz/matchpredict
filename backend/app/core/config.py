from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "MatchPredict"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/matchpredic"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/matchpredic"

    redis_url: str = "redis://localhost:6379/0"
    odds_api_key: str = ""
    football_api_key: str = ""

    model_dir: str = "ml_models"

    scrape_delay_min: float = 2.0
    scrape_delay_max: float = 5.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
