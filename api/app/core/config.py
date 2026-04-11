from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__

ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Goal Tracker"
    app_env: str = "development"
    app_version: str = __version__
    api_v1_prefix: str = "/api/v1"
    postgres_user: str = "ghw"
    postgres_password: str = "supersecure"
    postgres_db: str = "goals"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    session_key: str = "changeme"
    cors_origins: list[str] = [
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg2://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
