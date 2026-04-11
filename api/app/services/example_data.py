from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExampleSeedApplication, Goal, Metric, User
from app.services.goals import create_goal
from app.services.metrics import METRIC_TYPE_DATE, METRIC_TYPE_NUMBER, create_metric

EXAMPLE_SEED_REVISION_INITIAL_GOALS = "2026-04-11-initial-example-metrics-goals"

EXAMPLE_WEIGHT_METRIC_NAME = "Example Weight"
EXAMPLE_LAST_DRINK_METRIC_NAME = "Example Last Drink"
EXAMPLE_WEIGHT_GOAL_TITLE = "Reach 220 lbs"
EXAMPLE_LAST_DRINK_GOAL_TITLE = "Stay dry this month"


def utcnow() -> datetime:
    return datetime.now(UTC)


def example_goal_target_date(today: date) -> date:
    return today + timedelta(days=90)


def end_of_month(value: date) -> date:
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def get_metric_by_name_for_user(db: Session, *, user: User, name: str) -> Metric | None:
    statement = select(Metric).where(Metric.user_id == user.id, Metric.name == name)
    return db.scalar(statement)


def goal_exists_for_user(db: Session, *, user: User, title: str) -> bool:
    statement = select(Goal.id).where(Goal.user_id == user.id, Goal.title == title)
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


def upgrade_all_example_data_users(db: Session) -> None:
    users = list(db.scalars(select(User).where(User.is_example_data.is_(True))))
    for user in users:
        upgrade_example_data_for_user(db, user=user)
