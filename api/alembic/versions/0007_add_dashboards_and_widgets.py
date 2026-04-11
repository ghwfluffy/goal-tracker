"""add dashboards and widgets

Revision ID: 0007_add_dashboards_and_widgets
Revises: 0006_add_example_seed_tracking
Create Date: 2026-04-11 18:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_add_dashboards_and_widgets"
down_revision = "0006_add_example_seed_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "dashboard_widgets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("dashboard_id", sa.String(length=36), nullable=False),
        sa.Column("metric_id", sa.String(length=36), nullable=True),
        sa.Column("goal_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("widget_type", sa.String(length=40), nullable=False),
        sa.Column("rolling_window_days", sa.Integer(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["metric_id"], ["metrics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("users", sa.Column("default_dashboard_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_users_default_dashboard_id_dashboards",
        "users",
        "dashboards",
        ["default_dashboard_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_default_dashboard_id_dashboards", "users", type_="foreignkey")
    op.drop_column("users", "default_dashboard_id")
    op.drop_table("dashboard_widgets")
    op.drop_table("dashboards")
