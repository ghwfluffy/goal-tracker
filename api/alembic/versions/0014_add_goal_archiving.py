"""add goal archiving

Revision ID: 0014_add_goal_archiving
Revises: 0013_widget_forecast_algo
Create Date: 2026-04-12 10:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_add_goal_archiving"
down_revision = "0013_widget_forecast_algo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("goals", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("goals", "archived_at")
