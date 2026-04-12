"""add metric update type

Revision ID: 0020_add_metric_update_type
Revises: 0019_add_metric_notifications
Create Date: 2026-04-12 10:50:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_add_metric_update_type"
down_revision = "0019_add_metric_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "metrics",
        sa.Column("update_type", sa.String(length=20), nullable=True),
    )
    op.execute("UPDATE metrics SET update_type = 'success' WHERE update_type IS NULL")
    op.alter_column("metrics", "update_type", nullable=False)


def downgrade() -> None:
    op.drop_column("metrics", "update_type")
