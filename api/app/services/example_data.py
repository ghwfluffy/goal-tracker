from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Dashboard,
    DashboardWidget,
    ExampleSeedApplication,
    Goal,
    Metric,
    MetricEntry,
    User,
)
from app.services.dashboards import (
    WIDGET_TYPE_GOAL_PROGRESS,
    WIDGET_TYPE_GOAL_SUMMARY,
    WIDGET_TYPE_METRIC_HISTORY,
    WIDGET_TYPE_METRIC_SUMMARY,
    create_dashboard,
    create_dashboard_widget,
)
from app.services.goals import create_goal
from app.services.metrics import (
    METRIC_TYPE_DATE,
    METRIC_TYPE_NUMBER,
    create_metric,
    create_metric_entry,
)

EXAMPLE_SEED_REVISION_INITIAL_GOALS = "2026-04-11-initial-example-metrics-goals"
EXAMPLE_SEED_REVISION_INITIAL_DASHBOARD = "2026-04-11-initial-example-dashboard"
EXAMPLE_SEED_REVISION_EXPANDED_HISTORY = "2026-04-11-expanded-example-history-and-widgets"

EXAMPLE_WEIGHT_METRIC_NAME = "Example Weight"
EXAMPLE_LAST_DRINK_METRIC_NAME = "Example Last Drink"
EXAMPLE_WEIGHT_GOAL_TITLE = "Reach 220 lbs"
EXAMPLE_LAST_DRINK_GOAL_TITLE = "Stay dry this month"
EXAMPLE_DASHBOARD_NAME = "Example Dashboard"
EXAMPLE_DASHBOARD_DESCRIPTION = "Starter dashboard seeded for example-data accounts."
EXAMPLE_WEIGHT_TREND_WIDGET_TITLE = "Weight Trend"
EXAMPLE_WEIGHT_GOAL_WIDGET_TITLE = "Weight Goal Progress"
EXAMPLE_LAST_DRINK_WIDGET_TITLE = "Last Drink Snapshot"
EXAMPLE_WEIGHT_SUMMARY_WIDGET_TITLE = "Weight Snapshot"
EXAMPLE_WEIGHT_GOAL_SUMMARY_WIDGET_TITLE = "Weight Goal Summary"
EXAMPLE_LAST_DRINK_HISTORY_WIDGET_TITLE = "Last Drink History"


def utcnow() -> datetime:
    return datetime.now(UTC)


def example_goal_target_date(today: date) -> date:
    return today + timedelta(days=90)


def end_of_month(value: date) -> date:
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def utc_datetime(
    value: date,
    *,
    hour: int = 12,
    minute: int = 0,
) -> datetime:
    return datetime(value.year, value.month, value.day, hour, minute, tzinfo=UTC)


def get_metric_by_name_for_user(db: Session, *, user: User, name: str) -> Metric | None:
    statement = select(Metric).where(Metric.user_id == user.id, Metric.name == name)
    return db.scalar(statement)


def goal_exists_for_user(db: Session, *, user: User, title: str) -> bool:
    statement = select(Goal.id).where(Goal.user_id == user.id, Goal.title == title)
    return db.scalar(statement) is not None


def get_goal_by_title_for_user(db: Session, *, user: User, title: str) -> Goal | None:
    statement = select(Goal).where(Goal.user_id == user.id, Goal.title == title)
    return db.scalar(statement)


def get_dashboard_by_name_for_user(db: Session, *, user: User, name: str) -> Dashboard | None:
    statement = select(Dashboard).where(Dashboard.user_id == user.id, Dashboard.name == name)
    return db.scalar(statement)


def dashboard_widget_exists(
    db: Session,
    *,
    dashboard: Dashboard,
    title: str,
) -> bool:
    statement = select(DashboardWidget.id).where(
        DashboardWidget.dashboard_id == dashboard.id,
        DashboardWidget.title == title,
    )
    return db.scalar(statement) is not None


def metric_entry_exists_at(
    db: Session,
    *,
    metric: Metric,
    recorded_at: datetime,
) -> bool:
    statement = select(MetricEntry.id).where(
        MetricEntry.metric_id == metric.id,
        MetricEntry.recorded_at == recorded_at,
    )
    return db.scalar(statement) is not None


def is_example_seed_revision_applied(db: Session, *, user: User, revision: str) -> bool:
    statement = select(ExampleSeedApplication.id).where(
        ExampleSeedApplication.user_id == user.id,
        ExampleSeedApplication.revision == revision,
    )
    return db.scalar(statement) is not None


def mark_example_seed_revision_applied(db: Session, *, user: User, revision: str) -> None:
    if is_example_seed_revision_applied(db, user=user, revision=revision):
        return

    db.add(
        ExampleSeedApplication(
            id=str(uuid4()),
            user_id=user.id,
            revision=revision,
        )
    )
    db.flush()


