"""add invitation codes

Revision ID: 0004_add_invitation_codes
Revises: 0003_add_user_profile_fields
Create Date: 2026-04-11 15:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_add_invitation_codes"
down_revision = "0003_add_user_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invitation_codes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.add_column("users", sa.Column("invitation_code_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_users_invitation_code_id_invitation_codes",
        "users",
        "invitation_codes",
        ["invitation_code_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_invitation_code_id_invitation_codes", "users", type_="foreignkey")
    op.drop_column("users", "invitation_code_id")
    op.drop_table("invitation_codes")
