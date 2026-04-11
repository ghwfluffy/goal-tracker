from __future__ import annotations

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, ExampleSeedApplication, Goal, Metric
from app.services.auth import create_user
from app.services.example_data import (
    EXAMPLE_SEED_REVISION_INITIAL_GOALS,
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

        upgrade_all_example_data_users(db)
        db.commit()

        metric_count = db.scalar(
            select(func.count()).select_from(Metric).where(Metric.user_id == user.id)
        )
        goal_count = db.scalar(
            select(func.count()).select_from(Goal).where(Goal.user_id == user.id)
        )
        applied_revision_count = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_INITIAL_GOALS,
            )
        )

        assert metric_count == 2
        assert goal_count == 2
        assert applied_revision_count == 1

        upgrade_all_example_data_users(db)
        db.commit()

        metric_count_after_second_run = db.scalar(
            select(func.count()).select_from(Metric).where(Metric.user_id == user.id)
        )
        goal_count_after_second_run = db.scalar(
            select(func.count()).select_from(Goal).where(Goal.user_id == user.id)
        )
        applied_revision_count_after_second_run = db.scalar(
            select(func.count())
            .select_from(ExampleSeedApplication)
            .where(
                ExampleSeedApplication.user_id == user.id,
                ExampleSeedApplication.revision == EXAMPLE_SEED_REVISION_INITIAL_GOALS,
            )
        )

        assert metric_count_after_second_run == 2
        assert goal_count_after_second_run == 2
        assert applied_revision_count_after_second_run == 1

    Base.metadata.drop_all(engine)
