from __future__ import annotations

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.api.schemas.dashboards import serialize_dashboard, serialize_widget
from app.api.schemas.share_links import (
    CreateShareLinkRequest,
    ShareLinkListResponse,
    ShareLinkSummary,
    serialize_share_link,
    share_preview_image_path,
    share_public_path,
)
from app.core.config import Settings, get_settings
from app.db import User, get_db
from app.services.share_links import (
    ShareLinkAccessError,
    ShareLinkError,
    ShareLinkNotFoundError,
    create_share_link,
    get_public_share_link,
    get_share_link_for_user,
    list_share_links_for_user,
    revoke_share_link,
)
from app.services.share_rendering import (
    render_dashboard_preview_png,
    render_dashboard_share_page,
    render_widget_preview_png,
    render_widget_share_page,
)

router = APIRouter()


def _public_share_response_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Expires": "0",
        "Pragma": "no-cache",
        "X-Robots-Tag": "noindex, nofollow",
    }


def _absolute_share_url(settings: Settings, path: str, *, cache_bust: str | None = None) -> str:
    query = urlencode({"t": cache_bust}) if cache_bust is not None else ""
    suffix = f"?{query}" if query != "" else ""
    return f"{settings.public_origin}{path}{suffix}"


@router.get("/share-links", response_model=ShareLinkListResponse)
def get_share_links(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ShareLinkListResponse:
    share_links = list_share_links_for_user(db, user)
    return ShareLinkListResponse(share_links=[serialize_share_link(share_link) for share_link in share_links])


@router.post("/share-links", response_model=ShareLinkSummary, status_code=status.HTTP_201_CREATED)
def post_share_link(
    payload: CreateShareLinkRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ShareLinkSummary:
    try:
        share_link = create_share_link(
            db,
            user=user,
            target_type=payload.target_type,
            target_id=payload.target_id,
            expires_in_days=payload.expires_in_days,
        )
        db.commit()
    except ShareLinkNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ShareLinkError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_share_link(share_link)


@router.delete("/share-links/{share_link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_share_link(
    share_link_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        share_link = get_share_link_for_user(db, user=user, share_link_id=share_link_id)
        revoke_share_link(db, share_link=share_link)
        db.commit()
    except ShareLinkNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/shares/{token}", response_class=HTMLResponse)
def get_share_page(
    token: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    try:
        share_link = get_public_share_link(db, token=token)
    except ShareLinkAccessError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    cache_bust = request.query_params.get("t")
    share_url = _absolute_share_url(settings, share_public_path(share_link), cache_bust=cache_bust)
    preview_url = _absolute_share_url(
        settings,
        share_preview_image_path(share_link),
        cache_bust=cache_bust,
    )

    if share_link.target_type == "widget" and share_link.widget is not None:
        widget_summary = serialize_widget(share_link.widget)
        content = render_widget_share_page(
            widget_summary,
            dashboard_name=(
                share_link.widget.dashboard.name if share_link.widget.dashboard is not None else None
            ),
            profile_timezone=share_link.user.timezone,
            share_url=share_url,
            preview_url=preview_url,
        )
    elif share_link.target_type == "dashboard" and share_link.dashboard is not None:
        dashboard_summary = serialize_dashboard(share_link.dashboard, user=share_link.dashboard.user)
        content = render_dashboard_share_page(
            dashboard_summary,
            profile_timezone=share_link.user.timezone,
            share_url=share_url,
            preview_url=preview_url,
        )
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link was not found.")

    return HTMLResponse(content=content, headers=_public_share_response_headers())


@router.get("/shares/{token}/preview.png")
def get_share_preview(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        share_link = get_public_share_link(db, token=token)
    except ShareLinkAccessError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if share_link.target_type == "widget" and share_link.widget is not None:
        widget_summary = serialize_widget(share_link.widget)
        png_bytes = render_widget_preview_png(
            widget_summary,
            dashboard_name=(
                share_link.widget.dashboard.name if share_link.widget.dashboard is not None else None
            ),
            profile_timezone=share_link.user.timezone,
        )
    elif share_link.target_type == "dashboard" and share_link.dashboard is not None:
        dashboard_summary = serialize_dashboard(share_link.dashboard, user=share_link.dashboard.user)
        png_bytes = render_dashboard_preview_png(
            dashboard_summary,
            profile_timezone=share_link.user.timezone,
        )
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link was not found.")

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers=_public_share_response_headers(),
    )