def apply_initial_example_metrics_and_goals(db: Session, *, user: User) -> None:
    today = utcnow().date()
    yesterday = today - timedelta(days=1)

    weight_metric = get_metric_by_name_for_user(db, user=user, name=EXAMPLE_WEIGHT_METRIC_NAME)
    if weight_metric is None:
        weight_metric = create_metric(
            db,
            user=user,
            name=EXAMPLE_WEIGHT_METRIC_NAME,
            metric_type=METRIC_TYPE_NUMBER,
            decimal_places=1,
            unit_label="lbs",
            initial_number_value=245,
        )

    if not goal_exists_for_user(db, user=user, title=EXAMPLE_WEIGHT_GOAL_TITLE):
        create_goal(
            db,
            user=user,
            metric=weight_metric,
            title=EXAMPLE_WEIGHT_GOAL_TITLE,
            description="Example seeded goal tied to the example weight metric.",
            start_date=today,
            target_date=example_goal_target_date(today),
            target_value_number=220,
            target_value_date=None,
        )

    last_drink_metric = get_metric_by_name_for_user(
        db,
        user=user,
        name=EXAMPLE_LAST_DRINK_METRIC_NAME,
    )
    if last_drink_metric is None:
        last_drink_metric = create_metric(
            db,
            user=user,
            name=EXAMPLE_LAST_DRINK_METRIC_NAME,
            metric_type=METRIC_TYPE_DATE,
            unit_label=None,
            initial_date_value=yesterday,
        )

    if not goal_exists_for_user(db, user=user, title=EXAMPLE_LAST_DRINK_GOAL_TITLE):
        create_goal(
            db,
            user=user,
            metric=last_drink_metric,
            title=EXAMPLE_LAST_DRINK_GOAL_TITLE,
            description="Example seeded goal tied to the example last-drink metric.",
            start_date=today,
            target_date=end_of_month(today),
            target_value_number=None,
            target_value_date=None,
        )


def apply_initial_example_dashboard(db: Session, *, user: User) -> None:
    apply_initial_example_metrics_and_goals(db, user=user)

    weight_metric = get_metric_by_name_for_user(db, user=user, name=EXAMPLE_WEIGHT_METRIC_NAME)
    weight_goal = get_goal_by_title_for_user(db, user=user, title=EXAMPLE_WEIGHT_GOAL_TITLE)
    last_drink_metric = get_metric_by_name_for_user(
        db,
        user=user,
        name=EXAMPLE_LAST_DRINK_METRIC_NAME,
    )
    if weight_metric is None or weight_goal is None or last_drink_metric is None:
        return

    dashboard = get_dashboard_by_name_for_user(db, user=user, name=EXAMPLE_DASHBOARD_NAME)
    if dashboard is None:
        dashboard = create_dashboard(
            db,
            user=user,
            name=EXAMPLE_DASHBOARD_NAME,
            description=EXAMPLE_DASHBOARD_DESCRIPTION,
        )
    elif user.default_dashboard_id is None:
        user.default_dashboard_id = dashboard.id
        db.flush()

    if not dashboard_widget_exists(
        db,
        dashboard=dashboard,
        title=EXAMPLE_WEIGHT_TREND_WIDGET_TITLE,
    ):
        create_dashboard_widget(
            db,
            dashboard=dashboard,
            user=user,
            title=EXAMPLE_WEIGHT_TREND_WIDGET_TITLE,
            widget_type=WIDGET_TYPE_METRIC_HISTORY,
            metric=weight_metric,
            rolling_window_days=365,
        )

    if not dashboard_widget_exists(
        db,
        dashboard=dashboard,
        title=EXAMPLE_WEIGHT_GOAL_WIDGET_TITLE,
    ):
        create_dashboard_widget(
            db,
            dashboard=dashboard,
            user=user,
            title=EXAMPLE_WEIGHT_GOAL_WIDGET_TITLE,
            widget_type=WIDGET_TYPE_GOAL_PROGRESS,
            goal=weight_goal,
            rolling_window_days=365,
        )

    if not dashboard_widget_exists(
        db,
        dashboard=dashboard,
        title=EXAMPLE_LAST_DRINK_WIDGET_TITLE,
    ):
        create_dashboard_widget(
            db,
            dashboard=dashboard,
            user=user,
            title=EXAMPLE_LAST_DRINK_WIDGET_TITLE,
            widget_type=WIDGET_TYPE_METRIC_SUMMARY,
            metric=last_drink_metric,
            rolling_window_days=90,
        )


