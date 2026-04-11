from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db import Metric, MetricEntry, User, get_db
from app.services.metrics import (
    MetricError,
    MetricNotFoundError,
    create_metric,
    create_metric_entry,
    delete_metric,
    get_metric_for_user,
    list_metrics_for_user,
    set_metric_archived_state,
)

router = APIRouter(prefix="/metrics")

MetricType = Literal["number", "date"]


class MetricEntrySummary(BaseModel):
    id: str
    recorded_at: str
    number_value: float | None
    date_value: str | None


class MetricSummary(BaseModel):
    id: str
    name: str
    metric_type: MetricType
    decimal_places: int | None
    unit_label: str | None
    archived_at: str | None
    is_archived: bool
    latest_entry: MetricEntrySummary | None
    entries: list[MetricEntrySummary]


class MetricListResponse(BaseModel):
    metrics: list[MetricSummary]


class CreateMetricRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    metric_type: MetricType
    decimal_places: int | None = Field(default=None, ge=0, le=6)
    unit_label: str | None = Field(default=None, max_length=40)
    initial_number_value: float | None = None
    initial_date_value: date | None = None
    recorded_at: datetime | None = None


class CreateMetricEntryRequest(BaseModel):
    number_value: float | None = None
    date_value: date | None = None
    recorded_at: datetime | None = None


class UpdateMetricRequest(BaseModel):
    archived: bool


def decimal_to_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def serialize_metric_entry(entry: MetricEntry) -> MetricEntrySummary:
    return MetricEntrySummary(
        id=entry.id,
        recorded_at=entry.recorded_at.isoformat(),
        number_value=decimal_to_float(entry.number_value),
        date_value=entry.date_value.isoformat() if entry.date_value is not None else None,
    )


def serialize_metric(metric: Metric) -> MetricSummary:
    entries = [serialize_metric_entry(entry) for entry in metric.entries]
    return MetricSummary(
        id=metric.id,
        name=metric.name,
        metric_type=cast(MetricType, metric.metric_type),
        decimal_places=metric.decimal_places,
        unit_label=metric.unit_label,
        archived_at=metric.archived_at.isoformat() if metric.archived_at is not None else None,
        is_archived=metric.archived_at is not None,
        latest_entry=entries[0] if len(entries) > 0 else None,
        entries=entries,
    )


@router.get("", response_model=MetricListResponse)
def get_metrics(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    include_archived: Annotated[bool, Query()] = False,
) -> MetricListResponse:
    return MetricListResponse(
        metrics=[
            serialize_metric(metric)
            for metric in list_metrics_for_user(db, user, include_archived=include_archived)
        ]
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
            decimal_places=payload.decimal_places,
            unit_label=payload.unit_label,
            initial_number_value=payload.initial_number_value,
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
            number_value=payload.number_value,
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


@router.patch("/{metric_id}", response_model=MetricSummary)
def patch_metric(
    metric_id: str,
    payload: UpdateMetricRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MetricSummary:
    try:
        metric = get_metric_for_user(db, user=user, metric_id=metric_id)
        updated_metric = set_metric_archived_state(db, metric=metric, archived=payload.archived)
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


@router.delete("/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_metric(
    metric_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        metric = get_metric_for_user(db, user=user, metric_id=metric_id)
        delete_metric(db, metric=metric)
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)
