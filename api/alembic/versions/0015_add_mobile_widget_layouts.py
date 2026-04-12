"""add mobile widget layouts

Revision ID: 0015_mobile_widget_layouts
Revises: 0014_add_goal_archiving
Create Date: 2026-04-12 10:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_mobile_widget_layouts"
down_revision = "0014_add_goal_archiving"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dashboard_widgets",
        sa.Column("mobile_grid_x", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("mobile_grid_y", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("mobile_grid_w", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("mobile_grid_h", sa.Integer(), nullable=False, server_default="4"),
    )
    op.execute(
        """
        UPDATE dashboard_widgets
        SET
            mobile_grid_x = 0,
            mobile_grid_y = grid_y,
            mobile_grid_w = 1,
            mobile_grid_h = grid_h
        """
    )
    op.alter_column("dashboard_widgets", "mobile_grid_x", server_default=None)
    op.alter_column("dashboard_widgets", "mobile_grid_y", server_default=None)
    op.alter_column("dashboard_widgets", "mobile_grid_w", server_default=None)
    op.alter_column("dashboard_widgets", "mobile_grid_h", server_default=None)


def downgrade() -> None:
    op.drop_column("dashboard_widgets", "mobile_grid_h")
    op.drop_column("dashboard_widgets", "mobile_grid_w")
    op.drop_column("dashboard_widgets", "mobile_grid_y")
    op.drop_column("dashboard_widgets", "mobile_grid_x")
