"""add dashboard widget forecast algorithm

Revision ID: 0013_widget_forecast_algo
Revises: 0012_goal_exceptions_thresholds
Create Date: 2026-04-11 23:25:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_widget_forecast_algo"
down_revision = "0012_goal_exceptions_thresholds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dashboard_widgets",
        sa.Column("forecast_algorithm", sa.String(length=40), nullable=True),
    )
    op.execute(
        """
        UPDATE dashboard_widgets
        SET forecast_algorithm = 'simple'
        WHERE widget_type = 'goal_progress'
        """
    )


def downgrade() -> None:
    op.drop_column("dashboard_widgets", "forecast_algorithm")
