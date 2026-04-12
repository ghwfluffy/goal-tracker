from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import DashboardWidget, Goal, Metric, MetricEntry, User

METRIC_TYPE_NUMBER = "number"
METRIC_TYPE_DATE = "date"
SUPPORTED_METRIC_TYPES = {METRIC_TYPE_NUMBER, METRIC_TYPE_DATE}
UPDATE_TYPE_SUCCESS = "success"
UPDATE_TYPE_FAILURE = "failure"
SUPPORTED_UPDATE_TYPES = {UPDATE_TYPE_SUCCESS, UPDATE_TYPE_FAILURE}
MAX_DECIMAL_PLACES = 6


class MetricError(Exception):
    pass


class MetricNotFoundError(Exception):
    pass


def list_metrics_for_user(db: Session, user: User, *, include_archived: bool = False) -> list[Metric]:
    statement = select(Metric).options(selectinload(Metric.entries)).where(Metric.user_id == user.id)
    if not include_archived:
        statement = statement.where(Metric.archived_at.is_(None))
    statement = statement.order_by(Metric.created_at.desc())
    return list(db.scalars(statement))


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
        raise MetricError("Metric type must be either 'number' or 'date'.")
    return normalized


def normalize_metric_name(name: str) -> str:
    normalized = name.strip()
    if len(normalized) < 1:
        raise MetricError("Metric name is required.")
    return normalized


def normalize_update_type(*, metric_type: str, update_type: str | None) -> str:
    if metric_type == METRIC_TYPE_NUMBER:
        return UPDATE_TYPE_SUCCESS

    normalized = (update_type or UPDATE_TYPE_SUCCESS).strip().lower()
    if normalized not in SUPPORTED_UPDATE_TYPES:
        raise MetricError("Date metric update type must be either 'success' or 'failure'.")
    return normalized


def normalize_reminder_time(value: time | None, *, default: time | None = None) -> time | None:
    if value is not None:
        return value.replace(second=0, microsecond=0, tzinfo=None)
    if default is not None:
        return default.replace(second=0, microsecond=0, tzinfo=None)
    return None


def normalize_metric_reminder_schedule(
    *,
    reminder_time_1: time | None,
    reminder_time_2: time | None,
) -> tuple[time, time | None]:
    normalized_time_1 = normalize_reminder_time(reminder_time_1, default=time(6, 0))
    normalized_time_2 = normalize_reminder_time(reminder_time_2)
    if normalized_time_1 is None:
        raise MetricError("Primary reminder time is required.")
    if normalized_time_2 is not None and normalized_time_2 <= normalized_time_1:
        raise MetricError("Second reminder time must be later than the first reminder time.")
    return normalized_time_1, normalized_time_2


def normalize_decimal_places(*, metric_type: str, decimal_places: int | None) -> int | None:
    if metric_type == METRIC_TYPE_DATE:
        return None

    value = 0 if decimal_places is None else decimal_places
    if value < 0 or value > MAX_DECIMAL_PLACES:
        raise MetricError(f"Number metrics support 0 to {MAX_DECIMAL_PLACES} decimal places.")
    return value


def normalize_number_value(*, value: float | Decimal, decimal_places: int) -> Decimal:
    quantizer = Decimal("1").scaleb(-decimal_places)
    return Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP)


def validate_metric_value(
    *,
    metric_type: str,
    number_value: float | None,
    date_value: date | None,
    decimal_places: int | None,
) -> None:
    if metric_type == METRIC_TYPE_NUMBER:
        if number_value is None or date_value is not None:
            raise MetricError("Number metrics require a numeric value.")
        if decimal_places is None:
            raise MetricError("Number metrics require a decimal-places setting.")
        return

    if date_value is None or number_value is not None:
        raise MetricError("Date metrics require a date value.")


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
    decimal_places: int | None = None,
    update_type: str | None = None,
    reminder_time_1: time | None = None,
    reminder_time_2: time | None = None,
    initial_number_value: float | None = None,
    initial_date_value: date | None = None,
    recorded_at: datetime | None = None,
) -> Metric:
    normalized_metric_type = normalize_metric_type(metric_type)
    normalized_update_type = normalize_update_type(
        metric_type=normalized_metric_type,
        update_type=update_type,
    )
    normalized_reminder_time_1, normalized_reminder_time_2 = normalize_metric_reminder_schedule(
        reminder_time_1=reminder_time_1,
        reminder_time_2=reminder_time_2,
    )
    metric = Metric(
        id=str(uuid4()),
        user_id=user.id,
        name=normalize_metric_name(name),
        metric_type=normalized_metric_type,
        update_type=normalized_update_type,
        decimal_places=normalize_decimal_places(
            metric_type=normalized_metric_type,
            decimal_places=decimal_places,
        ),
        unit_label=(unit_label.strip() if unit_label is not None and unit_label.strip() != "" else None),
        reminder_time_1=normalized_reminder_time_1,
        reminder_time_2=normalized_reminder_time_2,
        updated_at=utcnow(),
    )
    db.add(metric)
    db.flush()

    if initial_number_value is not None or initial_date_value is not None:
        create_metric_entry(
            db,
            metric=metric,
            number_value=initial_number_value,
            date_value=initial_date_value,
            recorded_at=recorded_at,
        )

    return get_metric_for_user(db, user=user, metric_id=metric.id)


