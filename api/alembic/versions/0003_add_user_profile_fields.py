from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_add_user_profile_fields"
down_revision = "0002_add_auth_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("avatar_png", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_updated_at")
    op.drop_column("users", "avatar_png")
    op.drop_column("users", "display_name")
