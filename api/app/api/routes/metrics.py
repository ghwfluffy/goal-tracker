from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db import Metric, MetricEntry, User, get_db
from app.services.metrics import (
    MetricError,
    MetricNotFoundError,
    create_metric,
    create_metric_entry,
    get_metric_for_user,
    list_metrics_for_user,
)

router = APIRouter(prefix="/metrics")

MetricType = Literal["integer", "date"]


class MetricEntrySummary(BaseModel):
    id: str
    recorded_at: str
    integer_value: int | None
    date_value: str | None


class MetricSummary(BaseModel):
    id: str
    name: str
    metric_type: MetricType
    unit_label: str | None
    latest_entry: MetricEntrySummary | None
    entries: list[MetricEntrySummary]


class MetricListResponse(BaseModel):
    metrics: list[MetricSummary]


class CreateMetricRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    metric_type: MetricType
    unit_label: str | None = Field(default=None, max_length=40)
    initial_integer_value: int | None = None
    initial_date_value: date | None = None
    recorded_at: datetime | None = None


class CreateMetricEntryRequest(BaseModel):
    integer_value: int | None = None
    date_value: date | None = None
    recorded_at: datetime | None = None


def serialize_metric_entry(entry: MetricEntry) -> MetricEntrySummary:
    return MetricEntrySummary(
        id=entry.id,
        recorded_at=entry.recorded_at.isoformat(),
        integer_value=entry.integer_value,
        date_value=entry.date_value.isoformat() if entry.date_value is not None else None,
    )


def serialize_metric(metric: Metric) -> MetricSummary:
    entries = [serialize_metric_entry(entry) for entry in metric.entries]
    return MetricSummary(
        id=metric.id,
        name=metric.name,
        metric_type=cast(MetricType, metric.metric_type),
        unit_label=metric.unit_label,
        latest_entry=entries[0] if len(entries) > 0 else None,
        entries=entries,
    )


@router.get("", response_model=MetricListResponse)
def get_metrics(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MetricListResponse:
    return MetricListResponse(
        metrics=[serialize_metric(metric) for metric in list_metrics_for_user(db, user)]
    )


@router.post("", response_model=MetricSummary, status_code=status.HTTP_201_CREATED)
def post_metric(
    payload: CreateMetricRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MetricSummary:
    try:
        metric = create_metric(
            db,
            user=user,
            name=payload.name,
            metric_type=payload.metric_type,
            unit_label=payload.unit_label,
            initial_integer_value=payload.initial_integer_value,
            initial_date_value=payload.initial_date_value,
            recorded_at=payload.recorded_at,
        )
        db.commit()
    except MetricError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_metric(metric)


@router.post("/{metric_id}/entries", response_model=MetricSummary)
def post_metric_entry(
    metric_id: str,
    payload: CreateMetricEntryRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MetricSummary:
    try:
        metric = get_metric_for_user(db, user=user, metric_id=metric_id)
        updated_metric = create_metric_entry(
            db,
            metric=metric,
            integer_value=payload.integer_value,
            date_value=payload.date_value,
            recorded_at=payload.recorded_at,
        )
        db.commit()
    except MetricNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetricError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_metric(updated_metric)
