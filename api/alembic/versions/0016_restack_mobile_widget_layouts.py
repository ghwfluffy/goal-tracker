"""restack mobile widget layouts

Revision ID: 0016_restack_mobile_widgets
Revises: 0015_mobile_widget_layouts
Create Date: 2026-04-12 11:20:00.000000
"""

from collections import defaultdict

from alembic import op
import sqlalchemy as sa

revision = "0016_restack_mobile_widgets"
down_revision = "0015_mobile_widget_layouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, dashboard_id, grid_y, grid_x, display_order, mobile_grid_h
            FROM dashboard_widgets
            ORDER BY dashboard_id ASC, grid_y ASC, grid_x ASC, display_order ASC
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
            SET mobile_grid_x = 0,
                mobile_grid_y = grid_y,
                mobile_grid_w = 1
            """
        )
    )
