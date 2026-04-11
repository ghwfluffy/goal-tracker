from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Metric, MetricEntry, User

METRIC_TYPE_INTEGER = "integer"
METRIC_TYPE_DATE = "date"
SUPPORTED_METRIC_TYPES = {METRIC_TYPE_INTEGER, METRIC_TYPE_DATE}


class MetricError(Exception):
    pass


class MetricNotFoundError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_metric_recorded_at(recorded_at: datetime | None) -> datetime:
    value = recorded_at or utcnow()
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_metric_type(metric_type: str) -> str:
    normalized = metric_type.strip().lower()
    if normalized not in SUPPORTED_METRIC_TYPES:
        raise MetricError("Metric type must be either 'integer' or 'date'.")
    return normalized


def normalize_metric_name(name: str) -> str:
    normalized = name.strip()
    if len(normalized) < 1:
        raise MetricError("Metric name is required.")
    return normalized


def validate_metric_value(
    *,
    metric_type: str,
    integer_value: int | None,
    date_value: date | None,
) -> None:
    if metric_type == METRIC_TYPE_INTEGER:
        if integer_value is None or date_value is not None:
            raise MetricError("Integer metrics require an integer value.")
        return

    if date_value is None or integer_value is not None:
        raise MetricError("Date metrics require a date value.")


def list_metrics_for_user(db: Session, user: User) -> list[Metric]:
    statement = (
        select(Metric)
        .options(selectinload(Metric.entries))
        .where(Metric.user_id == user.id)
        .order_by(Metric.created_at.desc())
    )
    return list(db.scalars(statement))


def get_metric_for_user(db: Session, *, user: User, metric_id: str) -> Metric:
    statement = (
        select(Metric)
        .options(selectinload(Metric.entries))
        .where(Metric.id == metric_id, Metric.user_id == user.id)
    )
    metric = db.scalar(statement)
    if metric is None:
        raise MetricNotFoundError("Metric was not found.")
    return metric


def create_metric(
    db: Session,
    *,
    user: User,
    name: str,
    metric_type: str,
    unit_label: str | None,
    initial_integer_value: int | None = None,
    initial_date_value: date | None = None,
    recorded_at: datetime | None = None,
) -> Metric:
    normalized_metric_type = normalize_metric_type(metric_type)
    metric = Metric(
        id=str(uuid4()),
        user_id=user.id,
        name=normalize_metric_name(name),
        metric_type=normalized_metric_type,
        unit_label=(
            unit_label.strip() if unit_label is not None and unit_label.strip() != "" else None
        ),
        updated_at=utcnow(),
    )
    db.add(metric)
    db.flush()

    if initial_integer_value is not None or initial_date_value is not None:
        create_metric_entry(
            db,
            metric=metric,
            integer_value=initial_integer_value,
            date_value=initial_date_value,
            recorded_at=recorded_at,
        )

    return get_metric_for_user(db, user=user, metric_id=metric.id)


def create_metric_entry(
    db: Session,
    *,
    metric: Metric,
    integer_value: int | None,
    date_value: date | None,
    recorded_at: datetime | None = None,
) -> Metric:
    validate_metric_value(
        metric_type=metric.metric_type,
        integer_value=integer_value,
        date_value=date_value,
    )

    entry = MetricEntry(
        id=str(uuid4()),
        metric_id=metric.id,
        recorded_at=normalize_metric_recorded_at(recorded_at),
        integer_value=integer_value,
        date_value=date_value,
    )
    db.add(entry)
    metric.updated_at = utcnow()
    db.flush()
    return get_metric_for_user(db, user=metric.user, metric_id=metric.id)
