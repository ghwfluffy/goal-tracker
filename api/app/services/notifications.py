from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Metric, MetricNotification, User
from app.services.metrics import create_metric_entry, is_numeric_metric_type

NOTIFICATION_STATUS_PENDING = "pending"
NOTIFICATION_STATUS_COMPLETED = "completed"
NOTIFICATION_STATUS_SKIPPED = "skipped"


class NotificationError(Exception):
    pass


class NotificationNotFoundError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def get_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise NotificationError("Timezone was not recognized.") from exc


def due_slots_for_metric(metric: Metric) -> list[tuple[int, time]]:
    slots = [(1, metric.reminder_time_1)]
    if metric.reminder_time_2 is not None:
        slots.append((2, metric.reminder_time_2))
    return slots


def local_datetime(value: datetime, timezone: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(timezone)


def metric_entry_satisfies_notification(
    *,
    entry_local_datetime: datetime,
    notification_date: date,
    slot_index: int,
    second_reminder_time: time | None,
) -> bool:
    if entry_local_datetime.date() != notification_date:
        return False

    if slot_index == 1:
        if second_reminder_time is None:
            return True
        return entry_local_datetime.timetz().replace(tzinfo=None) < second_reminder_time

    if second_reminder_time is None:
        return False
    return entry_local_datetime.timetz().replace(tzinfo=None) >= second_reminder_time


def notification_is_satisfied(
    *,
    metric: Metric,
    notification_date: date,
    slot_index: int,
    timezone: ZoneInfo,
) -> bool:
    return any(
        metric_entry_satisfies_notification(
            entry_local_datetime=local_datetime(entry.recorded_at, timezone),
            notification_date=notification_date,
            slot_index=slot_index,
            second_reminder_time=metric.reminder_time_2,
        )
        for entry in metric.entries
    )


def notification_default_recorded_at(
    *,
    notification: MetricNotification,
    timezone: ZoneInfo,
) -> datetime:
    return datetime.combine(
        notification.notification_date,
        notification.scheduled_time,
        tzinfo=timezone,
    )


def sync_metric_notifications(
    db: Session,
    *,
    metric: Metric,
    timezone: ZoneInfo,
    now: datetime,
) -> None:
    existing_by_slot = {
        (notification.notification_date, notification.slot_index): notification
        for notification in metric.notifications
    }
    metric_created_local = local_datetime(metric.created_at, timezone)
    current_local_date = now.date()
    date_cursor = metric_created_local.date()

    while date_cursor <= current_local_date:
        for slot_index, scheduled_time in due_slots_for_metric(metric):
            scheduled_local = datetime.combine(date_cursor, scheduled_time, tzinfo=timezone)
            if scheduled_local > now or scheduled_local < metric_created_local:
                continue

            existing = existing_by_slot.get((date_cursor, slot_index))
            satisfied = notification_is_satisfied(
                metric=metric,
                notification_date=date_cursor,
                slot_index=slot_index,
                timezone=timezone,
            )

            if satisfied:
                if existing is not None and existing.status == NOTIFICATION_STATUS_PENDING:
                    existing.status = NOTIFICATION_STATUS_COMPLETED
                    existing.resolved_at = utcnow()
                    existing.updated_at = utcnow()
                continue

            if existing is None:
                notification = MetricNotification(
                    id=str(uuid4()),
                    user_id=metric.user_id,
                    metric_id=metric.id,
                    notification_date=date_cursor,
                    scheduled_time=scheduled_time,
                    slot_index=slot_index,
                    status=NOTIFICATION_STATUS_PENDING,
                    updated_at=utcnow(),
                )
                db.add(notification)
                metric.notifications.append(notification)
                existing_by_slot[(date_cursor, slot_index)] = notification
        date_cursor += timedelta(days=1)

    db.flush()


def sync_due_notifications_for_user(
    db: Session,
    *,
    user: User,
    timezone_name: str,
    now: datetime | None = None,
) -> None:
    timezone = get_timezone(timezone_name)
    current_time = local_datetime(now or utcnow(), timezone)
    metrics = list(
        db.scalars(
            select(Metric)
            .options(selectinload(Metric.entries), selectinload(Metric.notifications))
            .where(Metric.user_id == user.id, Metric.archived_at.is_(None))
        )
    )
    for metric in metrics:
        sync_metric_notifications(db, metric=metric, timezone=timezone, now=current_time)


def list_pending_notifications_for_user(
    db: Session,
    *,
    user: User,
    timezone_name: str,
    now: datetime | None = None,
) -> list[MetricNotification]:
    sync_due_notifications_for_user(db, user=user, timezone_name=timezone_name, now=now)
    statement = (
        select(MetricNotification)
        .options(selectinload(MetricNotification.metric))
        .join(Metric, Metric.id == MetricNotification.metric_id)
        .where(
            MetricNotification.user_id == user.id,
            MetricNotification.status == NOTIFICATION_STATUS_PENDING,
            Metric.archived_at.is_(None),
        )
        .order_by(
            MetricNotification.notification_date.desc(),
            MetricNotification.scheduled_time.desc(),
            MetricNotification.created_at.desc(),
        )
    )
    return list(db.scalars(statement))


def get_notification_for_user(db: Session, *, user: User, notification_id: str) -> MetricNotification:
    notification = db.scalar(
        select(MetricNotification)
        .options(
            selectinload(MetricNotification.metric).selectinload(Metric.entries),
        )
        .where(MetricNotification.id == notification_id, MetricNotification.user_id == user.id)
    )
    if notification is None:
        raise NotificationNotFoundError("Notification was not found.")
    return notification


def complete_notification_with_entry(
    db: Session,
    *,
    notification: MetricNotification,
    timezone_name: str,
    recorded_at: datetime | None,
    number_value: float | None,
) -> MetricNotification:
    if notification.status != NOTIFICATION_STATUS_PENDING:
        raise NotificationError("Notification has already been resolved.")

    timezone = get_timezone(timezone_name)
    effective_recorded_at = recorded_at or notification_default_recorded_at(
        notification=notification,
        timezone=timezone,
    )

    if is_numeric_metric_type(notification.metric.metric_type):
        if number_value is None:
            raise NotificationError("Numeric metrics require a numeric value.")
        create_metric_entry(
            db,
            metric=notification.metric,
            number_value=number_value,
            date_value=None,
            recorded_at=effective_recorded_at,
        )
    else:
        create_metric_entry(
            db,
            metric=notification.metric,
            number_value=None,
            date_value=notification.notification_date,
            recorded_at=effective_recorded_at,
        )

    notification.status = NOTIFICATION_STATUS_COMPLETED
    notification.resolved_at = utcnow()
    notification.updated_at = utcnow()
    db.flush()
    return get_notification_for_user(db, user=notification.metric.user, notification_id=notification.id)


def skip_notification(db: Session, *, notification: MetricNotification) -> MetricNotification:
    if notification.status != NOTIFICATION_STATUS_PENDING:
        raise NotificationError("Notification has already been resolved.")

    notification.status = NOTIFICATION_STATUS_SKIPPED
    notification.resolved_at = utcnow()
    notification.updated_at = utcnow()
    db.flush()
    return get_notification_for_user(db, user=notification.metric.user, notification_id=notification.id)
