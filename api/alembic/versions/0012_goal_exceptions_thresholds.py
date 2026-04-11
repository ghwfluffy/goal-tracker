"""add goal exception dates and thresholds

Revision ID: 0012_goal_exceptions_thresholds
Revises: 0011_add_dashboard_widget_layout
Create Date: 2026-04-11 22:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_goal_exceptions_thresholds"
down_revision = "0011_add_dashboard_widget_layout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "goals",
        sa.Column("success_threshold_percent", sa.Numeric(5, 2), nullable=True),
    )
    op.create_table(
        "goal_exception_dates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("goal_id", sa.String(length=36), nullable=False),
        sa.Column("exception_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", "exception_date", name="uq_goal_exception_dates_goal_date"),
    )


def downgrade() -> None:
    op.drop_table("goal_exception_dates")
    op.drop_column("goals", "success_threshold_percent")
