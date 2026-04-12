from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Dashboard, DashboardWidget, ExampleSeedApplication, Goal, Metric
from app.main import create_app
from app.services.auth import create_user
from app.services.example_data import (
    EXAMPLE_DASHBOARD_NAME,
    EXAMPLE_LAST_DRINK_HISTORY_WIDGET_TITLE,
    EXAMPLE_SEED_REVISION_EXPANDED_HISTORY,
    EXAMPLE_SEED_REVISION_INITIAL_DASHBOARD,
    EXAMPLE_SEED_REVISION_INITIAL_GOALS,
    EXAMPLE_WEIGHT_GOAL_SUMMARY_WIDGET_TITLE,
    EXAMPLE_WEIGHT_SUMMARY_WIDGET_TITLE,
    apply_initial_example_metrics_and_goals,
    mark_example_seed_revision_applied,
    upgrade_all_example_data_users,
)


def test_example_data_upgrader_backfills_existing_accounts_without_duplicates() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        future=True,
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)

    with session_factory() as db:
        user = create_user(
            db,
            username="legacy-demo",
            password="supersafepassword",
            is_admin=False,
            is_example_data=True,
        )
        db.commit()

        assert db.scalar(select(Metric).where(Metric.user_id == user.id)) is None
        assert db.scalar(select(Goal).where(Goal.user_id == user.id)) is None
        assert db.scalar(select(Dashboard).where(Dashboard.user_id == user.id)) is None

        upgrade_all_example_data_users(db)
        db.commit()

        metric_count = db.scalar(select(func.count()).select_from(Metric).where(Metric.user_id == user.id))
        goal_count = db.scalar(select(func.count()).select_from(Goal).where(Goal.user_id == user.id))
        dashboard_count = db.scalar(
            select(func.count()).select_from(Dashboard).where(Dashboard.user_id == user.id)
        )
        widget_count = db.scalar(
            select(func.count())
            .select_from(DashboardWidget)
            .join(Dashboard)
            .where(Dashboard.user_id == user.id)
        )
        applied_revision_count = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_INITIAL_GOALS,
            )
        )
        applied_dashboard_revision_count = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_INITIAL_DASHBOARD,
            )
        )
        applied_history_revision_count = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_EXPANDED_HISTORY,
            )
        )
        dashboard = db.scalar(select(Dashboard).where(Dashboard.user_id == user.id))
        weight_metric = db.scalar(
            select(Metric).where(Metric.user_id == user.id, Metric.name == "Example Weight")
        )
        last_drink_metric = db.scalar(
            select(Metric).where(Metric.user_id == user.id, Metric.name == "Example Last Drink")
        )
        widget_titles = set(
            db.scalars(select(DashboardWidget.title).join(Dashboard).where(Dashboard.user_id == user.id))
        )

        assert metric_count == 2
        assert goal_count == 2
        assert dashboard_count == 1
        assert widget_count == 6
        assert applied_revision_count == 1
        assert applied_dashboard_revision_count == 1
        assert applied_history_revision_count == 1
        assert dashboard is not None
        assert dashboard.name == EXAMPLE_DASHBOARD_NAME
        assert user.default_dashboard_id == dashboard.id
        assert weight_metric is not None
        assert len(weight_metric.entries) == 7
        assert last_drink_metric is not None
        assert len(last_drink_metric.entries) == 6
        assert widget_titles == {
            "Weight Trend",
            "Weight Goal Progress",
            "Last Drink Snapshot",
            EXAMPLE_WEIGHT_SUMMARY_WIDGET_TITLE,
            EXAMPLE_WEIGHT_GOAL_SUMMARY_WIDGET_TITLE,
            EXAMPLE_LAST_DRINK_HISTORY_WIDGET_TITLE,
        }

        upgrade_all_example_data_users(db)
        db.commit()

        metric_count_after_second_run = db.scalar(
            select(func.count()).select_from(Metric).where(Metric.user_id == user.id)
        )
        goal_count_after_second_run = db.scalar(
            select(func.count()).select_from(Goal).where(Goal.user_id == user.id)
        )
        dashboard_count_after_second_run = db.scalar(
            select(func.count()).select_from(Dashboard).where(Dashboard.user_id == user.id)
        )
        widget_count_after_second_run = db.scalar(
            select(func.count())
            .select_from(DashboardWidget)
            .join(Dashboard)
            .where(Dashboard.user_id == user.id)
        )
        applied_revision_count_after_second_run = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_INITIAL_GOALS,
            )
        )
        applied_dashboard_revision_count_after_second_run = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_INITIAL_DASHBOARD,
            )
        )
        applied_history_revision_count_after_second_run = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_EXPANDED_HISTORY,
            )
        )

        assert metric_count_after_second_run == 2
        assert goal_count_after_second_run == 2
        assert dashboard_count_after_second_run == 1
        assert widget_count_after_second_run == 6
        assert applied_revision_count_after_second_run == 1
        assert applied_dashboard_revision_count_after_second_run == 1
        assert applied_history_revision_count_after_second_run == 1

    Base.metadata.drop_all(engine)


def test_startup_upgrades_existing_example_accounts() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        future=True,
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)

    with session_factory() as db:
        user = create_user(
            db,
            username="startup-demo",
            password="supersafepassword",
            is_admin=False,
            is_example_data=True,
        )
        apply_initial_example_metrics_and_goals(db, user=user)
        mark_example_seed_revision_applied(
            db,
            user=user,
            revision=EXAMPLE_SEED_REVISION_INITIAL_GOALS,
        )
        db.commit()

        assert db.scalar(select(Dashboard).where(Dashboard.user_id == user.id)) is None

    app = create_app(session_factory=session_factory)

    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200

    with session_factory() as db:
        dashboard = db.scalar(select(Dashboard).where(Dashboard.user_id == user.id))
        applied_dashboard_revision_count = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_INITIAL_DASHBOARD,
            )
        )
        applied_history_revision_count = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_EXPANDED_HISTORY,
            )
        )

        assert dashboard is not None
        assert dashboard.name == EXAMPLE_DASHBOARD_NAME
        assert applied_dashboard_revision_count == 1
        assert applied_history_revision_count == 1

    Base.metadata.drop_all(engine)
