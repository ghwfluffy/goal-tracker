from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user, refresh_session_cookie
from app.core.config import Settings, get_settings
from app.db import Metric, MetricNotification, User, get_db
from app.services.metrics import MetricError
from app.services.notifications import (
    NotificationError,
    NotificationNotFoundError,
    complete_notification_with_entry,
    get_notification_for_user,
    list_pending_notifications_for_user,
    skip_notification,
)

router = APIRouter(prefix="/notifications")

MetricType = Literal["number", "date"]
MetricUpdateType = Literal["success", "failure"]


class NotificationMetricSummary(BaseModel):
    id: str
    name: str
    metric_type: MetricType
    update_type: MetricUpdateType
    decimal_places: int | None
    unit_label: str | None


class NotificationSummary(BaseModel):
    id: str
    metric: NotificationMetricSummary
    notification_date: str
    scheduled_time: str
    slot_index: int
    status: str


class NotificationListResponse(BaseModel):
    notifications: list[NotificationSummary]


class CompleteNotificationRequest(BaseModel):
    number_value: float | None = None
    recorded_at: datetime | None = None
    timezone: str


def serialize_metric(metric: Metric) -> NotificationMetricSummary:
    return NotificationMetricSummary(
        id=metric.id,
        name=metric.name,
        metric_type=cast(MetricType, metric.metric_type),
        update_type=cast(MetricUpdateType, metric.update_type),
        decimal_places=metric.decimal_places,
        unit_label=metric.unit_label,
    )


def serialize_notification(notification: MetricNotification) -> NotificationSummary:
    return NotificationSummary(
        id=notification.id,
        metric=serialize_metric(notification.metric),
        notification_date=notification.notification_date.isoformat(),
        scheduled_time=notification.scheduled_time.strftime("%H:%M"),
        slot_index=notification.slot_index,
        status=notification.status,
    )


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    request: Request,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    timezone: Annotated[str, Query(min_length=1)],
) -> NotificationListResponse:
    try:
        notifications = list_pending_notifications_for_user(db, user=user, timezone_name=timezone)
        db.commit()
    except NotificationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    refresh_session_cookie(response, request, settings=settings)
    return NotificationListResponse(
        notifications=[serialize_notification(notification) for notification in notifications]
    )


@router.post("/{notification_id}/complete", response_model=NotificationSummary)
def post_complete_notification(
    notification_id: str,
    payload: CompleteNotificationRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationSummary:
    try:
        notification = get_notification_for_user(db, user=user, notification_id=notification_id)
        updated_notification = complete_notification_with_entry(
            db,
            notification=notification,
            timezone_name=payload.timezone,
            recorded_at=payload.recorded_at,
            number_value=payload.number_value,
        )
        db.commit()
    except NotificationNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (NotificationError, MetricError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return serialize_notification(updated_notification)


@router.post("/{notification_id}/skip", response_model=NotificationSummary)
def post_skip_notification(
    notification_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationSummary:
    try:
        notification = get_notification_for_user(db, user=user, notification_id=notification_id)
        updated_notification = skip_notification(db, notification=notification)
        db.commit()
    except NotificationNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NotificationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return serialize_notification(updated_notification)
