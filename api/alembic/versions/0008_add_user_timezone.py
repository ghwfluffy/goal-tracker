"""add user timezone

Revision ID: 0008_add_user_timezone
Revises: 0007_add_dashboards_and_widgets
Create Date: 2026-04-11 18:50:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_add_user_timezone"
down_revision = "0007_add_dashboards_and_widgets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "timezone",
            sa.String(length=100),
            nullable=False,
            server_default="America/Chicago",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "timezone")
