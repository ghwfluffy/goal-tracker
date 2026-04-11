"""add dashboard widget layout

Revision ID: 0011_add_dashboard_widget_layout
Revises: 0010_add_metric_archiving
Create Date: 2026-04-11 21:40:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_add_dashboard_widget_layout"
down_revision = "0010_add_metric_archiving"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dashboard_widgets",
        sa.Column("grid_x", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("grid_y", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("grid_w", sa.Integer(), nullable=False, server_default=sa.text("6")),
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("grid_h", sa.Integer(), nullable=False, server_default=sa.text("4")),
    )

    bind = op.get_bind()
    widgets = list(
        bind.execute(
            sa.text(
                "SELECT id, display_order FROM dashboard_widgets ORDER BY display_order ASC, created_at ASC"
            )
        )
    )
    for index, widget in enumerate(widgets):
        grid_x = (index % 2) * 6
        grid_y = (index // 2) * 4
        bind.execute(
            sa.text(
                """
                UPDATE dashboard_widgets
                SET grid_x = :grid_x,
                    grid_y = :grid_y,
                    grid_w = 6,
                    grid_h = 4
                WHERE id = :id
                """
            ),
            {
                "id": widget.id,
                "grid_x": grid_x,
                "grid_y": grid_y,
            },
        )

    op.alter_column("dashboard_widgets", "grid_x", server_default=None)
    op.alter_column("dashboard_widgets", "grid_y", server_default=None)
    op.alter_column("dashboard_widgets", "grid_w", server_default=None)
    op.alter_column("dashboard_widgets", "grid_h", server_default=None)


def downgrade() -> None:
    op.drop_column("dashboard_widgets", "grid_h")
    op.drop_column("dashboard_widgets", "grid_w")
    op.drop_column("dashboard_widgets", "grid_y")
    op.drop_column("dashboard_widgets", "grid_x")
