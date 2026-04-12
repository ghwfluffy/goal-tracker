from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from io import StringIO
from uuid import uuid4
from zoneinfo import ZoneInfo

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


@dataclass(frozen=True)
class MetricImportRow:
    recorded_at: datetime
    number_value: Decimal | None
    date_value: date | None
    source_line: int


def list_metrics_for_user(db: Session, user: User, *, include_archived: bool = False) -> list[Metric]:
    statement = select(Metric).options(selectinload(Metric.entries)).where(Metric.user_id == user.id)
    if not include_archived:
        statement = statement.where(Metric.archived_at.is_(None))
    statement = statement.order_by(Metric.created_at.desc())
    return list(db.scalars(statement))


def utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_metric_recorded_at(
    recorded_at: datetime | None,
    *,
    timezone_name: str | None = None,
) -> datetime:
    value = recorded_at or utcnow()
    if value.tzinfo is None:
        if timezone_name is not None:
            return value.replace(tzinfo=ZoneInfo(timezone_name)).astimezone(UTC)
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
        created_at=utcnow(),
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


def parse_metric_import_text(
    *,
    metric: Metric,
    raw_text: str,
    timezone_name: str,
) -> list[MetricImportRow]:
    rows: list[MetricImportRow] = []
    for source_line, raw_line in enumerate(raw_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped == "":
            continue

        parsed_columns = next(
            csv.reader(
                StringIO(stripped),
                delimiter="\t" if "\t" in stripped else ",",
                skipinitialspace=True,
            ),
        )
        columns = [column.strip() for column in parsed_columns]
        if len(columns) != 2:
            raise MetricError(
                f"Import line {source_line} must contain exactly two columns: timestamp and value.",
            )

        try:
            recorded_at = parse_import_recorded_at(columns[0], timezone_name=timezone_name)
            number_value, date_value = parse_import_value(metric=metric, raw_value=columns[1])
        except ValueError as exc:
            if source_line == 1 and looks_like_header(columns):
                continue
            raise MetricError(f"Import line {source_line} is invalid: {exc}") from exc

        rows.append(
            MetricImportRow(
                recorded_at=recorded_at,
                number_value=number_value,
                date_value=date_value,
                source_line=source_line,
            ),
        )

    if len(rows) == 0:
        raise MetricError("Paste at least one timestamp and value pair to import.")

    return rows


def parse_import_recorded_at(raw_value: str, *, timezone_name: str) -> datetime:
    normalized = raw_value.strip()
    if normalized == "":
        raise ValueError("timestamp is required")

    try:
        if "T" in normalized or " " in normalized:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        else:
            parsed = datetime.combine(date.fromisoformat(normalized), time.min)
    except ValueError as exc:
        raise ValueError(
            "timestamp must be ISO-like, for example 2026-01-05 20:56 or 2026-01-05T20:56:00Z",
        ) from exc

    return normalize_metric_recorded_at(parsed, timezone_name=timezone_name)


def parse_import_value(*, metric: Metric, raw_value: str) -> tuple[Decimal | None, date | None]:
    normalized = raw_value.strip()
    if normalized == "":
        raise ValueError("value is required")

    if metric.metric_type == METRIC_TYPE_NUMBER:
        if metric.decimal_places is None:
            raise ValueError("number metrics require decimal places")
        try:
            return normalize_number_value(
                value=Decimal(normalized),
                decimal_places=metric.decimal_places,
            ), None
        except Exception as exc:  # noqa: BLE001
            raise ValueError("number value is invalid") from exc

    try:
        return None, date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("date value must use YYYY-MM-DD") from exc


def looks_like_header(columns: list[str]) -> bool:
    header_tokens = {"date", "datetime", "recorded_at", "timestamp", "time", "value", "metric"}
    return all(any(character.isalpha() for character in column) for column in columns) and any(
        column.strip().lower() in header_tokens for column in columns
    )


def import_metric_entries(
    db: Session,
    *,
    metric: Metric,
    rows: list[MetricImportRow],
) -> tuple[Metric, int, int]:
    if metric.archived_at is not None:
        raise MetricError("Archived metrics cannot be updated.")

    existing_entries = list(
        db.scalars(
            select(MetricEntry).where(MetricEntry.metric_id == metric.id),
        ),
    )
    existing_by_recorded_at: dict[datetime, list[MetricEntry]] = defaultdict(list)
    for entry in existing_entries:
        existing_by_recorded_at[canonical_recorded_at(entry.recorded_at)].append(entry)

    pending_by_recorded_at: dict[datetime, tuple[Decimal | None, date | None]] = {}
    pending_rows: list[MetricImportRow] = []
    skipped_count = 0

    for row in rows:
        recorded_at_key = canonical_recorded_at(row.recorded_at)
        row_signature = (row.number_value, row.date_value)
        existing_signatures = {
            metric_entry_signature(entry=entry, decimal_places=metric.decimal_places)
            for entry in existing_by_recorded_at.get(recorded_at_key, [])
        }
        if row_signature in existing_signatures:
            skipped_count += 1
            continue
        if len(existing_signatures) > 0:
            raise MetricError(
                f"Import line {row.source_line} conflicts with an existing entry at "
                f"{row.recorded_at.isoformat()}.",
            )

        pending_signature = pending_by_recorded_at.get(recorded_at_key)
        if pending_signature == row_signature:
            skipped_count += 1
            continue
        if pending_signature is not None:
            raise MetricError(
                f"Import line {row.source_line} conflicts with another imported row at "
                f"{row.recorded_at.isoformat()}.",
            )

        pending_by_recorded_at[recorded_at_key] = row_signature
        pending_rows.append(row)

    for row in pending_rows:
        db.add(
            MetricEntry(
                id=str(uuid4()),
                metric_id=metric.id,
                recorded_at=row.recorded_at,
                number_value=row.number_value,
                date_value=row.date_value,
            ),
        )

    if len(pending_rows) > 0:
        metric.updated_at = utcnow()
        db.flush()

    return get_metric_for_user(db, user=metric.user, metric_id=metric.id), len(pending_rows), skipped_count


def metric_entry_signature(
    *,
    entry: MetricEntry,
    decimal_places: int | None,
) -> tuple[Decimal | None, date | None]:
    if entry.number_value is not None:
        return normalize_number_value(
            value=entry.number_value,
            decimal_places=decimal_places or 0,
        ), None
    return None, entry.date_value


def canonical_recorded_at(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(microsecond=0)
    return value.astimezone(UTC).replace(tzinfo=None, microsecond=0)


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
