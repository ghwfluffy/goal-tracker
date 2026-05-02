from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0028_add_optional_oauth_identity"
down_revision = "0027_add_mobile_widget_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("identity_provider", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("external_subject", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("central_avatar_url", sa.String(length=500), nullable=True))
    op.create_unique_constraint(
        "uq_users_identity_provider_external_subject",
        "users",
        ["identity_provider", "external_subject"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_identity_provider_external_subject", "users", type_="unique")
    op.drop_column("users", "central_avatar_url")
    op.drop_column("users", "external_subject")
    op.drop_column("users", "identity_provider")
