"""add checklist goals

Revision ID: 0025_add_checklist_goals
Revises: 0024_share_link_timestamps
Create Date: 2026-04-12 14:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0025_add_checklist_goals"
down_revision = "0024_share_link_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "goals",
        sa.Column("goal_type", sa.String(length=20), nullable=False, server_default="metric"),
    )
    op.alter_column(
        "goals",
        "metric_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )

    op.create_table(
        "goal_checklist_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("goal_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute("UPDATE goals SET goal_type = 'metric' WHERE goal_type IS NULL")
    op.alter_column(
        "goals",
        "goal_type",
        existing_type=sa.String(length=20),
        server_default=None,
    )
    op.alter_column(
        "goal_checklist_items",
        "display_order",
        existing_type=sa.Integer(),
        server_default=None,
    )


def downgrade() -> None:
    op.drop_table("goal_checklist_items")
    op.alter_column(
        "goals",
        "metric_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.drop_column("goals", "goal_type")
