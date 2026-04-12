from __future__ import annotations

from typing import cast

from pydantic import BaseModel, Field

from app.api.schemas.dashboards import WidgetType
from app.core.config import get_settings
from app.db.models import ShareLink
from app.services.share_links import (
    DEFAULT_SHARE_LINK_EXPIRATION_DAYS,
    ShareLinkStatus,
    ShareTargetType,
    share_link_status,
)


class ShareLinkSummary(BaseModel):
    id: str
    target_type: ShareTargetType
    target_name: str
    dashboard_name: str | None
    widget_type: WidgetType | None
    status: ShareLinkStatus
    created_at: str
    expires_at: str | None
    revoked_at: str | None
    public_path: str
    preview_image_path: str


class ShareLinkListResponse(BaseModel):
    share_links: list[ShareLinkSummary]


class CreateShareLinkRequest(BaseModel):
    target_type: ShareTargetType
    target_id: str = Field(min_length=1, max_length=36)
    expires_in_days: int | None = Field(
        default=DEFAULT_SHARE_LINK_EXPIRATION_DAYS,
        ge=1,
        le=3650,
    )


def share_public_path(share_link: ShareLink) -> str:
    settings = get_settings()
    app_base_path = settings.normalized_app_base_path
    api_prefix = settings.api_v1_prefix.rstrip("/")
    return f"{app_base_path}{api_prefix}/shares/{share_link.token}"


def share_preview_image_path(share_link: ShareLink) -> str:
    return f"{share_public_path(share_link)}/preview.png"


def serialize_share_link(share_link: ShareLink) -> ShareLinkSummary:
    if share_link.target_type == "dashboard" and share_link.dashboard is not None:
        target_name = share_link.dashboard.name
        dashboard_name = share_link.dashboard.name
        widget_type = None
    elif share_link.target_type == "widget" and share_link.widget is not None:
        target_name = share_link.widget.title
        dashboard_name = share_link.widget.dashboard.name if share_link.widget.dashboard is not None else None
        widget_type = cast(WidgetType, share_link.widget.widget_type)
    else:
        target_name = "Shared item"
        dashboard_name = None
        widget_type = None

    return ShareLinkSummary(
        id=share_link.id,
        target_type=cast(ShareTargetType, share_link.target_type),
        target_name=target_name,
        dashboard_name=dashboard_name,
        widget_type=widget_type,
        status=share_link_status(share_link),
        created_at=share_link.created_at.isoformat(),
        expires_at=share_link.expires_at.isoformat() if share_link.expires_at is not None else None,
        revoked_at=share_link.revoked_at.isoformat() if share_link.revoked_at is not None else None,
        public_path=share_public_path(share_link),
        preview_image_path=share_preview_image_path(share_link),
    )