def apply_expanded_example_history_and_widgets(db: Session, *, user: User) -> None:
    apply_initial_example_dashboard(db, user=user)

    today = utcnow().date()
    weight_metric = get_metric_by_name_for_user(db, user=user, name=EXAMPLE_WEIGHT_METRIC_NAME)
    weight_goal = get_goal_by_title_for_user(db, user=user, title=EXAMPLE_WEIGHT_GOAL_TITLE)
    last_drink_metric = get_metric_by_name_for_user(
        db,
        user=user,
        name=EXAMPLE_LAST_DRINK_METRIC_NAME,
    )
    dashboard = get_dashboard_by_name_for_user(db, user=user, name=EXAMPLE_DASHBOARD_NAME)
    if (
        weight_metric is None
        or weight_goal is None
        or last_drink_metric is None
        or dashboard is None
    ):
        return

    weight_history = [
        (today - timedelta(days=35), 248.4),
        (today - timedelta(days=28), 246.9),
        (today - timedelta(days=21), 244.8),
        (today - timedelta(days=14), 242.2),
        (today - timedelta(days=7), 239.6),
        (today - timedelta(days=3), 237.8),
    ]
    for recorded_date, number_value in weight_history:
        recorded_at = utc_datetime(recorded_date, hour=7, minute=30)
        if metric_entry_exists_at(db, metric=weight_metric, recorded_at=recorded_at):
            continue
        create_metric_entry(
            db,
            metric=weight_metric,
            number_value=number_value,
            date_value=None,
            recorded_at=recorded_at,
        )

    last_drink_history = [
        (today - timedelta(days=26), today - timedelta(days=27)),
        (today - timedelta(days=17), today - timedelta(days=18)),
        (today - timedelta(days=11), today - timedelta(days=12)),
        (today - timedelta(days=6), today - timedelta(days=7)),
        (today - timedelta(days=1), today - timedelta(days=2)),
    ]
    for recorded_date, date_value in last_drink_history:
        recorded_at = utc_datetime(recorded_date, hour=21, minute=0)
        if metric_entry_exists_at(db, metric=last_drink_metric, recorded_at=recorded_at):
            continue
        create_metric_entry(
            db,
            metric=last_drink_metric,
            number_value=None,
            date_value=date_value,
            recorded_at=recorded_at,
        )

    if not dashboard_widget_exists(
        db,
        dashboard=dashboard,
        title=EXAMPLE_WEIGHT_SUMMARY_WIDGET_TITLE,
    ):
        create_dashboard_widget(
            db,
            dashboard=dashboard,
            user=user,
            title=EXAMPLE_WEIGHT_SUMMARY_WIDGET_TITLE,
            widget_type=WIDGET_TYPE_METRIC_SUMMARY,
            metric=weight_metric,
            rolling_window_days=90,
        )

    if not dashboard_widget_exists(
        db,
        dashboard=dashboard,
        title=EXAMPLE_WEIGHT_GOAL_SUMMARY_WIDGET_TITLE,
    ):
        create_dashboard_widget(
            db,
            dashboard=dashboard,
            user=user,
            title=EXAMPLE_WEIGHT_GOAL_SUMMARY_WIDGET_TITLE,
            widget_type=WIDGET_TYPE_GOAL_SUMMARY,
            goal=weight_goal,
            rolling_window_days=365,
        )

    if not dashboard_widget_exists(
        db,
        dashboard=dashboard,
        title=EXAMPLE_LAST_DRINK_HISTORY_WIDGET_TITLE,
    ):
        create_dashboard_widget(
            db,
            dashboard=dashboard,
            user=user,
            title=EXAMPLE_LAST_DRINK_HISTORY_WIDGET_TITLE,
            widget_type=WIDGET_TYPE_METRIC_HISTORY,
            metric=last_drink_metric,
            rolling_window_days=90,
        )


def upgrade_example_data_for_user(db: Session, *, user: User) -> None:
    if not user.is_example_data:
        return

    if not is_example_seed_revision_applied(
        db,
        user=user,
        revision=EXAMPLE_SEED_REVISION_INITIAL_GOALS,
    ):
        apply_initial_example_metrics_and_goals(db, user=user)
        mark_example_seed_revision_applied(
            db,
            user=user,
            revision=EXAMPLE_SEED_REVISION_INITIAL_GOALS,
        )

    if not is_example_seed_revision_applied(
        db,
        user=user,
        revision=EXAMPLE_SEED_REVISION_INITIAL_DASHBOARD,
    ):
        apply_initial_example_dashboard(db, user=user)
        mark_example_seed_revision_applied(
            db,
            user=user,
            revision=EXAMPLE_SEED_REVISION_INITIAL_DASHBOARD,
        )

    if not is_example_seed_revision_applied(
        db,
        user=user,
        revision=EXAMPLE_SEED_REVISION_EXPANDED_HISTORY,
    ):
        apply_expanded_example_history_and_widgets(db, user=user)
        mark_example_seed_revision_applied(
            db,
            user=user,
            revision=EXAMPLE_SEED_REVISION_EXPANDED_HISTORY,
        )


def upgrade_all_example_data_users(db: Session) -> None:
    users = list(db.scalars(select(User).where(User.is_example_data.is_(True))))
    for user in users:
        upgrade_example_data_for_user(db, user=user)
