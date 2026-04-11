"""add metric archiving

Revision ID: 0010_add_metric_archiving
Revises: 0009_add_number_metrics
Create Date: 2026-04-11 17:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_add_metric_archiving"
down_revision = "0009_add_number_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("metrics", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("metrics", "archived_at")
