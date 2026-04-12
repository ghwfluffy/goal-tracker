"""set share link timestamp defaults

Revision ID: 0024_share_link_timestamps
Revises: 0023_add_share_links
Create Date: 2026-04-12 12:58:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0024_share_link_timestamps"
down_revision = "0023_add_share_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "share_links",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        existing_nullable=False,
    )
    op.alter_column(
        "share_links",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "share_links",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )
    op.alter_column(
        "share_links",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )
