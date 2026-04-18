"""add mobile widget order

Revision ID: 0027_add_mobile_widget_order
Revises: 0026_add_goal_calendar_widgets
Create Date: 2026-04-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0027_add_mobile_widget_order"
down_revision = "0026_add_goal_calendar_widgets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dashboard_widgets",
        sa.Column("mobile_order", sa.Numeric(18, 6), nullable=True),
    )
    op.execute("UPDATE dashboard_widgets SET mobile_order = mobile_grid_y")
    op.alter_column("dashboard_widgets", "mobile_order", nullable=False)


def downgrade() -> None:
    op.drop_column("dashboard_widgets", "mobile_order")
