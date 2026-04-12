from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, sessionmaker

from app.api import api_router
from app.core.config import ROOT_DIR, get_settings
from app.db.session import get_session_factory
from app.services.example_data import upgrade_all_example_data_users

logger = logging.getLogger(__name__)


def create_app(
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    settings = get_settings()
    startup_session_factory = session_factory or get_session_factory()

    if settings.session_key_source == "default":
        logger.warning("SESSION_KEY is using the insecure default 'changeme'.")
    elif settings.session_key_source == "generated":
        logger.warning("SESSION_KEY was not set. A temporary in-memory key was generated at startup.")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        with startup_session_factory() as db:
            upgrade_all_example_data_users(db)
            db.commit()
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount(
        "/vendor",
        StaticFiles(directory=ROOT_DIR / "web" / "public" / "vendor"),
        name="vendor",
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/healthz", tags=["health"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
