from __future__ import annotations

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, future=True, pool_pre_ping=True)
