"""shorten mobile summary widgets more

Revision ID: 0018_mobile_summary_tight
Revises: 0017_mobile_summary_height
Create Date: 2026-04-12 12:10:00.000000
"""

from collections import defaultdict

from alembic import op
import sqlalchemy as sa

revision = "0018_mobile_summary_tight"
down_revision = "0017_mobile_summary_height"
branch_labels = None
depends_on = None

SUMMARY_WIDGET_TYPES = (
    "metric_summary",
    "days_since",
    "goal_summary",
    "goal_completion_percent",
    "goal_success_percent",
    "goal_failure_risk",
)


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE dashboard_widgets
            SET mobile_grid_h = 1
            WHERE widget_type IN :summary_widget_types
            """
        ).bindparams(sa.bindparam("summary_widget_types", expanding=True)),
        {"summary_widget_types": SUMMARY_WIDGET_TYPES},
    )

    rows = bind.execute(
        sa.text(
            """
            SELECT id, dashboard_id, mobile_grid_h, mobile_grid_y, display_order
            FROM dashboard_widgets
            ORDER BY dashboard_id ASC, mobile_grid_y ASC, display_order ASC
            """
        )
    ).mappings()

    next_y_by_dashboard: dict[str, int] = defaultdict(int)
    for row in rows:
        next_y = next_y_by_dashboard[row["dashboard_id"]]
        bind.execute(
            sa.text(
                """
                UPDATE dashboard_widgets
                SET mobile_grid_x = 0,
                    mobile_grid_y = :mobile_grid_y,
                    mobile_grid_w = 1
                WHERE id = :widget_id
                """
            ),
            {
                "mobile_grid_y": next_y,
                "widget_id": row["id"],
            },
        )
        next_y_by_dashboard[row["dashboard_id"]] = next_y + row["mobile_grid_h"]


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE dashboard_widgets
            SET mobile_grid_h = 2
            WHERE widget_type IN :summary_widget_types
            """
        ).bindparams(sa.bindparam("summary_widget_types", expanding=True)),
        {"summary_widget_types": SUMMARY_WIDGET_TYPES},
    )
