"""add goal calendar widgets

Revision ID: 0026_add_goal_calendar_widgets
Revises: 0025_add_checklist_goals
Create Date: 2026-04-13 20:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0026_add_goal_calendar_widgets"
down_revision = "0025_add_checklist_goals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dashboard_widgets", sa.Column("goal_scope", sa.String(length=20), nullable=True))
    op.add_column("dashboard_widgets", sa.Column("calendar_period", sa.String(length=30), nullable=True))

    op.create_table(
        "dashboard_widget_goals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("widget_id", sa.String(length=36), nullable=False),
        sa.Column("goal_id", sa.String(length=36), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["widget_id"], ["dashboard_widgets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("widget_id", "goal_id", name="uq_dashboard_widget_goals_widget_goal"),
    )

    op.alter_column(
        "dashboard_widget_goals",
        "display_order",
        existing_type=sa.Integer(),
        server_default=None,
    )


def downgrade() -> None:
    op.drop_table("dashboard_widget_goals")
    op.drop_column("dashboard_widgets", "calendar_period")
    op.drop_column("dashboard_widgets", "goal_scope")
