"""add login lockouts

Revision ID: 0021_add_login_lockouts
Revises: 0020_add_metric_update_type
Create Date: 2026-04-12 11:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021_add_login_lockouts"
down_revision = "0020_add_metric_update_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("failed_login_attempt_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE users SET failed_login_attempt_count = 0 WHERE failed_login_attempt_count IS NULL")
    op.alter_column("users", "failed_login_attempt_count", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempt_count")
