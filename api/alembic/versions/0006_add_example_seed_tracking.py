"""add example seed tracking

Revision ID: 0006_add_example_seed_tracking
Revises: 0005_add_metrics_and_goals
Create Date: 2026-04-11 16:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_add_example_seed_tracking"
down_revision = "0005_add_metrics_and_goals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "example_seed_applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("revision", sa.String(length=100), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "revision", name="uq_example_seed_applications_user_revision"),
    )


def downgrade() -> None:
    op.drop_table("example_seed_applications")
