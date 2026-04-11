"""add number metrics

Revision ID: 0009_add_number_metrics
Revises: 0008_add_user_timezone
Create Date: 2026-04-11 16:40:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_add_number_metrics"
down_revision = "0008_add_user_timezone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("metrics", sa.Column("decimal_places", sa.Integer(), nullable=True))
    op.add_column(
        "metric_entries",
        sa.Column("number_value", sa.Numeric(precision=18, scale=6), nullable=True),
    )
    op.add_column(
        "goals",
        sa.Column("target_value_number", sa.Numeric(precision=18, scale=6), nullable=True),
    )

    op.execute("UPDATE metrics SET metric_type = 'number' WHERE metric_type = 'integer'")
    op.execute("UPDATE metrics SET decimal_places = 0 WHERE metric_type = 'number'")
    op.execute("UPDATE metric_entries SET number_value = integer_value WHERE integer_value IS NOT NULL")
    op.execute(
        "UPDATE goals SET target_value_number = target_value_integer "
        "WHERE target_value_integer IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("UPDATE metrics SET metric_type = 'integer' WHERE metric_type = 'number'")
    op.drop_column("goals", "target_value_number")
    op.drop_column("metric_entries", "number_value")
    op.drop_column("metrics", "decimal_places")
