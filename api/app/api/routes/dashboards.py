from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.api.schemas.dashboards import (
    CreateDashboardRequest,
    CreateWidgetRequest,
    DashboardListResponse,
    DashboardSummary,
    UpdateDashboardRequest,
    UpdateWidgetRequest,
    WidgetSummary,
    serialize_dashboard,
    serialize_widget,
)
from app.db import User, get_db
from app.services.dashboard_layout import DashboardError
from app.services.dashboards import (
    DashboardNotFoundError,
    DashboardWidgetNotFoundError,
    create_dashboard,
    create_dashboard_widget,
    delete_dashboard,
    delete_dashboard_widget,
    get_dashboard_for_user,
    get_dashboard_widget_for_user,
    list_dashboards_for_user,
    update_dashboard,
    update_dashboard_widget,
)
from app.services.goals import GoalNotFoundError, get_goal_for_user
from app.services.metrics import MetricNotFoundError, get_metric_for_user

router = APIRouter(prefix="/dashboards")


@router.get("", response_model=DashboardListResponse)
def get_dashboards(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardListResponse:
    dashboards = list_dashboards_for_user(db, user)
    return DashboardListResponse(
        dashboards=[serialize_dashboard(dashboard, user=user) for dashboard in dashboards]
    )


@router.post("", response_model=DashboardSummary, status_code=status.HTTP_201_CREATED)
def post_dashboard(
    payload: CreateDashboardRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummary:
    try:
        dashboard = create_dashboard(
            db,
            user=user,
            name=payload.name,
            description=payload.description,
            make_default=payload.make_default,
        )
        db.commit()
    except DashboardError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_dashboard(dashboard, user=user)


@router.patch("/{dashboard_id}", response_model=DashboardSummary)
def patch_dashboard(
    dashboard_id: str,
    payload: UpdateDashboardRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummary:
    try:
        dashboard = get_dashboard_for_user(db, user=user, dashboard_id=dashboard_id)
        updated_dashboard = update_dashboard(
            db,
            dashboard=dashboard,
            user=user,
            name=payload.name,
            description=payload.description,
            make_default=payload.make_default,
        )
        db.commit()
    except DashboardNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DashboardError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_dashboard(updated_dashboard, user=user)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_dashboard(
    dashboard_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        dashboard = get_dashboard_for_user(db, user=user, dashboard_id=dashboard_id)
        delete_dashboard(db, dashboard=dashboard, user=user)
        db.commit()
    except DashboardNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{dashboard_id}/widgets",
    response_model=WidgetSummary,
    status_code=status.HTTP_201_CREATED,
)
def post_dashboard_widget(
    dashboard_id: str,
    payload: CreateWidgetRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WidgetSummary:
    try:
        dashboard = get_dashboard_for_user(db, user=user, dashboard_id=dashboard_id)
        metric = (
            get_metric_for_user(db, user=user, metric_id=payload.metric_id)
            if payload.metric_id is not None
            else None
        )
        goal = (
            get_goal_for_user(db, user=user, goal_id=payload.goal_id) if payload.goal_id is not None else None
        )
        widget = create_dashboard_widget(
            db,
            dashboard=dashboard,
            user=user,
            title=payload.title,
            widget_type=payload.widget_type,
            metric=metric,
            goal=goal,
            rolling_window_days=payload.rolling_window_days,
            forecast_algorithm=payload.forecast_algorithm,
            grid_x=payload.grid_x,
            grid_y=payload.grid_y,
            grid_w=payload.grid_w,
            grid_h=payload.grid_h,
        )
        db.commit()
    except DashboardNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetricNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoalNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DashboardError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_widget(widget)


@router.patch("/{dashboard_id}/widgets/{widget_id}", response_model=WidgetSummary)
def patch_dashboard_widget(
    dashboard_id: str,
    widget_id: str,
    payload: UpdateWidgetRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WidgetSummary:
    try:
        dashboard = get_dashboard_for_user(db, user=user, dashboard_id=dashboard_id)
        widget = get_dashboard_widget_for_user(
            db,
            user=user,
            dashboard_id=dashboard_id,
            widget_id=widget_id,
        )
        updated_widget = update_dashboard_widget(
            db,
            dashboard=dashboard,
            widget=widget,
            user=user,
            title=payload.title,
            rolling_window_days=payload.rolling_window_days,
            forecast_algorithm=payload.forecast_algorithm,
            layout_mode=payload.layout_mode,
            grid_x=payload.grid_x,
            grid_y=payload.grid_y,
            grid_w=payload.grid_w,
            grid_h=payload.grid_h,
        )
        db.commit()
    except DashboardNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DashboardWidgetNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DashboardError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_widget(updated_widget)


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_dashboard_widget(
    dashboard_id: str,
    widget_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        widget = get_dashboard_widget_for_user(
            db,
            user=user,
            dashboard_id=dashboard_id,
            widget_id=widget_id,
        )
        delete_dashboard_widget(db, widget=widget)
        db.commit()
    except DashboardWidgetNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