def create_metric_entry(
    db: Session,
    *,
    metric: Metric,
    number_value: float | None,
    date_value: date | None,
    recorded_at: datetime | None = None,
) -> Metric:
    if metric.archived_at is not None:
        raise MetricError("Archived metrics cannot be updated.")

    validate_metric_value(
        metric_type=metric.metric_type,
        number_value=number_value,
        date_value=date_value,
        decimal_places=metric.decimal_places,
    )

    entry = MetricEntry(
        id=str(uuid4()),
        metric_id=metric.id,
        recorded_at=normalize_metric_recorded_at(recorded_at),
        number_value=(
            normalize_number_value(value=number_value, decimal_places=metric.decimal_places or 0)
            if number_value is not None
            else None
        ),
        date_value=date_value,
    )
    db.add(entry)
    metric.updated_at = utcnow()
    db.flush()
    return get_metric_for_user(db, user=metric.user, metric_id=metric.id)


def set_metric_archived_state(db: Session, *, metric: Metric, archived: bool) -> Metric:
    metric.archived_at = utcnow() if archived else None
    metric.updated_at = utcnow()
    db.flush()
    return get_metric_for_user(db, user=metric.user, metric_id=metric.id)


def update_metric(
    db: Session,
    *,
    metric: Metric,
    update_fields: set[str],
    name: str | None = None,
    decimal_places: int | None = None,
    update_type: str | None = None,
    unit_label: str | None = None,
    reminder_time_1: time | None = None,
    reminder_time_2: time | None = None,
    archived: bool | None = None,
) -> Metric:
    if "name" in update_fields:
        metric.name = normalize_metric_name(name or "")

    if "decimal_places" in update_fields:
        metric.decimal_places = normalize_decimal_places(
            metric_type=metric.metric_type,
            decimal_places=decimal_places,
        )

    if "update_type" in update_fields:
        metric.update_type = normalize_update_type(
            metric_type=metric.metric_type,
            update_type=update_type,
        )

    if "unit_label" in update_fields:
        metric.unit_label = (
            unit_label.strip() if unit_label is not None and unit_label.strip() != "" else None
        )

    if "reminder_time_1" in update_fields or "reminder_time_2" in update_fields:
        resolved_time_1 = reminder_time_1 if "reminder_time_1" in update_fields else metric.reminder_time_1
        resolved_time_2 = reminder_time_2 if "reminder_time_2" in update_fields else metric.reminder_time_2
        normalized_time_1, normalized_time_2 = normalize_metric_reminder_schedule(
            reminder_time_1=resolved_time_1,
            reminder_time_2=resolved_time_2,
        )
        metric.reminder_time_1 = normalized_time_1
        metric.reminder_time_2 = normalized_time_2

    if "archived" in update_fields:
        metric.archived_at = utcnow() if archived else None

    metric.updated_at = utcnow()
    db.flush()
    return get_metric_for_user(db, user=metric.user, metric_id=metric.id)


def delete_metric(db: Session, *, metric: Metric) -> None:
    goal_exists = db.scalar(select(Goal.id).where(Goal.metric_id == metric.id).limit(1)) is not None
    if goal_exists:
        raise MetricError("Metrics linked to goals cannot be deleted.")

    widget_exists = (
        db.scalar(select(DashboardWidget.id).where(DashboardWidget.metric_id == metric.id).limit(1))
        is not None
    )
    if widget_exists:
        raise MetricError("Metrics linked to dashboard widgets cannot be deleted.")

    db.delete(metric)
    db.flush()
