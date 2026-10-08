"""Create user, role, authority, refresh and password reset tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_auth_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False), sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("email", name="uq_users_email"))
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table("roles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(64), nullable=False), sa.UniqueConstraint("name", name="uq_roles_name"))
    op.create_index("ix_roles_name", "roles", ["name"])
    op.create_table("authorities", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.UniqueConstraint("name", name="uq_authorities_name"))
    op.create_index("ix_authorities_name", "authorities", ["name"])
    op.create_table("user_roles", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("role_authorities", sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True), sa.Column("authority_id", sa.Integer(), sa.ForeignKey("authorities.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("refresh_tokens", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"))
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_index("ix_refresh_user_revoked", "refresh_tokens", ["user_id", "revoked_at"])
    op.create_table("password_resets", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("used_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("token_hash", name="uq_password_resets_token_hash"))
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])
    op.create_index("ix_password_resets_token_hash", "password_resets", ["token_hash"])
    op.create_index("ix_password_resets_expires_at", "password_resets", ["expires_at"])


def downgrade():
    op.drop_table("password_resets")
    op.drop_table("refresh_tokens")
    op.drop_table("role_authorities")
    op.drop_table("user_roles")
    op.drop_table("authorities")
    op.drop_table("roles")
    op.drop_table("users")
