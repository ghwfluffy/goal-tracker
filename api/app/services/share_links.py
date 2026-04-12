from __future__ import annotations

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Dashboard, DashboardWidget, ShareLink, User
from app.services.goal_progress import utcnow

ShareTargetType = Literal["dashboard", "widget"]
ShareLinkStatus = Literal["active", "expired", "revoked"]

SHARE_TARGET_DASHBOARD: ShareTargetType = "dashboard"
SHARE_TARGET_WIDGET: ShareTargetType = "widget"
DEFAULT_SHARE_LINK_EXPIRATION_DAYS = 30


class ShareLinkError(Exception):
    pass


class ShareLinkNotFoundError(Exception):
    pass


class ShareLinkAccessError(Exception):
    pass


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def share_link_status(
    share_link: ShareLink,
    *,
    now: datetime | None = None,
) -> ShareLinkStatus:
    current_time = _normalize_datetime(now or utcnow()) or utcnow()
    if _normalize_datetime(share_link.revoked_at) is not None:
        return "revoked"
    expires_at = _normalize_datetime(share_link.expires_at)
    if expires_at is not None and expires_at <= current_time:
        return "expired"
    return "active"


def share_link_is_active(share_link: ShareLink, *, now: datetime | None = None) -> bool:
    return share_link_status(share_link, now=now) == "active"


def list_share_links_for_user(db: Session, user: User) -> list[ShareLink]:
    statement = (
        select(ShareLink)
        .options(
            joinedload(ShareLink.dashboard),
            joinedload(ShareLink.widget).joinedload(DashboardWidget.dashboard),
        )
        .where(ShareLink.user_id == user.id)
        .order_by(ShareLink.created_at.desc())
    )
    return list(db.scalars(statement))


def get_share_link_for_user(db: Session, *, user: User, share_link_id: str) -> ShareLink:
    statement = (
        select(ShareLink)
        .options(
            joinedload(ShareLink.dashboard),
            joinedload(ShareLink.widget).joinedload(DashboardWidget.dashboard),
        )
        .where(ShareLink.id == share_link_id, ShareLink.user_id == user.id)
    )
    share_link = db.scalar(statement)
    if share_link is None:
        raise ShareLinkNotFoundError("Share link was not found.")
    return share_link


def get_public_share_link(db: Session, *, token: str) -> ShareLink:
    statement = (
        select(ShareLink)
        .options(
            joinedload(ShareLink.dashboard).joinedload(Dashboard.user),
            joinedload(ShareLink.widget).joinedload(DashboardWidget.dashboard),
        )
        .where(ShareLink.token == token)
    )
    share_link = db.scalar(statement)
    if share_link is None or not share_link_is_active(share_link):
        raise ShareLinkAccessError("Share link was not found.")
    return share_link


def _generate_share_token(db: Session) -> str:
    for _ in range(5):
        token = token_urlsafe(24)
        existing = db.scalar(select(ShareLink.id).where(ShareLink.token == token))
        if existing is None:
            return token
    raise ShareLinkError("Unable to generate a unique share link token.")


def _get_dashboard_for_share_target(db: Session, *, user: User, dashboard_id: str) -> Dashboard:
    dashboard = db.scalar(select(Dashboard).where(Dashboard.id == dashboard_id, Dashboard.user_id == user.id))
    if dashboard is None:
        raise ShareLinkNotFoundError("Dashboard was not found.")
    return dashboard


def _get_widget_for_share_target(db: Session, *, user: User, widget_id: str) -> DashboardWidget:
    widget = db.scalar(
        select(DashboardWidget)
        .options(joinedload(DashboardWidget.dashboard))
        .where(DashboardWidget.id == widget_id, DashboardWidget.user_id == user.id)
    )
    if widget is None:
        raise ShareLinkNotFoundError("Widget was not found.")
    return widget


def create_share_link(
    db: Session,
    *,
    user: User,
    target_type: ShareTargetType,
    target_id: str,
    expires_in_days: int | None = DEFAULT_SHARE_LINK_EXPIRATION_DAYS,
) -> ShareLink:
    now = utcnow()
    expires_at = now + timedelta(days=expires_in_days) if expires_in_days is not None else None

    dashboard_id: str | None = None
    widget_id: str | None = None

    if target_type == SHARE_TARGET_DASHBOARD:
        dashboard_id = _get_dashboard_for_share_target(db, user=user, dashboard_id=target_id).id
    elif target_type == SHARE_TARGET_WIDGET:
        widget_id = _get_widget_for_share_target(db, user=user, widget_id=target_id).id
    else:
        raise ShareLinkError("Unsupported share target.")

    share_link = ShareLink(
        id=str(uuid4()),
        user_id=user.id,
        dashboard_id=dashboard_id,
        widget_id=widget_id,
        token=_generate_share_token(db),
        target_type=target_type,
        expires_at=expires_at,
        created_at=now,
        updated_at=now,
    )
    db.add(share_link)
    db.flush()
    return get_share_link_for_user(db, user=user, share_link_id=share_link.id)


def revoke_share_link(db: Session, *, share_link: ShareLink) -> ShareLink:
    if share_link.revoked_at is None:
        share_link.revoked_at = utcnow()
        share_link.updated_at = utcnow()
        db.flush()
    return share_link
