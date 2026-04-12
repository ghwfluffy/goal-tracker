"""add share links

Revision ID: 0023_add_share_links
Revises: 0022_add_backup_operations
Create Date: 2026-04-12 12:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0023_add_share_links"
down_revision = "0022_add_backup_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "share_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("dashboard_id", sa.String(length=36), nullable=True),
        sa.Column("widget_id", sa.String(length=36), nullable=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(dashboard_id IS NOT NULL AND widget_id IS NULL) "
            "OR (dashboard_id IS NULL AND widget_id IS NOT NULL)",
            name="ck_share_links_single_target",
        ),
        sa.ForeignKeyConstraint(["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["widget_id"], ["dashboard_widgets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )


def downgrade() -> None:
    op.drop_table("share_links")
