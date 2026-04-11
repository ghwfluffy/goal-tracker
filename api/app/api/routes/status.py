from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter()


class StatusResponse(BaseModel):
    application: str
    environment: str
    status: str
    version: str
    checked_at: datetime


@router.get("/status", response_model=StatusResponse)
def get_status(
    settings: Annotated[Settings, Depends(get_settings)],
) -> StatusResponse:
    return StatusResponse(
        application=settings.app_name,
        environment=settings.app_env,
        status="ok",
        version=settings.app_version,
        checked_at=datetime.now(UTC),
    )
