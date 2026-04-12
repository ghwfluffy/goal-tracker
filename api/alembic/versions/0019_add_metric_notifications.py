"""add metric notifications

Revision ID: 0019_add_metric_notifications
Revises: 0018_mobile_summary_tight
Create Date: 2026-04-12 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0019_add_metric_notifications"
down_revision = "0018_mobile_summary_tight"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "metrics",
        sa.Column("reminder_time_1", sa.Time(), nullable=True),
    )
    op.add_column(
        "metrics",
        sa.Column("reminder_time_2", sa.Time(), nullable=True),
    )
    op.execute("UPDATE metrics SET reminder_time_1 = '06:00:00' WHERE reminder_time_1 IS NULL")
    op.alter_column("metrics", "reminder_time_1", nullable=False)

    op.create_table(
        "metric_notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("metric_id", sa.String(length=36), nullable=False),
        sa.Column("notification_date", sa.Date(), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["metric_id"], ["metrics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "metric_id",
            "notification_date",
            "slot_index",
            name="uq_metric_notifications_metric_date_slot",
        ),
    )


def downgrade() -> None:
    op.drop_table("metric_notifications")
    op.drop_column("metrics", "reminder_time_2")
    op.drop_column("metrics", "reminder_time_1")
